"""Widok „Mikrokontroler”: karty z grupami danych, źródła informacji, raport."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from stcgal_gui.core.mcu_report import SOURCE_CHIP, SOURCE_DB, build_report, grouped_options
from stcgal_gui.gui.context import AppContext
from stcgal_gui.gui.widgets import Card, MemoryBar, hbox, icon, muted
from stcgal_gui.models.data import McuInfo

NA = "-"
TOTAL_FLASH = 65536


def _fmt(value: object, unit: str = "") -> str:
    return NA if value is None else f"{value}{unit}"


def _value_label(text: str = NA) -> QLabel:
    lab = QLabel(text)
    lab.setTextInteractionFlags(lab.textInteractionFlags().TextSelectableByMouse)
    lab.setWordWrap(True)
    return lab


class McuTab(QWidget):
    """Czytelny panel informacyjny; każda grupa ma podane źródło danych."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.fields: dict[str, QLabel] = {}

        self.empty = QLabel(
            self.tr(
                "Nie zidentyfikowano jeszcze mikrokontrolera.\nUżyj „Wykryj mikrokontroler” w widoku Połączenie (Ctrl+D)."
            )
        )
        self.empty.setWordWrap(True)
        self.empty.setMargin(24)

        self.title = QLabel()
        f = self.title.font()
        f.setPointSizeF(f.pointSizeF() * 1.6)
        f.setBold(True)
        self.title.setFont(f)
        self.subtitle = muted(QLabel())
        self.copy_btn = QPushButton(icon("edit-copy"), self.tr("Kopiuj raport"))
        self.export_btn = QPushButton(icon("document-save"), self.tr("Eksportuj raport…"))
        self.copy_btn.clicked.connect(self.copy_report)
        self.export_btn.clicked.connect(self.export_report)

        # podstawowe
        basic = Card(
            self.tr("Podstawowe informacje"), info=self.tr("Źródło: %1").replace("%1", SOURCE_CHIP)
        )
        g = QGridLayout()
        self._rows(g, [
            ("model", self.tr("Model")), ("magic", self.tr("Identyfikator (magic)")),
            ("family", self.tr("Protokół")), ("bsl", self.tr("Bootloader")),
        ])  # fmt: skip
        basic.body().addLayout(g)

        # pamięć
        mem = Card(self.tr("Pamięć"), info=self.tr("Źródło: %1").replace("%1", SOURCE_DB))
        self.membar = MemoryBar()
        mem.body().addWidget(self.membar)
        g = QGridLayout()
        self._rows(g, [("code", self.tr("Flash (kod)")), ("eeprom", self.tr("EEPROM / IAP"))])
        mem.body().addLayout(g)

        # zegar
        clock = Card(
            self.tr("Zegar i zasilanie"), info=self.tr("Źródło: %1").replace("%1", SOURCE_CHIP)
        )
        g = QGridLayout()
        self._rows(g, [
            ("freq", self.tr("Częstotliwość zegara")), ("wake", self.tr("Zegar wybudzania")),
            ("vref", self.tr("Napięcie referencyjne")), ("mfg", self.tr("Data produkcji")),
        ])  # fmt: skip
        clock.body().addLayout(g)

        self.config_card = Card(
            self.tr("Konfiguracja (tylko odczyt)"),
            info=self.tr("Źródło: %1. Nazwy techniczne stcgal w nawiasach.").replace(
                "%1", SOURCE_CHIP
            ),
        )
        self.config_grid = QGridLayout()
        self.config_grid.setColumnStretch(0, 3)
        self.config_grid.setColumnStretch(1, 2)
        self.config_grid.setHorizontalSpacing(24)
        self.config_card.body().addLayout(self.config_grid)

        self.cards = [basic, mem, clock, self.config_card]
        self.content = QWidget()
        cl = QVBoxLayout(self.content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(10)
        head = QVBoxLayout()
        head.addWidget(self.title)
        head.addWidget(self.subtitle)
        top = QGridLayout()
        top.addLayout(head, 0, 0)
        top.addLayout(hbox(self.copy_btn, self.export_btn), 0, 1)
        top.setColumnStretch(0, 1)
        cl.addLayout(top)
        two = QGridLayout()
        two.setSpacing(10)
        two.addWidget(basic, 0, 0)
        two.addWidget(clock, 0, 1)
        two.setColumnStretch(0, 1)
        two.setColumnStretch(1, 1)
        cl.addLayout(two)
        cl.addWidget(mem)
        cl.addWidget(self.config_card)
        cl.addStretch(1)

        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0)
        il.addWidget(self.empty)
        il.addWidget(self.content)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)
        ctx.mcu_changed.connect(self.show_mcu)
        self.show_mcu(ctx.mcu)

    def _rows(self, grid: QGridLayout, items: list[tuple[str, str]]) -> None:
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(14)
        for r, (key, title) in enumerate(items):
            grid.addWidget(QLabel(title + ":"), r, 0)
            lab = _value_label()
            self.fields[key] = lab
            grid.addWidget(lab, r, 1)

    def show_mcu(self, mcu: McuInfo | None) -> None:
        self.empty.setVisible(mcu is None)
        self.content.setVisible(mcu is not None)
        self.copy_btn.setEnabled(mcu is not None)
        self.export_btn.setEnabled(mcu is not None)
        if mcu is None:
            for lab in self.fields.values():
                lab.setText(NA)
            return
        f = self.fields
        self.title.setText(mcu.model or self.tr("Nieznany model"))
        self.subtitle.setText(
            self.tr("Port %1 · odczytano %2")
            .replace("%1", self.ctx.mcu_port or NA)
            .replace("%2", f"{datetime.now():%H:%M:%S}")
        )
        f["model"].setText(_fmt(mcu.model))
        f["magic"].setText(_fmt(mcu.magic and "0x" + mcu.magic))
        f["family"].setText(_fmt(mcu.protocol))
        f["bsl"].setText(_fmt(mcu.bsl_version))
        f["code"].setText(
            _fmt(mcu.code_bytes, " B")
            + (f"  ({mcu.code_flash_kb:g} KB)" if mcu.code_flash_kb else "")
        )
        f["eeprom"].setText(
            _fmt(mcu.eeprom_bytes, " B") + (f"  ({mcu.eeprom_kb:g} KB)" if mcu.eeprom_kb else "")
        )
        f["freq"].setText(_fmt(mcu.frequency_mhz, " MHz"))
        f["wake"].setText(_fmt(mcu.wakeup_khz, " kHz"))
        f["vref"].setText(_fmt(mcu.ref_voltage_mv, " mV"))
        f["mfg"].setText(_fmt(mcu.mfg_date))
        segs = []
        if mcu.code_bytes:
            segs.append(
                (self.tr("Flash %1 B").replace("%1", str(mcu.code_bytes)), mcu.code_bytes, "flash")
            )
        if mcu.eeprom_bytes:
            segs.append(
                (
                    self.tr("EEPROM %1 B").replace("%1", str(mcu.eeprom_bytes)),
                    mcu.eeprom_bytes,
                    "eeprom",
                )
            )
        self.membar.set_layout(segs)
        # opcje: wyczyść i zbuduj od nowa
        while (item := self.config_grid.takeAt(0)) is not None:
            w = item.widget()
            if w is not None:
                w.deleteLater()
        row = 0
        groups = grouped_options(mcu)
        for group, rows in groups.items():
            head = QLabel(f"<b>{group}</b>")
            self.config_grid.addWidget(head, row, 0, 1, 2)
            row += 1
            for desc, name, value in rows:
                d = QLabel(f"{desc}  <span style='color:gray'>({name})</span>")
                d.setTextInteractionFlags(d.textInteractionFlags().TextSelectableByMouse)
                v = _value_label(value)
                d.setWordWrap(True)
                self.config_grid.addWidget(d, row, 0)
                self.config_grid.addWidget(v, row, 1)
                row += 1
        if not groups:
            self.config_grid.addWidget(
                QLabel(self.tr("Backend nie zwrócił opcji konfiguracyjnych.")), 0, 0
            )

    def report_text(self) -> str:
        return build_report(self.ctx.mcu, self.ctx.mcu_port) if self.ctx.mcu else ""

    def copy_report(self) -> None:
        QGuiApplication.clipboard().setText(self.report_text())
        self.ctx.add_info(self.tr("Skopiowano raport MCU do schowka"))

    def export_report(self) -> None:
        name = f"mcu-raport-{datetime.now():%Y%m%d-%H%M%S}.md"
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Eksportuj raport MCU"), name, self.tr("Markdown (*.md);;Tekst (*.txt)")
        )
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.report_text())
