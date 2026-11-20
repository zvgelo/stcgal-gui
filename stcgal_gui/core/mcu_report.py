"""Opisy opcji bootloadera, grupowanie i raport tekstowy o MCU."""

from __future__ import annotations

import platform
from datetime import datetime
from typing import Any

from PySide6.QtCore import QT_TRANSLATE_NOOP
from PySide6.QtCore import QCoreApplication as Q

from stcgal_gui import __version__
from stcgal_gui.core.i18n import fmt
from stcgal_gui.models.data import McuInfo

# nazwa techniczna -> (grupa, przyjazny opis)
OPTION_INFO: dict[str, tuple[Any, Any]] = {
    "reset_pin_enabled": (
        QT_TRANSLATE_NOOP("McuReport", "Reset i zasilanie"),
        QT_TRANSLATE_NOOP("McuReport", "Pin RST jako wejście resetu"),
    ),
    "low_voltage_reset": (
        QT_TRANSLATE_NOOP("McuReport", "Reset i zasilanie"),
        QT_TRANSLATE_NOOP("McuReport", "Reset przy niskim napięciu (LVD)"),
    ),
    "low_voltage_threshold": (
        QT_TRANSLATE_NOOP("McuReport", "Reset i zasilanie"),
        QT_TRANSLATE_NOOP("McuReport", "Próg niskiego napięcia"),
    ),
    "por_reset_delay": (
        QT_TRANSLATE_NOOP("McuReport", "Reset i zasilanie"),
        QT_TRANSLATE_NOOP("McuReport", "Opóźnienie resetu po włączeniu zasilania"),
    ),
    "rstout_por_state": (
        QT_TRANSLATE_NOOP("McuReport", "Reset i zasilanie"),
        QT_TRANSLATE_NOOP("McuReport", "Stan wyjścia P2.0 po resecie"),
    ),
    "watchdog_por_enabled": (
        QT_TRANSLATE_NOOP("McuReport", "Watchdog"),
        QT_TRANSLATE_NOOP("McuReport", "Watchdog włączony po włączeniu zasilania"),
    ),
    "watchdog_stop_idle": (
        QT_TRANSLATE_NOOP("McuReport", "Watchdog"),
        QT_TRANSLATE_NOOP("McuReport", "Zatrzymanie watchdoga w trybie idle"),
    ),
    "watchdog_prescale": (
        QT_TRANSLATE_NOOP("McuReport", "Watchdog"),
        QT_TRANSLATE_NOOP("McuReport", "Dzielnik watchdoga"),
    ),
    "clock_gain": (
        QT_TRANSLATE_NOOP("McuReport", "Zegar"),
        QT_TRANSLATE_NOOP("McuReport", "Wzmocnienie oscylatora"),
    ),
    "uart1_remap": (
        QT_TRANSLATE_NOOP("McuReport", "UART"),
        QT_TRANSLATE_NOOP("McuReport", "Przemapowanie UART1"),
    ),
    "uart2_passthrough": (
        QT_TRANSLATE_NOOP("McuReport", "UART"),
        QT_TRANSLATE_NOOP("McuReport", "Przelot UART2"),
    ),
    "uart2_pin_mode": (
        QT_TRANSLATE_NOOP("McuReport", "UART"),
        QT_TRANSLATE_NOOP("McuReport", "Tryb pinów UART2"),
    ),
    "bsl_pindetect_enabled": (
        QT_TRANSLATE_NOOP("McuReport", "Bootloader i EEPROM"),
        QT_TRANSLATE_NOOP("McuReport", "Wejście do bootloadera po stanie pinu"),
    ),
    "eeprom_erase_enabled": (
        QT_TRANSLATE_NOOP("McuReport", "Bootloader i EEPROM"),
        QT_TRANSLATE_NOOP("McuReport", "Kasowanie EEPROM razem z flash"),
    ),
    "program_eeprom_split": (
        QT_TRANSLATE_NOOP("McuReport", "Bootloader i EEPROM"),
        QT_TRANSLATE_NOOP("McuReport", "Podział flash/EEPROM (bajty)"),
    ),
    "epwm_open_drain": (
        QT_TRANSLATE_NOOP("McuReport", "Inne"),
        QT_TRANSLATE_NOOP("McuReport", "Wyjścia EPWM jako open-drain"),
    ),
}
GROUP_ORDER: tuple[Any, ...] = (
    QT_TRANSLATE_NOOP("McuReport", "Reset i zasilanie"),
    QT_TRANSLATE_NOOP("McuReport", "Watchdog"),
    QT_TRANSLATE_NOOP("McuReport", "Zegar"),
    QT_TRANSLATE_NOOP("McuReport", "UART"),
    QT_TRANSLATE_NOOP("McuReport", "Bootloader i EEPROM"),
    QT_TRANSLATE_NOOP("McuReport", "Inne"),
)

