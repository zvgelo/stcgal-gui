"""Testy warstwy platformowej: gałęzie Windows symulowane na Linuksie + testy tylko dla Windows."""

import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from stcgal_gui import platform_support as ps
from stcgal_gui.backends import procctl
from stcgal_gui.backends.stcgal import StcgalBackend, classify_error, find_stcgal
from stcgal_gui.core import diagnosis
from stcgal_gui.devices.ports import enumerate_ports
from stcgal_gui.models.data import (
    ConnectionParams,
    ErrorKind,
    OperationState,
)

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="wymaga Windows")


def com(device, vid=None, pid=None, desc="n/a", serial=None, loc=None, mfr=None):
    return SimpleNamespace(
        device=device, vid=vid, pid=pid, description=desc, serial_number=serial,
        location=loc, manufacturer=mfr,
    )  # fmt: skip


# ----------------------------------------------------------------- porty COM (symulacja)


def test_windows_com_ports_ch340_and_natural_order(tmp_path: Path):
    src = lambda: [  # noqa: E731
        com("COM10", 0x1A86, 0x7523, "USB-SERIAL CH340 (COM10)", loc="1-4"),
        com("COM3", 0x10C4, 0xEA60, "Silicon Labs CP210x USB to UART Bridge (COM3)", serial="0001"),
        com("COM2", 0x0403, 0x6001, "USB Serial Port (COM2)", serial="A50285BI"),
        com("COM1"),
        com("COM12", None, None, "Standard Serial over Bluetooth link (COM12)"),
    ]
    ports = enumerate_ports(src, tmp_path, windows=True)
    assert [p.device for p in ports] == ["COM2", "COM3", "COM10"]  # COM2 < COM10, bez wbudowanych
    ch = ports[2]
    assert ch.is_ch340 and ch.vid_pid == "1a86:7523" and ch.location == "1-4"
    assert ch.serial_number == "" and ch.by_id is None  # brak numeru seryjnego = pusty napis
    assert ports[0].serial_number == "A50285BI"
    assert all(p.accessible for p in ports)
    assert len(enumerate_ports(src, tmp_path, windows=True, include_builtin=True)) == 5


def test_windows_never_uses_by_id(tmp_path: Path):
    by_id = tmp_path / "by-id"
    by_id.mkdir()
    (by_id / "usb-x").symlink_to(tmp_path)
    p = enumerate_ports(lambda: [com("COM4", 0x1A86, 0x7523)], by_id, windows=True)[0]
    assert p.by_id is None


def test_normalize_port_windows_and_linux():
    assert ps.normalize_port("com10", windows=True) == "COM10"
    assert ps.normalize_port("\\\\.\\COM12", windows=True) == "COM12"
    assert ps.normalize_port("", windows=True) == ""
    assert ps.normalize_port("/dev/ttyUSB0", windows=False).endswith("ttyUSB0")


def test_builtin_rules():
    assert ps.is_builtin_port("COM1", None, windows=True)
    assert not ps.is_builtin_port("COM3", 0x1A86, windows=True)
    assert ps.is_builtin_port("/dev/ttyS3", None, windows=False)
    assert not ps.is_builtin_port("/dev/ttyUSB0", 0x1A86, windows=False)
    assert not ps.supports_by_id(windows=True) and ps.supports_by_id(windows=False)


def test_port_vanishes_between_enumerations(tmp_path: Path):
    first = enumerate_ports(lambda: [com("COM5", 0x1A86, 0x7523)], tmp_path, windows=True)
    second = enumerate_ports(lambda: [], tmp_path, windows=True)
    assert [p.device for p in first] == ["COM5"] and second == []


# ----------------------------------------------------------------- błędy Windows


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        (
            "could not open port 'COM3': PermissionError(13, 'Access is denied.', None, 5)",
            ErrorKind.PORT_BUSY,
        ),
        (
            "could not open port 'COM7': FileNotFoundError(2, 'The system cannot find the file specified.', None, 2)",
            ErrorKind.PORT_MISSING,
        ),
        (
            "ClearCommError failed (OSError(22, 'The device does not recognize the command.', None, 22))",
            ErrorKind.DEVICE_LOST,
        ),
        (
            "WriteFile failed (OSError(22, 'A device attached to the system is not functioning.', None, 31))",
            ErrorKind.DEVICE_LOST,
        ),
        (
            "device reports readiness to read but returned no data (device disconnected or multiple access on port?)",
            ErrorKind.DEVICE_LOST,
        ),
        ("[Errno 5] Input/output error", ErrorKind.DEVICE_LOST),
    ],
)
def test_windows_error_classification(text, kind):
    got, msg = classify_error(text, windows=True)
    assert got is kind and msg
    assert "dialout" not in msg and "ModemManager" not in msg  # brak wskazówek linuksowych


