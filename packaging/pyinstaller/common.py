"""Wspólne elementy specyfikacji PyInstaller (backend i GUI)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from stcgal_gui import __version__  # noqa: E402

IS_WIN = sys.platform == "win32"
ICON = str(ROOT / "packaging" / "windows" / "stcgal-gui.ico") if IS_WIN else None
APP_NAME = "STC-Programmer"


def version_info():
    """Zasób wersji exe (Windows) - metadane widoczne we Właściwościach pliku."""
    if not IS_WIN:
        return None
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo,
        StringFileInfo,
        StringStruct,
        StringTable,
        VarFileInfo,
        VarStruct,
        VSVersionInfo,
    )

    nums = tuple((list(map(int, __version__.split("."))) + [0, 0, 0, 0])[:4])
    return VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=nums,
            prodvers=nums,
            mask=0x3F,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
        ),
        kids=[
            StringFileInfo(
                [
                    StringTable(
                        "040904B0",
                        [
                            StringStruct("CompanyName", "stcgal-gui"),
                            StringStruct("FileDescription", "STC Programmer GUI"),
                            StringStruct("FileVersion", __version__),
                            StringStruct("InternalName", APP_NAME),
                            StringStruct("OriginalFilename", APP_NAME + ".exe"),
                            StringStruct("ProductName", "STC Programmer GUI"),
                            StringStruct("ProductVersion", __version__),
                        ],
                    )
                ]
            ),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )
