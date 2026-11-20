"""Widok „Połączenie”: adapter, port, protokół i niedestrukcyjne wykrywanie MCU."""

from __future__ import annotations

import time

from PySide6.QtCore import QT_TRANSLATE_NOOP, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from stcgal_gui import platform_support as ps
from stcgal_gui.core.i18n import tx
from stcgal_gui.core.linkstate import LinkState, describe
from stcgal_gui.devices.mcu_db import protocol_warning
from stcgal_gui.devices.ports import enumerate_ports
from stcgal_gui.gui.context import AppContext
from stcgal_gui.gui.widgets import Banner, Card, CollapsibleSection, StatusBadge, icon, muted
from stcgal_gui.models.data import (
    PROTOCOLS,
    ConnectionParams,
    OperationKind,
    OperationResult,
    PortInfo,
)

BAUDS = (1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800)
KIND = {
    LinkState.NO_ADAPTER: "error", LinkState.ADAPTER_READY: "info", LinkState.WAITING_MCU: "warn",
    LinkState.IDENTIFYING: "info", LinkState.PROGRAMMING: "info", LinkState.MCU_DETECTED: "ok",
    LinkState.TIMEOUT: "warn", LinkState.ERROR: "error",
}  # fmt: skip
NO_ACCESS_HINT_LINUX = QT_TRANSLATE_NOOP(
    "ConnectionTab", "Dodaj użytkownika do grupy dialout i zaloguj się ponownie (docs/CH340.md)."
)
NO_ACCESS_HINT_WIN = QT_TRANSLATE_NOOP(
    "ConnectionTab", "Brak dostępu do portu COM - zamknij programy używające tego portu."
)
POWER_CYCLE_TEXT = QT_TRANSLATE_NOOP(
    "ConnectionTab",
    "Wyłącz i ponownie włącz zasilanie mikrokontrolera. Nie odłączaj adaptera CH340 od portu USB.",
)


