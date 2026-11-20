"""Wspólne widgety: karty, sekcje zwijane, pasek pamięci, plakietki stanu, ikony."""

from __future__ import annotations

import contextlib
import weakref

from PySide6.QtCore import QEvent, QObject, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

_FALLBACK = {
    "view-refresh": QStyle.StandardPixmap.SP_BrowserReload,
    "dialog-ok-apply": QStyle.StandardPixmap.SP_DialogApplyButton,
    "dialog-cancel": QStyle.StandardPixmap.SP_DialogCancelButton,
    "document-open": QStyle.StandardPixmap.SP_DialogOpenButton,
    "document-save": QStyle.StandardPixmap.SP_DialogSaveButton,
    "edit-clear": QStyle.StandardPixmap.SP_DialogResetButton,
    "dialog-warning": QStyle.StandardPixmap.SP_MessageBoxWarning,
    "dialog-error": QStyle.StandardPixmap.SP_MessageBoxCritical,
    "dialog-information": QStyle.StandardPixmap.SP_MessageBoxInformation,
    "edit-copy": QStyle.StandardPixmap.SP_FileIcon,
}


def icon(name: str) -> QIcon:
    """Ikona z motywu systemu z awaryjnym zamiennikiem stylu Qt."""
    ic = QIcon.fromTheme(name)
    if ic.isNull() and name in _FALLBACK:
        app = QApplication.instance()
        if isinstance(app, QApplication):
            return app.style().standardIcon(_FALLBACK[name])
    return ic


def is_dark(widget: QWidget | None = None) -> bool:
    pal = (widget or QApplication.instance()).palette()  # type: ignore[union-attr]
    return pal.color(QPalette.ColorRole.Window).lightness() < 128


def semantic_color(kind: str, widget: QWidget | None = None) -> QColor:
    """Kolory semantyczne (ok/warn/error/info) dobrane do jasnego i ciemnego motywu."""
    dark = is_dark(widget)
    table = {
        "ok": ("#3fb950", "#1a7f37"),
        "warn": ("#d29922", "#9a6700"),
        "error": ("#f85149", "#cf222e"),
        "info": ("#58a6ff", "#0969da"),
    }
    if kind not in table:
        return (widget or QApplication.instance()).palette().color(QPalette.ColorRole.Text)  # type: ignore[union-attr]
    return QColor(table[kind][0 if dark else 1])


_PALETTE_EVENTS = (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange)


_PENDING: set[int] = set()
_APPLYING: set[int] = set()


def restyle(widget: QWidget, qss: str) -> None:
    """Odroczone (poza obsługą zdarzenia) ponowne wyliczenie arkusza z ``palette(...)``."""
    key = id(widget)
    if key in _PENDING or key in _APPLYING:
        return
    _PENDING.add(key)

    def apply() -> None:
        _PENDING.discard(key)
        _APPLYING.add(key)
        try:
            widget.setStyleSheet("")
            widget.setStyleSheet(qss)
        except RuntimeError:  # widget już usunięty
            pass
        finally:
            _APPLYING.discard(key)

    QTimer.singleShot(0, apply)