def test_platform_specific_messages():
    assert "dialout" in diagnosis.user_message(ErrorKind.PERMISSION, windows=False)
    assert "dialout" not in diagnosis.user_message(ErrorKind.PERMISSION, windows=True)
    assert "Menedżer urządzeń" in diagnosis.troubleshooting_hint(
        ErrorKind.PORT_MISSING, windows=True
    )
    assert "lsusb" in diagnosis.troubleshooting_hint(ErrorKind.PORT_MISSING, windows=False)
    assert diagnosis.troubleshooting_hint(ErrorKind.TIMEOUT, windows=True)


# ----------------------------------------------------------------- proces (symulacja Windows)


def test_windows_popen_flags_no_console_no_shell():
    kw = procctl.popen_kwargs(windows=True)
    assert kw["creationflags"] & 0x08000000  # CREATE_NO_WINDOW
    assert kw["creationflags"] & 0x00000200  # CREATE_NEW_PROCESS_GROUP
    assert kw["stdin"] == subprocess.PIPE and "start_new_session" not in kw
    assert "shell" not in kw
    lin = procctl.popen_kwargs(windows=False)
    assert lin["start_new_session"] and lin["stdin"] == subprocess.DEVNULL
    assert procctl.extra_env(windows=True)[procctl.CANCEL_ENV] == "1"
    assert procctl.CANCEL_ENV not in procctl.extra_env(windows=False)


def test_windows_graceful_cancel_writes_command_to_stdin():
    class Stdin:
        data = b""

        def write(self, b):
            self.data += b

        def flush(self):
            pass

    proc = SimpleNamespace(stdin=Stdin(), pid=1)
    procctl.graceful_cancel(proc, windows=True)
    assert proc.stdin.data == b"cancel\n"
    proc.stdin = None  # zamknięty stdin nie może rzucić wyjątku
    procctl.graceful_cancel(proc, windows=True)


# ----------------------------------------------------------------- lokalizacja backendu


def test_bundled_backend_found_next_to_app(tmp_path: Path):
    assert ps.bundled_backend(windows=True, base=tmp_path) is None
    exe = tmp_path / "stcgal-backend.exe"
    exe.write_bytes(b"MZ")
    assert ps.bundled_backend(windows=True, base=tmp_path) == exe
    other = tmp_path / "x"
    (other / "backend").mkdir(parents=True)
    (other / "backend" / "stcgal-backend").write_text("")
    assert ps.bundled_backend(windows=False, base=other) is not None


def test_find_stcgal_prefers_configured_then_bundled(tmp_path: Path, monkeypatch):
    bundled = tmp_path / ps.backend_filename()
    bundled.write_text("")
    cfg = tmp_path / "custom"
    cfg.write_text("")
    monkeypatch.setattr(ps, "app_dir", lambda: tmp_path)
    assert find_stcgal(str(cfg)) == str(cfg)
    assert find_stcgal() == str(bundled)


def test_resource_dir_contains_icon():
    assert (ps.resource_dir() / "stcgal-gui.svg").is_file()


def test_missing_backend_message_mentions_bundle(tmp_path: Path):
    res = StcgalBackend(str(tmp_path / "nope")).identify(
        ConnectionParams(port="COM3"),
        __import__("stcgal_gui.backends.base", fromlist=["Callbacks"]).Callbacks(),
        threading.Event(),
    )
    assert res.error_kind is ErrorKind.BACKEND_MISSING and res.state is OperationState.FAILED


# ----------------------------------------------------------------- backend_entry (wspólny, Linux i Windows)


def _skip_if_pty_unusable(p: subprocess.Popen) -> None:
    """Niektóre środowiska (CI) nie pozwalają pyserial otworzyć pty - wtedy test nie ma sensu."""
    if p.poll() is not None:
        out, err = p.communicate()
        text = (out + err).lower()
        if "serial port error" in text or "invalid argument" in text or "serial" in text:
            pytest.skip(f"pyserial nie otworzył pty: {(out + err).strip()[-200:]}")
        pytest.fail(
            f"backend zakończył się przed anulowaniem (kod {p.returncode}): {(out + err)[-400:]}"
        )