class ConnectionTab(QWidget):
    """Kompaktowa konfiguracja połączenia + wyraźne stany operacji."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self._started = 0.0
        self._waiting = False

        # --- adapter i port
        self.adapter_badge = StatusBadge()
        self.port_combo = QComboBox()
        self.port_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.port_combo.setMinimumContentsLength(18)
        self.port_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.port_combo.setToolTip(self.tr("Port szeregowy programatora (F5 - odśwież listę)"))
        self.refresh_btn = QPushButton(icon("view-refresh"), self.tr("Odśwież"))
        self.refresh_btn.setToolTip(self.tr("Odśwież listę portów (F5)"))
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(PROTOCOLS)
        self.protocol_combo.setToolTip(
            self.tr("„auto” - stcgal rozpoznaje rodzinę; dla STC8H8K64U wybiera stc8d.")
        )
        self.port_note = muted(QLabel())
        self.proto_warn = QLabel()
        self.proto_warn.setWordWrap(True)

        adapter = Card(
            self.tr("Adapter i port"),
            info=self.tr(
                "Wykrycie adaptera (np. CH340) nie oznacza wykrycia mikrokontrolera. Sprawdź zgodność "
                "napięcia zasilania i poziomów logicznych (3,3 V / 5 V); aplikacja nie przełącza napięcia. "
                "Wykrywanie niczego nie kasuje ani nie programuje."
            ),
        )
        self.adapter_card = adapter
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setColumnStretch(1, 3)
        grid.setColumnStretch(3, 1)
        grid.addWidget(QLabel(self.tr("Port:")), 0, 0)
        grid.addWidget(self.port_combo, 0, 1)
        grid.addWidget(self.refresh_btn, 0, 2)
        proto_lbl = QLabel(self.tr("Protokół:"))
        grid.addWidget(proto_lbl, 1, 0)
        grid.addWidget(self.protocol_combo, 1, 1)
        proto_lbl.setBuddy(self.protocol_combo)
        adapter.body().addWidget(self.adapter_badge)
        adapter.body().addLayout(grid)
        adapter.body().addWidget(self.port_note)
        adapter.body().addWidget(self.proto_warn)

        # --- stan i wykrywanie
        self.status = StatusBadge()
        f = self.status.font()
        f.setPointSizeF(f.pointSizeF() * 1.25)
        self.status.setFont(f)
        self.status_detail = muted(QLabel())
        self.wait_label = Banner()
        self.timer_label = QLabel()
        self.detect_btn = QPushButton(icon("dialog-ok-apply"), self.tr("Wykryj mikrokontroler"))
        self.detect_btn.setDefault(True)
        self.detect_btn.setToolTip(
            self.tr("Niedestrukcyjna identyfikacja (Ctrl+D). Nie kasuje i nie programuje pamięci.")
        )
        self.cancel_btn = QPushButton(icon("dialog-cancel"), self.tr("Anuluj"))
        self.cancel_btn.setToolTip(self.tr("Przerwij bieżącą operację (Esc)"))
        self.cancel_btn.setEnabled(False)
        state = Card(self.tr("Stan"))
        state.body().addWidget(self.status)
        state.body().addWidget(self.status_detail)
        state.body().addWidget(self.wait_label)
        row = QHBoxLayout()
        row.addWidget(self.detect_btn)
        row.addWidget(self.cancel_btn)
        row.addWidget(self.timer_label)
        row.addStretch(1)
        state.body().addLayout(row)

        # --- zaawansowane
        self.baud_combo = QComboBox()
        self.baud_combo.addItems([str(b) for b in BAUDS])
        self.hs_combo = QComboBox()
        self.hs_combo.addItems([str(b) for b in BAUDS[:6]])
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 600)
        self.timeout_spin.setSuffix(self.tr(" s"))
        self.autoreset_cb = QCheckBox(self.tr("Reset sygnałem DTR"))
        self.autoreset_cb.setToolTip(
            self.tr("Wymaga układu, w którym DTR zasila/resetuje MCU. Zwykle zostaw wyłączone.")
        )
        self.all_ports_cb = QCheckBox(self.tr("Pokaż porty bez adaptera USB"))
        self.all_ports_cb.setToolTip(
            self.tr("Wbudowane (ttyS*/COM płyty głównej) i Bluetooth - zwykle nieużywane")
        )
        self.advanced = CollapsibleSection(self.tr("Parametry zaawansowane"))
        g2 = QGridLayout(self.advanced.content)
        g2.setContentsMargins(18, 0, 0, 0)
        g2.addWidget(QLabel(self.tr("Transfer (baud):")), 0, 0)
        g2.addWidget(self.baud_combo, 0, 1)
        g2.addWidget(QLabel(self.tr("Handshake (baud):")), 0, 2)
        g2.addWidget(self.hs_combo, 0, 3)
        g2.addWidget(QLabel(self.tr("Limit czasu:")), 1, 0)
        g2.addWidget(self.timeout_spin, 1, 1)
        g2.addWidget(self.autoreset_cb, 1, 2, 1, 2)
        g2.addWidget(self.all_ports_cb, 2, 0, 1, 2)
        g2.setColumnStretch(4, 1)

        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(adapter)
        lay.addWidget(state)
        lay.addWidget(self.advanced)
        lay.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._tick = QTimer(self)
        self._tick.setInterval(250)
        self._tick.timeout.connect(self._update_timer)

        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.all_ports_cb.toggled.connect(lambda _c: self.refresh_ports())
        self.detect_btn.clicked.connect(self.detect)
        self.cancel_btn.clicked.connect(ctx.controller.cancel)
        self.port_combo.currentIndexChanged.connect(self._on_port_changed)
        self.protocol_combo.currentTextChanged.connect(self._update_proto_warn)
        ctx.controller.busy_changed.connect(self._on_busy)
        ctx.link_changed.connect(self._on_link)
        ctx.result_ready.connect(self._on_finished)
        ctx.mcu_changed.connect(lambda _m: self._update_proto_warn())
        ctx.settings_saved.connect(lambda _s: self.apply_settings())
        ctx.conn_getter = self.current_params
        self.setTabOrder(self.port_combo, self.refresh_btn)
        self.setTabOrder(self.refresh_btn, self.protocol_combo)
        self.setTabOrder(self.protocol_combo, self.detect_btn)
        self.setTabOrder(self.detect_btn, self.cancel_btn)
        self.apply_settings()
        self.refresh_ports()
        self._on_link(ctx.link)

    # ------------------------------------------------------------------ parametry

    def apply_settings(self) -> None:
        s = self.ctx.settings
        self.protocol_combo.setCurrentText(s.protocol)
        self.baud_combo.setCurrentText(str(s.baud))
        self.hs_combo.setCurrentText(str(s.handshake_baud))
        self.timeout_spin.setValue(s.timeout_s)
        self.autoreset_cb.setChecked(s.autoreset)

    def selected_port(self) -> str:
        return str(self.port_combo.currentData() or "")

    def current_params(self) -> ConnectionParams | None:
        port = self.selected_port()
        if not port:
            return None
        return ConnectionParams(
            port=port,
            protocol=self.protocol_combo.currentText(),
            baud=int(self.baud_combo.currentText()),
            handshake_baud=int(self.hs_combo.currentText()),
            debug=self.ctx.settings.debug,
            autoreset=self.autoreset_cb.isChecked(),
            timeout_s=float(self.timeout_spin.value()),
        )

    # ------------------------------------------------------------------ porty

    def refresh_ports(self) -> None:
        previous = self.selected_port() or self.ctx.settings.default_port
        ports = enumerate_ports(include_builtin=self.all_ports_cb.isChecked())
        known = {p.device for p in self.ctx.ports}
        self.ctx.set_ports(ports)
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        for p in ports:
            self.port_combo.addItem(self._label(p), p.device)
            self.port_combo.setItemData(self.port_combo.count() - 1, self._tooltip(p), 3)
        idx = self.port_combo.findData(ps.normalize_port(previous))
        if idx < 0 and self.port_combo.count():
            idx = self._preferred_index(ports)
        self.port_combo.setCurrentIndex(idx)
        self.port_combo.blockSignals(False)
        self._on_port_changed()
        if {p.device for p in ports} != known:  # loguj tylko zmianę listy
            self.ctx.add_info(self.tr("Wykryte porty: %n", "", len(ports)))
            for p in ports:
                self.ctx.add_info(
                    f"  {p.device} [{p.vid_pid or '-'}] {p.description}"
                    f"{' (CH340)' if p.is_ch340 else ''}"
                    f"{'' if p.accessible else self.tr(' - BRAK UPRAWNIEŃ')}"
                    f"{(' by-id=' + p.by_id) if p.by_id else ''}"
                    f"{(' loc=' + p.location) if p.location else ''}"
                )

    @staticmethod
    def _preferred_index(ports: list[PortInfo]) -> int:
        """Domyślny wybór: adapter CH340, w drugiej kolejności pierwszy adapter USB."""
        for i, p in enumerate(ports):
            if p.is_ch340:
                return i
        if not ps.IS_WINDOWS:
            for i, p in enumerate(ports):
                if p.device == "/dev/ttyUSB0":
                    return i
        return 0

    @staticmethod
    def _label(p: PortInfo) -> str:
        extra = f"  [{p.vid_pid}]" if p.vid_pid else ""
        return f"{p.device} - {p.description}{extra}"

    @staticmethod
    def _tooltip(p: PortInfo) -> str:
        return "\n".join(
            x
            for x in (
                p.device,
                p.by_id or "",
                p.manufacturer,
                p.vid_pid,
                p.serial_number,
                p.location,
            )
            if x
        )

    def _on_port_changed(self) -> None:
        self.ctx.set_port(self.selected_port())
        p = self.ctx.port_info(self.selected_port())
        if p is None:
            self.adapter_badge.set_status("✖", self.tr("Nie wykryto adaptera USB-UART"), "error")
            self.port_note.setText(self.tr("Podłącz programator USB i odśwież listę portów (F5)."))
        else:
            name = f"CH340 ({p.vid_pid})" if p.is_ch340 else (p.description or p.device)
            if p.accessible:
                self.adapter_badge.set_status("✔", self.tr("Adapter: %1").replace("%1", name), "ok")
            else:
                self.adapter_badge.set_status(
                    "⚠", self.tr("Adapter %1 - brak uprawnień do portu").replace("%1", name), "warn"
                )
            lines = []
            if p.by_id:
                lines.append(self.tr("Stabilna ścieżka: %1").replace("%1", p.by_id))
            if p.location:
                lines.append(self.tr("Lokalizacja USB: %1").replace("%1", p.location))
            if p.serial_number:
                lines.append(self.tr("Numer seryjny: %1").replace("%1", p.serial_number))
            if not p.accessible:
                lines.append(
                    tx(
                        "ConnectionTab",
                        NO_ACCESS_HINT_WIN if ps.IS_WINDOWS else NO_ACCESS_HINT_LINUX,
                    )
                )
            self.port_note.setText("\n".join(lines))
        self.port_note.setVisible(bool(self.port_note.text()))
        self.detect_btn.setEnabled(p is not None and not self.ctx.controller.busy)

    def _update_proto_warn(self, *_: object) -> None:
        mcu = self.ctx.mcu
        msg = protocol_warning(mcu.model if mcu else None, self.protocol_combo.currentText())
        self.proto_warn.setText(("⚠ " + msg) if msg else "")
        self.proto_warn.setVisible(bool(msg))

    # ------------------------------------------------------------------ wykrywanie

    def detect(self) -> None:
        params = self.current_params()
        if params is None or self.ctx.controller.busy:
            return
        self.status_detail.setText("")
        self.ctx.invalidate_mcu(
            self.tr("ponowne wykrywanie")
        )  # stary wynik nie może przeżyć nieudanej identyfikacji
        self.ctx.add_info(
            self.tr("Rozpoczęto wykrywanie (tryb niedestrukcyjny) na %1").replace("%1", params.port)
        )
        self.ctx.controller.start_identify(params)

    def _on_busy(self, busy: bool) -> None:
        p = self.ctx.port_info(self.selected_port())
        self.detect_btn.setEnabled(not busy and p is not None)
        self.cancel_btn.setEnabled(busy)
        for w in (self.port_combo, self.refresh_btn, self.protocol_combo, self.baud_combo,
                  self.hs_combo, self.timeout_spin, self.autoreset_cb, self.all_ports_cb):  # fmt: skip
            w.setEnabled(not busy)
        if busy:
            self._started = time.monotonic()
            self._tick.start()
        else:
            self._tick.stop()
            self._waiting = False
            self.wait_label.setVisible(False)
            self.timer_label.setText("")

    def _on_link(self, link: LinkState) -> None:
        glyph, text = describe(link)
        self.status.set_status(glyph, text, KIND[link])
        self._waiting = link is LinkState.WAITING_MCU
        self.wait_label.setVisible(self._waiting)
        if self._waiting:
            self.wait_label.setText("⏻  " + tx("ConnectionTab", POWER_CYCLE_TEXT))
        if link is LinkState.MCU_DETECTED and self.ctx.mcu is not None:
            self.status_detail.setText(
                f"{self.ctx.mcu.model or '?'} · {self.ctx.mcu.protocol or '?'} · "
                + self.tr("szczegóły w widoku „Mikrokontroler”")
            )
        elif link in (LinkState.NO_ADAPTER, LinkState.ADAPTER_READY):
            self.status_detail.setText("")

    def _update_timer(self) -> None:
        elapsed = time.monotonic() - self._started
        remaining = max(self.timeout_spin.value() - elapsed, 0)
        if self._waiting:
            self.timer_label.setText(
                self.tr("Upłynęło %1 s · limit za %2 s")
                .replace("%1", f"{elapsed:.0f}")
                .replace("%2", f"{remaining:.0f}")
            )
        else:
            self.timer_label.setText(self.tr("Upłynęło %1 s").replace("%1", f"{elapsed:.0f}"))

    def _on_finished(self, res: OperationResult) -> None:
        if res.state.value in ("failed", "timeout", "cancelled") or (
            res.kind is OperationKind.PROGRAM
        ):
            self.status_detail.setText(res.message)
