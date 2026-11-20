"""Widok „Diagnostyka”: zdarzenia z poziomami, filtr i wyszukiwanie, surowy log, eksport."""

from __future__ import annotations

import platform
from datetime import datetime

from PySide6.QtCore import (
    QT_TRANSLATE_NOOP,
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
)
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from stcgal_gui import __version__
from stcgal_gui.core import diagnosis
from stcgal_gui.core.i18n import tx
from stcgal_gui.core.logmodel import LEVELS, LogEntry
from stcgal_gui.core.redact import redact
from stcgal_gui.gui.context import AppContext
from stcgal_gui.gui.widgets import Card, icon, muted, semantic_color
from stcgal_gui.models.data import OperationResult

MAX_ENTRIES = 20000
TRIM = 1000
GLYPH = {"DEBUG": "·", "INFO": "ℹ", "WARNING": "⚠", "ERROR": "✖"}
KIND = {"DEBUG": "none", "INFO": "info", "WARNING": "warn", "ERROR": "error"}
FILTERS = (
    QT_TRANSLATE_NOOP("DiagnosticsTab", "Wszystkie"),
    QT_TRANSLATE_NOOP("DiagnosticsTab", "Ostrzeżenia i błędy"),
    QT_TRANSLATE_NOOP("DiagnosticsTab", "Tylko błędy"),
)


