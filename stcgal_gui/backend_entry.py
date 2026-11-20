"""Samodzielny punkt wejścia backendu: ``stcgal-backend`` = dokładnie ``stcgal`` 1.10.

W pakiecie Windows jest budowany jako osobny program konsolowy (uruchamiany przez GUI bez
okna). Argumenty, wyjście i kody wyjścia są identyczne jak w ``stcgal`` - GUI nie zna różnicy.

Dodatki wyłącznie dla trybu osadzonego:
* wyjście stdout/stderr w UTF-8 i bez buforowania (GUI czyta postęp na żywo);
* łagodne anulowanie: gdy ustawiono ``STCGAL_GUI_CANCEL_STDIN=1``, wątek czyta stdin; linia
  ``cancel`` lub EOF zgłaszają ``KeyboardInterrupt`` w głównym wątku, więc stcgal rozłącza się
  z MCU tak jak po Ctrl+C. (Windows: aplikacja GUI nie ma konsoli, więc ``CTRL_BREAK`` odpada.)
* ``--backend-info`` wypisuje wersję i moduły (diagnostyka); nie istnieje w stcgal.
"""

from __future__ import annotations

import _thread
import os
import sys
import threading

CANCEL_ENV = "STCGAL_GUI_CANCEL_STDIN"
_DONE = threading.Event()  # główny wątek zakończył pracę - nie wolno już przerywać


def _configure_streams() -> None:
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def _watch_stdin() -> None:
    """Czeka na polecenie ``cancel`` (lub zamknięcie stdin) i przerywa główny wątek."""
    try:
        for line in sys.stdin:
            if line.strip().lower() == "cancel":
                break
    except (OSError, ValueError):
        pass
    if not _DONE.is_set():
        _thread.interrupt_main()


def backend_info() -> str:
    import serial
    import stcgal

    return (
        f"stcgal {stcgal.__version__}\npyserial {serial.VERSION}\npython {sys.version.split()[0]}"
    )


def main(argv: list[str] | None = None) -> int:
    _configure_streams()
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if args == ["--backend-info"]:
            print(backend_info())
            return 0
        from stcgal.frontend import cli

        # watcher dopiero po imporcie: ``cancel`` w trakcie importu nie powinien dawać tracebacku
        if os.environ.get(CANCEL_ENV) == "1" and sys.stdin is not None:
            threading.Thread(target=_watch_stdin, daemon=True, name="cancel-watch").start()
        sys.argv = ["stcgal", *args]
        return int(cli() or 0)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 2
    finally:
        _DONE.set()


if __name__ == "__main__":
    raise SystemExit(main())
