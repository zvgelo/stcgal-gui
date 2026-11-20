import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from stcgal_gui.devices.mcu_db import expected_protocol, protocol_warning
from stcgal_gui.devices.ports import enumerate_ports, is_ch340


def fake_port(device, vid=None, pid=None, desc="n/a"):
    return SimpleNamespace(
        device=device,
        vid=vid,
        pid=pid,
        description=desc,
        manufacturer="QinHeng",
        serial_number="ABC123456",
    )


@pytest.mark.skipif(sys.platform == "win32", reason="by-id i symlinki - tylko Linux")
def test_enumerates_ch340_with_by_id(tmp_path: Path):
    by_id = tmp_path / "by-id"
    by_id.mkdir()
    dev = tmp_path / "ttyUSB0"
    dev.touch()
    (by_id / "usb-1a86_USB_Serial-if00-port0").symlink_to(dev)
    ports = enumerate_ports(
        lambda: [fake_port(str(dev), 0x1A86, 0x7523, "USB Serial")], by_id, access=lambda _p: True
    )
    assert len(ports) == 1
    p = ports[0]
    assert p.is_ch340 and p.vid_pid == "1a86:7523"
    assert p.by_id is not None and p.by_id.endswith("usb-1a86_USB_Serial-if00-port0")
    assert p.accessible


def test_inaccessible_port_flagged(tmp_path: Path):
    ports = enumerate_ports(
        lambda: [fake_port("/dev/ttyUSB0", 0x1A86, 0x7523)], tmp_path, access=lambda _p: False
    )
    assert not ports[0].accessible
    assert ports[0].description == "CH340"  # opis zastępczy dla "n/a"


def test_builtin_ttys_hidden_unless_requested(tmp_path: Path):
    src = lambda: [fake_port("/dev/ttyS0"), fake_port("/dev/ttyUSB0", 0x10C4, 0xEA60)]  # noqa: E731
    assert [p.device for p in enumerate_ports(src, tmp_path, lambda _p: True)] == ["/dev/ttyUSB0"]
    assert len(enumerate_ports(src, tmp_path, lambda _p: True, include_builtin=True)) == 2


def test_no_ports(tmp_path: Path):
    assert enumerate_ports(lambda: [], tmp_path) == []


def test_is_ch340():
    assert is_ch340(0x1A86, 0x7523)
    assert not is_ch340(0x10C4, 0xEA60)
    assert not is_ch340(None, None)


def test_stc8h_uses_stc8d_not_stc8g():
    assert expected_protocol("STC8H8K64U") == "stc8d"
    assert expected_protocol("STC8H1K08") == "stc8g"
    assert expected_protocol("STC8G1K08") == "stc8g"
    assert protocol_warning("STC8H8K64U", "stc8g") is not None
    assert protocol_warning("STC8H8K64U", "stc8d") is None
    assert protocol_warning("STC8H8K64U", "auto") is None
    assert protocol_warning(None, "stc8g") is None
