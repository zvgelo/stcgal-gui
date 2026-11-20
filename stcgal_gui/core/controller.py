"""Kontroler operacji: uruchamia backend w osobnym wątku, nigdy w głównym wątku Qt."""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import QCoreApplication as Q
from PySide6.QtCore import QObject, QThread, Signal

from stcgal_gui.backends.base import Backend, Callbacks, SafetyError, WriteConfirmation
from stcgal_gui.core.i18n import fmt
from stcgal_gui.models.data import (
    ConnectionParams,
    ErrorKind,
    OperationKind,
    OperationResult,
    OperationState,
    ProgramParams,
)


class _OperationThread(QThread):
    log = Signal(str, str)
    state = Signal(object)
    progress = Signal(object)
    result = Signal(object)

    def __init__(self, kind: OperationKind, job: Callable[[Callbacks], OperationResult]) -> None:
        super().__init__()
        self._kind = kind
        self._job = job

    def run(self) -> None:
        cb = Callbacks(
            on_log=lambda s, t: self.log.emit(s, t),
            on_state=lambda s: self.state.emit(s),
            on_progress=lambda p: self.progress.emit(p),
        )
        try:
            res = self._job(cb)
        except SafetyError as ex:
            res = OperationResult(
                self._kind, OperationState.FAILED, None, ErrorKind.UNKNOWN, str(ex)
            )
        except Exception as ex:  # noqa: BLE001 - wątek nie może zginąć bez raportu
            res = OperationResult(
                self._kind,
                OperationState.FAILED,
                None,
                ErrorKind.UNKNOWN,
                fmt(Q.translate("Controller", "Błąd wewnętrzny: %1"), ex),
            )
        self.result.emit(res)


class OperationController(QObject):
    """Serializuje operacje sprzętowe: w danej chwili działa najwyżej jedna."""

    log = Signal(str, str)  # (strumień, tekst)
    state_changed = Signal(object)  # OperationState
    progress = Signal(object)  # Progress
    finished = Signal(object)  # OperationResult
    busy_changed = Signal(bool)

    def __init__(self, backend: Backend, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.backend = backend
        self._thread: _OperationThread | None = None
        self._cancel = threading.Event()
        self.state = OperationState.IDLE
        self.current_kind: OperationKind | None = None

    @property
    def busy(self) -> bool:
        return self._thread is not None

    def set_backend(self, backend: Backend) -> None:
        if self.busy:
            raise RuntimeError(
                Q.translate("Controller", "Nie można zmienić backendu w trakcie operacji")
            )
        self.backend = backend

    def start_identify(self, conn: ConnectionParams) -> bool:
        """Niedestrukcyjna identyfikacja. Zwraca False, gdy trwa inna operacja."""
        return self._start(
            OperationKind.IDENTIFY, lambda cb: self.backend.identify(conn, cb, self._cancel)
        )

    def start_program(
        self,
        conn: ConnectionParams,
        prog: ProgramParams,
        confirmation: WriteConfirmation | None,
    ) -> bool:
        """Zapis; backend odrzuci wywołanie bez ``confirmation``."""
        if confirmation is None:
            raise SafetyError(Q.translate("Controller", "Zapis wymaga potwierdzenia użytkownika"))
        return self._start(
            OperationKind.PROGRAM,
            lambda cb: self.backend.program(conn, prog, confirmation, cb, self._cancel),
        )

    def start_erase(self, conn: ConnectionParams, confirmation: WriteConfirmation | None) -> bool:
        """Kasowanie Flash (tryb eksperta); backend wymaga potwierdzenia."""
        if confirmation is None:
            raise SafetyError(
                Q.translate("Controller", "Kasowanie wymaga potwierdzenia użytkownika")
            )
        return self._start(
            OperationKind.ERASE, lambda cb: self.backend.erase(conn, confirmation, cb, self._cancel)
        )

    def cancel(self) -> None:
        """Prosi o przerwanie (SIGINT → SIGTERM → SIGKILL w backendzie procesowym)."""
        if self.busy:
            self._cancel.set()

    def wait(self, timeout_ms: int = 10000) -> bool:
        t = self._thread
        return True if t is None else t.wait(timeout_ms)

    def _start(self, kind: OperationKind, job: Callable[[Callbacks], OperationResult]) -> bool:
        if self.busy:
            return False
        self._cancel = threading.Event()
        self.current_kind = kind
        t = _OperationThread(kind, job)
        t.log.connect(self.log)
        t.state.connect(self._on_state)
        t.progress.connect(self.progress)
        t.result.connect(self._on_result)
        self._thread = t
        self.busy_changed.emit(True)
        t.start()
        return True

    def _on_state(self, state: OperationState) -> None:
        self.state = state
        self.state_changed.emit(state)

    def _on_result(self, res: OperationResult) -> None:
        t = self._thread
        if t is not None:
            t.wait(5000)
            t.deleteLater()
        self._thread = None
        self.state = res.state
        self.state_changed.emit(res.state)
        self.busy_changed.emit(False)
        self.finished.emit(res)
