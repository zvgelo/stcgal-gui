"""Okno główne: nawigacja boczna, stały pasek stanu połączenia i widoki."""

from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QIcon,
    QKeySequence,
    QPalette,
    QResizeEvent,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from stcgal_gui import platform_support as ps
from stcgal_gui.core.linkstate import describe
from stcgal_gui.core.settings import AppSettings
from stcgal_gui.devices.ports import enumerate_ports
from stcgal_gui.gui.context import AppContext
from stcgal_gui.gui.tabs.backup import BackupTab
from stcgal_gui.gui.tabs.connection import KIND, ConnectionTab
from stcgal_gui.gui.tabs.diagnostics import DiagnosticsTab
from stcgal_gui.gui.tabs.mcu import McuTab
from stcgal_gui.gui.tabs.program import ProgramTab
from stcgal_gui.gui.tabs.settings import SettingsTab
from stcgal_gui.gui.widgets import StatusBadge, icon, refresh_muted, restyle
from stcgal_gui.models.data import OperationKind, OperationResult

ICON_PATH = ps.resource_dir() / "stcgal-gui.svg"
COMPACT_WIDTH = 820
SP = QStyle.StandardPixmap


_SYSTEM_PALETTE: QPalette | None = None

_LIGHT = {
    "Window": "#eff0f1", "WindowText": "#31363b", "Base": "#fcfcfc", "AlternateBase": "#eff0f1",
    "Text": "#31363b", "Button": "#eff0f1", "ButtonText": "#31363b", "Highlight": "#3daee9",
    "HighlightedText": "#fcfcfc", "Mid": "#bdc3c7", "Midlight": "#dfe2e5", "Light": "#ffffff",
    "Dark": "#9ea4a9", "PlaceholderText": "#6f777e", "ToolTipBase": "#31363b", "ToolTipText": "#eff0f1",
    "Link": "#2980b9", "BrightText": "#ffffff",
}  # fmt: skip
_DARK = {
    "Window": "#31363b", "WindowText": "#eff0f1", "Base": "#232629", "AlternateBase": "#2a2e32",
    "Text": "#eff0f1", "Button": "#31363b", "ButtonText": "#eff0f1", "Highlight": "#3daee9",
    "HighlightedText": "#eff0f1", "Mid": "#4d5359", "Midlight": "#3c4147", "Light": "#4d5359",
    "Dark": "#1b1e20", "PlaceholderText": "#9aa1a8", "ToolTipBase": "#31363b", "ToolTipText": "#eff0f1",
    "Link": "#3daee9", "BrightText": "#ffffff",
}  # fmt: skip


def _palette(colors: dict[str, str]) -> QPalette:
    pal = QPalette()
    for name, value in colors.items():
        pal.setColor(getattr(QPalette.ColorRole, name), QColor(value))
    disabled = QColor(colors["Text"])
    disabled.setAlpha(110)
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.ButtonText,
    ):
        pal.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    return pal


def apply_theme(theme: str) -> None:
    """Motyw: „system” = paleta systemu; „light”/„dark” wymuszają własną paletę.

    ``QStyleHints.setColorScheme`` bywa ignorowane przez motyw platformy, dlatego wymuszenie
    odbywa się przez jawną paletę aplikacji.
    """
    global _SYSTEM_PALETTE
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return
    if _SYSTEM_PALETTE is None:
        _SYSTEM_PALETTE = QPalette(app.palette())
    scheme = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(
        theme, Qt.ColorScheme.Unknown
    )
    app.styleHints().setColorScheme(scheme)
    if theme == "light":
        app.setPalette(_palette(_LIGHT))
    elif theme == "dark":
        app.setPalette(_palette(_DARK))
    else:
        app.setPalette(_SYSTEM_PALETTE)
    refresh_muted()


