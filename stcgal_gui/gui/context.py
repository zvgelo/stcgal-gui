"""Współdzielony kontekst aplikacji: ustawienia, kontroler, log, stan połączenia i MCU."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from stcgal_gui.core import linkstate
from stcgal_gui.core.controller import OperationController
from stcgal_gui.core.linkstate import LinkState
from stcgal_gui.core.logmodel import LogAssembler, LogEntry
from stcgal_gui.core.settings import AppSettings, SettingsStore
from stcgal_gui.models.data import (
    ConnectionParams,
    McuInfo,
    OperationKind,
    OperationResult,
    OperationState,
    PortInfo,
)

MCU_VALID_SECONDS = 900  # identyfikacja starsza niż 15 min nie uprawnia do zapisu
MAX_ENTRIES = 20000
TRIM = 1000


class AppContext(QObject):
    """Stan wspólny dla widoków (GUI nie rozmawia ze sprzętem bezpośrednio)."""

    mcu_changed = Signal(object)
    ports_changed = Signal(object)
    port_changed = Signal(str)
    settings_changed = Signal(object)
    settings_saved = Signal(object)
    link_changed = Signal(object)
    log_appended = Signal(str, str)  # surowy fragment (strumień, tekst)
    entry_added = Signal(object)  # LogEntry
    result_ready = Signal(object)

    def __init__(
        self, controller: OperationController, store: SettingsStore, settings: AppSettings
    ) -> None:
        super().__init__()
        self.controller = controller
        self.store = store
        self.settings = settings
        self.mcu: McuInfo | None = None
        self.mcu_port: str | None = None
        self.mcu_time: float = 0.0
        self.modal_active = (
            False  # trwa okno potwierdzenia - wstrzymaj automatyczne odświeżanie portów
        )
        self.port: str = ""
        self.ports: list[PortInfo] = []
        self.seen_serials: set[str] = (
            set()
        )  # numery seryjne USB widziane w sesji (do redakcji logów)
        self.last_result: OperationResult | None = None
        self.link = LinkState.NO_ADAPTER
        self.log_entries: list[tuple[str, str]] = []  # surowe dane
        self.entries: list[LogEntry] = []  # zdarzenia strukturalne
        self._assembler = LogAssembler()
        self.conn_getter: Callable[[], ConnectionParams | None] = lambda: None
        controller.log.connect(self._on_log)
        controller.state_changed.connect(self._on_op_state)
        controller.finished.connect(self._on_finished)

    # ------------------------------------------------------------------ log

    def _on_log(self, stream: str, text: str) -> None:
        self.log_entries.append((stream, text))
        if len(self.log_entries) > MAX_ENTRIES:
            del self.log_entries[:TRIM]
        self.log_appended.emit(stream, text)
        if stream == "info":
            for line in text.splitlines():
                self.add_entry("INFO", line, "app", raw=False)
            return
        for e in self._assembler.feed(stream, text):
            self._store_entry(e)

    def add_entry(self, level: str, text: str, source: str = "app", *, raw: bool = True) -> None:
        if raw:
            self.log_entries.append(("info", text + "\n"))
            self.log_appended.emit("info", text + "\n")
        self._store_entry(LogEntry(datetime.now(), level, source, text))

    def add_info(self, text: str) -> None:
        for line in text.splitlines() or [""]:
            self.add_entry("INFO", line)

    def _store_entry(self, e: LogEntry) -> None:
        if len(self.entries) >= MAX_ENTRIES:
            del self.entries[:TRIM]
        self.entries.append(e)
        self.entry_added.emit(e)

    def clear_log(self) -> None:
        self.log_entries.clear()
        self.entries.clear()
        self._assembler = LogAssembler()

    # ------------------------------------------------------------------ stan

    def _set_link(self, link: LinkState) -> None:
        if link is not self.link:
            self.link = link
            self.link_changed.emit(link)

    def _idle_link(self) -> LinkState:
        if not self.port or self.port_info(self.port) is None:
            return LinkState.NO_ADAPTER
        if self.mcu is not None and self.mcu_port == self.port:
            return LinkState.MCU_DETECTED
        return LinkState.ADAPTER_READY

    def refresh_link(self) -> None:
        """Przelicza stan, gdy nie trwa operacja i nie ma świeżego błędu/timeoutu."""
        if self.controller.busy:
            return
        if self.link in (LinkState.TIMEOUT, LinkState.ERROR) and self.port_info(self.port):
            return
        self._set_link(self._idle_link())

    def _on_op_state(self, state: OperationState) -> None:
        link = linkstate.from_operation(state, self.controller.current_kind)
        if link is not None:
            if link is LinkState.WAITING_MCU:
                self.add_entry("INFO", self.tr("Oczekiwanie na zasilenie MCU"), raw=False)
            self._set_link(link)

    def _on_finished(self, res: OperationResult) -> None:
        for e in self._assembler.flush():
            self._store_entry(e)
        self.last_result = res
        if res.kind in (OperationKind.PROGRAM, OperationKind.ERASE):
            # po zapisie/przerwaniu stan układu (flash, opcje) mógł się zmienić - wymagaj ponownego wykrycia
            self.invalidate_mcu(self.tr("po operacji zapisu - wykryj mikrokontroler ponownie"))
        if res.kind is OperationKind.IDENTIFY and res.ok and res.mcu is not None:
            self.set_mcu(res.mcu, self.port)
        known = self.mcu is not None and self.mcu_port == self.port
        self.add_entry(
            "INFO" if res.ok else "ERROR",
            f"{res.kind.value}: {res.state.value}" + (f" - {res.message}" if res.message else ""),
            raw=False,
        )
        self._set_link(linkstate.from_result(res, known))
        self.result_ready.emit(res)

    def set_mcu(self, mcu: McuInfo | None, port: str | None) -> None:
        self.mcu, self.mcu_port = mcu, port
        self.mcu_time = time.monotonic() if mcu is not None else 0.0
        self.mcu_changed.emit(mcu)
        self.refresh_link()

    def mcu_fresh(self) -> bool:
        """Czy identyfikacja MCU jest świeża (zapis wymaga niedawnej, udanej identyfikacji)."""
        return self.mcu is not None and (time.monotonic() - self.mcu_time) < MCU_VALID_SECONDS

    def current_mcu(self) -> McuInfo | None:
        """MCU zidentyfikowany na BIEŻĄCYM porcie i niedawno - inaczej ``None`` (brak zgadywania)."""
        return self.mcu if (self.mcu_port == self.port and self.mcu_fresh()) else None

    def invalidate_mcu(self, reason: str = "") -> None:
        """Czyści dane MCU (zmiana portu/urządzenia, odłączenie adaptera)."""
        if self.mcu is not None:
            if reason:
                self.add_entry(
                    "INFO", self.tr("Dane MCU wyczyszczone: %1").replace("%1", reason), raw=False
                )
            self.set_mcu(None, None)

    def set_port(self, device: str) -> None:
        if device == self.port:
            return
        self.port = device
        if self.mcu_port is not None and device != self.mcu_port:
            self.invalidate_mcu(self.tr("zmieniono port"))
        if self.link in (LinkState.TIMEOUT, LinkState.ERROR):
            self._set_link(LinkState.ADAPTER_READY)
        self.port_changed.emit(device)
        self.refresh_link()

    def set_ports(self, ports: list[PortInfo]) -> None:
        self.ports = ports
        self.seen_serials.update(p.serial_number for p in ports if p.serial_number)
        if self.mcu_port and not any(p.device == self.mcu_port for p in ports):
            self.invalidate_mcu(self.tr("port zniknął (odłączono adapter?)"))
        self.ports_changed.emit(ports)
        self.refresh_link()

    def update_settings(self, settings: AppSettings, *, explicit_save: bool = False) -> None:
        """Zapisuje ustawienia; ``explicit_save`` odświeża widok Połączenie."""
        self.settings = settings
        self.store.save(settings)
        self.settings_changed.emit(settings)
        if explicit_save:
            self.settings_saved.emit(settings)

    def port_info(self, device: str) -> PortInfo | None:
        return next((p for p in self.ports if p.device == device), None)
