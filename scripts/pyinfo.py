"""Wypisuje „MAJOR.MINOR.PATCH BITY” interpretera (używane przez build-windows.ps1; bez cytowania w -c)."""

import struct
import sys

major, minor, micro = sys.version_info[:3]
print(f"{major}.{minor}.{micro} {struct.calcsize('P') * 8}")
