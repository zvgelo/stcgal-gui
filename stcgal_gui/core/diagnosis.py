"""Komunikaty i wskazówki diagnostyczne zależne od systemu."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QT_TRANSLATE_NOOP
from PySide6.QtCore import QCoreApplication as Q

from stcgal_gui import platform_support as ps
from stcgal_gui.models.data import ErrorKind

_USER_LINUX: dict[ErrorKind, Any] = {
    ErrorKind.PERMISSION: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Brak uprawnień do portu. Dodaj użytkownika do grupy „dialout” "
        "(sudo usermod -aG dialout $USER) i zaloguj się ponownie.",
    ),
    ErrorKind.PORT_BUSY: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Port jest zajęty przez inny proces (np. ModemManager, terminal szeregowy, "
        "druga instancja programu). Zamknij go i spróbuj ponownie.",
    ),
    ErrorKind.PORT_MISSING: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Port nie istnieje. Sprawdź połączenie programatora USB i odśwież listę portów.",
    ),
}
_USER_WINDOWS: dict[ErrorKind, Any] = {
    ErrorKind.PERMISSION: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Brak dostępu do portu COM. Zamknij programy używające portu (terminal szeregowy, "
        "inne narzędzia ISP, druga instancja) lub sprawdź politykę dostępu do urządzeń.",
    ),
    ErrorKind.PORT_BUSY: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Port COM jest zajęty (Windows zgłasza „Access is denied”). Zamknij inny program "
        "używający tego portu i spróbuj ponownie.",
    ),
    ErrorKind.PORT_MISSING: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Port COM nie istnieje. Sprawdź kabel USB, Menedżer urządzeń i odśwież listę portów - "
        "numer COM mógł się zmienić.",
    ),
}
_USER_COMMON: dict[ErrorKind, Any] = {
    ErrorKind.DEVICE_LOST: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Utracono połączenie z adapterem USB-UART (odłączony lub zresetowany). "
        "Podłącz go ponownie, odśwież listę portów i powtórz operację.",
    ),
}

_TROUBLE_LINUX: dict[ErrorKind, Any] = {
    ErrorKind.PERMISSION: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Uprawnienia: sprawdź `id -nG` (grupa dialout) i `ls -l` na porcie; po `usermod` wyloguj się.",
    ),
    ErrorKind.PORT_BUSY: QT_TRANSLATE_NOOP(
        "Diagnosis", "Port zajęty: `fuser -v /dev/ttyUSB0`, `systemctl status ModemManager`."
    ),
    ErrorKind.PORT_MISSING: QT_TRANSLATE_NOOP(
        "Diagnosis", "Brak portu: `dmesg | tail`, `lsusb` (oczekiwane 1a86:7523, sterownik ch341)."
    ),
    ErrorKind.BACKEND_MISSING: QT_TRANSLATE_NOOP(
        "Diagnosis", "Backend: `pipx install stcgal` lub wskaż ścieżkę w Ustawieniach."
    ),
}
_TROUBLE_WINDOWS: dict[ErrorKind, Any] = {
    ErrorKind.PERMISSION: QT_TRANSLATE_NOOP(
        "Diagnosis", "Dostęp: zamknij inne programy używające COM; uruchom ponownie aplikację."
    ),
    ErrorKind.PORT_BUSY: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Port zajęty: zamknij terminale szeregowe/inne programmery; w Menedżerze urządzeń sprawdź numer COM.",
    ),
    ErrorKind.BACKEND_MISSING: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Backend: pakiet aplikacji jest niekompletny (brak stcgal-backend.exe) - zainstaluj ponownie.",
    ),
    ErrorKind.PORT_MISSING: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Brak portu: Menedżer urządzeń → Porty (COM i LPT); oczekiwany „USB-SERIAL CH340 (COMx)”, VID_1A86&PID_7523.",
    ),
}
_TROUBLE_COMMON: dict[ErrorKind, Any] = {
    ErrorKind.DEVICE_LOST: QT_TRANSLATE_NOOP(
        "Diagnosis", "Utrata urządzenia: sprawdź kabel/hub USB, zasilanie i ponownie wykryj port."
    ),
    ErrorKind.TIMEOUT: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Timeout: wyłącz i włącz zasilanie MCU zaraz po starcie wykrywania; nie odłączaj CH340; sprawdź TX↔RX, GND, poziomy logiczne.",
    ),
    ErrorKind.HANDSHAKE: QT_TRANSLATE_NOOP(
        "Diagnosis",
        "Handshake: wybierz protokół ręcznie (STC8H → stc8d) lub obniż prędkość handshake.",
    ),
    ErrorKind.PROTOCOL: QT_TRANSLATE_NOOP(
        "Diagnosis", "Protokół: spróbuj niższego baud, krótszych przewodów i stabilnego zasilania."
    ),
}


def backend_missing_message(windows: bool | None = None) -> str:
    if ps.IS_WINDOWS if windows is None else windows:
        return Q.translate(
            "Diagnosis",
            "Nie znaleziono wbudowanego backendu (stcgal-backend.exe). Pakiet aplikacji jest "
            "uszkodzony lub niekompletny - zainstaluj ponownie albo wskaż stcgal w Ustawieniach.",
        )
    return Q.translate(
        "Diagnosis",
        "Nie znaleziono programu stcgal. Zainstaluj: pipx install stcgal lub wskaż ścieżkę w Ustawieniach.",
    )


def user_message(kind: ErrorKind, windows: bool | None = None) -> str | None:
    """Opis błędu dla użytkownika (zależny od systemu) albo ``None``."""
    table = _USER_WINDOWS if (ps.IS_WINDOWS if windows is None else windows) else _USER_LINUX
    text = _USER_COMMON.get(kind) or table.get(kind)
    return Q.translate("Diagnosis", text) if text else None


def troubleshooting_hint(kind: ErrorKind, windows: bool | None = None) -> str:
    """Krótka wskazówka diagnostyczna (polecenia/miejsca do sprawdzenia)."""
    table = _TROUBLE_WINDOWS if (ps.IS_WINDOWS if windows is None else windows) else _TROUBLE_LINUX
    text = table.get(kind) or _TROUBLE_COMMON.get(kind, "")
    return Q.translate("Diagnosis", text) if text else ""