def run_entry(args, **kw):
    return subprocess.run(
        [sys.executable, "-m", "stcgal_gui.backend_entry", *args],
        capture_output=True, text=True, timeout=60, **kw,
    )  # fmt: skip


def test_backend_entry_version_matches_stcgal():
    r = run_entry(["-V"])
    assert r.returncode == 0 and r.stdout.strip() == "stcgal 1.10"
    info = run_entry(["--backend-info"])
    assert "stcgal 1.10" in info.stdout and "pyserial" in info.stdout


def test_backend_entry_passes_arguments_unchanged():
    """Błędny protokół musi dać ten sam błąd argparse co oryginalny stcgal (semantyka argv)."""
    r = run_entry(["-P", "zly"])
    assert r.returncode == 2 and "invalid choice" in r.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="pty tylko POSIX")
def test_backend_entry_cancel_via_stdin_interrupts_gracefully():
    """Pty udaje port, na którym nikt nie odpowiada (jak MCU bez restartu zasilania).

    Polecenie ``cancel`` na stdin musi przerwać oczekiwanie jak Ctrl+C: kod 2 i „interrupted”.
    """
    import os
    import pty
    import time

    master, slave = pty.openpty()
    try:
        env = dict(os.environ, **{procctl.CANCEL_ENV: "1"})
        p = subprocess.Popen(
            [sys.executable, "-m", "stcgal_gui.backend_entry", "-p", os.ttyname(slave), "-P", "stc8d"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
        )  # fmt: skip
        time.sleep(1.5)
        _skip_if_pty_unusable(p)  # czeka na MCU
        p.stdin.write("cancel\n")
        p.stdin.flush()
        out, err = p.communicate(timeout=30)
        assert p.returncode == 2 and "interrupted" in out + err
    finally:
        os.close(master)
        os.close(slave)


@pytest.mark.skipif(sys.platform == "win32", reason="pty tylko POSIX")
def test_backend_entry_stdin_eof_interrupts_orphan():
    """Zamknięcie stdin (GUI zniknęło) także przerywa backend - brak osieroconych procesów."""
    import os
    import pty
    import time

    master, slave = pty.openpty()
    try:
        env = dict(os.environ, **{procctl.CANCEL_ENV: "1"})
        p = subprocess.Popen(
            [sys.executable, "-m", "stcgal_gui.backend_entry", "-p", os.ttyname(slave), "-P", "stc8d"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
        )  # fmt: skip
        time.sleep(1.5)
        _skip_if_pty_unusable(p)
        p.stdin.close()
        p.communicate(timeout=30)
        assert p.returncode == 2
    finally:
        os.close(master)
        os.close(slave)


# ----------------------------------------------------------------- tylko Windows (CI na windows-latest)


@windows_only
def test_real_com_enumeration_runs():
    assert isinstance(enumerate_ports(), list)


@windows_only
def test_real_backend_subprocess_no_console_window(tmp_path: Path):
    """Uruchomienie backendu przez run_process: stdout przechwycony, kod wyjścia 0."""
    from stcgal_gui.backends.process import run_process

    chunks = []
    out = run_process(
        [sys.executable, "-m", "stcgal_gui.backend_entry", "-V"],
        on_chunk=lambda s, t: chunks.append((s, t)),
        cancel=threading.Event(),
        connect_timeout_s=30,
        is_connected=lambda: True,
    )
    assert out.return_code == 0 and "stcgal 1.10" in out.stdout and chunks


@windows_only
def test_job_object_kills_child_when_gui_handle_closes():
    """Backend nie może przeżyć GUI: zamknięcie uchwytu Job Object (jak śmierć procesu) ubija dziecko."""
    import time

    p = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", "import time; time.sleep(120)"], **procctl.popen_kwargs()
    )
    try:
        assert procctl.attach_kill_on_close(p) is True
        assert p.poll() is None
        procctl._close_job_for_tests()
        deadline = time.monotonic() + 10
        while p.poll() is None and time.monotonic() < deadline:
            time.sleep(0.1)
        assert p.poll() is not None
    finally:
        if p.poll() is None:
            p.kill()


def test_job_object_is_noop_on_linux():
    assert procctl.attach_kill_on_close(SimpleNamespace(), windows=False) is False
