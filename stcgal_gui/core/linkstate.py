"""Model stanu połączenia pokazywanego w całej aplikacji."""

from __future__ import annotations

from enum import Enum
from typing import Any

from PySide6.QtCore import QT_TRANSLATE_NOOP
from PySide6.QtCore import QCoreApplication as Q

from stcgal_gui.models.data import ErrorKind, OperationKind, OperationResult, OperationState


class LinkState(Enum):
    """Stan relacji: adapter → port → mikrokontroler."""

    NO_ADAPTER = "no_adapter"
    ADAPTER_READY = "adapter_ready"
    WAITING_MCU = "waiting_mcu"
    IDENTIFYING = "identifying"
    PROGRAMMING = "programming"
    MCU_DETECTED = "mcu_detected"
    TIMEOUT = "timeout"
    ERROR = "error"


def from_operation(state: OperationState, kind: OperationKind | None) -> LinkState | None:
    """Stan chwilowy w trakcie operacji (None = brak operacji w toku)."""
    if state is OperationState.WAITING_FOR_MCU:
        return LinkState.WAITING_MCU
    if state is OperationState.RUNNING:
        return (
            LinkState.IDENTIFYING
            if kind in (OperationKind.IDENTIFY, None)
            else LinkState.PROGRAMMING
        )
    return None


def from_result(res: OperationResult, mcu_known: bool) -> LinkState:
    """Stan po zakończeniu operacji."""
    if res.state is OperationState.TIMEOUT:
        return LinkState.TIMEOUT
    if res.state is OperationState.CANCELLED:
        return LinkState.MCU_DETECTED if mcu_known else LinkState.ADAPTER_READY
    if res.state is OperationState.FAILED:
        if res.error_kind in (ErrorKind.PORT_MISSING, ErrorKind.DEVICE_LOST):
            return LinkState.NO_ADAPTER
        return LinkState.ERROR
    return LinkState.MCU_DETECTED if mcu_known else LinkState.ADAPTER_READY


# (glif, krótki opis) - status nigdy nie opiera się wyłącznie na kolorze
DESCRIPTIONS: dict[LinkState, tuple[str, Any]] = {
    LinkState.NO_ADAPTER: ("✖", QT_TRANSLATE_NOOP("LinkState", "Brak adaptera")),
    LinkState.ADAPTER_READY: ("●", QT_TRANSLATE_NOOP("LinkState", "Adapter dostępny")),
    LinkState.WAITING_MCU: ("⏳", QT_TRANSLATE_NOOP("LinkState", "Oczekiwanie na zasilenie MCU")),
    LinkState.IDENTIFYING: ("⟳", QT_TRANSLATE_NOOP("LinkState", "Trwa identyfikacja")),
    LinkState.PROGRAMMING: ("⟳", QT_TRANSLATE_NOOP("LinkState", "Trwa programowanie")),
    LinkState.MCU_DETECTED: ("✔", QT_TRANSLATE_NOOP("LinkState", "Mikrokontroler wykryty")),
    LinkState.TIMEOUT: ("⚠", QT_TRANSLATE_NOOP("LinkState", "Przekroczono czas oczekiwania")),
    LinkState.ERROR: ("✖", QT_TRANSLATE_NOOP("LinkState", "Błąd komunikacji")),
}


def describe(state: LinkState) -> tuple[str, str]:
    """(glif, przetłumaczony opis) stanu połączenia."""
    glyph, text = DESCRIPTIONS[state]
    return glyph, Q.translate("LinkState", text)