SOURCE_DB: Any = QT_TRANSLATE_NOOP(
    "McuReport", "baza modeli stcgal (wg identyfikatora, nie pomiar)"
)
SOURCE_CHIP: Any = QT_TRANSLATE_NOOP("McuReport", "odpowiedź bootloadera układu")


def _t(text: object) -> str:
    return Q.translate("McuReport", str(text))


def source_chip() -> str:
    return _t(SOURCE_CHIP)


def source_db() -> str:
    return _t(SOURCE_DB)


def option_label(name: str) -> str:
    """Przyjazny opis opcji (przetłumaczony) albo sama nazwa techniczna."""
    info = OPTION_INFO.get(name)
    return _t(info[1]) if info else name


def grouped_options(mcu: McuInfo) -> dict[str, list[tuple[str, str, str]]]:
    """Opcje pogrupowane: grupa -> [(opis, nazwa techniczna, wartość)]."""
    groups: dict[str, list[tuple[str, str, str]]] = {}
    for name, value in mcu.options.items():
        group = OPTION_INFO[name][0] if name in OPTION_INFO else OPTION_INFO["epwm_open_drain"][0]
        groups.setdefault(group, []).append((option_label(name), name, value))
    return {_t(g): groups[g] for g in GROUP_ORDER if g in groups}


def _v(value: object, unit: str = "") -> str:
    return "-" if value is None else f"{value}{unit}"


def build_report(mcu: McuInfo, port: str | None = None) -> str:
    """Raport tekstowy (Markdown) z podaniem źródła każdej grupy danych."""
    chip, db = source_chip(), source_db()
    l_0 = Q.translate("McuReport", "Model")
    l_1 = Q.translate("McuReport", "Identyfikator (magic)")
    l_2 = Q.translate("McuReport", "Protokół")
    l_3 = Q.translate("McuReport", "Bootloader")
    l_4 = Q.translate("McuReport", "Flash (kod)")
    l_5 = Q.translate("McuReport", "Częstotliwość")
    l_6 = Q.translate("McuReport", "Zegar wybudzania")
    l_7 = Q.translate("McuReport", "Data produkcji")
    l_8 = Q.translate("McuReport", "Dodatkowe")
    lines = [
        fmt(
            Q.translate("McuReport", "# Raport MCU - %1"),
            mcu.model or Q.translate("McuReport", "nieznany"),
        ),
        fmt(
            Q.translate("McuReport", "Wygenerowano: %1 · stcgal-gui %2 · Python %3"),
            f"{datetime.now():%Y-%m-%d %H:%M:%S}",
            __version__,
            platform.python_version(),
        ),
        fmt(Q.translate("McuReport", "Port: %1"), port or "-"),
        "",
        fmt(Q.translate("McuReport", "## Podstawowe (źródło: %1)"), chip),
        f"- {l_0}: {_v(mcu.model)}",
        f"- {l_1}: {_v(mcu.magic and '0x' + mcu.magic)}",
        f"- {l_2}: {_v(mcu.protocol)}",
        f"- {l_3}: {_v(mcu.bsl_version)}",
        "",
        fmt(Q.translate("McuReport", "## Pamięć (źródło: %1)"), db),
        f"- {l_4}: {_v(mcu.code_bytes, ' B')}",
        f"- EEPROM/IAP: {_v(mcu.eeprom_bytes, ' B')}",
        "",
        fmt(Q.translate("McuReport", "## Zegar i zasilanie (źródło: %1)"), chip),
        f"- {l_5}: {_v(mcu.frequency_mhz, ' MHz')}",
        f"- {l_6}: {_v(mcu.wakeup_khz, ' kHz')}",
        f"- Vref: {_v(mcu.ref_voltage_mv, ' mV')}",
        f"- {l_7}: {_v(mcu.mfg_date)}",
        "",
        fmt(Q.translate("McuReport", "## Konfiguracja (źródło: %1; tylko odczyt)"), chip),
    ]
    for group, rows in grouped_options(mcu).items():
        lines.append(f"### {group}")
        lines += [f"- {desc} (`{name}`): {value}" for desc, name, value in rows]
    if mcu.extra:
        lines.append(f"### {l_8}")
        lines += [f"- {k}: {v}" for k, v in mcu.extra.items()]
    return "\n".join(lines) + "\n"
