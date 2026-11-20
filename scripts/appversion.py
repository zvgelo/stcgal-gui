"""Wypisuje wersję aplikacji (używane przez build-windows.ps1 dla Inno Setup)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stcgal_gui import __version__  # noqa: E402

print(__version__)
