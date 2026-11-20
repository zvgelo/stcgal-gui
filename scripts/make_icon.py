"""Generuje ikonę Windows (ICO z osadzonymi PNG) z SVG aplikacji. Wymaga PySide6 (QtSvg).

Użycie: python scripts/make_icon.py   → packaging/windows/stcgal-gui.ico
"""

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> int:
    app = QGuiApplication(sys.argv)
    renderer = QSvgRenderer(str(ROOT / "stcgal_gui" / "resources" / "stcgal-gui.svg"))
    if not renderer.isValid():
        print("Nieprawidłowy SVG", file=sys.stderr)
        return 1
    pngs: list[bytes] = []
    for size in SIZES:
        img = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(0)
        p = QPainter(img)
        renderer.render(p)
        p.end()
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        pngs.append(bytes(QByteArray(buf.data())))
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries = b""
    for size, data in zip(SIZES, pngs, strict=True):
        w = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    lin = ROOT / "packaging" / "linux"
    lin.mkdir(parents=True, exist_ok=True)
    (lin / "stc-programmer.png").write_bytes(pngs[SIZES.index(256)])
    out = ROOT / "packaging" / "windows" / "stcgal-gui.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(header + entries + b"".join(pngs))
    print(f"zapisano {out} ({out.stat().st_size} B)")
    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
