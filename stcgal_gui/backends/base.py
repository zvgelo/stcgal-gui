"""Abstrakcja backendu ISP. GUI zależy wyłącznie od tego interfejsu."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QCoreApplication as Q

from stcgal_gui.models.data import (
    ConnectionParams,
    OperationResult,
    OperationState,
    ProgramParams,
    Progress,
    WriteScope,
)


@dataclass(frozen=True)
class Capabilities:
    """Co backend FAKTYCZNIE potrafi. GUI nie może obiecywać więcej."""

    identify: bool = True
    program_flash: bool = True
    program_eeprom: bool = True
    verify: bool = False
    read_firmware: bool = False
    real_progress: bool = False
    read_options: bool = True
    # Gwarancje techniczne dotyczące ochrony danych (domyślnie BRAK - wymaga dowodu w backendzie)
    preserves_eeprom: bool = False  # kasowanie/zapis Flash na pewno nie rusza EEPROM/IAP
    preserves_options: bool = False  # option bytes i trim zegara pozostają bez zmian
    erase_only: bool = False  # osobne kasowanie Flash (bez zapisu)
    notes: tuple[str, ...] = ()


def _noop(*_: object) -> None:
    return None


@dataclass
class Callbacks:
    """Zwrotne wywołania zdarzeń (wywoływane z wątku roboczego)."""

    on_log: Callable[[str, str], None] = _noop  # (strumień: stdout|stderr|info, tekst)
    on_state: Callable[[OperationState], None] = _noop
    on_progress: Callable[[Progress], None] = _noop


@dataclass(frozen=True)
class WriteConfirmation:
    """Niemutowalne potwierdzenie zapisu wystawiane po jawnej decyzji użytkownika.

    Zawiera port, plik, zakres (tylko Flash / Flash+EEPROM), pojemność kodu i model zidentyfikowanego
    MCU oraz zbiór świadomie zaakceptowanych ryzyk. Backend odmawia zapisu bez niego i przy każdym
    nierozwiązanym ryzyku (``core/safety.py``). To obrona w głąb: backend ufa danym o MCU od
    wywołującego, dlatego dodatkowo sprawdza zgodność modelu układu w trakcie zapisu
    (``expected_model``) i przerywa przed kasowaniem, jeśli podłączono inny układ.
    """

    port: str
    code_image: Path
    scope: WriteScope = WriteScope.FLASH_ONLY
    acknowledged: frozenset[str] = frozenset()
    mcu_code_bytes: int | None = None
    expected_model: str | None = None
    expert: bool = False  # tryb eksperta włączony świadomie przez użytkownika

    def __post_init__(self) -> None:
        if not isinstance(self.scope, WriteScope):
            raise TypeError(f"scope musi być WriteScope, jest {type(self.scope).__name__}")
        if not isinstance(self.acknowledged, frozenset):
            raise TypeError("acknowledged musi być frozenset")
        if self.mcu_code_bytes is not None and (
            not isinstance(self.mcu_code_bytes, int) or self.mcu_code_bytes <= 0
        ):
            raise TypeError("mcu_code_bytes musi być dodatnią liczbą całkowitą lub None")

    def matches(self, conn: ConnectionParams, prog: ProgramParams) -> bool:
        return self.port == conn.port and self.code_image == prog.code_image


class SafetyError(RuntimeError):
    """Próba operacji destrukcyjnej bez wymaganego potwierdzenia."""


@dataclass
class Backend(ABC):
    """Interfejs backendu programowania ISP."""

    name: str = field(default="backend", init=False)

    @property
    @abstractmethod
    def capabilities(self) -> Capabilities: ...

    @abstractmethod
    def identify(
        self, conn: ConnectionParams, cb: Callbacks, cancel: threading.Event
    ) -> OperationResult:
        """Niedestrukcyjna identyfikacja MCU. Nie wolno kasować ani programować."""

    @abstractmethod
    def program(
        self,
        conn: ConnectionParams,
        prog: ProgramParams,
        confirmation: WriteConfirmation | None,
        cb: Callbacks,
        cancel: threading.Event,
    ) -> OperationResult:
        """Zapis flash/EEPROM. Wymaga ``WriteConfirmation``."""

    def erase(
        self,
        conn: ConnectionParams,
        confirmation: WriteConfirmation | None,
        cb: Callbacks,
        cancel: threading.Event,
    ) -> OperationResult:
        """Kasowanie Flash bez zapisu (tryb eksperta). Domyślnie niewspierane."""
        raise NotImplementedError(Q.translate("Backend", "Backend nie obsługuje samego kasowania"))

    def version(self) -> str | None:
        """Wersja narzędzia, jeśli da się ją ustalić."""
        return None
