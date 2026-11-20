import json
import sys
import threading
import time
from pathlib import Path

import pytest

from stcgal_gui.backends.base import Callbacks, SafetyError, WriteConfirmation
from stcgal_gui.backends.stcgal import StcgalBackend
from stcgal_gui.models.data import (
    ConnectionParams,
    ErrorKind,
    OperationState,
    ProgramParams,
    Progress,
)
from tests.conftest import risk_acknowledged


def conn(**kw):
    return ConnectionParams(
        port="/dev/ttyUSB0", protocol="stc8d", timeout_s=kw.pop("timeout_s", 5), **kw
    )


def collect():
    log, states, progress = [], [], []
    return (
        log,
        states,
        progress,
        Callbacks(
            on_log=lambda s, t: log.append((s, t)),
            on_state=states.append,
            on_progress=progress.append,
        ),
    )


def test_identify_success_parses_and_signals_waiting(fake_backend, argv_log):
    log, states, _p, cb = collect()
    res = fake_backend.identify(conn(), cb, threading.Event())
    assert res.ok and res.mcu and res.mcu.model == "STC8H8K64U"
    assert OperationState.WAITING_FOR_MCU in states
    assert any(s == "stdout" and "Target model" in t for s, t in log)
    assert res.verified is False and res.programmed is False


def test_identify_never_passes_destructive_args(fake_backend, argv_log):
    fake_backend.identify(conn(), collect()[3], threading.Event())
    argv = json.loads(argv_log.read_text().splitlines()[-1])
    for bad in ("-e", "--erase", "-o", "-t"):
        assert bad not in argv
    assert not any(a.endswith((".bin", ".hex")) for a in argv)


def test_stderr_and_exit_code_permission(fake_backend, monkeypatch):
    monkeypatch.setenv("FAKE_STCGAL_SCENARIO", "permission")
    log, _s, _p, cb = collect()
    res = fake_backend.identify(conn(), cb, threading.Event())
    assert res.state is OperationState.FAILED and res.error_kind is ErrorKind.PERMISSION
    assert ("dialout" in res.message) or sys.platform == "win32"  # komunikat zależy od systemu
    assert any(s == "stderr" and "Permission denied" in t for s, t in log)


@pytest.mark.parametrize(
    ("scenario", "kind"),
    [
        ("busy", ErrorKind.PORT_BUSY),
        ("missing", ErrorKind.PORT_MISSING),
        ("handshake_fail", ErrorKind.PROTOCOL),
    ],
)
def test_error_scenarios(fake_backend, monkeypatch, scenario, kind):
    monkeypatch.setenv("FAKE_STCGAL_SCENARIO", scenario)
    res = fake_backend.identify(conn(), collect()[3], threading.Event())
    assert not res.ok and res.error_kind is kind


def test_timeout_while_waiting_for_power_cycle(fake_backend, monkeypatch):
    monkeypatch.setenv("FAKE_STCGAL_SCENARIO", "hang")
    t0 = time.monotonic()
    res = fake_backend.identify(conn(timeout_s=1), collect()[3], threading.Event())
    assert res.state is OperationState.TIMEOUT and res.error_kind is ErrorKind.TIMEOUT
    assert "zasilanie" in res.message
    assert time.monotonic() - t0 < 8  # proces został zakończony, nie wisi


def test_cancel_stops_process(fake_backend, monkeypatch):
    monkeypatch.setenv("FAKE_STCGAL_SCENARIO", "hang")
    cancel = threading.Event()
    threading.Timer(0.5, cancel.set).start()
    t0 = time.monotonic()
    res = fake_backend.identify(conn(timeout_s=60), collect()[3], cancel)
    assert res.state is OperationState.CANCELLED
    assert time.monotonic() - t0 < 8


def test_missing_backend_reported():
    res = StcgalBackend("/nonexistent/stcgal-xyz").identify(conn(), collect()[3], threading.Event())
    assert res.error_kind is ErrorKind.BACKEND_MISSING


def test_program_requires_confirmation(fake_backend, argv_log, firmware_bin):
    be = fake_backend
    prog = ProgramParams(firmware_bin)
    cb = collect()[3]
    with pytest.raises(SafetyError):
        be.program(conn(), prog, None, cb, threading.Event())
    with pytest.raises(SafetyError):  # potwierdzenie dla innego portu
        be.program(
            conn(), prog, WriteConfirmation("/dev/ttyUSB1", firmware_bin), cb, threading.Event()
        )
    with pytest.raises(SafetyError):  # potwierdzenie dla innego pliku
        be.program(
            conn(),
            prog,
            WriteConfirmation("/dev/ttyUSB0", firmware_bin.with_name("x.bin")),
            cb,
            threading.Event(),
        )
    assert not argv_log.exists()  # stcgal nigdy nie został uruchomiony


def test_program_reports_real_progress_and_no_verification(fake_backend, argv_log, firmware_bin):
    log, _s, progress, cb = collect()
    prog = ProgramParams(firmware_bin)
    res = fake_backend.program(
        conn(), prog, risk_acknowledged("/dev/ttyUSB0", firmware_bin), cb, threading.Event()
    )
    assert res.ok and res.programmed
    assert res.verified is False
    assert "nie wykonuje weryfikacji" in res.message
    assert progress and isinstance(progress[-1], Progress) and progress[-1].done == 512
    argv = json.loads(argv_log.read_text().splitlines()[-1])
    assert argv[-1] == str(firmware_bin.resolve()) and "-e" not in argv


def test_cancel_during_program_warns_about_incomplete_firmware(
    fake_backend, monkeypatch, firmware_bin
):
    monkeypatch.setenv("FAKE_STCGAL_SCENARIO", "program_hang")
    cancel = threading.Event()
    threading.Timer(1.0, cancel.set).start()
    res = fake_backend.program(
        conn(),
        ProgramParams(firmware_bin),
        risk_acknowledged("/dev/ttyUSB0", Path(firmware_bin)),
        collect()[3],
        cancel,
    )
    assert res.state is OperationState.CANCELLED and "niekompletny" in res.message


def test_version(fake_backend):
    assert fake_backend.version() == "stcgal 1.10-fake"
