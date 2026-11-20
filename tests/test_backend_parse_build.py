from pathlib import Path

import pytest

from stcgal_gui.backends.stcgal import (
    build_identify_command,
    build_program_command,
    classify_error,
    parse_mcu_info,
    parse_progress,
)
from stcgal_gui.models.data import ConnectionParams, ErrorKind, ProgramParams, WriteScope
from tests.conftest import SAMPLE_OUTPUT


def test_parse_sample():
    m = parse_mcu_info(SAMPLE_OUTPUT)
    assert m.protocol == "stc8d"
    assert m.model == "STC8H8K64U" and m.magic == "F784"
    assert m.code_flash_kb == 63.5 and m.eeprom_kb == 0.5
    assert m.code_bytes == 65024 and m.eeprom_bytes == 512
    assert m.frequency_mhz == 24.0 and m.bsl_version == "7.4.4U"
    assert m.wakeup_khz == 32.768 and m.ref_voltage_mv == 1190 and m.mfg_date == "2023-05-01"
    assert m.options == {"reset_pin_enabled": "False", "program_eeprom_split": "65024"}


def test_parse_missing_fields_stay_none():
    m = parse_mcu_info("Waiting for MCU, please cycle power: ")
    assert m.is_empty and m.frequency_mhz is None and m.bsl_version is None


def test_parse_unknown_target_lines_go_to_extra():
    m = parse_mcu_info("Target frequency: 11.059 MHz\nTarget UID: 0102\n")
    assert m.frequency_mhz == 11.059 and m.extra == {"UID": "0102"}


def test_parse_progress_takes_last_tqdm_state():
    text = "\rWriting flash:   0%|          | 0/65024 [00:00<?]\rWriting flash:  50%|#####     | 32512/65024 [00:03<00:03]"
    p = parse_progress(text)
    assert p is not None and (p.done, p.total) == (32512, 65024) and round(p.percent) == 50
    assert parse_progress("Erasing flash: done") is None


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("Serial port error: [Errno 13] Permission denied: '/dev/ttyUSB0'", ErrorKind.PERMISSION),
        (
            "could not exclusively lock port /dev/ttyUSB0: [Errno 11]\nDevice or resource busy",
            ErrorKind.PORT_BUSY,
        ),
        (
            "[Errno 2] could not open port /dev/ttyUSB0: No such file or directory",
            ErrorKind.PORT_MISSING,
        ),
        ("Protocol error: cannot detect protocol", ErrorKind.HANDSHAKE),
        ("Protocol error: incorrect magic in status packet", ErrorKind.PROTOCOL),
        ("Option error: foo", ErrorKind.OPTION),
        ("coś dziwnego", ErrorKind.UNKNOWN),
    ],
)
def test_classify_error(text, kind):
    assert classify_error(text)[0] is kind


def test_identify_command_is_non_destructive():
    argv = build_identify_command("stcgal", ConnectionParams(port="/dev/ttyUSB0", protocol="auto"))
    assert argv == ["stcgal", "-p", "/dev/ttyUSB0", "-P", "auto", "-b", "115200", "-l", "2400"]
    for bad in ("-e", "--erase", "-o", "--option", "-t"):
        assert bad not in argv
    assert not any(a.endswith((".bin", ".hex")) for a in argv)


def test_identify_with_debug_and_autoreset():
    argv = build_identify_command(
        "stcgal",
        ConnectionParams(port="/dev/ttyUSB0", protocol="stc8d", debug=True, autoreset=True),
    )
    assert "-D" in argv and "-a" in argv and argv[argv.index("-A") + 1] == "dtr"
    assert "-e" not in argv


def test_program_command(tmp_path: Path):
    fw, ee = tmp_path / "a.bin", tmp_path / "e.hex"
    fw.touch()
    ee.touch()
    argv = build_program_command(
        "stcgal",
        ConnectionParams(port="/dev/ttyUSB0", protocol="stc8d"),
        ProgramParams(fw, ee, trim_khz=24000, options=["program_eeprom_split=64000"]),
        WriteScope.FLASH_AND_EEPROM,
        expert=True,  # -o i -t tylko w trybie eksperta
    )
    assert argv[-2:] == [str(fw), str(ee)]
    assert argv[argv.index("-o") + 1] == "program_eeprom_split=64000"
    assert argv[argv.index("-t") + 1] == "24000"
    assert "-e" not in argv and "--erase" not in argv


@pytest.mark.parametrize("opt", ["rm -rf /", "a=b;c", "x= y", "--erase", "-e"])
def test_program_rejects_bad_options(tmp_path: Path, opt):
    fw = tmp_path / "a.bin"
    fw.touch()
    with pytest.raises(ValueError):
        build_program_command(
            "stcgal", ConnectionParams(port="/dev/x"), ProgramParams(fw, options=[opt])
        )


def test_bad_protocol_or_port_rejected():
    with pytest.raises(ValueError):
        build_identify_command("stcgal", ConnectionParams(port="/dev/x", protocol="evil; ls"))
    with pytest.raises(ValueError):
        build_identify_command("stcgal", ConnectionParams(port=""))