class LogTableModel(QAbstractTableModel):
    """Model zdarzeń (czas, poziom, źródło, komunikat)."""

    HEAD = (
        QT_TRANSLATE_NOOP("LogTableModel", "Czas"),
        QT_TRANSLATE_NOOP("LogTableModel", "Poziom"),
        QT_TRANSLATE_NOOP("LogTableModel", "Źródło"),
        QT_TRANSLATE_NOOP("LogTableModel", "Komunikat"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[LogEntry] = []

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self.entries)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else 4

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return tx("LogTableModel", self.HEAD[section])
        return None

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object:
        if not index.isValid():
            return None
        e = self.entries[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return (
                f"{e.ts:%H:%M:%S}.{e.ts.microsecond // 1000:03d}",
                f"{GLYPH[e.level]} {e.level}",
                e.source,
                e.text,
            )[col]
        if role == Qt.ItemDataRole.ForegroundRole and col == 1 and e.level != "DEBUG":
            return semantic_color(KIND[e.level])
        if role == Qt.ItemDataRole.UserRole:
            return e
        return None

    def add(self, e: LogEntry) -> None:
        if len(self.entries) >= MAX_ENTRIES:  # ogranicz pamięć: usuń najstarsze
            self.beginRemoveRows(QModelIndex(), 0, TRIM - 1)
            del self.entries[:TRIM]
            self.endRemoveRows()
        n = len(self.entries)
        self.beginInsertRows(QModelIndex(), n, n)
        self.entries.append(e)
        self.endInsertRows()

    def clear(self) -> None:
        self.beginResetModel()
        self.entries.clear()
        self.endResetModel()


class LevelProxy(QSortFilterProxyModel):
    """Filtr poziomu + wyszukiwanie tekstu (bez rozróżniania wielkości liter)."""

    def __init__(self) -> None:
        super().__init__()
        self.min_level = 0
        self.needle = ""

    def filterAcceptsRow(self, row: int, parent: QModelIndex | QPersistentModelIndex) -> bool:
        model = self.sourceModel()
        e: LogEntry = model.index(row, 0, parent).data(Qt.ItemDataRole.UserRole)
        if LEVELS.index(e.level) < self.min_level:
            return False
        return not self.needle or self.needle in e.text.lower() or self.needle in e.source


class DiagnosticsTab(QWidget):
    """Log operacji i narzędzia diagnostyczne."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.model = LogTableModel()
        self.proxy = LevelProxy()
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(self.fontMetrics().height() + 8)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setStretchLastSection(True)
        self.raw = QPlainTextEdit()
        self.raw.setReadOnly(True)
        self.raw.setMaximumBlockCount(20000)
        self.raw.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.raw.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.tabs = QTabWidget()
        self.tabs.addTab(self.table, self.tr("Zdarzenia"))
        self.tabs.addTab(self.raw, self.tr("Surowy output (stdout/stderr)"))

        self.level_combo = QComboBox()
        for name in FILTERS:
            self.level_combo.addItem(tx("DiagnosticsTab", name))
        self.level_combo.setToolTip(self.tr("Filtr poziomu zdarzeń"))
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText(self.tr("Szukaj w logu (Ctrl+F)…"))
        self.count_label = muted(QLabel())
        self.debug_cb = QCheckBox(self.tr("Tryb debug stcgal (-D)"))
        self.debug_cb.setToolTip(self.tr("Wypisuje surowe pakiety protokołu (poziom DEBUG)"))
        self.redact_cb = QCheckBox(self.tr("Redaguj dane wrażliwe"))
        self.redact_cb.setToolTip(
            self.tr(
                "Przy kopiowaniu i eksporcie zastępuje katalog domowy, nazwę użytkownika/hosta, numery seryjne USB"
            )
        )
        self.redact_cb.setChecked(True)
        self.copy_btn = QPushButton(icon("edit-copy"), self.tr("Kopiuj"))
        self.copy_btn.setToolTip(self.tr("Kopiuj zaznaczone (lub wszystkie widoczne) zdarzenia"))
        self.export_btn = QPushButton(icon("document-save"), self.tr("Eksportuj…"))
        self.clear_btn = QPushButton(icon("edit-clear"), self.tr("Wyczyść"))
        self.sys_btn = QPushButton(self.tr("Informacje o środowisku"))

        self.diag_card = Card(self.tr("Wynik ostatniej operacji"))
        self.diag = QLabel(self.tr("Brak zgłoszonych problemów."))
        self.diag.setWordWrap(True)
        self.diag.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.diag_card.body().addWidget(self.diag)

        top = QHBoxLayout()
        top.addWidget(self.level_combo)
        top.addWidget(self.search, 1)
        top.addWidget(self.count_label)
        bottom = QHBoxLayout()
        for w in (self.copy_btn, self.export_btn, self.clear_btn, self.sys_btn):
            bottom.addWidget(w)
        bottom.addStretch(1)
        options = QHBoxLayout()
        options.addWidget(self.debug_cb)
        options.addWidget(self.redact_cb)
        options.addStretch(1)
        self.tabs.setMinimumHeight(200)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.diag_card)
        lay.addLayout(top)
        lay.addWidget(self.tabs, 1)
        lay.addLayout(bottom)
        lay.addLayout(options)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.debug_cb.setChecked(ctx.settings.debug)
        self.debug_cb.toggled.connect(self._debug_toggled)
        self.level_combo.currentIndexChanged.connect(self._apply_filter)
        self.search.textChanged.connect(self._apply_filter)
        self.copy_btn.clicked.connect(self.copy_log)
        self.export_btn.clicked.connect(self.export_log)
        self.clear_btn.clicked.connect(self.clear)
        self.sys_btn.clicked.connect(self.add_environment)
        ctx.entry_added.connect(self._add_entry)
        ctx.log_appended.connect(self._append_raw)
        ctx.result_ready.connect(self._on_finished)
        ctx.settings_changed.connect(lambda s: self.debug_cb.setChecked(s.debug))
        self.proxy.rowsInserted.connect(lambda *_: self._update_count())
        self.proxy.layoutChanged.connect(self._update_count)
        for e in ctx.entries:
            self.model.add(e)
        for stream, text in ctx.log_entries:
            self._append_raw(stream, text)
        self._update_count()

    # ------------------------------------------------------------------ dane

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()

    def _add_entry(self, e: LogEntry) -> None:
        bar = self.table.verticalScrollBar()
        at_end = bar.value() >= bar.maximum() - 2
        self.model.add(e)
        if at_end:
            self.table.scrollToBottom()

    def _append_raw(self, stream: str, text: str) -> None:
        clean = text.replace("\r\n", "\n").replace("\r", "\n")
        cursor = self.raw.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        prefix = "[err] " if stream == "stderr" and clean.strip() else ""
        cursor.insertText(prefix + clean)
        self.raw.setTextCursor(cursor)
        self.raw.ensureCursorVisible()

    def _apply_filter(self) -> None:
        begin = getattr(self.proxy, "beginFilterChange", None)
        if begin:  # Qt >= 6.10
            begin()
        self.proxy.min_level = (0, 2, 3)[self.level_combo.currentIndex()]
        self.proxy.needle = self.search.text().strip().lower()
        if begin:
            self.proxy.endFilterChange()
        else:
            self.proxy.invalidateFilter()
        self._update_count()

    def _update_count(self) -> None:
        self.count_label.setText(
            self.tr("%1 z %2 zdarzeń")
            .replace("%1", str(self.proxy.rowCount()))
            .replace("%2", str(self.model.rowCount()))
        )

    def _debug_toggled(self, on: bool) -> None:
        s = self.ctx.settings
        if s.debug != on:
            s.debug = on
            self.ctx.update_settings(s)

    def _on_finished(self, res: OperationResult) -> None:
        hint = diagnosis.troubleshooting_hint(res.error_kind)
        if res.ok:
            self.diag.setText(self.tr("Ostatnia operacja zakończona powodzeniem."))
        else:
            self.diag.setText(f"✖ {res.message}\n{hint}".strip())

    # ------------------------------------------------------------------ eksport

    def _visible_entries(self) -> list[LogEntry]:
        return [
            self.proxy.index(r, 0).data(Qt.ItemDataRole.UserRole)
            for r in range(self.proxy.rowCount())
        ]

    def _selected_entries(self) -> list[LogEntry]:
        rows = sorted({i.row() for i in self.table.selectionModel().selectedRows()})
        return [self.proxy.index(r, 0).data(Qt.ItemDataRole.UserRole) for r in rows]

    @staticmethod
    def format_entries(entries: list[LogEntry]) -> str:
        return "\n".join(
            f"{e.ts:%Y-%m-%d %H:%M:%S.%f}"[:-3] + f" [{e.level}] {e.source}: {e.text}"
            for e in entries
        )

    def text(self, *, selected: bool = False) -> str:
        entries = (self._selected_entries() if selected else []) or self._visible_entries()
        raw = self.format_entries(entries)
        return self._redacted(raw)

    def raw_text(self) -> str:
        raw = "".join(("[err] " if st == "stderr" else "") + t for st, t in self.ctx.log_entries)
        return self._redacted(raw.replace("\r\n", "\n").replace("\r", "\n"))

    def _redacted(self, raw: str) -> str:
        return redact(raw, self.ctx.seen_serials) if self.redact_cb.isChecked() else raw

    def copy_log(self) -> None:
        QGuiApplication.clipboard().setText(self.text(selected=True))

    def export_log(self) -> None:
        name = f"stcgal-gui-{datetime.now():%Y%m%d-%H%M%S}.log"
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Eksportuj log"), name, self.tr("Log (*.log *.txt)")
        )
        if path:
            body = (
                self.tr("# stcgal-gui %1 - zdarzenia (przefiltrowane widokiem)").replace(
                    "%1", __version__
                )
                + f"\n{self.text()}\n\n"
                + self.tr("# Surowy output stcgal")
                + f"\n{self.raw_text()}\n"
            )
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)

    def clear(self) -> None:
        self.ctx.clear_log()
        self.model.clear()
        self.raw.clear()
        self._update_count()

    def add_environment(self) -> None:
        be = self.ctx.controller.backend
        lines = [
            f"stcgal-gui {__version__}",
            f"Python {platform.python_version()} / {platform.platform()}",
            f"Backend: {be.name} {be.version() or ''}".strip(),
        ]
        for p in self.ctx.ports:
            lines.append(
                self.tr("Port %1 vid:pid=%2 dostęp=%3")
                .replace("%1", p.device)
                .replace("%2", p.vid_pid or "-")
                .replace("%3", self.tr("tak") if p.accessible else self.tr("NIE"))
            )
        self.ctx.add_info("\n".join(lines))
