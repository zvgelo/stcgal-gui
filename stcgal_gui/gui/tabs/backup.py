"""Widok „Odczyt i kopia” - uczciwy zakres możliwości odczytu."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime

from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
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

from stcgal_gui.core.i18n import tx
from stcgal_gui.gui.context import AppContext
from stcgal_gui.gui.widgets import Card, InfoButton, StatusBadge, icon

FIRMWARE_UNSUPPORTED = QT_TRANSLATE_NOOP(
    "BackupTab", "Odczyt firmware nie jest obsługiwany przez wybrany backend i protokół ISP"
)


class BackupTab(QWidget):
    """Pokazuje, co backend potrafi odczytać; nie generuje żadnych plików BIN."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        caps = ctx.controller.backend.capabilities
        self.rows: dict[str, str] = {}
        yes, no = self.tr("Obsługiwane"), self.tr("Nieobsługiwane")
        spec = [
            (self.tr("Identyfikator MCU"), caps.identify,
             self.tr("Widok Połączenie → „Wykryj mikrokontroler”")),
            (self.tr("Opcje konfiguracyjne"), caps.read_options,
             self.tr("Odczyt bajtów opcji z bootloadera - tylko podgląd")),
            (self.tr("Dane pamięci (Flash/EEPROM)"), False,
             self.tr("Protokół ISP STC nie udostępnia odczytu zawartości pamięci")),
            (self.tr("Firmware aplikacji"), caps.read_firmware,
             self.tr("Bootloader STC nie umożliwia odczytu kodu użytkownika")),
        ]  # fmt: skip
        card = Card(self.tr("Zakres możliwości odczytu"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setColumnStretch(2, 1)
        for r, (name, ok, note) in enumerate(spec):
            badge = StatusBadge()
            badge.set_status("✔" if ok else "✖", yes if ok else no, "ok" if ok else "error")
            self.rows[name] = yes if ok else no
            label = QLabel(f"<b>{name}</b>")
            label.setToolTip(note)
            badge.setToolTip(note)
            grid.addWidget(label, r, 0)
            grid.addWidget(badge, r, 1)
            grid.addWidget(InfoButton(note, name), r, 2, Qt.AlignmentFlag.AlignLeft)
        card.body().addLayout(grid)

        self.msg = QLabel(tx("BackupTab", FIRMWARE_UNSUPPORTED) + ".")
        self.msg.setWordWrap(True)
        f = self.msg.font()
        f.setBold(True)
        self.msg.setFont(f)
        self.save_btn = QPushButton(
            icon("document-save"), self.tr("Zapisz informacje o MCU (JSON)…")
        )
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_info)
        info = Card(
            self.tr("Kopia informacji o układzie"),
            info=self.tr(
                "Plik JSON zawiera wyłącznie dane faktycznie zwrócone przez stcgal "
                "(identyfikator, parametry, opcje). To NIE jest kopia firmware."
            ),
        )
        info.body().addWidget(self.save_btn)

        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(10)
        il.addWidget(card)
        il.addWidget(self.msg)
        il.addWidget(info)
        il.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)
        ctx.mcu_changed.connect(lambda m: self.save_btn.setEnabled(m is not None))

    def save_info(self) -> None:
        mcu = self.ctx.mcu
        if mcu is None:
            return
        name = f"mcu-info-{datetime.now():%Y%m%d-%H%M%S}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Zapisz informacje o MCU"), name, self.tr("JSON (*.json)")
        )
        if not path:
            return
        data = {"source": "stcgal", "port": self.ctx.mcu_port, "mcu": asdict(mcu)}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        self.ctx.add_info(self.tr("Zapisano informacje o MCU: %1").replace("%1", path))
