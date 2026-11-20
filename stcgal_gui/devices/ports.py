"""Enumeracja portów szeregowych i rozpoznawanie adapterów USB-UART."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from stcgal_gui import platform_support as ps
from stcgal_gui.models.data import PortInfo

# Znane układy USB-UART (VID, PID). Wykrycie adaptera NIE oznacza wykrycia MCU.
KNOWN_ADAPTERS: dict[tuple[int, int], str] = {
    (0x1A86, 0x7523): "CH340",
    (0x1A86, 0x7522): "CH340K",
    (0x1A86, 0x5523): "CH341",
    (0x1A86, 0x55D4): "CH9102",
    (0x10C4, 0xEA60): "CP210x",
    (0x0403, 0x6001): "FTDI FT232",
    (0x067B, 0x2303): "PL2303",
}

BY_ID_DIR = Path("/dev/serial/by-id")


def is_ch340(vid: int | None, pid: int | None) -> bool:
    """Czy VID:PID należy do rodziny CH340/CH341."""
    return vid == 0x1A86 and pid in (0x7523, 0x7522, 0x5523)


def adapter_name(vid: int | None, pid: int | None) -> str:
    """Nazwa znanego adaptera lub pusty napis."""
    if vid is None or pid is None:
        return ""
    return KNOWN_ADAPTERS.get((vid, pid), "")


def by_id_map(directory: Path = BY_ID_DIR) -> dict[str, str]:
    """Mapuje realną ścieżkę urządzenia (/dev/ttyUSB0) na stabilny link w by-id (tylko Linux)."""
    result: dict[str, str] = {}
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return result
    for entry in entries:
        try:
            result.setdefault(os.path.realpath(entry), str(entry))
        except OSError:
            continue
    return result


def _default_comports() -> Iterable[Any]:
    from serial.tools import list_ports

    try:
        return list(list_ports.comports())
    except Exception:  # noqa: BLE001 - dziwne sterowniki/Wine: lista pusta zamiast awarii GUI
        logging.getLogger(__name__).exception("Enumeracja portów nie powiodła się")
        return []


def _clean(value: object) -> str:
    """Tekst bez wartości zastępczych pyserial („n/a”, None)."""
    text = str(value or "").strip()
    return "" if text.lower() == "n/a" else text


def enumerate_ports(
    comports: Callable[[], Iterable[Any]] = _default_comports,
    by_id_dir: Path = BY_ID_DIR,
    access: Callable[[str], bool] | None = None,
    include_builtin: bool = False,
    windows: bool | None = None,
) -> list[PortInfo]:
    """Zwraca listę portów (Linux: /dev/tty*, Windows: COMn). Parametry ułatwiają testy bez sprzętu.

    Domyślnie pomija porty bez adaptera USB (Linux: ``/dev/ttyS*``; Windows: wbudowane COM
    i Bluetooth); ``include_builtin=True`` je pokazuje.
    """
    check = access or (lambda p: ps.port_access_check(p, windows))
    by_id = by_id_map(by_id_dir) if ps.supports_by_id(windows) else {}
    ports: list[PortInfo] = []
    for p in comports():
        device = str(p.device)
        vid = getattr(p, "vid", None)
        pid = getattr(p, "pid", None)
        if not include_builtin and ps.is_builtin_port(device, vid, windows):
            continue
        desc = _clean(getattr(p, "description", ""))
        if not desc:
            desc = adapter_name(vid, pid) or device
        ports.append(
            PortInfo(
                device=device,
                description=desc,
                vid=vid,
                pid=pid,
                manufacturer=_clean(getattr(p, "manufacturer", "")),
                serial_number=_clean(getattr(p, "serial_number", "")),
                by_id=by_id.get(os.path.realpath(device)) if by_id else None,
                location=_clean(getattr(p, "location", "")),
                is_ch340=is_ch340(vid, pid),
                accessible=check(device),
            )
        )
    # USB-UART najpierw, potem naturalnie wg numeru (COM2 < COM10)
    ports.sort(key=lambda x: (x.vid is None, _natural_key(x.device)))
    return ports


def _natural_key(device: str) -> list[object]:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", device)]
