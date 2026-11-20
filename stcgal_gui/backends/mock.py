"""Backend symulowany - pełne testy i tryb demo bez fizycznego programatora."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from PySide6.QtCore import QCoreApplication as Q

from stcgal_gui.backends.base import (
    Backend,
    Callbacks,
    Capabilities,
    SafetyError,
    WriteConfirmation,
)
from stcgal_gui.core import safety
from stcgal_gui.models.data import (
    ConnectionParams,
    ErrorKind,
    McuInfo,
    OperationKind,
    OperationResult,
    OperationState,
    ProgramParams,
    Progress,
    WriteScope,
)

DEMO_MCU = McuInfo(
    protocol="stc8d", model="STC8H8K64U", magic="F784",
    code_flash_kb=63.5, eeprom_kb=0.5, frequency_mhz=24.0, bsl_version="7.4.4U",
    wakeup_khz=32.768, ref_voltage_mv=1190, mfg_date="2023-05-01",
    options={"reset_pin_enabled": "False", "program_eeprom_split": "65024"},
)  # fmt: skip


@dataclass
class MockCall:
    kind: str
    conn: ConnectionParams
    prog: ProgramParams | None = None


class MockBackend(Backend):
    """Symuluje stcgal. ``scenario``: ok | no_mcu | permission | busy | fail."""

    def __init__(
        self,
        scenario: str = "ok",
        wait_s: float = 0.2,
        write_s: float = 0.2,
        guarantees: bool = True,
    ) -> None:
        """``guarantees=False`` symuluje backend bez gwarancji ochrony EEPROM/opcji (jak stcgal)."""
        self.name = "mock"
        self.scenario = scenario
        self.wait_s = wait_s
        self.write_s = write_s
        self.guarantees = guarantees
        self.calls: list[MockCall] = []
        self.mcu = DEMO_MCU
        self._busy = threading.Lock()

    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(
            verify=False, read_firmware=False, real_progress=True,
            preserves_eeprom=self.guarantees, preserves_options=self.guarantees, erase_only=True,
            notes=(Q.translate("MockBackend", "Backend symulowany - brak komunikacji ze sprzętem."),),
        )  # fmt: skip

    def _sleep(self, seconds: float, cancel: threading.Event) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if cancel.is_set():
                return False
            time.sleep(0.01)
        return True

    def _connect(
        self, conn: ConnectionParams, cb: Callbacks, cancel: threading.Event
    ) -> OperationResult | None:
        """Wspólna faza łączenia; zwraca wynik błędu lub None, gdy połączono."""
        kind = OperationKind.IDENTIFY
        if self.scenario in ("permission", "busy"):
            ek = ErrorKind.PERMISSION if self.scenario == "permission" else ErrorKind.PORT_BUSY
            cb.on_log("stderr", "Serial port error: [Errno 13] Permission denied\n")
            return OperationResult(
                kind,
                OperationState.FAILED,
                1,
                ek,
                Q.translate("MockBackend", "Błąd portu (symulacja)."),
            )
        cb.on_state(OperationState.WAITING_FOR_MCU)
        cb.on_log("stdout", "Waiting for MCU, please cycle power: ")
        if self.scenario == "no_mcu":
            end = time.monotonic() + conn.timeout_s
            while time.monotonic() < end:
                if cancel.is_set():
                    return OperationResult(
                        kind,
                        OperationState.CANCELLED,
                        2,
                        ErrorKind.CANCELLED,
                        Q.translate("MockBackend", "Anulowano."),
                    )
                time.sleep(0.01)
            return OperationResult(
                kind,
                OperationState.TIMEOUT,
                None,
                ErrorKind.TIMEOUT,
                Q.translate("MockBackend", "Timeout oczekiwania na MCU."),
            )
        if not self._sleep(self.wait_s, cancel):
            return OperationResult(
                kind,
                OperationState.CANCELLED,
                2,
                ErrorKind.CANCELLED,
                Q.translate("MockBackend", "Anulowano."),
            )
        cb.on_log("stdout", "done\n")
        cb.on_state(OperationState.RUNNING)
        return None

    def identify(
        self, conn: ConnectionParams, cb: Callbacks, cancel: threading.Event
    ) -> OperationResult:
        if not self._busy.acquire(blocking=False):
            raise RuntimeError(Q.translate("MockBackend", "Port zajęty przez inną operację"))
        try:
            self.calls.append(MockCall("identify", conn))
            cb.on_state(OperationState.RUNNING)
            if (res := self._connect(conn, cb, cancel)) is not None:
                return res
            cb.on_log("stdout", f"Target model:\n  Name: {self.mcu.model}\nDisconnected!\n")
            return OperationResult(
                OperationKind.IDENTIFY, OperationState.FINISHED, 0,
                message=Q.translate("MockBackend", "Identyfikacja zakończona (symulacja)."), mcu=self.mcu,
            )  # fmt: skip
        finally:
            self._busy.release()

    def erase(
        self,
        conn: ConnectionParams,
        confirmation: WriteConfirmation | None,
        cb: Callbacks,
        cancel: threading.Event,
    ) -> OperationResult:
        if confirmation is None or confirmation.scope is not WriteScope.ERASE_ONLY:
            raise SafetyError(Q.translate("MockBackend", "Brak potwierdzenia kasowania"))
        safety.enforce_erase(self.capabilities, confirmation)
        if not self._busy.acquire(blocking=False):
            raise RuntimeError(Q.translate("MockBackend", "Port zajęty przez inną operację"))
        try:
            self.calls.append(MockCall("erase", conn))
            cb.on_state(OperationState.RUNNING)
            if (res := self._connect(conn, cb, cancel)) is not None:
                res.kind = OperationKind.ERASE
                return res
            self._sleep(self.write_s, cancel)
            return OperationResult(
                OperationKind.ERASE,
                OperationState.FINISHED,
                0,
                message=Q.translate("MockBackend", "Kasowanie zakończone (symulacja)."),
            )
        finally:
            self._busy.release()

    def program(
        self,
        conn: ConnectionParams,
        prog: ProgramParams,
        confirmation: WriteConfirmation | None,
        cb: Callbacks,
        cancel: threading.Event,
    ) -> OperationResult:
        if confirmation is None or not confirmation.matches(conn, prog):
            raise SafetyError(Q.translate("MockBackend", "Brak potwierdzenia zapisu"))
        if confirmation.scope is WriteScope.ERASE_ONLY:
            raise SafetyError(Q.translate("MockBackend", "Zakres kasowania nie dotyczy zapisu"))
        safety.enforce(self.capabilities, prog, confirmation)
        if not self._busy.acquire(blocking=False):
            raise RuntimeError(Q.translate("MockBackend", "Port zajęty przez inną operację"))
        try:
            self.calls.append(MockCall("program", conn, prog))
            cb.on_state(OperationState.RUNNING)
            if (res := self._connect(conn, cb, cancel)) is not None:
                res.kind = OperationKind.PROGRAM
                return res
            steps = 10
            size = prog.code_image.stat().st_size or 1
            for i in range(steps + 1):
                if not self._sleep(self.write_s / steps, cancel):
                    return OperationResult(
                        OperationKind.PROGRAM, OperationState.CANCELLED, 2, ErrorKind.CANCELLED,
                        Q.translate("MockBackend", "Anulowano w trakcie zapisu - firmware może być niekompletny."),
                    )  # fmt: skip
                cb.on_progress(Progress(size * i // steps, size, "Writing flash"))
            if self.scenario == "fail":
                return OperationResult(
                    OperationKind.PROGRAM, OperationState.FAILED, 1, ErrorKind.PROTOCOL,
                    Q.translate("MockBackend", "Błąd protokołu (symulacja)."),
                )  # fmt: skip
            return OperationResult(
                OperationKind.PROGRAM, OperationState.FINISHED, 0,
                message=Q.translate("MockBackend", "Zapis zakończony (symulacja)."), programmed=True, verified=False,
            )  # fmt: skip
        finally:
            self._busy.release()
