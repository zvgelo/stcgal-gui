"""Atrapa stcgal do testów end-to-end podprocesu (naśladuje format wyjścia stcgal 1.10).

Zachowanie wybiera zmienna FAKE_STCGAL_SCENARIO; argv jest dopisywane do FAKE_STCGAL_LOG.
"""

import json
import os
import signal
import sys
import time

scenario = os.environ.get("FAKE_STCGAL_SCENARIO", "ok")
log = os.environ.get("FAKE_STCGAL_LOG")
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(sys.argv[1:]) + "\n")

if "-V" in sys.argv:
    print("stcgal 1.10-fake")
    sys.exit(0)


def interrupted(*_):
    print("interrupted", file=sys.stderr)
    sys.exit(2)


_orig_hook = sys.excepthook


def _hook(t, v, tb):
    if t is KeyboardInterrupt:  # przerwanie z wątku stdin (Windows) → jak Ctrl+C w stcgal
        print("interrupted", file=sys.stderr, flush=True)
        os._exit(2)
    _orig_hook(t, v, tb)


sys.excepthook = _hook


signal.signal(signal.SIGINT, interrupted)

if (
    os.environ.get("STCGAL_GUI_CANCEL_STDIN") == "1"
):  # jak backend_entry: 'cancel' na stdin → przerwanie
    import _thread
    import threading

    def _watch():
        for line in sys.stdin:
            if line.strip().lower() == "cancel":
                break
        _thread.interrupt_main()

    threading.Thread(target=_watch, daemon=True).start()


def out(text, end="\n"):
    sys.stdout.write(text + end)
    sys.stdout.flush()


if scenario == "permission":
    print(
        "Serial port error: [Errno 13] could not open port /dev/ttyUSB0: Permission denied",
        file=sys.stderr,
    )
    sys.exit(1)
if scenario == "busy":
    print(
        "Serial port error: [Errno 16] could not exclusively lock port: Device or resource busy",
        file=sys.stderr,
    )
    sys.exit(1)
if scenario == "missing":
    print(
        "Serial port error: [Errno 2] could not open port /dev/ttyUSB0: No such file or directory",
        file=sys.stderr,
    )
    sys.exit(1)

out("Waiting for MCU, please cycle power: ", end="")
if scenario == "hang":
    while True:
        time.sleep(0.05)
time.sleep(float(os.environ.get("FAKE_STCGAL_DELAY", "0.2")))
if scenario == "handshake_fail":
    print("Protocol error: incorrect magic in status packet", file=sys.stderr)
    sys.exit(1)
out("done")
out("Protocol detected: stc8d")
out(
    "Target model:\n  Name: STC8H8K64U\n  Magic: F784\n  Code flash: 63.5 KB\n  EEPROM flash: 0.5 KB"
)
if os.environ.get("FAKE_STCGAL_MODEL_PAUSE"):
    time.sleep(
        float(os.environ["FAKE_STCGAL_MODEL_PAUSE"])
    )  # okno na przerwanie po wypisaniu modelu
out("Target frequency: 24.000 MHz")
out("Target BSL version: 7.4.4U")
out("Target wakeup frequency: 32.768 KHz")
out("Target ref. voltage: 1190 mV")
out("Target mfg. date: 2023-05-01")
out("Target options:\n  reset_pin_enabled=False\n  program_eeprom_split=65024")
if scenario == "program_hang":
    out("Loading flash: 100 bytes (Binary)")
    out("Erasing flash: ", end="")
    while True:
        time.sleep(0.05)
if any(
    not a.startswith("-") and "." in os.path.basename(a) and os.path.exists(a) for a in sys.argv[1:]
):
    out("Loading flash: 100 bytes (Binary)")
    out("Erasing flash: done")
    for pct, n in ((0, 0), (50, 256), (100, 512)):
        sys.stderr.write(
            f"\rWriting flash: {pct:3d}%|{'#' * (pct // 10):<10}| {n}/512 [00:00<?, ?Bytes/s]"
        )
        sys.stderr.flush()
        time.sleep(0.05)
    sys.stderr.write("\n")
    out("Finishing write: done")
    out("Setting options: done")
    out("Target UID: 0102030405060708")
out("Disconnected!")
