# -*- mode: python ; coding: utf-8 -*-
# GUI (PySide6) bez konsoli. Tryb z env STC_PYI_MODE: onefile (domyślny) | onedir.
# Wymaga zbudowanego backendu: STC_BACKEND_DIR=<distpath>/stcgal-backend (backend.spec).
# onefile → <distpath>/STC-Programmer[.exe]   onedir → <distpath>/STC-Programmer/
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH)))
from common import APP_NAME, ICON, ROOT, version_info  # noqa: E402
from PyInstaller.utils.hooks import collect_submodules  # noqa: E402

MODE = os.environ.get("STC_PYI_MODE", "onefile")
BACKEND_DIR = Path(os.environ["STC_BACKEND_DIR"])
if not (BACKEND_DIR / ("stcgal-backend.exe" if sys.platform == "win32" else "stcgal-backend")).is_file():
    raise SystemExit(f"Brak zbudowanego backendu w {BACKEND_DIR} (uruchom backend.spec)")

datas = [
    (str(ROOT / "stcgal_gui" / "resources"), "stcgal_gui/resources"),
    (str(BACKEND_DIR), "backend"),   # onefile: _MEIPASS/backend/…; onedir: _internal/backend/…
]
a = Analysis(
    [str(ROOT / "packaging" / "pyinstaller" / "entry_gui.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=collect_submodules("serial") + collect_submodules("stcgal_gui"),
    excludes=["tkinter", "unittest", "pydoc", "PySide6.QtWebEngineCore", "PySide6.QtQml",
              "PySide6.QtQuick", "PySide6.QtPdf", "PySide6.QtDesigner", "PySide6.Qt3DCore"],
)
pyz = PYZ(a.pure)

if MODE == "onefile":
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name=APP_NAME,
              console=False, icon=ICON, version=version_info(), upx=False)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=APP_NAME,
              console=False, icon=ICON, version=version_info(), upx=False)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=APP_NAME)
