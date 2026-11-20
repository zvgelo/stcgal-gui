"""Kontrolowane uruchamianie podprocesu (bez shell=True) z timeoutem i anulowaniem."""

from __future__ import annotations

import contextlib
import os
import subprocess
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import IO

from stcgal_gui.backends import procctl


@dataclass
class ProcessOutcome:
    return_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    cancelled: bool = False
    start_failed: str | None = None


def _pump(
    stream: IO[bytes], name: str, sink: list[str], on_chunk: Callable[[str, str], None]
) -> None:
    decoder_buf = b""
    while True:
        try:
            data = stream.read1(4096)  # type: ignore[attr-defined]
        except (OSError, ValueError):
            break
        if not data:
            break
        data = decoder_buf + data
        try:
            text = data.decode("utf-8")
            decoder_buf = b""
        except UnicodeDecodeError as ex:
            # niepełna sekwencja na końcu bloku - dopisz po następnym odczycie
            if ex.start >= len(data) - 3:
                text = data[: ex.start].decode("utf-8", "replace")
                decoder_buf = data[ex.start :]
            else:
                text = data.decode("utf-8", "replace")
                decoder_buf = b""
        sink.append(text)
        on_chunk(name, text)


def run_process(
    argv: Sequence[str],
    *,
    on_chunk: Callable[[str, str], None],
    cancel: threading.Event,
    connect_timeout_s: float,
    is_connected: Callable[[], bool],
    idle_timeout_s: float = 90.0,
    env: Mapping[str, str] | None = None,
    grace_s: float | None = None,
    windows: bool | None = None,
) -> ProcessOutcome:
    """Uruchamia ``argv`` i czeka na zakończenie.

    * Faza 1 (do ``is_connected()``): limit ``connect_timeout_s`` - oczekiwanie na restart MCU.
    * Faza 2: limit ciszy ``idle_timeout_s`` bez żadnego wyjścia.
    * Anulowanie/timeout: łagodne przerwanie (stcgal sam się rozłącza), potem zakończenie,
      na końcu wymuszone zabicie (szczegóły platformowe: ``procctl``).
    """
    if grace_s is None:
        grace_s = procctl.default_grace_s(windows)
    full_env = procctl.sanitize_env(dict(os.environ))
    full_env.update(procctl.extra_env(windows))
    if env:
        full_env.update(env)
    try:
        proc = subprocess.Popen(  # noqa: S603 - brak powłoki, argv jako lista
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=full_env,
            shell=False,
            **procctl.popen_kwargs(windows),
        )
    except OSError as ex:
        return ProcessOutcome(None, "", "", start_failed=str(ex))

    procctl.attach_kill_on_close(proc, windows)  # Windows: backend nie przeżyje GUI
    out: list[str] = []
    err: list[str] = []
    last_activity = time.monotonic()

    def chunk(stream: str, text: str) -> None:
        nonlocal last_activity
        last_activity = time.monotonic()
        on_chunk(stream, text)

    assert proc.stdout is not None and proc.stderr is not None
    threads = [
        threading.Thread(target=_pump, args=(proc.stdout, "stdout", out, chunk), daemon=True),
        threading.Thread(target=_pump, args=(proc.stderr, "stderr", err, chunk), daemon=True),
    ]
    for t in threads:
        t.start()

    started = time.monotonic()
    timed_out = False
    cancelled = False
    while proc.poll() is None:
        now = time.monotonic()
        if cancel.is_set():
            cancelled = True
            break
        if is_connected():
            if now - last_activity > idle_timeout_s:
                timed_out = True
                break
        elif now - started > connect_timeout_s:
            timed_out = True
            break
        time.sleep(0.03)

    if proc.poll() is None:
        steps = (
            (partial(procctl.graceful_cancel, proc, windows), grace_s),
            (partial(procctl.terminate, proc, windows), grace_s),
            (partial(procctl.kill, proc, windows), 5.0),
        )
        for action, wait_s in steps:
            action()
            try:
                proc.wait(timeout=wait_s)
                break
            except subprocess.TimeoutExpired:
                continue
    rc = proc.wait()
    procctl.close_stdin(proc)
    for t in threads:
        t.join(timeout=2)
    for f in (proc.stdout, proc.stderr):
        with contextlib.suppress(OSError):
            f.close()
    return ProcessOutcome(rc, "".join(out), "".join(err), timed_out=timed_out, cancelled=cancelled)
