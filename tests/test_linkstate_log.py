from datetime import datetime

from stcgal_gui.backends.mock import DEMO_MCU
from stcgal_gui.core import linkstate
from stcgal_gui.core.linkstate import DESCRIPTIONS, LinkState
from stcgal_gui.core.logmodel import LogAssembler, classify
from stcgal_gui.core.mcu_report import build_report, grouped_options
from stcgal_gui.models.data import ErrorKind, OperationKind, OperationResult, OperationState


def res(state, kind=OperationKind.IDENTIFY, err=ErrorKind.NONE):
    return OperationResult(kind, state, error_kind=err)


def test_link_from_operation():
    f = linkstate.from_operation
    assert f(OperationState.WAITING_FOR_MCU, OperationKind.IDENTIFY) is LinkState.WAITING_MCU
    assert f(OperationState.RUNNING, OperationKind.IDENTIFY) is LinkState.IDENTIFYING
    assert f(OperationState.RUNNING, OperationKind.PROGRAM) is LinkState.PROGRAMMING
    assert f(OperationState.IDLE, None) is None


def test_link_from_result():
    f = linkstate.from_result
    assert f(res(OperationState.FINISHED), True) is LinkState.MCU_DETECTED
    assert f(res(OperationState.TIMEOUT), False) is LinkState.TIMEOUT
    assert f(res(OperationState.FAILED, err=ErrorKind.PERMISSION), False) is LinkState.ERROR
    assert f(res(OperationState.FAILED, err=ErrorKind.PORT_MISSING), False) is LinkState.NO_ADAPTER
    assert f(res(OperationState.CANCELLED), False) is LinkState.ADAPTER_READY


def test_every_state_has_glyph_and_text():
    for s in LinkState:
        glyph, text = DESCRIPTIONS[s]
        assert glyph and text  # status nie polega wyłącznie na kolorze


def test_classify_levels():
    assert classify("stderr", "Serial port error: x") == "ERROR"
    assert classify("stderr", "WARNING: code_image truncated!") == "WARNING"
    assert classify("stderr", "<- Packet data: 46 B9") == "DEBUG"
    assert classify("stderr", "Writing flash:  50%|#####| 1/2") == "INFO"
    assert classify("stdout", "Target model:") == "INFO"


def test_assembler_collapses_progress_and_flushes_partial():
    a = LogAssembler()
    assert a.feed("stdout", "Waiting for MCU: ") == []
    out = a.flush(datetime(2026, 1, 1))
    assert [e.text for e in out] == ["Waiting for MCU:"]
    got = a.feed("stderr", "\rW 10%|#| 1/9\rW 100%|##| 9/9\nnext\n")
    assert [e.text for e in got] == ["W 100%|##| 9/9", "next"]


def test_grouped_options_and_report_sources():
    groups = grouped_options(DEMO_MCU)
    assert "Reset i zasilanie" in groups and "Bootloader i EEPROM" in groups
    desc, name, value = groups["Reset i zasilanie"][0]
    assert name == "reset_pin_enabled" and value == "False" and desc
    rep = build_report(DEMO_MCU, "/dev/ttyUSB0")
    assert "baza modeli stcgal" in rep and "odpowiedź bootloadera" in rep
    assert "`reset_pin_enabled`" in rep and "0xF784" in rep


def test_crlf_lines_are_not_lost():
    a = LogAssembler()
    assert [e.text for e in a.feed("stdout", "Connecting...\r\n")] == ["Connecting..."]
