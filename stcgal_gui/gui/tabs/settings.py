"""Zakładka „Ustawienia”."""

from __future__ import annotations

from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from stcgal_gui import platform_support as ps
from stcgal_gui.backends.stcgal import find_stcgal
from stcgal_gui.core.i18n import tx
from stcgal_gui.core.settings import AppSettings
from stcgal_gui.gui.context import AppContext
from stcgal_gui.gui.widgets import Card, icon
from stcgal_gui.models.data import PROTOCOLS

PORT_PLACEHOLDER = (
    "COM3"
    if ps.IS_WINDOWS
    else QT_TRANSLATE_NOOP("SettingsTab", "/dev/ttyUSB0 lub /dev/serial/by-id/…")
)
STCGAL_PLACEHOLDER = (
    QT_TRANSLATE_NOOP("SettingsTab", "(puste = wbudowany backend aplikacji)")
    if ps.IS_WINDOWS
    else QT_TRANSLATE_NOOP("SettingsTab", "(puste = backend aplikacji, PATH lub ~/.local/bin)")
)
THEMES = (
    ("system", QT_TRANSLATE_NOOP("SettingsTab", "Systemowy")),
    ("light", QT_TRANSLATE_NOOP("SettingsTab", "Jasny")),
    ("dark", QT_TRANSLATE_NOOP("SettingsTab", "Ciemny")),
)
LANGUAGE_CHOICES = (
    ("system", QT_TRANSLATE_NOOP("SettingsTab", "Systemowy")),
    ("pl", "Polski"),
    ("en", "English"),
)
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class SettingsTab(QWidget):
    """Edycja i zapis ustawień (QSettings)."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.port = QLineEdit()
        self.port.setPlaceholderText(tx("SettingsTab", PORT_PLACEHOLDER))
        self.port.setToolTip(self.tr("Ścieżka by-id jest stabilna po ponownym podłączeniu"))
        self.protocol = QComboBox()
        self.protocol.addItems(PROTOCOLS)
        self.baud = QSpinBox()
        self.baud.setRange(1200, 2_000_000)
        self.hs = QSpinBox()
        self.hs.setRange(300, 115200)
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 600)
        self.timeout.setSuffix(" s")
        self.theme = QComboBox()
        for key, name in THEMES:
            self.theme.addItem(tx("SettingsTab", name), key)
        self.language = QComboBox()
        for key, name in LANGUAGE_CHOICES:
            self.language.addItem(tx("SettingsTab", name), key)
        self.language.setToolTip(
            self.tr("Język interfejsu. Zmiana działa po ponownym uruchomieniu aplikacji.")
        )
        self.lang_note = QLabel(
            "Zmiana języka wymaga ponownego uruchomienia aplikacji.\n"
            "Restart the application to apply the language change."
        )
        self.lang_note.setWordWrap(True)
        self.lang_note.setVisible(False)
        self._loaded_language = ctx.settings.language
        self.fwdir = QLineEdit()
        fw_btn = QPushButton(self.tr("Wybierz…"))
        fw_btn.clicked.connect(self._pick_dir)
        self.level = QComboBox()
        self.level.addItems(LEVELS)
        self.stcgal = QLineEdit()
        self.stcgal.setPlaceholderText(tx("SettingsTab", STCGAL_PLACEHOLDER))
        self.autoreset = QCheckBox(self.tr("Automatyczny reset DTR domyślnie"))
        self.found = QLabel()
        self.found.setWordWrap(True)
        save = QPushButton(icon("document-save"), self.tr("Zapisz ustawienia"))
        save.setToolTip(self.tr("Zapisz ustawienia (Ctrl+S)"))
        self.save_btn = save
        save.clicked.connect(self.save)

        fwrow = QHBoxLayout()
        fwrow.addWidget(self.fwdir, 1)
        fwrow.addWidget(fw_btn)
        conn = Card(self.tr("Domyślne parametry połączenia"))
        f1 = QFormLayout()
        f1.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        f1.addRow(self.tr("Port:"), self.port)
        f1.addRow(self.tr("Protokół:"), self.protocol)
        f1.addRow(self.tr("Transfer (baud):"), self.baud)
        f1.addRow(self.tr("Handshake (baud):"), self.hs)
        f1.addRow(self.tr("Limit czasu:"), self.timeout)
        f1.addRow("", self.autoreset)
        conn.body().addLayout(f1)
        app = Card(self.tr("Aplikacja"))
        f2 = QFormLayout()
        f2.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        f2.addRow(self.tr("Motyw:"), self.theme)
        f2.addRow(self.tr("Język:"), self.language)
        f2.addRow("", self.lang_note)
        f2.addRow(self.tr("Katalog firmware:"), fwrow)
        f2.addRow(self.tr("Poziom logowania:"), self.level)
        f2.addRow(self.tr("Ścieżka do stcgal:"), self.stcgal)
        f2.addRow("", self.found)
        app.body().addLayout(f2)
        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(10)
        il.addWidget(conn)
        il.addWidget(app)
        il.addWidget(save, 0, Qt.AlignmentFlag.AlignLeft)
        il.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)
        self.load(ctx.settings)

    def load(self, s: AppSettings) -> None:
        self.port.setText(s.default_port)
        self.protocol.setCurrentText(s.protocol)
        self.baud.setValue(s.baud)
        self.hs.setValue(s.handshake_baud)
        self.timeout.setValue(s.timeout_s)
        self.theme.setCurrentIndex(max(self.theme.findData(s.theme), 0))
        self.language.setCurrentIndex(max(self.language.findData(s.language), 0))
        self.fwdir.setText(s.firmware_dir)
        self.level.setCurrentText(s.log_level)
        self.stcgal.setText(s.stcgal_path)
        self.autoreset.setChecked(s.autoreset)
        self._show_found()

    def _show_found(self) -> None:
        exe = find_stcgal(self.stcgal.text().strip())
        self.found.setText(
            self.tr("Znaleziono stcgal: %1").replace("%1", exe)
            if exe
            else self.tr("Nie znaleziono stcgal - zainstaluj: pipx install stcgal")
        )

    def _pick_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, self.tr("Katalog firmware"), self.fwdir.text())
        if d:
            self.fwdir.setText(d)

    def save(self) -> None:
        s = self.ctx.settings
        s.default_port = self.port.text().strip()
        s.protocol = self.protocol.currentText()
        s.baud = self.baud.value()
        s.handshake_baud = self.hs.value()
        s.timeout_s = self.timeout.value()
        s.theme = str(self.theme.currentData())
        s.language = str(self.language.currentData())
        s.firmware_dir = self.fwdir.text().strip()
        s.log_level = self.level.currentText()
        s.stcgal_path = self.stcgal.text().strip()
        s.autoreset = self.autoreset.isChecked()
        self.lang_note.setVisible(s.language != self._loaded_language)
        self.ctx.update_settings(s, explicit_save=True)
        self._show_found()
