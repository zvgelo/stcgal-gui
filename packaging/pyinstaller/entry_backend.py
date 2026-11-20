"""Punkt wejścia backendu (stcgal) dla PyInstaller: program konsolowy ``stcgal-backend``."""

import multiprocessing

from stcgal_gui.backend_entry import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
