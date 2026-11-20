"""Polityka bezpieczeństwa zapisu: ochrona EEPROM/IAP i konfiguracji (option bytes) MCU.

Zasada: jeżeli backend nie potrafi TECHNICZNIE zagwarantować zachowania EEPROM i opcji,
zapis jest zablokowany. Ryzyka „miękkie” może świadomie zaakceptować wyłącznie użytkownik
(osobne potwierdzenie, nigdy utrwalane); ryzyka „twarde” nie da się obejść.

Fakty o stcgal 1.10 (źródła protokołów STC15/STC8, ``frontend.py``) - patrz docs/SAFETY.md:

* ``erase_flash``: komenda ``0x03``; autorzy stcgal opisują ją „always seems to erase everything”.
  Wariant ``0x01`` (jawne kasowanie flash **i EEPROM**) jest wysyłany, gdy obraz jest większy niż
  pamięć kodu albo podano obraz EEPROM.
* ``program_options``: ZAWSZE zapisuje blok opcji (bajty MSR z układu + ewentualne ``-o``) oraz
  trim częstotliwości; ``handshake()`` rekalibruje zegar. Nie ma trybu „tylko flash”.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QCoreApplication as Q

from stcgal_gui.backends.base import Capabilities, SafetyError, WriteConfirmation
from stcgal_gui.core.i18n import fmt
from stcgal_gui.models.data import McuInfo, ProgramParams, WriteScope


@dataclass(frozen=True)
class Risk:
    """Pojedyncze ryzyko operacji. ``hard`` = nie do obejścia."""

    id: str
    title: str
    detail: str
    hard: bool = False


def effective_code_bytes(mcu: McuInfo | None) -> int | None:
    """Pojemność obszaru kodu: mniejsza z bazy modeli stcgal i podziału odczytanego z układu."""
    if mcu is None or mcu.code_bytes is None:
        return None
    sizes = [mcu.code_bytes]
    split = mcu.options.get("program_eeprom_split", "")
    if split.isdigit() and int(split) > 0:
        sizes.append(int(split))
    return min(sizes)


def requested_split(options: list[str]) -> int | None:
    """Wartość ``program_eeprom_split`` z opcji ``-o`` (bajty), jeśli podano poprawną."""
    for opt in options:
        key, _, value = opt.partition("=")
        if key == "program_eeprom_split":
            try:
                return int(value, 0)
            except ValueError:
                return None
    return None


def _file_size(path: Path) -> int | None:
    try:
        from stcgal_gui.core.firmware import load_firmware

        return load_firmware(path).size
    except Exception:  # noqa: BLE001 - niepoprawny plik = brak rozmiaru (blokada niżej)
        return None


def assess(
    caps: Capabilities,
    prog: ProgramParams,
    scope: WriteScope,
    mcu_code_bytes: int | None,
    expert: bool = False,
    image_size: int | None = None,
) -> list[Risk]:
    """Zwraca wszystkie ryzyka zapisu (twarde i miękkie).

    Tryb eksperta (świadomie włączony) zamienia część ryzyk twardych w miękkie: zmiana opcji
    (``-o``), trim (``-t``) i obraz nachodzący na EEPROM wymagają wtedy dodatkowego potwierdzenia.
    ``image_size`` nadpisuje rozmiar obrazu (np. po dodaniu offsetu).
    """
    if not isinstance(scope, WriteScope):
        raise TypeError("scope musi być WriteScope")
    risks: list[Risk] = []
    if scope is WriteScope.ERASE_ONLY:
        risks.append(
            Risk(
                "wrong_scope",
                Q.translate("Safety", "Zły zakres operacji"),
                Q.translate("Safety", "Kasowanie ma osobną ścieżkę (erase)."),
                hard=True,
            )
        )
    requested = requested_split(prog.options)
    if requested is not None and mcu_code_bytes is not None:
        mcu_code_bytes = min(
            mcu_code_bytes, requested
        )  # stcgal użyje żądanego podziału jako obszaru kodu
    if prog.options:
        if expert:
            title = Q.translate("Safety", "Zmiana opcji MCU (-o)")
            detail = fmt(
                Q.translate(
                    "Safety",
                    "Zmieniane są option bytes (EEPROM, zegar, watchdog, reset, UART): %1. "
                    "Nieprawidłowa wartość może zablokować układ lub zmienić jego działanie.",
                ),
                ", ".join(prog.options),
            )
        else:
            title = Q.translate("Safety", "Zmiana opcji (-o) jest zabroniona")
            detail = fmt(
                Q.translate(
                    "Safety", "Zmieniane są option bytes (EEPROM, zegar, watchdog, reset, UART): %1"
                ),
                ", ".join(prog.options),
            )
        risks.append(Risk("options_requested", title, detail, hard=not expert))
    if prog.trim_khz is not None:
        risks.append(
            Risk(
                "trim_requested",
                Q.translate("Safety", "Zmiana częstotliwości (-t)")
                if expert
                else Q.translate("Safety", "Zmiana częstotliwości (-t) jest zabroniona"),
                Q.translate(
                    "Safety",
                    "Trim częstotliwości RC jest częścią option bytes; zmieni się zegar układu.",
                ),
                hard=not expert,
            )
        )
    if scope is WriteScope.FLASH_ONLY and prog.eeprom_image is not None:
        risks.append(
            Risk(
                "eeprom_in_flash_scope",
                Q.translate("Safety", "Obraz EEPROM w zapisie tylko-Flash"),
                Q.translate(
                    "Safety",
                    "Zapis Flash nie może zawierać obrazu EEPROM - użyj osobnej operacji „Flash + EEPROM”.",
                ),
                hard=True,
            )
        )
    if scope is WriteScope.FLASH_AND_EEPROM and prog.eeprom_image is None:
        risks.append(
            Risk(
                "eeprom_image_missing",
                Q.translate("Safety", "Brak obrazu EEPROM"),
                Q.translate("Safety", "Operacja „Flash + EEPROM” wymaga pliku z danymi EEPROM."),
                hard=True,
            )
        )
    if mcu_code_bytes is None:
        risks.append(
            Risk(
                "mcu_unknown",
                Q.translate("Safety", "MCU nie został zidentyfikowany"),
                Q.translate(
                    "Safety",
                    "Bez identyfikacji nie można sprawdzić, czy obraz mieści się w pamięci kodu. "
                    "Najpierw użyj „Wykryj mikrokontroler”.",
                ),
                hard=True,
            )
        )
    else:
        size = image_size if image_size is not None else _file_size(prog.code_image)
        if size is None:
            risks.append(
                Risk(
                    "image_invalid",
                    Q.translate("Safety", "Nieczytelny obraz firmware"),
                    Q.translate("Safety", "Nie udało się odczytać rozmiaru obrazu."),
                    hard=True,
                )
            )
        elif size > mcu_code_bytes:
            risks.append(
                Risk(
                    "image_exceeds_flash",
                    Q.translate("Safety", "Obraz nachodzi na EEPROM/IAP"),
                    fmt(
                        Q.translate(
                            "Safety",
                            "Obraz (%1 B) jest większy niż pamięć kodu (%2 B). stcgal wysłałby "
                            "wtedy jawne kasowanie Flash i EEPROM oraz zapisałby dane w obszarze EEPROM.",
                        ),
                        size,
                        mcu_code_bytes,
                    ),
                    hard=not expert,
                )
            )
    if scope is WriteScope.FLASH_AND_EEPROM:
        risks.append(
            Risk(
                "eeprom_overwrite",
                Q.translate("Safety", "EEPROM/IAP zostanie nadpisany"),
                Q.translate(
                    "Safety",
                    "Ta operacja kasuje i nadpisuje dane w EEPROM/IAP (poza Flash). Dane nie podlegają "
                    "odzyskaniu. Aplikacja nie potrafi odczytać EEPROM, więc nie wykona kopii.",
                ),
            )
        )
    if not caps.preserves_eeprom:
        risks.append(
            Risk(
                "erase_scope_unverified",
                Q.translate("Safety", "Backend nie gwarantuje zachowania EEPROM/IAP"),
                Q.translate(
                    "Safety",
                    "Komenda kasowania stcgal („always seems to erase everything”) może objąć także "
                    "EEPROM/IAP, nawet przy zapisie samego Flash. Zawartość EEPROM może zostać utracona.",
                ),
            )
        )
    if not caps.preserves_options:
        risks.append(
            Risk(
                "option_rewrite",
                Q.translate("Safety", "Backend nie gwarantuje zachowania konfiguracji MCU"),
                Q.translate(
                    "Safety",
                    "stcgal zawsze zapisuje blok option bytes (bieżące wartości z układu) i rekalibruje oraz "
                    "zapisuje trim częstotliwości - zegar (np. 11,05 MHz) może zmienić się nieznacznie, a "
                    "opcje nie są weryfikowane po zapisie.",
                ),
            )
        )
    return risks


def assess_erase(caps: Capabilities, mcu_code_bytes: int | None, expert: bool) -> list[Risk]:
    """Ryzyka samego kasowania Flash (``stcgal -e``) - tylko w trybie eksperta."""
    risks: list[Risk] = []
    if not expert:
        risks.append(
            Risk(
                "erase_requires_expert",
                Q.translate("Safety", "Kasowanie wymaga trybu eksperta"),
                Q.translate(
                    "Safety", "Samo kasowanie Flash jest dostępne wyłącznie w trybie eksperta."
                ),
                hard=True,
            )
        )
    if mcu_code_bytes is None:
        risks.append(
            Risk(
                "mcu_unknown",
                Q.translate("Safety", "MCU nie został zidentyfikowany"),
                Q.translate("Safety", "Najpierw użyj „Wykryj mikrokontroler”."),
                hard=True,
            )
        )
    risks.append(
        Risk(
            "erase_destructive",
            Q.translate("Safety", "Kasowanie usunie program z Flash"),
            Q.translate("Safety", "Zawartość pamięci programu zostanie nieodwracalnie skasowana."),
        )
    )
    if not caps.preserves_eeprom:
        risks.append(
            Risk(
                "erase_scope_unverified",
                Q.translate("Safety", "Backend nie gwarantuje zachowania EEPROM/IAP"),
                Q.translate(
                    "Safety",
                    "Komenda kasowania stcgal („always seems to erase everything”) może objąć także EEPROM/IAP.",
                ),
            )
        )
    return risks


def _require_model(conf: WriteConfirmation) -> None:
    if not conf.expected_model:
        raise SafetyError(
            Q.translate(
                "Safety",
                "Operacja wymaga znanego modelu zidentyfikowanego MCU (kontrola zgodności układu).",
            )
        )


def enforce_erase(caps: Capabilities, conf: WriteConfirmation) -> None:
    """Egzekwowanie polityki dla samego kasowania (backend)."""
    _require_model(conf)
    blocking = unresolved(assess_erase(caps, conf.mcu_code_bytes, conf.expert), conf.acknowledged)
    if blocking:
        raise SafetyError(
            Q.translate("Safety", "Kasowanie zablokowane ze względów bezpieczeństwa:")
            + "\n"
            + format_risks(blocking)
        )


def unresolved(risks: list[Risk], acknowledged: frozenset[str]) -> list[Risk]:
    """Ryzyka, które nadal blokują operację (twarde lub niepotwierdzone miękkie)."""
    return [r for r in risks if r.hard or r.id not in acknowledged]


def format_risks(risks: list[Risk]) -> str:
    return "\n".join(f"• {r.title}: {r.detail}" for r in risks)


def enforce(caps: Capabilities, prog: ProgramParams, conf: WriteConfirmation) -> None:
    """Egzekwowanie polityki w backendzie (ostatnia linia obrony, niezależna od GUI)."""
    _require_model(conf)
    blocking = unresolved(
        assess(caps, prog, conf.scope, conf.mcu_code_bytes, conf.expert), conf.acknowledged
    )
    if blocking:
        raise SafetyError(
            Q.translate(
                "Safety", "Zapis zablokowany ze względów bezpieczeństwa EEPROM/konfiguracji MCU:"
            )
            + "\n"
            + format_risks(blocking)
        )
