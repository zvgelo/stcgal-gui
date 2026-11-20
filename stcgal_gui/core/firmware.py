"""Walidacja plików firmware BIN/HEX zgodnie z zachowaniem stcgal."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QCoreApplication as Q

from stcgal_gui.core.i18n import fmt
from stcgal_gui.models.data import McuInfo

HEX_EXTENSIONS = (".hex", ".ihx", ".ihex")
BIN_EXTENSIONS = (".bin",)
MAX_FILE_BYTES = 16 * 1024 * 1024


class FirmwareError(ValueError):
    """Plik firmware jest niepoprawny."""


@dataclass
class FirmwareInfo:
    """Wynik analizy pliku."""

    path: Path
    fmt: str  # "bin" | "hex"
    size: int  # rozmiar obrazu, który stcgal faktycznie zapisze (przed dopełnieniem do 512 B)
    warnings: list[str] = field(default_factory=list)


def _looks_like_hex(head: bytes) -> bool:
    first = head.lstrip(b"\xef\xbb\xbf \t\r\n")[:1]
    return first == b":"


class _Areas:
    """Odwzorowanie ``stcgal.ihex.IHex`` (insert_data/extract_data) - rozmiar MUSI być identyczny
    z tym, co zapisze stcgal: sklejanie obszarów, nadpisywanie przez „splice”, brak zastosowania
    adresu bazowego (rekordy 02/04 są ignorowane przez extract_data)."""

    def __init__(self) -> None:
        self.areas: dict[int, bytes] = {}

    def _get_area(self, addr: int) -> int | None:
        for start, data in self.areas.items():
            if start <= addr <= start + len(data):
                return start
        return None

    def insert(self, istart: int, idata: bytes) -> None:
        iend = istart + len(idata)
        area = self._get_area(istart)
        if area is None:
            self.areas[istart] = idata
        else:
            data = self.areas[area]
            self.areas[area] = data[: istart - area] + idata + data[iend - area :]

    def extract(self) -> bytes:
        out = bytearray()
        for addr, data in self.areas.items():
            if len(out) < addr:
                out[len(out) : addr] = bytes(addr - len(out))
            out[addr : addr + len(data)] = data
        return bytes(out)


def _line(n: int, msg: str) -> str:
    return fmt(Q.translate("Firmware", "Linia %1: %2"), n, msg)


def parse_ihex(text: str) -> bytes:
    """Parsuje Intel HEX do obrazu o TAKIM SAMYM rozmiarze i układzie jak w stcgal 1.10.

    Rzuca ``FirmwareError`` przy błędnej sumie kontrolnej, formacie lub brakującym EOF
    (walidacja ostrzejsza niż stcgal, który nie wymaga rekordu końca).
    """
    areas = _Areas()
    eof = False
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if eof:
            raise FirmwareError(_line(n, Q.translate("Firmware", "dane po rekordzie końca pliku")))
        if not line.startswith(":") or len(line) < 11 or len(line) % 2 == 0:
            raise FirmwareError(_line(n, Q.translate("Firmware", "niepoprawny rekord Intel HEX")))
        try:
            rec = bytes.fromhex(line[1:])
        except ValueError as ex:
            raise FirmwareError(
                _line(n, Q.translate("Firmware", "znaki spoza zapisu szesnastkowego"))
            ) from ex
        length, addr, rtype = rec[0], (rec[1] << 8) | rec[2], rec[3]
        if len(rec) != length + 5:
            raise FirmwareError(_line(n, Q.translate("Firmware", "niezgodna długość rekordu")))
        if sum(rec) & 0xFF:
            raise FirmwareError(_line(n, Q.translate("Firmware", "błędna suma kontrolna")))
        data = rec[4:-1]
        if rtype == 0x00:
            areas.insert(addr, data)  # bez adresu bazowego - tak jak stcgal
        elif rtype == 0x01:
            eof = True
        elif rtype in (0x02, 0x03, 0x04, 0x05):
            pass
        else:
            raise FirmwareError(
                _line(
                    n,
                    fmt(Q.translate("Firmware", "nieznany typ rekordu %1"), f"{rtype:#04x}"),
                )
            )
    if not eof:
        raise FirmwareError(Q.translate("Firmware", "Brak rekordu końca pliku (:00000001FF)"))
    return areas.extract()


def load_firmware(path: Path) -> FirmwareInfo:
    """Waliduje plik i zwraca jego opis. Rzuca ``FirmwareError``."""
    path = Path(path)
    if not path.is_file():
        raise FirmwareError(Q.translate("Firmware", "Plik nie istnieje"))
    size = path.stat().st_size
    if size == 0:
        raise FirmwareError(Q.translate("Firmware", "Plik jest pusty"))
    if size > MAX_FILE_BYTES:
        raise FirmwareError(Q.translate("Firmware", "Plik jest zbyt duży"))
    ext = path.suffix.lower()
    raw = path.read_bytes()
    is_hex_ext = ext in HEX_EXTENSIONS
    if ext not in HEX_EXTENSIONS + BIN_EXTENSIONS:
        raise FirmwareError(
            Q.translate(
                "Firmware",
                "Nieobsługiwane rozszerzenie. stcgal rozpoznaje Intel HEX tylko po rozszerzeniu "
                ".hex/.ihx/.ihex; inne pliki zapisuje jako surowy BIN.",
            )
        )
    warnings: list[str] = []
    if is_hex_ext:
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError as ex:
            raise FirmwareError(
                Q.translate("Firmware", "Plik HEX zawiera znaki spoza ASCII")
            ) from ex
        image = parse_ihex(text)
        if not image:
            raise FirmwareError(Q.translate("Firmware", "Plik HEX nie zawiera danych"))
        return FirmwareInfo(path, "hex", len(image), warnings)
    if _looks_like_hex(raw[:16]):
        raise FirmwareError(
            Q.translate(
                "Firmware",
                "Plik .bin wygląda jak Intel HEX (zaczyna się od „:”). stcgal zapisałby tekst "
                "jako surowe dane - zmień rozszerzenie na .hex.",
            )
        )
    if all(b == 0xFF for b in raw):
        warnings.append(Q.translate("Firmware", "Plik zawiera wyłącznie bajty 0xFF (pusty obraz)."))
    return FirmwareInfo(path, "bin", len(raw), warnings)


def split_from_options(options: list[str], mcu: McuInfo) -> int | None:
    """Wartość program_eeprom_split (bajty) z opcji -o, jeśli podano."""
    for opt in options:
        key, _, value = opt.partition("=")
        if key == "program_eeprom_split":
            try:
                return int(value, 0)
            except ValueError:
                return None
    return None


def check_fit(
    fw: FirmwareInfo,
    mcu: McuInfo | None,
    *,
    eeprom: FirmwareInfo | None = None,
    options: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Porównuje rozmiary z pamięcią MCU. Zwraca (błędy, ostrzeżenia).

    Bez informacji z urządzenia nie da się sprawdzić zgodności - zwracamy ostrzeżenie.
    """
    errors: list[str] = []
    warns: list[str] = []
    if mcu is None or mcu.code_bytes is None:
        warns.append(
            Q.translate(
                "Firmware", "Brak informacji o pamięci MCU - najpierw wykryj mikrokontroler."
            )
        )
        return errors, warns
    code = mcu.code_bytes
    ee = mcu.eeprom_bytes or 0
    split = split_from_options(options or [], mcu)
    if split is not None and code + ee:
        total = code + ee
        code, ee = split, max(total - split, 0)
    if fw.size > code + ee:
        errors.append(
            fmt(
                Q.translate(
                    "Firmware",
                    "Firmware (%1 B) przekracza całą pamięć programu+EEPROM (%2 B); "
                    "stcgal obcina nadmiar.",
                ),
                fw.size,
                code + ee,
            )
        )
    elif fw.size > code:
        warns.append(
            fmt(
                Q.translate(
                    "Firmware",
                    "Firmware (%1 B) wchodzi w obszar EEPROM (kod: %2 B) - "
                    "zostanie zapisany także w segmencie EEPROM.",
                ),
                fw.size,
                code,
            )
        )
    if eeprom is not None:
        if eeprom.size > ee:
            warns.append(
                fmt(
                    Q.translate(
                        "Firmware",
                        "Obraz EEPROM (%1 B) większy niż EEPROM (%2 B) - zostanie obcięty.",
                    ),
                    eeprom.size,
                    ee,
                )
            )
        if fw.size > code:
            warns.append(
                Q.translate(
                    "Firmware",
                    "Obraz kodu nachodzi na EEPROM - stcgal obetnie go, by dopisać obraz EEPROM.",
                )
            )
    return errors, warns


def image_bytes(path: Path) -> bytes:
    """Obraz binarny dokładnie taki, jaki zapisze stcgal (HEX spłaszczony, BIN surowy)."""
    info = load_firmware(path)
    raw = Path(path).read_bytes()
    return parse_ihex(raw.decode("ascii")) if info.fmt == "hex" else raw
