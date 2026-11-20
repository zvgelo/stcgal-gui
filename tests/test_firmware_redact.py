from pathlib import Path

import pytest

from stcgal_gui.core.firmware import FirmwareError, check_fit, load_firmware, parse_ihex
from stcgal_gui.core.redact import redact
from stcgal_gui.models.data import McuInfo

MCU = McuInfo(model="STC8H8K64U", code_flash_kb=63.5, eeprom_kb=0.5)
HEX = ":0400000001020304F2\n:00000001FF\n"


def test_bin_ok(firmware_bin):
    fw = load_firmware(firmware_bin)
    assert fw.fmt == "bin" and fw.size == 1024


def test_empty_and_missing(tmp_path: Path):
    (tmp_path / "e.bin").write_bytes(b"")
    with pytest.raises(FirmwareError):
        load_firmware(tmp_path / "e.bin")
    with pytest.raises(FirmwareError):
        load_firmware(tmp_path / "none.bin")


def test_hex_ok(tmp_path: Path):
    p = tmp_path / "a.hex"
    p.write_text(HEX)
    fw = load_firmware(p)
    assert fw.fmt == "hex" and fw.size == 4
    assert parse_ihex(HEX) == bytes([1, 2, 3, 4])


@pytest.mark.parametrize(
    "text",
    [
        ":0400000001020304F3\n:00000001FF\n",
        ":0400000001020304F2\n",
        "garbage\n",
        ":0400000001020304F2\n:00000001FF\n:00\n",
    ],
)
def test_hex_invalid(tmp_path: Path, text):
    p = tmp_path / "a.hex"
    p.write_text(text)
    with pytest.raises(FirmwareError):
        load_firmware(p)


def test_hex_content_in_bin_extension_rejected(tmp_path: Path):
    p = tmp_path / "a.bin"
    p.write_text(HEX)
    with pytest.raises(FirmwareError, match="Intel HEX"):
        load_firmware(p)


def test_unknown_extension_rejected(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_text(HEX)
    with pytest.raises(FirmwareError, match="rozszerzenie"):
        load_firmware(p)


def test_fit_checks(tmp_path: Path):
    def fw(size):
        p = tmp_path / f"{size}.bin"
        p.write_bytes(b"\x01" * size)
        return load_firmware(p)

    assert check_fit(fw(1000), MCU) == ([], [])
    errs, warns = check_fit(fw(65200), MCU)
    assert not errs and warns  # wchodzi w EEPROM
    errs, _ = check_fit(fw(70000), MCU)
    assert errs
    errs, _ = check_fit(fw(70000), MCU, options=["program_eeprom_split=65536"])
    assert errs
    errs, warns = check_fit(fw(1000), None)
    assert not errs and warns  # brak danych o MCU → ostrzeżenie, nie zgadywanie


def test_redact(monkeypatch):
    monkeypatch.setenv("HOME", "/home/tester")
    monkeypatch.setenv("USERPROFILE", "/home/tester")  # Windows: expanduser używa USERPROFILE
    out = redact("open /home/tester/fw.bin usb-1a86_USB_Serial_ABCDEF123-if00 SER9999", ["SER9999"])
    assert "/home/tester" not in out and "~/fw.bin" in out
    assert "ABCDEF123" not in out and "SER9999" not in out
