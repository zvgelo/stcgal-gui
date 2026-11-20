"""Sterowanie cyklem życia podprocesu (tworzenie, łagodne anulowanie, zakończenie) - Linux/Windows.

Linux: nowa sesja; anulowanie = SIGINT → SIGTERM → SIGKILL do grupy procesów.
Windows: bez okna konsoli (``CREATE_NO_WINDOW``); łagodne anulowanie przez stdin (wbudowany
backend czyta polecenie ``cancel`` i zgłasza ``KeyboardInterrupt``, więc stcgal rozłącza się
z MCU), potem ``TerminateProcess``. ``CTRL_BREAK`` odpada, bo aplikacja GUI nie ma konsoli.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
from typing import Any

from stcgal_gui import platform_support as ps

CANCEL_ENV = "STCGAL_GUI_CANCEL_STDIN"
CANCEL_COMMAND = b"cancel\n"


def _win(windows: bool | None) -> bool:
    return ps.IS_WINDOWS if windows is None else windows


def _killpg(pid: int, sig_name: str) -> None:
    """Sygnał do grupy procesów (tylko POSIX; ``getattr``, bo na Windows tych symboli nie ma)."""
    killpg = getattr(os, "killpg")  # noqa: B009
    killpg(pid, getattr(signal, sig_name))


def popen_kwargs(windows: bool | None = None) -> dict[str, Any]:
    """Argumenty ``subprocess.Popen`` specyficzne dla systemu (zawsze bez ``shell=True``)."""
    if _win(windows):
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
        )
        return {"stdin": subprocess.PIPE, "creationflags": flags}
    return {"stdin": subprocess.DEVNULL, "start_new_session": True}


def default_grace_s(windows: bool | None = None) -> float:
    """Czas na łagodne zakończenie przed ``TerminateProcess``/SIGTERM.

    Windows: ``interrupt_main`` nie przerywa blokującego odczytu pyserial (do 15 s po handshake),
    a ``TerminateProcess`` w środku zapisu jest gorszy niż czekanie - stąd długi limit.
    """
    return 20.0 if _win(windows) else 3.0


def extra_env(windows: bool | None = None, cancel_via_stdin: bool = True) -> dict[str, str]:
    env = {"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    if _win(windows) and cancel_via_stdin:
        env[CANCEL_ENV] = "1"  # tylko gdy stdin jest kanałem (PIPE) - nie dla DEVNULL
    if ps.is_frozen():
        # backend to INNY program PyInstaller: nie może dziedziczyć stanu rozpakowania GUI
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def sanitize_env(env: dict[str, str]) -> dict[str, str]:
    """Środowisko dla podprocesu: usuwa zmiany biblioteczne wprowadzone przez bootloader.

    Linux (spakowany): bootloader nadpisuje ``LD_LIBRARY_PATH`` ścieżką rozpakowania; podproces
    musi dostać wartość pierwotną, inaczej załaduje biblioteki GUI.
    """
    out = dict(env)
    if ps.is_frozen() and not ps.IS_WINDOWS:
        orig = out.pop("LD_LIBRARY_PATH_ORIG", None)
        if orig is not None:
            out["LD_LIBRARY_PATH"] = orig
        else:
            out.pop("LD_LIBRARY_PATH", None)
    return out


def graceful_cancel(proc: subprocess.Popen[bytes], windows: bool | None = None) -> None:
    """Prosi proces o zakończenie z możliwością posprzątania (rozłączenie z MCU)."""
    if _win(windows):
        with contextlib.suppress(OSError, ValueError):
            if proc.stdin is not None:
                proc.stdin.write(CANCEL_COMMAND)
                proc.stdin.flush()
        return
    with contextlib.suppress(ProcessLookupError, PermissionError):
        _killpg(proc.pid, "SIGINT")


def terminate(proc: subprocess.Popen[bytes], windows: bool | None = None) -> None:
    if _win(windows):
        with contextlib.suppress(OSError):
            proc.terminate()
        return
    with contextlib.suppress(ProcessLookupError, PermissionError):
        _killpg(proc.pid, "SIGTERM")


def kill(proc: subprocess.Popen[bytes], windows: bool | None = None) -> None:
    if _win(windows):
        with contextlib.suppress(OSError):
            proc.kill()
        return
    with contextlib.suppress(ProcessLookupError, PermissionError):
        _killpg(proc.pid, "SIGKILL")


def close_stdin(proc: subprocess.Popen[bytes]) -> None:
    if proc.stdin is not None:
        with contextlib.suppress(OSError, ValueError):
            proc.stdin.close()


# ----------------------------------------------------------------------------- Job Object (Windows)
_JOB_HANDLE: int | None = None
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9


def _job_handle() -> int | None:
    """Tworzy (raz) Job Object z ``KILL_ON_JOB_CLOSE`` - procesy w nim giną razem z aplikacją GUI."""
    global _JOB_HANDLE
    if _JOB_HANDLE is not None:
        return _JOB_HANDLE
    import ctypes
    from ctypes import wintypes

    k32 = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)  # noqa: B009 - brak WinDLL na Linuksie
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    k32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]

    class _Basic(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]  # fmt: skip

    class _Io(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]  # fmt: skip

    class _Extended(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _Basic), ("IoInfo", _Io),
            ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]  # fmt: skip

    job = k32.CreateJobObjectW(None, None)
    if not job:
        return None
    info = _Extended()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ok = k32.SetInformationJobObject(
        job, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info), ctypes.sizeof(info)
    )
    if not ok:
        k32.CloseHandle(job)
        return None
    _JOB_HANDLE = int(job)
    return _JOB_HANDLE


def attach_kill_on_close(proc: subprocess.Popen[bytes], windows: bool | None = None) -> bool:
    """Windows: dodaje proces do Job Object, by nie został osierocony po awarii/zabiciu GUI.

    Best-effort (zwraca ``False`` przy niepowodzeniu). Brak działania na Linuksie.
    """
    if not _win(windows):
        return False
    try:
        import ctypes
        from ctypes import wintypes

        job = _job_handle()
        if job is None:
            return False
        k32 = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)  # noqa: B009
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        handle = int(getattr(proc, "_handle"))  # noqa: B009 - uchwał procesu Popen (Windows)
        return bool(k32.AssignProcessToJobObject(job, handle))
    except (OSError, AttributeError, ValueError):
        return False


def _close_job_for_tests() -> None:
    """Zamyka uchwyt Job Object (symuluje zniknięcie GUI) - wyłącznie testy."""
    global _JOB_HANDLE
    if _JOB_HANDLE is not None:
        import ctypes

        getattr(ctypes, "WinDLL")("kernel32").CloseHandle(ctypes.c_void_p(_JOB_HANDLE))  # noqa: B009
        _JOB_HANDLE = None
