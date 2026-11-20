"""Widok "Programowanie": tryb podstawowy (plik i jeden przycisk) oraz tryb eksperta.

Ochrona EEPROM/IAP i konfiguracji MCU (docs/SAFETY.md): zapis Flash nie zawiera obrazu EEPROM ani
opcji. Gdy backend nie gwarantuje zachowania danych (stcgal), każdy zapis wymaga osobnego
potwierdzenia ryzyka. Opcje -o, trim, offset obrazu, zapis EEPROM i samo kasowanie są dostępne
tylko w trybie eksperta.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from stcgal_gui.backends.base import WriteConfirmation
from stcgal_gui.backends.stcgal import OPTION_RE
from stcgal_gui.core import safety
from stcgal_gui.core.firmware import (
    FirmwareError,
    FirmwareInfo,
    check_fit,
    image_bytes,
    load_firmware,
)
from stcgal_gui.core.i18n import tx
from stcgal_gui.core.linkstate import LinkState
from stcgal_gui.core.mcu_report import option_label
from stcgal_gui.core.safety import Risk
from stcgal_gui.gui.context import AppContext
from stcgal_gui.gui.tabs.connection import POWER_CYCLE_TEXT
from stcgal_gui.gui.widgets import Banner, Card, InfoButton, MemoryBar, StatusBadge, icon
from stcgal_gui.models.data import (
    ConnectionParams,
    McuInfo,
    OperationKind,
    OperationResult,
    OperationState,
    ProgramParams,
    Progress,
    WriteScope,
)

MAX_OFFSET = 0x20000  # 128 KiB: więcej niż pojemność wszystkich układów STC
FILTER = QT_TRANSLATE_NOOP("ProgramTab", "Firmware (*.bin *.hex *.ihx *.ihex);;Wszystkie pliki (*)")


class ProgramTab(QWidget):
    """Wybór pliku, kontrola bezpieczeństwa i zapis (zawsze po jawnym potwierdzeniu)."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.fw: FirmwareInfo | None = None
        self.ee: FirmwareInfo | None = None
        self.fw_errors: list[str] = []
        self.risks: dict[WriteScope, list[Risk]] = {s: [] for s in WriteScope}
        self._got_progress = False
        self._snapshot_dir: str | None = None
        self._option_rows: list[tuple[str, str]] = []

        # --- plik
        self.fw_edit = QLineEdit()
        self.fw_edit.setClearButtonEnabled(True)
        self.fw_edit.setPlaceholderText(self.tr("Plik BIN/HEX do zapisu"))
        self.fw_btn = QPushButton(icon("document-open"), self.tr("Wybierz…"))
        self.fw_btn.setToolTip(self.tr("Wybierz plik firmware (Ctrl+O)"))
        self.expert_cb = QCheckBox(self.tr("Tryb eksperta"))
        self.expert_cb.setToolTip(
            self.tr(
                "Pełne parametry: opcje MCU, częstotliwość, offset obrazu, EEPROM, kasowanie. "
                "Operacje wymagają dodatkowych potwierdzeń."
            )
        )
        self.file_summary = StatusBadge()
        self.target_label = QLabel()
        self.target_label.setWordWrap(True)
        self.membar = MemoryBar()
        self.membar.setVisible(False)
        self.usage_label = QLabel()
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.risk_label = QLabel()
        self.risk_label.setWordWrap(True)
        self.risk_info = InfoButton("", self.tr("Ryzyko zapisu"))
        self.risk_info.setVisible(False)

        main = Card(
            self.tr("Plik firmware"),
            info=self.tr(
                "Zapis Flash dotyczy wyłącznie pamięci programu: bez obrazu EEPROM, bez opcji (-o) i bez zmiany "
                "częstotliwości. stcgal nie weryfikuje zapisu. Przerwanie zapisu może zostawić niekompletny "
                "firmware (bootloader ISP pozostaje dostępny)."
            ),
        )
        row = QHBoxLayout()
        row.addWidget(self.fw_edit, 1)
        row.addWidget(self.fw_btn)
        main.body().addLayout(row)
        main.body().addWidget(self.file_summary)
        main.body().addWidget(self.target_label)
        main.body().addWidget(self.membar)
        main.body().addWidget(self.usage_label)
        main.body().addWidget(self.info)
        rrow = QHBoxLayout()
        rrow.addWidget(self.risk_label, 1)
        rrow.addWidget(self.risk_info, 0, Qt.AlignmentFlag.AlignTop)
        main.body().addLayout(rrow)

        # --- akcje
        self.program_btn = QPushButton(icon("dialog-warning"), self.tr("Programuj"))
        self.program_btn.setEnabled(False)
        self.program_btn.setDefault(True)
        self.program_btn.setToolTip(
            self.tr("Kasuje i zapisuje pamięć programu (Ctrl+Shift+P). Wymaga potwierdzenia.")
        )
        self.cancel_btn = QPushButton(icon("dialog-cancel"), self.tr("Anuluj"))
        self.cancel_btn.setEnabled(False)
        self.stage = StatusBadge()
        self.stage.setVisible(False)
        self.wait_label = Banner()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setMaximumHeight(90)
        self.report.setPlaceholderText(self.tr("Raport wyniku pojawi się po zakończeniu operacji"))
        act = QHBoxLayout()
        act.addWidget(self.program_btn)
        act.addWidget(self.cancel_btn)
        act.addStretch(1)
        act.addWidget(self.expert_cb)

        # --- tryb eksperta
        self.options_table = QTableWidget(0, 3)
        self.options_table.setHorizontalHeaderLabels(
            [self.tr("Opcja"), self.tr("Obecna"), self.tr("Nowa (puste = bez zmiany)")]
        )
        self.options_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.options_table.verticalHeader().setVisible(False)
        self.options_table.setMinimumHeight(140)
        opt_card = Card(
            self.tr("Opcje MCU (-o)"),
            info=self.tr(
                "Zmiana option bytes: EEPROM (eeprom_erase_enabled, program_eeprom_split), zegar, watchdog, reset, UART. "
                "Wpisz nową wartość tylko tam, gdzie chcesz zmianę. Błędna wartość może zablokować układ."
            ),
        )
        opt_card.body().addWidget(self.options_table)
        self.trim_spin = QDoubleSpinBox()
        self.trim_spin.setRange(0, 65000)
        self.trim_spin.setDecimals(3)
        self.trim_spin.setSuffix(" kHz")
        self.trim_spin.setSpecialValueText(self.tr("bez zmiany"))
        self.offset_edit = QLineEdit("0")
        self.offset_edit.setToolTip(
            self.tr(
                "Adres początkowy obrazu (dziesiętnie lub 0x…); wcześniejsze bajty zostają wypełnione"
            )
        )
        self.fill_combo = QComboBox()
        self.fill_combo.addItems(["0xFF", "0x00"])
        adv = Card(
            self.tr("Parametry zapisu"),
            info=self.tr(
                "Offset: obraz zostaje przesunięty o podaną liczbę bajtów, a początek wypełniony wybranym bajtem "
                "(stcgal zapisuje od adresu 0). Częstotliwość (-t): docelowy zegar RC w kHz."
            ),
        )
        form = QFormLayout()
        form.addRow(self.tr("Częstotliwość (trim):"), self.trim_spin)
        form.addRow(self.tr("Offset początkowy:"), self.offset_edit)
        form.addRow(self.tr("Wypełnienie:"), self.fill_combo)
        adv.body().addLayout(form)
        self.ee_edit = QLineEdit()
        self.ee_edit.setClearButtonEnabled(True)
        self.ee_edit.setPlaceholderText(self.tr("Plik BIN/HEX z danymi EEPROM/IAP"))
        self.ee_btn = QPushButton(icon("document-open"), self.tr("Wybierz…"))
        self.eeprom_btn = QPushButton(icon("dialog-warning"), self.tr("Programuj Flash + EEPROM"))
        self.eeprom_btn.setEnabled(False)
        self.ee_risk_label = QLabel()
        self.ee_risk_label.setWordWrap(True)
        ee_card = Card(
            self.tr("EEPROM"),
            info=self.tr(
                "Osobna operacja: EEPROM/IAP jest nadpisywany razem z Flash (stcgal nie zapisze samego EEPROM). "
                "Dane nie podlegają odzyskaniu, a aplikacja nie może ich wcześniej odczytać."
            ),
        )
        er = QHBoxLayout()
        er.addWidget(self.ee_edit, 1)
        er.addWidget(self.ee_btn)
        ee_card.body().addLayout(er)
        ee_card.body().addWidget(self.ee_risk_label)
        ee_card.body().addWidget(self.eeprom_btn, 0, Qt.AlignmentFlag.AlignLeft)
        self.erase_btn = QPushButton(icon("dialog-warning"), self.tr("Kasuj Flash"))
        self.erase_btn.setEnabled(False)
        erase_card = Card(
            self.tr("Kasowanie"),
            info=self.tr(
                "Kasuje pamięć programu bez zapisu nowego obrazu. stcgal może przy tym skasować także EEPROM."
            ),
        )
        erase_card.body().addWidget(self.erase_btn, 0, Qt.AlignmentFlag.AlignLeft)
        self.expert_box = QWidget()
        eb = QVBoxLayout(self.expert_box)
        eb.setContentsMargins(0, 0, 0, 0)
        eb.setSpacing(10)
        for card in (opt_card, adv, ee_card, erase_card):
            eb.addWidget(card)
        self.expert_box.setVisible(False)

        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(10)
        il.addWidget(main)
        il.addLayout(act)
        il.addWidget(self.stage)
        il.addWidget(self.wait_label)
        il.addWidget(self.progress)
        il.addWidget(self.report)
        il.addWidget(self.expert_box)
        il.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)

        self.fw_btn.clicked.connect(lambda: self._pick(self.fw_edit))
        self.ee_btn.clicked.connect(lambda: self._pick(self.ee_edit))
        for w in (self.fw_edit, self.ee_edit, self.offset_edit):
            w.textChanged.connect(self.revalidate)
        self.fill_combo.currentIndexChanged.connect(lambda _i: self.revalidate())
        self.trim_spin.valueChanged.connect(lambda _v: self.revalidate())
        self.options_table.itemChanged.connect(lambda _i: self.revalidate())
        self.expert_cb.toggled.connect(self._on_expert)
        self.program_btn.clicked.connect(lambda: self.start_program(WriteScope.FLASH_ONLY))
        self.eeprom_btn.clicked.connect(lambda: self.start_program(WriteScope.FLASH_AND_EEPROM))
        self.erase_btn.clicked.connect(self.start_erase)
        self.cancel_btn.clicked.connect(ctx.controller.cancel)
        ctx.mcu_changed.connect(lambda _m: self._on_context_changed())
        ctx.port_changed.connect(lambda _p: self._on_context_changed())
        ctx.link_changed.connect(self._on_link)
        ctx.controller.busy_changed.connect(self._on_busy)
        ctx.controller.progress.connect(self._on_progress)
        ctx.result_ready.connect(self._on_finished)
        self.setTabOrder(self.fw_edit, self.fw_btn)
        self.setTabOrder(self.fw_btn, self.program_btn)
        self.setTabOrder(self.program_btn, self.cancel_btn)
        self.revalidate()

    # ------------------------------------------------------------------ tryb i parametry

    def expert(self) -> bool:
        return self.expert_cb.isChecked()

    def _on_expert(self, on: bool) -> None:
        self.expert_box.setVisible(on)
        self.revalidate()

    def _on_context_changed(self) -> None:
        self._fill_options()
        self.revalidate()

    def _fill_options(self) -> None:
        mcu = self.ctx.current_mcu()
        rows = list(mcu.options.items()) if mcu else []
        if rows == self._option_rows:
            return
        self._option_rows = rows
        self.options_table.blockSignals(True)
        self.options_table.setRowCount(len(rows))
        for r, (name, value) in enumerate(rows):
            desc = option_label(name)
            a = QTableWidgetItem(f"{desc} ({name})")
            a.setFlags(Qt.ItemFlag.ItemIsEnabled)
            a.setData(Qt.ItemDataRole.UserRole, name)
            b = QTableWidgetItem(value)
            b.setFlags(Qt.ItemFlag.ItemIsEnabled)
            c = QTableWidgetItem("")
            self.options_table.setItem(r, 0, a)
            self.options_table.setItem(r, 1, b)
            self.options_table.setItem(r, 2, c)
        self.options_table.blockSignals(False)

    def option_list(self) -> list[str]:
        """Zmiany opcji z tabeli (wyłącznie w trybie eksperta): ``nazwa=wartość``."""
        if not self.expert():
            return []
        out: list[str] = []
        for r in range(self.options_table.rowCount()):
            a, b, c = (self.options_table.item(r, i) for i in range(3))
            if a is None or b is None or c is None:
                continue
            name = a.data(Qt.ItemDataRole.UserRole)
            cur = b.text()
            new = c.text().strip()
            if new and new != cur:
                out.append(f"{name}={new}")
        return out

    def _offset(self) -> int | None:
        if not self.expert():
            return 0
        try:
            v = int(self.offset_edit.text().strip() or "0", 0)
        except ValueError:
            return None
        return v if 0 <= v <= MAX_OFFSET else None

    def _fill_byte(self) -> int:
        return int(self.fill_combo.currentText(), 16)

    def _trim(self) -> float | None:
        return (self.trim_spin.value() or None) if self.expert() else None

    def _effective_size(self) -> int | None:
        off = self._offset()
        return None if self.fw is None or off is None else self.fw.size + off

    # ------------------------------------------------------------------ pliki i ryzyka

    def _pick(self, edit: QLineEdit) -> None:
        if self.ctx.controller.busy:
            return
        start = edit.text() or self.ctx.settings.firmware_dir
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Wybierz plik firmware"), start, tx("ProgramTab", FILTER)
        )
        if path:
            edit.setText(path)

    def pick_firmware(self) -> None:
        self._pick(self.fw_edit)

    def _params(self, scope: WriteScope) -> ProgramParams | None:
        if self.fw is None:
            return None
        ee = self.ee.path if (scope is WriteScope.FLASH_AND_EEPROM and self.ee) else None
        return ProgramParams(self.fw.path, ee, trim_khz=self._trim(), options=self.option_list())

    def revalidate(self) -> None:
        self.fw = self.ee = None
        self.fw_errors = []
        warnings: list[str] = []
        text = self.fw_edit.text().strip()
        if text:
            try:
                self.fw = load_firmware(Path(text))
                warnings += self.fw.warnings
            except FirmwareError as ex:
                self.fw_errors.append(self.tr("Firmware: %1").replace("%1", str(ex)))
        if self.expert() and self.ee_edit.text().strip():
            try:
                self.ee = load_firmware(Path(self.ee_edit.text().strip()))
            except FirmwareError as ex:
                self.fw_errors.append(self.tr("EEPROM: %1").replace("%1", str(ex)))
        if self._offset() is None:
            self.fw_errors.append(self.tr("Offset: liczba od 0 do 0x20000 (np. 0 lub 0x400)"))
        for o in self.option_list():
            if not OPTION_RE.match(o):
                self.fw_errors.append(self.tr("Niepoprawna opcja: %1").replace("%1", o))
        mcu = self.ctx.current_mcu()
        if self.fw is not None and not self.expert():
            errs, warns = check_fit(self.fw, mcu, eeprom=self.ee)
            self.fw_errors += errs
            warnings += warns
        caps = self.ctx.controller.backend.capabilities
        code = (
            safety.effective_code_bytes(mcu) if (mcu and mcu.model) else None
        )  # bez modelu: brak kontroli zgodności
        for scope in WriteScope:
            params = self._params(scope)
            self.risks[scope] = (
                safety.assess(caps, params, scope, code, self.expert(), self._effective_size())
                if params and scope is not WriteScope.ERASE_ONLY
                else []
            )
        self.risks[WriteScope.ERASE_ONLY] = safety.assess_erase(caps, code, self.expert())
        self._render(mcu, warnings)
        self._update_enabled()

    def _render(self, mcu: McuInfo | None, warnings: list[str]) -> None:
        if self.fw is not None:
            self.file_summary.set_status(
                "✔", f"{self.fw.path.name} · {self.fw.fmt.upper()} · {self.fw.size} B", "ok"
            )
        elif self.fw_edit.text().strip():
            self.file_summary.set_status("✖", self.tr("Plik nie przeszedł walidacji"), "error")
        else:
            self.file_summary.set_status("○", self.tr("Nie wybrano pliku"), "none")
        conn = self.ctx.conn_getter()
        self.target_label.setText(
            self.tr("Cel: <b>%1</b> · port %2 · protokół %3")
            .replace("%1", mcu.model if mcu and mcu.model else self.tr("MCU nie zidentyfikowany"))
            .replace("%2", conn.port if conn else "-")
            .replace("%3", conn.protocol if conn else "-")
        )
        size = self._effective_size()
        if self.fw is not None and mcu is not None and mcu.code_bytes and size is not None:
            code = safety.effective_code_bytes(mcu) or mcu.code_bytes
            segs = [(self.tr("Flash %1 B").replace("%1", str(code)), code, "flash")]
            if mcu.eeprom_bytes:
                segs.append(
                    (
                        self.tr("EEPROM %1 B").replace("%1", str(mcu.eeprom_bytes)),
                        mcu.eeprom_bytes,
                        "eeprom",
                    )
                )
            self.membar.set_layout(segs, used=min(size, code))
            self.membar.setVisible(True)
            self.usage_label.setText(
                self.tr("Wykorzystanie flash: %1 z %2 B (%3%)")
                .replace("%1", str(size))
                .replace("%2", str(code))
                .replace("%3", f"{100.0 * size / code:.1f}")
            )
            self.usage_label.setToolTip(
                self.tr("Pojemność z bazy modeli stcgal i podziału odczytanego z układu")
            )
        else:
            self.membar.setVisible(False)
            self.usage_label.setText(
                self.tr(
                    "Rozmiar nie został porównany z pamięcią MCU - najpierw wykryj mikrokontroler."
                )
                if self.fw is not None
                else ""
            )
        self.info.setText(
            "\n".join([f"⚠ {w}" for w in warnings] + [f"✖ {e}" for e in self.fw_errors])
        )
        self.info.setVisible(bool(self.info.text()))
        risks = self.risks[WriteScope.FLASH_ONLY] if self.fw is not None else []
        self.risk_label.setText("<br>".join(f"{'✖' if r.hard else '⚠'} {r.title}" for r in risks))
        self.risk_label.setVisible(bool(risks))
        self.risk_info.info_text = safety.format_risks(risks)
        self.risk_info.setToolTip(self.risk_info.info_text)
        self.risk_info.setVisible(bool(risks))
        ee_risks = (
            self.risks[WriteScope.FLASH_AND_EEPROM]
            if (self.fw is not None and self.ee is not None)
            else []
        )
        self.ee_risk_label.setText(
            "<br>".join(f"{'✖' if r.hard else '⚠'} {r.title}" for r in ee_risks)
        )
        self.ee_risk_label.setToolTip(safety.format_risks(ee_risks))
        self.ee_risk_label.setVisible(bool(ee_risks))

    def _hard(self, scope: WriteScope) -> list[Risk]:
        return [r for r in self.risks[scope] if r.hard]

    def _update_enabled(self) -> None:
        busy = self.ctx.controller.busy
        base = (
            self.fw is not None
            and not self.fw_errors
            and not busy
            and self.ctx.conn_getter() is not None
        )
        self.program_btn.setEnabled(bool(base and not self._hard(WriteScope.FLASH_ONLY)))
        self.eeprom_btn.setEnabled(
            bool(
                base
                and self.expert()
                and self.ee is not None
                and not self._hard(WriteScope.FLASH_AND_EEPROM)
            )
        )
        self.erase_btn.setEnabled(
            bool(self.expert() and not busy and self.ctx.conn_getter() is not None
                 and not self._hard(WriteScope.ERASE_ONLY))
        )  # fmt: skip

    # ------------------------------------------------------------------ zapis

    def _confirm(self, title: str, text: str, ok_label: str) -> bool:
        box = QMessageBox(
            QMessageBox.Icon.Warning, title, text, QMessageBox.StandardButton.Cancel, self
        )
        yes = box.addButton(ok_label, QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        self.ctx.modal_active = True  # wstrzymaj odświeżanie portów na czas dialogu
        try:
            box.exec()
        finally:
            self.ctx.modal_active = False
        return box.clickedButton() is yes

    def _risk_dialog(self, soft: list[Risk]) -> bool:
        if not soft:
            return True
        detail = (
            self.tr(
                "Backend (stcgal) NIE gwarantuje zachowania EEPROM/IAP ani konfiguracji MCU.\n\n"
            )
            + safety.format_risks(soft)
            + self.tr("\n\nDane mogą zostać utracone bezpowrotnie. Czy na pewno kontynuować?")
        )
        return self._confirm(
            self.tr("Potwierdź ryzyko dla EEPROM i konfiguracji"),
            detail,
            self.tr("Rozumiem, kontynuuj"),
        )

    def start_program(self, scope: WriteScope = WriteScope.FLASH_ONLY) -> None:
        conn = self.ctx.conn_getter()
        if conn is None or self.ctx.controller.busy:
            return
        self.revalidate()  # plik/MCU mogły się zmienić od wyboru
        mcu = self.ctx.current_mcu()
        if self.fw is None or self.fw_errors or self._hard(scope) or mcu is None:
            return
        snapshot_dir, code_snap, ee_snap = self._snapshot(scope)
        if code_snap is None:
            return
        try:
            self._run_confirmed(scope, conn, mcu, code_snap, ee_snap, snapshot_dir)
        except Exception:
            shutil.rmtree(snapshot_dir, ignore_errors=True)
            raise

    def _snapshot(self, scope: WriteScope) -> tuple[str, Path | None, Path | None]:
        """Kopia plików w prywatnym katalogu (offset/wypełnienie zastosowane); sprawdzana kopia trafia do stcgal."""
        assert self.fw is not None
        d = tempfile.mkdtemp(prefix="stc-fw-")
        try:
            offset = self._offset() or 0
            if offset:
                code = Path(d) / "firmware.bin"
                code.write_bytes(bytes([self._fill_byte()]) * offset + image_bytes(self.fw.path))
            else:
                code = Path(d) / ("firmware" + self.fw.path.suffix.lower())
                shutil.copyfile(self.fw.path, code)
            ee: Path | None = None
            if scope is WriteScope.FLASH_AND_EEPROM and self.ee is not None:
                ee = Path(d) / ("eeprom" + self.ee.path.suffix.lower())
                shutil.copyfile(self.ee.path, ee)
            load_firmware(code)
            if ee is not None:
                load_firmware(ee)
            return d, code, ee
        except (OSError, FirmwareError) as ex:
            shutil.rmtree(d, ignore_errors=True)
            self.fw_errors.append(self.tr("Migawka pliku: %1").replace("%1", str(ex)))
            self._render(self.ctx.current_mcu(), [])
            return d, None, None

    def _run_confirmed(
        self, scope: WriteScope, conn: ConnectionParams, mcu: McuInfo, code_snap: Path,
        ee_snap: Path | None, snapshot_dir: str,
    ) -> None:  # fmt: skip
        assert self.fw is not None
        expert = self.expert()
        prog = ProgramParams(code_snap, ee_snap, trim_khz=self._trim(), options=self.option_list())
        caps = self.ctx.controller.backend.capabilities
        risks = safety.assess(caps, prog, scope, safety.effective_code_bytes(mcu), expert)
        if [r for r in risks if r.hard]:
            shutil.rmtree(snapshot_dir, ignore_errors=True)
            return
        soft = [r for r in risks if not r.hard]
        eeprom = scope is WriteScope.FLASH_AND_EEPROM
        text = (
            self.tr("Za chwilę nastąpi KASOWANIE i ZAPIS pamięci %6 mikrokontrolera.\n\n"
                    "Port: %1\nProtokół: %2\nMCU: %3\nFirmware: %4 (%5 B)\n\n"
                    "Po rozpoczęciu trzeba będzie wyłączyć i włączyć zasilanie MCU. Kontynuować?")
            .replace("%1", conn.port).replace("%2", conn.protocol).replace("%3", mcu.model or "?")
            .replace("%4", self.fw.path.name).replace("%5", str(code_snap.stat().st_size))
            .replace("%6", self.tr("Flash ORAZ EEPROM/IAP") if eeprom else self.tr("programu (Flash)"))
        )  # fmt: skip
        title = (
            self.tr("Potwierdź zapis Flash + EEPROM")
            if eeprom
            else self.tr("Potwierdź zapis Flash")
        )
        if not self._confirm(title, text, self.tr("Kasuj i programuj")) or not self._risk_dialog(
            soft
        ):
            shutil.rmtree(snapshot_dir, ignore_errors=True)
            return
        if not self._still_valid(scope, mcu, conn, {r.id for r in soft}):
            shutil.rmtree(snapshot_dir, ignore_errors=True)
            return
        confirmation = WriteConfirmation(
            conn.port, prog.code_image, scope=scope, acknowledged=frozenset(r.id for r in soft),
            mcu_code_bytes=safety.effective_code_bytes(mcu), expected_model=mcu.model, expert=expert,
        )  # fmt: skip
        self._snapshot_dir = snapshot_dir
        self._begin_ui("Flash+EEPROM" if eeprom else "Flash")
        self.ctx.controller.start_program(conn, prog, confirmation)

    def _still_valid(
        self, scope: WriteScope, mcu: McuInfo, conn: ConnectionParams, soft_ids: set[str]
    ) -> bool:
        """Dialogi uruchamiają zagnieżdżoną pętlę zdarzeń: sprawdź, czy port/MCU/plik/ryzyka się nie zmieniły."""
        now = self.ctx.conn_getter()
        self.revalidate()
        ok = (
            self.ctx.current_mcu() is mcu and now is not None and now.port == conn.port and not self.ctx.controller.busy
            and (scope is WriteScope.ERASE_ONLY or (self.fw is not None and not self.fw_errors))
            and not self._hard(scope) and {r.id for r in self.risks[scope] if not r.hard} <= soft_ids
        )  # fmt: skip
        if not ok:
            self.ctx.add_info(
                self.tr(
                    "Operacja anulowana: w trakcie potwierdzania zmienił się port, MCU, plik lub ryzyka."
                )
            )
        return ok

    def start_erase(self) -> None:
        conn = self.ctx.conn_getter()
        mcu = self.ctx.current_mcu()
        if not self.expert() or conn is None or mcu is None or not mcu.model:
            return
        if self.ctx.controller.busy or self._hard(WriteScope.ERASE_ONLY):
            return
        self.revalidate()
        risks = self.risks[WriteScope.ERASE_ONLY]
        soft = [r for r in risks if not r.hard]
        text = (
            self.tr(
                "Za chwilę nastąpi KASOWANIE pamięci programu (Flash).\n\nPort: %1\nMCU: %2\n\nKontynuować?"
            )
            .replace("%1", conn.port)
            .replace("%2", mcu.model or "?")
        )
        if not self._confirm(
            self.tr("Potwierdź kasowanie Flash"), text, self.tr("Kasuj Flash")
        ) or not self._risk_dialog(soft):
            return
        if not self._still_valid(WriteScope.ERASE_ONLY, mcu, conn, {r.id for r in soft}):
            return
        confirmation = WriteConfirmation(
            conn.port, Path("-"), scope=WriteScope.ERASE_ONLY, acknowledged=frozenset(r.id for r in soft),
            mcu_code_bytes=safety.effective_code_bytes(mcu), expected_model=mcu.model, expert=self.expert(),
        )  # fmt: skip
        self._begin_ui("kasowanie")
        self.ctx.controller.start_erase(conn, confirmation)

    def _begin_ui(self, what: str) -> None:
        self.progress.setRange(0, 0)  # nieokreślony do czasu rzeczywistego postępu
        self._got_progress = False
        self.report.clear()
        self.stage.setVisible(True)
        self.stage.set_status("⟳", self.tr("Przygotowanie…"), "info")
        self.ctx.add_info(
            self.tr("Rozpoczęto operację (%1), potwierdzone przez użytkownika").replace("%1", what)
        )

    # ------------------------------------------------------------------ stan operacji

    def _on_link(self, link: LinkState) -> None:
        kind = self.ctx.controller.current_kind
        waiting = link is LinkState.WAITING_MCU and kind in (
            OperationKind.PROGRAM,
            OperationKind.ERASE,
        )
        self.wait_label.setVisible(waiting)
        if waiting:
            self.wait_label.setText("⏻  " + tx("ConnectionTab", POWER_CYCLE_TEXT))
            self.stage.set_status("⏳", self.tr("Oczekiwanie na zasilenie MCU"), "warn")
        elif link is LinkState.PROGRAMMING and not self._got_progress:
            self.stage.set_status("⟳", self.tr("Kasowanie i przygotowanie pamięci…"), "info")

    def _on_busy(self, busy: bool) -> None:
        self.cancel_btn.setEnabled(busy)
        for w in (
            self.fw_edit,
            self.fw_btn,
            self.ee_edit,
            self.ee_btn,
            self.expert_box,
            self.expert_cb,
        ):
            w.setEnabled(not busy)
        if busy:
            for b in (self.program_btn, self.eeprom_btn, self.erase_btn):
                b.setEnabled(False)
        else:
            self._update_enabled()

    def _on_progress(self, p: Progress) -> None:
        self._got_progress = True
        self.progress.setRange(0, 100)
        self.progress.setValue(int(p.percent))
        self.stage.set_status(
            "⟳", self.tr("Zapis flash: %1%").replace("%1", f"{p.percent:.0f}"), "info"
        )

    def _on_finished(self, res: OperationResult) -> None:
        if res.kind not in (OperationKind.PROGRAM, OperationKind.ERASE):
            return
        d = self._snapshot_dir
        if d:
            shutil.rmtree(d, ignore_errors=True)
            self._snapshot_dir = None
        self.progress.setRange(0, 100)
        if res.ok and self._got_progress:
            self.progress.setValue(100)
        elif not res.ok:
            self.progress.setValue(self.progress.value() if self._got_progress else 0)
        lines = [self.tr("Wynik: %1").replace("%1", res.state.value), res.message]
        if res.ok:
            if res.kind is OperationKind.PROGRAM:
                lines.append(
                    self.tr("Weryfikacja: NIE wykonano (stcgal nie weryfikuje zawartości po zapisie).")
                    if not res.verified else self.tr("Weryfikacja: wykonana przez backend.")
                )  # fmt: skip
            lines.append(
                self.tr(
                    "Uwaga: stan EEPROM/IAP i option bytes nie jest weryfikowany - wykryj MCU ponownie."
                )
            )
        self.stage.setVisible(True)
        if res.ok:
            self.stage.set_status(
                "✔",
                self.tr("Zakończono (bez weryfikacji)")
                if res.kind is OperationKind.PROGRAM
                else self.tr("Skasowano"),
                "ok",
            )
        else:
            self.stage.set_status(
                "✖", self.tr("Operacja nie powiodła się lub została przerwana"), "error"
            )
        self.report.setPlainText("\n".join(x for x in lines if x))
        if res.state is OperationState.FINISHED:
            self.ctx.add_info(self.tr("Operacja zakończona"))
