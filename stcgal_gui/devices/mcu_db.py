"""Wiedza o doborze protokołu - odzwierciedla tablicę autodetekcji stcgal 1.10.

Źródło: ``stcgal.protocols.StcAutoProtocol.initialize_model``. Używane tylko do
OSTRZEŻEŃ w GUI (np. wybrano stc8g, a stcgal dla STC8H8K64U wybiera stc8d).
"""

from __future__ import annotations

import re

from PySide6.QtCore import QCoreApplication as Q

from stcgal_gui.core.i18n import fmt

_PROTOCOL_DB: tuple[tuple[str, str], ...] = (
    ("stc89", r"STC(89|90)(C|LE)\d"),
    ("stc12a", r"STC12(C|LE)\d052"),
    ("stc12b", r"STC12(C|LE)(52|56)"),
    ("stc12", r"(STC|IAP)(10|11|12)\D"),
    ("stc15a", r"(STC|IAP)15[FL][012]0\d(E|EA|)$"),
    ("stc15", r"(STC|IAP|IRC)15\D"),
    ("stc8g", r"STC8H1K\d\d$"),
    ("stc8g", r"STC8G"),
    ("stc8d", r"STC8H"),
    ("stc8d", r"STC32"),
    ("stc8d", r"STC8A8K\d\dD\d"),
    ("stc8", r"STC8\D"),
)


def expected_protocol(model_name: str) -> str | None:
    """Protokół, który stcgal 1.10 autodetekcją wybiera dla danego modelu."""
    for protocol, pattern in _PROTOCOL_DB:
        if re.match(pattern, model_name):
            return protocol
    return None


def protocol_warning(model_name: str | None, selected: str) -> str | None:
    """Tekst ostrzeżenia, gdy wybrany protokół różni się od oczekiwanego."""
    if not model_name or selected == "auto":
        return None
    expected = expected_protocol(model_name)
    if expected and expected != selected:
        return fmt(
            Q.translate(
                "McuDb",
                "Dla %1 stcgal w trybie auto używa protokołu „%2”, "
                "a wybrano „%3”. Niezgodny protokół może uniemożliwić zapis.",
            ),
            model_name,
            expected,
            selected,
        )
    return None
