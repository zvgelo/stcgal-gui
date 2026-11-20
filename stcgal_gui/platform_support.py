"""Jedyne miejsce z logiką zależną od systemu (Linux / Windows).

Reszta kodu pyta ten moduł, zamiast sprawdzać ``sys.platform``. Funkcje przyjmują opcjonalny
parametr ``windows``, dzięki czemu gałęzie Windows da się testować na Linuksie.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
BACKEND_BASENAME = "stcgal-backend"
APP_USER_MODEL_ID = "stcgal-gui.StcProgrammerGUI"


def _win(windows: bool | None) -> bool:
    return IS_WINDOWS if windows is None else windows


def is_frozen() -> bool:
    """Czy działamy ze spakowanego (PyInstaller) pakietu."""
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Katalog aplikacji: obok exe po spakowaniu, w przeciwnym razie katalog pakietu."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir() -> Path:
    """Katalog zasobów (ikony, tłumaczenia) - działa w trybie deweloperskim i po spakowaniu."""
    meipass = getattr(sys, "_MEIPASS", None)
    if is_frozen() and meipass:
        return Path(meipass) / "stcgal_gui" / "resources"
    return Path(__file__).resolve().parent / "resources"


def backend_filename(windows: bool | None = None) -> str:
    return BACKEND_BASENAME + (".exe" if _win(windows) else "")


def bundle_roots() -> list[Path]:
    """Katalogi, w których może leżeć dołączony backend.

    * onefile: katalog rozpakowania PyInstaller (``sys._MEIPASS``) - backend w ``backend/``;
    * onedir: obok exe oraz w ``_internal`` (=``_MEIPASS``);
    * tryb deweloperski: katalog pakietu.
    """
    roots: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    roots.append(app_dir())
    return roots


def bundled_backend(windows: bool | None = None, base: Path | None = None) -> Path | None:
    """Ścieżka do backendu dołączonego do aplikacji, jeśli istnieje."""
    name = backend_filename(windows)
    for root in [base] if base is not None else bundle_roots():
        for cand in (root / "backend" / name, root / name):
            if cand.is_file():
                return cand
    return None


def normalize_port(name: str, windows: bool | None = None) -> str:
    """Postać porównywalna nazwy portu.

    Linux: ``realpath`` (rozwija linki z ``/dev/serial/by-id``). Windows: wielkie litery bez
    prefiksu ``\\\\.\\`` (``com10`` → ``COM10``); ``realpath`` byłby błędny dla nazw COM.
    """
    if not name:
        return name
    if _win(windows):
        n = name.strip()
        if n.startswith("\\\\.\\"):
            n = n[4:]
        return n.upper()
    return os.path.realpath(name)


def is_builtin_port(device: str, vid: int | None, windows: bool | None = None) -> bool:
    """Porty bez adaptera USB (ttyS* / wbudowane COM, Bluetooth) - domyślnie ukrywane."""
    if _win(windows):
        return vid is None
    return vid is None and device.startswith("/dev/ttyS")


def supports_by_id(windows: bool | None = None) -> bool:
    """Stabilne ścieżki ``/dev/serial/by-id`` istnieją tylko w Linuksie."""
    return not _win(windows)


def port_access_check(device: str, windows: bool | None = None) -> bool:
    """Czy proces ma prawo do portu. Windows nie udostępnia taniego testu - zakładamy „tak”;
    brak dostępu ujawni się przy otwarciu portu (rozpoznawane w diagnostyce)."""
    if _win(windows):
        return True
    return os.access(device, os.R_OK | os.W_OK)


def example_port(windows: bool | None = None) -> str:
    return "COM3" if _win(windows) else "/dev/ttyUSB0"


def init_process(windows: bool | None = None) -> None:
    """Inicjalizacja specyficzna dla systemu (identyfikator aplikacji dla paska zadań Windows)."""
    if _win(windows):
        try:
            import ctypes

            windll = getattr(ctypes, "windll")  # noqa: B009 - tylko Windows
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except (AttributeError, OSError):
            pass