class InfoButton(QToolButton):
    """Mały przycisk „i”: dymek po najechaniu, pełne okno po kliknięciu (dłuższe objaśnienia)."""

    def __init__(self, text: str, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.info_text = text
        self._title = title or self.tr("Informacja")
        self.setText("i")
        f = self.font()
        f.setBold(True)
        f.setItalic(True)
        self.setFont(f)
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(text)
        self.setAccessibleName(self._title)
        self.setFixedSize(22, 22)
        self.clicked.connect(self._show)

    def _show(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        box = QMessageBox(
            QMessageBox.Icon.Information, self._title, self.info_text, parent=self.window()
        )
        box.exec()


class Card(QFrame):
    """Delikatnie wyodrębniony panel (kolory z palety). ``info`` = dłuższe objaśnienie pod przyciskiem „i”."""

    def __init__(self, title: str = "", parent: QWidget | None = None, info: str = "") -> None:
        super().__init__(parent)
        self.info_text = info
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._qss = (
            "QFrame#card { background: palette(base); border: 1px solid palette(midlight);"
            " border-radius: 6px; }"
        )
        self.setStyleSheet(self._qss)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(12, 10, 12, 12)
        self._lay.setSpacing(8)
        self.title_label = QLabel(title)
        f = self.title_label.font()
        f.setBold(True)
        self.title_label.setFont(f)
        self.title_label.setVisible(bool(title))
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(self.title_label)
        head.addStretch(1)
        self.info_button = InfoButton(info, title) if info else None
        if self.info_button is not None:
            head.addWidget(self.info_button)
        self._lay.addLayout(head)

    def body(self) -> QVBoxLayout:
        return self._lay

    def changeEvent(self, event: QEvent) -> None:
        if event.type() in _PALETTE_EVENTS:
            restyle(self, self._qss)
        super().changeEvent(event)


class Banner(QLabel):
    """Wyróżniony komunikat (np. instrukcja restartu zasilania)."""

    QSS = (
        "QLabel { background: palette(alternate-base); border: 1px solid palette(mid);"
        " border-left: 4px solid palette(highlight); border-radius: 4px; padding: 8px;"
        " font-weight: bold; }"
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWordWrap(True)
        self.setStyleSheet(self.QSS)
        self.setVisible(False)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() in _PALETTE_EVENTS:
            restyle(self, self.QSS)
        super().changeEvent(event)


class StatusBadge(QLabel):
    """Glif + tekst + kolor semantyczny (stan nie zależy wyłącznie od koloru)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        f = self.font()
        f.setBold(True)
        self.setFont(f)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._last: tuple[str, str, str] | None = None

    def changeEvent(self, event: QEvent) -> None:
        if event.type() in _PALETTE_EVENTS and self._last:
            self.set_status(*self._last)
        super().changeEvent(event)

    def set_status(self, glyph: str, text: str, kind: str) -> None:
        self._last = (glyph, text, kind)
        col = semantic_color(kind, self).name()
        self.setText(f"<span style='color:{col}'>{glyph}</span> {text}")
        self.setAccessibleName(text)


class CollapsibleSection(QWidget):
    """Sekcja zwijana (parametry zaawansowane)."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.toggle = QToolButton()
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle.setAutoRaise(True)
        self.content = QWidget()
        self.content.setVisible(False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self.content)
        self.toggle.toggled.connect(self._on_toggle)

    def _on_toggle(self, on: bool) -> None:
        self.toggle.setArrowType(Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow)
        self.content.setVisible(on)

    def set_expanded(self, on: bool) -> None:
        self.toggle.setChecked(on)


class MemoryBar(QWidget):
    """Pasek pojemności: segmenty (etykieta, bajty, rola koloru) względem sumy."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._segments: list[tuple[str, int, QColor]] = []
        self._total = 0
        self._used = 0
        self.setMinimumHeight(22)
        self.setMaximumHeight(26)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_layout(self, segments: list[tuple[str, int, str]], used: int = 0) -> None:
        """``segments``: (nazwa, bajty, rola: 'flash'|'eeprom'); ``used``: wypełnienie flash."""
        palette = {"flash": semantic_color("info", self), "eeprom": semantic_color("warn", self)}
        self._segments = [(n, b, palette.get(r, QColor("gray"))) for n, b, r in segments]
        self._total = sum(b for _, b, _ in self._segments)
        self._used = used
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(300, 24)

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 2.5, -0.5, -2.5)
        pal = self.palette()
        p.setPen(pal.color(QPalette.ColorRole.Mid))
        p.setBrush(pal.color(QPalette.ColorRole.AlternateBase))
        p.drawRoundedRect(r, 4, 4)
        if self._total <= 0:
            return
        x = r.left()
        for i, (_name, size, col) in enumerate(self._segments):
            w = r.width() * size / self._total
            seg = QRectF(x, r.top(), max(w, 2), r.height())
            fill = QColor(col)
            fill.setAlpha(70)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(seg.adjusted(1, 1, -1, -1), 3, 3)
            if i == 0 and self._used > 0:
                used_w = min(self._used / size, 1.0) * seg.width() if size else 0
                p.setBrush(col)
                p.drawRoundedRect(
                    QRectF(seg.left() + 1, seg.top() + 1, max(used_w - 2, 2), seg.height() - 2),
                    3,
                    3,
                )
            x += w
        p.setPen(pal.color(QPalette.ColorRole.Text))
        f = QFont(self.font())
        f.setPointSizeF(max(f.pointSizeF() - 1, 7))
        p.setFont(f)
        x = r.left()
        for name, size, _col in self._segments:
            w = r.width() * size / self._total
            p.drawText(
                QRectF(x + 4, r.top(), w - 6, r.height()), Qt.AlignmentFlag.AlignVCenter, name
            )
            x += w


_MUTED: weakref.WeakSet[_MutedFilter] = weakref.WeakSet()


def refresh_muted() -> None:
    """Odświeża kolory przygaszonych etykiet po zmianie motywu."""
    for f in list(_MUTED):
        with contextlib.suppress(RuntimeError):
            f.apply()


class _MutedFilter(QObject):
    """Utrzymuje przygaszony kolor etykiety zgodny z bieżącą paletą (jasny/ciemny motyw)."""

    def __init__(self, label: QLabel) -> None:
        super().__init__(label)
        self._label = label
        self._busy = False
        label.installEventFilter(self)
        _MUTED.add(self)
        self.apply()

    def apply(self) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            color = QApplication.palette().color(QPalette.ColorRole.PlaceholderText).name()
            qss = f"color: {color};"
            if self._label.styleSheet() != qss:
                self._label.setStyleSheet(qss)
        finally:
            self._busy = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() in _PALETTE_EVENTS:
            self.apply()
        return False


def muted(label: QLabel) -> QLabel:
    """Przygaszony tekst pomocniczy (kolor z palety, odświeżany przy zmianie motywu)."""
    label.setWordWrap(True)
    _MutedFilter(label)
    return label


def hbox(*widgets: QWidget | None, stretch_end: bool = False, margins: int = 0) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setContentsMargins(margins, margins, margins, margins)
    for w in widgets:
        if w is not None:
            lay.addWidget(w)
    if stretch_end:
        lay.addStretch(1)
    return lay