class StatusHeader(QFrame):
    """Stały pasek: stan połączenia, adapter/port i zidentyfikowany MCU (widoczny w każdym widoku)."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.setObjectName("statusHeader")
        self._qss = (
            "QFrame#statusHeader { background: palette(alternate-base);"
            " border: 1px solid palette(midlight); border-radius: 6px; }"
        )
        self.setStyleSheet(self._qss)
        self.badge = StatusBadge()
        self.summary = QLabel()
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.summary.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.summary.setWordWrap(True)
        self.summary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.addWidget(self.badge)
        lay.addWidget(self.summary, 1)
        self.setAccessibleName("Stan połączenia")
        for sig in (ctx.link_changed, ctx.mcu_changed, ctx.ports_changed, ctx.port_changed):
            sig.connect(lambda *_: self.refresh())
        self.refresh()

    def changeEvent(self, event: QEvent) -> None:
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange):
            restyle(self, self._qss)
        super().changeEvent(event)

    def refresh(self) -> None:
        glyph, text = describe(self.ctx.link)
        self.badge.set_status(glyph, text, KIND_MAP[self.ctx.link])
        p = self.ctx.port_info(self.ctx.port)
        if p is None:
            parts = [self.tr("Adapter: -")]
        else:
            name = "CH340" if p.is_ch340 else (p.description or self.tr("USB-UART"))
            parts = [f"{self.tr('Adapter')}: {name} · {p.device}"]
        m = self.ctx.current_mcu()
        if self.ctx.controller.backend.name == "mock":
            parts.insert(0, self.tr("⚠ SYMULACJA (backend mock - brak sprzętu)"))
        if m is not None:
            parts.append(
                self.tr("MCU: <b>%1</b> (%2)")
                .replace("%1", m.model or "?")
                .replace("%2", m.protocol or "?")
            )
        else:
            parts.append(self.tr("MCU: nie zidentyfikowany"))
        self.summary.setText("  ·  ".join(parts))


KIND_MAP = KIND


class MainWindow(QMainWindow):
    """Nawigacja boczna (kolejność = przepływ pracy) + stos widoków."""

    def __init__(self, ctx: AppContext) -> None:
        super().__init__()
        self.ctx = ctx
        suffix = self.tr(" [SYMULACJA]") if ctx.controller.backend.name == "mock" else ""
        self.setWindowTitle(self.tr("STC Programmer GUI") + suffix)
        self.setWindowIcon(QIcon.fromTheme("stcgal-gui", QIcon(str(ICON_PATH))))
        self.setMinimumSize(560, 420)

        self.connection = ConnectionTab(ctx)
        self.mcu = McuTab(ctx)
        self.program = ProgramTab(ctx)
        self.backup = BackupTab(ctx)
        self.diagnostics = DiagnosticsTab(ctx)
        self.settings_tab = SettingsTab(ctx)
        self.pages: list[tuple[QWidget, str, str, SP]] = [
            (self.connection, self.tr("Połączenie"), "network-connect", SP.SP_DriveNetIcon),
            (self.mcu, self.tr("Mikrokontroler"), "cpu", SP.SP_ComputerIcon),
            (self.program, self.tr("Programowanie"), "document-save", SP.SP_DialogSaveButton),
            (self.backup, self.tr("Odczyt i kopia"), "drive-harddisk", SP.SP_DriveHDIcon),
            (self.diagnostics, self.tr("Diagnostyka"), "utilities-terminal", SP.SP_FileDialogDetailedView),
            (self.settings_tab, self.tr("Ustawienia"), "configure", SP.SP_FileDialogContentsView),
        ]  # fmt: skip

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setIconSize(QSize(22, 22))
        self.nav.setFrameShape(QFrame.Shape.NoFrame)
        self.nav.setSpacing(2)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.nav.setAccessibleName(self.tr("Nawigacja"))
        self.stack = QStackedWidget()
        for i, (w, title, theme, fallback) in enumerate(self.pages):
            ic = icon(theme)
            if ic.isNull():
                ic = self.style().standardIcon(fallback)
            item = QListWidgetItem(ic, title)
            item.setToolTip(f"{title}  (Ctrl+{i + 1})")
            item.setSizeHint(QSize(150, 40))
            self.nav.addItem(item)
            self.stack.addWidget(w)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)

        self.header = StatusHeader(ctx)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.addWidget(self.header)
        rl.addWidget(self.stack, 1)
        central = QWidget()
        cl = QHBoxLayout(central)
        cl.setContentsMargins(8, 8, 8, 4)
        cl.setSpacing(10)
        cl.addWidget(self.nav)
        cl.addWidget(right, 1)
        self.setCentralWidget(central)
        self.nav.setCurrentRow(0)
        self._compact: bool | None = None
        self._close_after_finish = False
        self._apply_compact(False)

        self._make_shortcuts()
        ctx.controller.state_changed.connect(self._on_state)
        ctx.result_ready.connect(self._on_finished)
        ctx.settings_changed.connect(self._on_settings)
        ctx.mcu_changed.connect(self._on_mcu)
        self.statusBar().showMessage(self.tr("Gotowy"))
        geometry, state = ctx.store.load_geometry()
        if geometry is not None:
            self.restoreGeometry(geometry)
        else:
            self.resize(940, 700)
        if state is not None:
            self.restoreState(state)
        apply_theme(ctx.settings.theme)
        self._apply_log_level(ctx.settings)

        self._port_timer = QTimer(self)
        self._port_timer.setInterval(3000)
        self._port_timer.timeout.connect(self._auto_refresh)
        self._port_timer.start()

    # ------------------------------------------------------------------ nawigacja

    def show_page(self, widget: QWidget) -> None:
        self.nav.setCurrentRow(self.stack.indexOf(widget))

    def _make_shortcuts(self) -> None:
        def sc(keys: str, fn: object) -> None:
            s = QShortcut(QKeySequence(keys), self)
            s.setContext(Qt.ShortcutContext.WindowShortcut)
            s.activated.connect(fn)

        for i in range(len(self.pages)):
            sc(f"Ctrl+{i + 1}", lambda i=i: self.nav.setCurrentRow(i))
        sc("F5", self._refresh_ports)
        sc("Ctrl+D", self._detect)
        sc("Esc", self._escape)
        sc("Ctrl+O", self._open_firmware)
        sc("Ctrl+Shift+P", self.program.start_program)
        sc("Ctrl+F", self._find)
        sc("Ctrl+S", self._save_settings)

    def _escape(self) -> None:
        """Esc anuluje wykrywanie od razu; przerwanie zapisu wymaga potwierdzenia."""
        c = self.ctx.controller
        if not c.busy:
            return
        if c.current_kind is OperationKind.PROGRAM:
            ans = QMessageBox.question(
                self, self.tr("Przerwać zapis?"),
                self.tr("Przerwanie w trakcie zapisu może zostawić niekompletny firmware. Przerwać?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )  # fmt: skip
            if ans != QMessageBox.StandardButton.Yes:
                return
        c.cancel()

    def _refresh_ports(self) -> None:
        if not self.ctx.controller.busy:
            self.connection.refresh_ports()

    def _detect(self) -> None:
        self.show_page(self.connection)
        self.connection.detect()

    def _open_firmware(self) -> None:
        self.show_page(self.program)
        self.program.pick_firmware()

    def _find(self) -> None:
        self.show_page(self.diagnostics)
        self.diagnostics.focus_search()

    def _save_settings(self) -> None:
        if self.stack.currentWidget() is self.settings_tab:
            self.settings_tab.save()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._apply_compact(self.width() < COMPACT_WIDTH)

    def _apply_compact(self, compact: bool) -> None:
        """Wąskie okno: nawigacja tylko z ikonami (etykiety w podpowiedziach)."""
        if compact == self._compact:
            return
        self._compact = compact
        for i, (_w, title, _t, _f) in enumerate(self.pages):
            item = self.nav.item(i)
            item.setText("" if compact else title)
            item.setSizeHint(QSize(44 if compact else 150, 40))
        self.nav.setFixedWidth(56 if compact else 168)

    # ------------------------------------------------------------------ zdarzenia

    def _auto_refresh(self) -> None:
        """Reaguje na podłączenie/odłączenie adaptera w dowolnym widoku."""
        if self.ctx.controller.busy or self.ctx.modal_active:
            return
        current = {p.device for p in self.ctx.ports}
        if {
            p.device
            for p in enumerate_ports(include_builtin=self.connection.all_ports_cb.isChecked())
        } != current:
            self.connection.refresh_ports()

    def _on_settings(self, s: AppSettings) -> None:
        apply_theme(s.theme)
        self._apply_log_level(s)
        be = self.ctx.controller.backend
        if hasattr(be, "_configured") and not self.ctx.controller.busy:
            be._configured = s.stcgal_path

    @staticmethod
    def _apply_log_level(s: AppSettings) -> None:
        logging.getLogger("stcgal_gui").setLevel(getattr(logging, s.log_level, logging.INFO))

    def _on_state(self, _state: object) -> None:
        glyph, text = describe(self.ctx.link)
        self.statusBar().showMessage(f"{glyph} {text}")

    def _on_mcu(self, mcu: object) -> None:
        if mcu is not None and self.stack.currentWidget() is self.connection:
            self.show_page(self.mcu)

    def _on_finished(self, res: OperationResult) -> None:
        if self._close_after_finish:
            QTimer.singleShot(0, self.close)
        self.statusBar().showMessage(res.message or res.state.value)
        idx = self.stack.indexOf(self.diagnostics)
        title = self.pages[idx][1]
        self.nav.item(idx).setText("" if self._compact else (title if res.ok else title + " ●"))
        self.nav.item(idx).setToolTip(
            f"{title}  (Ctrl+{idx + 1})"
            + ("" if res.ok else "\n" + self.tr("Wykryto problem - zobacz Diagnostykę"))
        )
        if self._compact and not res.ok:
            self.statusBar().showMessage("● " + (res.message or res.state.value))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.ctx.controller.busy:
            ans = QMessageBox.question(
                self,
                self.tr("Operacja w toku"),
                self.tr("Trwa operacja na porcie szeregowym. Anulować i zamknąć?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans == QMessageBox.StandardButton.Yes:
                # bez blokowania GUI: anuluj i zamknij po zakończeniu operacji (sygnał finished)
                self._close_after_finish = True
                self.ctx.controller.cancel()
                self.statusBar().showMessage(
                    self.tr("Anulowanie operacji… okno zamknie się po jej zakończeniu")
                )
            event.ignore()
            return
        self.ctx.store.save_geometry(self.saveGeometry(), self.saveState())
        event.accept()
