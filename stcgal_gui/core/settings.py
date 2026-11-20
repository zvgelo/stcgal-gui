"""Ustawienia aplikacji (QSettings)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QByteArray, QSettings


@dataclass
class AppSettings:
    """Wartości konfigurowane przez użytkownika."""

    default_port: str = ""
    protocol: str = "auto"
    baud: int = 115200
    handshake_baud: int = 2400
    timeout_s: int = 60
    theme: str = "system"  # system | light | dark
    language: str = "system"  # system | pl | en (zmiana po ponownym uruchomieniu)
    firmware_dir: str = ""
    log_level: str = "INFO"
    stcgal_path: str = ""
    debug: bool = False
    autoreset: bool = False


def _to_int(value: object, default: int) -> int:
    """Odporna konwersja wartości z QSettings (mogą być tekstem lub uszkodzone)."""
    try:
        return int(str(value))
    except ValueError:
        return default


class SettingsStore:
    """Cienka warstwa nad QSettings."""

    def __init__(self, qs: QSettings | None = None) -> None:
        self._qs = qs or QSettings("stcgal-gui", "stcgal-gui")

    def load(self) -> AppSettings:
        s = AppSettings()
        q = self._qs
        s.default_port = str(q.value("default_port", s.default_port))
        s.protocol = str(q.value("protocol", s.protocol))
        s.baud = _to_int(q.value("baud", s.baud), s.baud)
        s.handshake_baud = _to_int(q.value("handshake_baud", s.handshake_baud), s.handshake_baud)
        s.timeout_s = _to_int(q.value("timeout_s", s.timeout_s), s.timeout_s)
        s.theme = str(q.value("theme", s.theme))
        s.language = str(q.value("language", s.language))
        if s.language not in ("system", "pl", "en"):
            s.language = "system"
        s.firmware_dir = str(q.value("firmware_dir", s.firmware_dir))
        s.log_level = str(q.value("log_level", s.log_level))
        s.stcgal_path = str(q.value("stcgal_path", s.stcgal_path))
        s.debug = str(q.value("debug", "false")).lower() == "true"
        s.autoreset = str(q.value("autoreset", "false")).lower() == "true"
        return s

    def save(self, s: AppSettings) -> None:
        for key, value in vars(s).items():
            self._qs.setValue(key, value)
        self._qs.sync()

    def save_geometry(self, geometry: QByteArray, state: QByteArray) -> None:
        self._qs.setValue("window/geometry", geometry)
        self._qs.setValue("window/state", state)

    def load_geometry(self) -> tuple[QByteArray | None, QByteArray | None]:
        g = self._qs.value("window/geometry")
        st = self._qs.value("window/state")
        return (
            g if isinstance(g, QByteArray) else None,
            st if isinstance(st, QByteArray) else None,
        )
