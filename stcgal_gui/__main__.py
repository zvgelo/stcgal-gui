"""Punkt wejścia: ``python -m stcgal_gui`` / ``stcgal-gui``."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from stcgal_gui import __version__
from stcgal_gui import platform_support as ps
from stcgal_gui.backends.base import Backend
from stcgal_gui.backends.mock import MockBackend
from stcgal_gui.backends.stcgal import StcgalBackend
from stcgal_gui.core.controller import OperationController
from stcgal_gui.core.i18n import install_translators
from stcgal_gui.core.settings import SettingsStore
from stcgal_gui.gui.context import AppContext
from stcgal_gui.gui.main_window import MainWindow


def build_window(backend: Backend | None = None, store: SettingsStore | None = None) -> MainWindow:
    """Składa aplikację; ``backend``/``store`` wstrzykiwane w testach."""
    store = store or SettingsStore()
    settings = store.load()
    backend = backend or StcgalBackend(settings.stcgal_path)
    ctx = AppContext(OperationController(backend), store, settings)
    return MainWindow(ctx)


def _ensure_std_streams() -> None:
    """Okienkowy exe (PyInstaller --windowed) ma ``sys.stdout``/``stderr`` równe ``None``."""

    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115


def _setup_logging() -> None:
    fmt = "%(asctime)s %(name)s %(levelname)s %(message)s"
    handlers: list[logging.Handler] = []
    if ps.is_frozen() and ps.IS_WINDOWS:  # brak konsoli - log do pliku w profilu użytkownika
        from PySide6.QtCore import QStandardPaths

        base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        try:
            d = Path(base or ".") / "stcgal-gui"
            d.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(d / "app.log", encoding="utf-8"))
        except OSError:
            pass
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers or None)


def selftest(report_path: str | None = None) -> int:
    """Kontrola poprawności pakietu bez uruchamiania okna: zasoby, Qt, backend, porty.

    Używane przez CI i po instalacji (``stc-programmer.exe --selftest``). Zwraca 0 tylko
    wtedy, gdy wszystko działa; nie komunikuje się z MCU i niczego nie zapisuje.
    """
    import json

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    report: dict[str, object] = {"version": __version__, "frozen": ps.is_frozen()}
    problems: list[str] = []
    res = ps.resource_dir()
    report["resource_dir"] = str(res)
    if not (res / "stcgal-gui.svg").is_file():
        problems.append("brak zasobu stcgal-gui.svg")
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.instance() is None:
        QApplication([sys.argv[0]])
    report["qt_platform"] = QGuiApplication.platformName()
    try:
        from PySide6.QtGui import QIcon

        if QIcon(str(res / "stcgal-gui.svg")).isNull():
            problems.append("Qt nie wczytał ikony SVG (brak wtyczki obrazów?)")
    except Exception as ex:  # noqa: BLE001
        problems.append(f"ikona: {ex}")
    backend = StcgalBackend()
    exe = backend.executable()
    report["backend"] = exe
    if not exe:
        problems.append("nie znaleziono backendu stcgal")
    else:
        ver = backend.version()
        report["backend_version"] = ver
        if not ver or "stcgal" not in ver.lower():
            problems.append(f"backend nie zwrócił wersji: {ver!r}")
    try:
        from stcgal_gui.devices.ports import enumerate_ports

        report["ports"] = [p.device for p in enumerate_ports()]
    except Exception as ex:  # noqa: BLE001
        problems.append(f"enumeracja portów: {ex}")
    report["problems"] = problems
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if report_path:  # okienkowy exe (Windows) nie ma stdout - raport trafia do pliku
        Path(report_path).write_text(text, encoding="utf-8")
    print(text)
    return 1 if problems else 0


def smoke_gui(out_dir: str) -> int:
    """Test dymny GUI bez sprzętu: pełne okno + symulowane wykrywanie + zrzut ekranu.

    Zapisuje ``smoke.json`` i ``smoke.png`` w ``out_dir``. Kod 0 = okno wystartowało, symulowany
    backend zidentyfikował MCU, stan połączenia = „wykryty”. Nie dotyka portów ani prawdziwego
    backendu; ustawienia idą do pliku tymczasowego (nie do rejestru/profilu użytkownika).
    """
    import json

    from PySide6.QtCore import QSettings, QTimer

    from stcgal_gui.core.linkstate import LinkState
    from stcgal_gui.models.data import ConnectionParams

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication([sys.argv[0]])
    app.setApplicationName("stcgal-gui-smoke")
    store = SettingsStore(QSettings(str(out / "smoke.ini"), QSettings.Format.IniFormat))
    install_translators(app, store.load().language)
    window = build_window(MockBackend(wait_s=0.3), store)
    window.show()
    result: dict[str, object] = {"platform": QApplication.platformName(), "ok": False}

    def finish(code: int) -> None:
        result["exit"] = code
        (out / "smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
        app.exit(code)

    def check() -> None:
        ctx = window.ctx
        result["link"] = ctx.link.value
        result["model"] = ctx.mcu.model if ctx.mcu else None
        result["grabbed"] = window.grab().save(str(out / "smoke.png"))
        ok = ctx.link is LinkState.MCU_DETECTED and result["model"] == "STC8H8K64U"
        result["ok"] = bool(ok and result["grabbed"])
        finish(0 if result["ok"] else 1)

    ctx = window.ctx
    ctx.controller.finished.connect(lambda _r: QTimer.singleShot(300, check))
    QTimer.singleShot(
        500, lambda: ctx.controller.start_identify(ConnectionParams(port="SMOKE", protocol="stc8d"))
    )
    QTimer.singleShot(60000, lambda: finish(3))  # zabezpieczenie przed zawieszeniem
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stcgal-gui")
    parser.add_argument("--mock", action="store_true", help="symulowany backend (bez sprzętu)")
    parser.add_argument("--version", action="store_true")
    parser.add_argument(
        "--lang", choices=("pl", "en"), help="język interfejsu (nadpisuje ustawienie)"
    )
    parser.add_argument(
        "--selftest", action="store_true", help="szybka kontrola pakietu (zasoby, Qt, backend)"
    )
    parser.add_argument("--report", metavar="PLIK", help="zapisz raport --selftest do pliku (JSON)")
    parser.add_argument(
        "--smoke-gui", metavar="KATALOG", help="test dymny GUI z symulowanym backendem (PNG+JSON)"
    )
    _ensure_std_streams()
    args, qt_args = parser.parse_known_args(argv if argv is not None else sys.argv[1:])
    if args.version:
        print(f"stcgal-gui {__version__}")
        return 0
    if args.selftest:
        return selftest(args.report)
    if args.smoke_gui:
        return smoke_gui(args.smoke_gui)
    ps.init_process()
    _setup_logging()
    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("stcgal-gui")
    app.setOrganizationName("stcgal-gui")
    app.setDesktopFileName("stcgal-gui")
    install_translators(app, args.lang or SettingsStore().load().language)
    backend = MockBackend(guarantees=False) if args.mock else None  # symulacja tylko jawnym --mock
    window = build_window(backend)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
