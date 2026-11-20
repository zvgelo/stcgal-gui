"""Strukturalny log zdarzeń budowany ze strumieni stdout/stderr (surowe dane zostają osobno)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
_ERR_RE = re.compile(r"error|exception|traceback|permission denied|failed|interrupted", re.I)
_WARN_RE = re.compile(r"warning|truncated|overflows", re.I)
_DEBUG_RE = re.compile(r"^(<-|->) Packet data:")


@dataclass
class LogEntry:
    """Pojedyncze zdarzenie."""

    ts: datetime
    level: str
    source: str  # app | stdout | stderr
    text: str


def classify(stream: str, line: str) -> str:
    """Poziom wpisu na podstawie strumienia i treści."""
    if stream == "stderr":
        if _DEBUG_RE.match(line):
            return "DEBUG"
        if _ERR_RE.search(line):
            return "ERROR"
        if _WARN_RE.search(line):
            return "WARNING"
        if re.search(r"\d+%\|", line):
            return "INFO"  # pasek postępu tqdm
        return "WARNING"
    if _ERR_RE.search(line):
        return "ERROR"
    if _WARN_RE.search(line):
        return "WARNING"
    return "INFO"


@dataclass
class LogAssembler:
    """Składa fragmenty strumienia w kompletne linie.

    ``\\r`` (paski postępu) zwija kolejne odświeżenia do ostatniego stanu; surowy tekst jest
    przechowywany osobno i nigdy nie jest zmieniany.
    """

    pending: dict[str, str] = field(default_factory=dict)

    def feed(self, stream: str, text: str, now: datetime | None = None) -> list[LogEntry]:
        now = now or datetime.now()
        buf = self.pending.get(stream, "") + text
        entries: list[LogEntry] = []
        *lines, rest = buf.split("\n")
        for line in lines:
            line = line.rstrip("\r").split("\r")[-1]
            if line.strip():
                entries.append(LogEntry(now, classify(stream, line), stream, line.rstrip()))
        self.pending[stream] = rest
        return entries

    def flush(self, now: datetime | None = None) -> list[LogEntry]:
        """Wypisuje niedokończone linie (np. „Waiting for MCU…: ” bez znaku nowej linii)."""
        now = now or datetime.now()
        out: list[LogEntry] = []
        for stream, rest in self.pending.items():
            line = rest.split("\r")[-1].rstrip()
            if line.strip():
                out.append(LogEntry(now, classify(stream, line), stream, line))
        self.pending = {}
        return out
