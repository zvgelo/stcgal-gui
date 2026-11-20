# -*- mode: python ; coding: utf-8 -*-
# Backend (stcgal 1.10) jako osobny program KONSOLOWY, tryb onedir.
# Wynik: <distpath>/stcgal-backend/{stcgal-backend[.exe], _internal/...}
# GUI zagnieżdża ten katalog jako dane (backend/) - patrz gui.spec.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH)))
from common import ICON, ROOT, version_info  # noqa: E402
from PyInstaller.utils.hooks import collect_submodules  # noqa: E402

a = Analysis(
    [str(ROOT / "packaging" / "pyinstaller" / "entry_backend.py")],
    pathex=[str(ROOT)],
    hiddenimports=(
        collect_submodules("stcgal") + collect_submodules("serial") + collect_submodules("usb")
        + ["tqdm", "stcgal_gui.backend_entry"]
    ),
    excludes=["tkinter", "unittest", "PySide6", "shiboken6"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="stcgal-backend",
          console=True, icon=ICON, version=version_info(), upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="stcgal-backend")
