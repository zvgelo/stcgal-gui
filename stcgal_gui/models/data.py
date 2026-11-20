"""Modele danych współdzielone przez GUI, rdzeń i backendy (bez zależności od Qt)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

PROTOCOLS: tuple[str, ...] = (
    "auto",
    "stc89",
    "stc89a",
    "stc12a",
    "stc12b",
    "stc12",
    "stc15a",
    "stc15",
    "stc8",
    "stc8d",
    "stc8g",
    "usb15",
)


class OperationKind(Enum):
    """Rodzaj operacji wykonywanej przez backend."""

    IDENTIFY = "identify"
    PROGRAM = "program"
    ERASE = "erase"


class WriteScope(Enum):
    """Zakres zapisu zatwierdzony przez użytkownika (patrz core/safety.py)."""

    FLASH_ONLY = "flash_only"
    FLASH_AND_EEPROM = "flash_and_eeprom"
    ERASE_ONLY = "erase_only"


class OperationState(Enum):
    """Stan cyklu życia operacji."""

    IDLE = "idle"
    WAITING_FOR_MCU = "waiting_for_mcu"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ErrorKind(Enum):
    """Sklasyfikowana przyczyna niepowodzenia (do diagnostyki)."""

    NONE = "none"
    PERMISSION = "permission"
    PORT_BUSY = "port_busy"
    PORT_MISSING = "port_missing"
    DEVICE_LOST = "device_lost"
    TIMEOUT = "timeout"
    HANDSHAKE = "handshake"
    PROTOCOL = "protocol"
    OPTION = "option"
    BACKEND_MISSING = "backend_missing"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PortInfo:
    """Port szeregowy wykryty w systemie."""

    device: str
    description: str = ""
    vid: int | None = None
    pid: int | None = None
    manufacturer: str = ""
    serial_number: str = ""
    by_id: str | None = None
    location: str = ""
    is_ch340: bool = False
    accessible: bool = True

    @property
    def vid_pid(self) -> str:
        if self.vid is None or self.pid is None:
            return ""
        return f"{self.vid:04x}:{self.pid:04x}"


@dataclass
class ConnectionParams:
    """Parametry połączenia z MCU."""

    port: str
    protocol: str = "auto"
    baud: int = 115200
    handshake_baud: int = 2400
    debug: bool = False
    autoreset: bool = False
    resetpin: str = "dtr"
    timeout_s: float = 60.0


@dataclass
class McuInfo:
    """Informacje faktycznie zwrócone przez backend (nic nie jest zgadywane)."""

    protocol: str | None = None
    model: str | None = None
    magic: str | None = None
    code_flash_kb: float | None = None
    eeprom_kb: float | None = None
    frequency_mhz: float | None = None
    bsl_version: str | None = None
    wakeup_khz: float | None = None
    ref_voltage_mv: int | None = None
    mfg_date: str | None = None
    options: dict[str, str] = field(default_factory=dict)
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def code_bytes(self) -> int | None:
        return None if self.code_flash_kb is None else round(self.code_flash_kb * 1024)

    @property
    def eeprom_bytes(self) -> int | None:
        return None if self.eeprom_kb is None else round(self.eeprom_kb * 1024)

    @property
    def is_empty(self) -> bool:
        return self.model is None and self.magic is None


@dataclass
class ProgramParams:
    """Parametry zapisu. Wymaga jawnego potwierdzenia przez użytkownika."""

    code_image: Path
    eeprom_image: Path | None = None
    trim_khz: float | None = None
    options: list[str] = field(default_factory=list)  # pary klucz=wartość (-o)


@dataclass
class Progress:
    """Rzeczywisty postęp zgłoszony przez backend."""

    done: int
    total: int
    label: str = ""

    @property
    def percent(self) -> float:
        return 0.0 if self.total <= 0 else 100.0 * self.done / self.total


@dataclass
class OperationResult:
    """Wynik zakończonej operacji."""

    kind: OperationKind
    state: OperationState
    return_code: int | None = None
    error_kind: ErrorKind = ErrorKind.NONE
    message: str = ""
    mcu: McuInfo | None = None
    argv: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    verified: bool = False  # True wyłącznie, gdy backend faktycznie zweryfikował zapis
    programmed: bool = False

    @property
    def ok(self) -> bool:
        return self.state is OperationState.FINISHED
