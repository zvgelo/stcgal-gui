"""Dwujęzyczność PL/EN: kompletność tłumaczeń, wybór języka i widoki w angielskim."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QLocale

import stcgal_gui.gui.main_window as mw_mod
import stcgal_gui.gui.tabs.connection as conn_mod
from stcgal_gui.__main__ import build_window
from stcgal_gui.backends.base import Capabilities
from stcgal_gui.backends.mock import MockBackend
from stcgal_gui.core import diagnosis, safety
from stcgal_gui.core.firmware import FirmwareError, parse_ihex
from stcgal_gui.core.i18n import TRANSLATIONS_DIR, effective_language, install_translators
from stcgal_gui.core.linkstate import LinkState, describe
from stcgal_gui.core.settings import AppSettings, SettingsStore
from stcgal_gui.models.data import ErrorKind, PortInfo, ProgramParams, WriteScope

TS = Path(__file__).parent.parent / "stcgal_gui" / "resources" / "translations" / "stcgal_gui_en.ts"
CH340 = PortInfo("/dev/ttyUSB0", "USB Serial", 0x1A86, 0x7523, is_ch340=True)  # fmt: skip
POLISH = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")


@pytest.fixture
def en(qapp):
    install_translators(qapp, "en")
    yield
    install_translators(qapp, "pl")


def _messages() -> list[tuple[str, str, ET.Element]]:
    root = ET.parse(TS).getroot()
    return [
        (c.findtext("name") or "", m.findtext("source") or "", m)
        for c in root.findall("context")
        for m in c.findall("message")
    ]


def test_every_message_translated():
    msgs = _messages()
    assert len(msgs) > 300
    for ctx, src, m in msgs:
        tr = m.find("translation")
        assert tr is not None
        assert tr.get("type") != "unfinished", (ctx, src)
        forms = [f.text for f in tr.findall("numerusform")] or [tr.text]
        assert all(f and f.strip() for f in forms), (ctx, src)
        for f in forms:
            assert f is not None
            assert not POLISH.search(f), (ctx, src, f)  # brak polskich liter w angielskim
            assert sorted(re.findall(r"%\d|%n", f)) == sorted(re.findall(r"%\d|%n", src)), (src, f)


def test_compiled_catalog_exists_next_to_source():
    assert (TRANSLATIONS_DIR / "stcgal_gui_en.qm").is_file()
    assert (TRANSLATIONS_DIR / "stcgal_gui_en.qm").stat().st_size > 10_000


def test_language_resolution():
    assert effective_language("pl") == "pl"
    assert effective_language("en") == "en"
    assert effective_language("system", QLocale("pl_PL")) == "pl"
    assert effective_language("system", QLocale("de_DE")) == "en"
    assert effective_language("system", QLocale("en_US")) == "en"


def test_switching_language_changes_texts(qapp):
    assert QCoreApplication.translate("Safety", "Kasowanie wymaga trybu eksperta") == (
        "Kasowanie wymaga trybu eksperta"
    )
    assert install_translators(qapp, "en") == "en"
    assert QCoreApplication.translate("Safety", "Kasowanie wymaga trybu eksperta") == (
        "Erase needs expert mode"
    )
    assert install_translators(qapp, "pl") == "pl"
    assert QCoreApplication.translate("Safety", "Kasowanie wymaga trybu eksperta") == (
        "Kasowanie wymaga trybu eksperta"
    )


def test_language_setting_roundtrip_and_invalid_value(store):
    s = store.load()
    assert s.language == "system"
    s.language = "en"
    store.save(s)
    assert store.load().language == "en"
    s.language = "xx"
    store.save(s)
    assert store.load().language == "system"


def test_core_messages_in_english(en):
    assert describe(LinkState.NO_ADAPTER)[1] == "No adapter"
    assert "Permissions" in diagnosis.troubleshooting_hint(ErrorKind.PERMISSION, windows=False)
    assert diagnosis.user_message(ErrorKind.PORT_MISSING, windows=True) is not None
    with pytest.raises(FirmwareError, match="Line 1: "):
        parse_ihex(":zz\n")
    assert not POLISH.search(diagnosis.backend_missing_message(windows=True))


def test_safety_risks_keep_their_meaning_in_english(en, tmp_path):
    img = tmp_path / "a.bin"
    img.write_bytes(b"\x01" * 100)
    caps = Capabilities()
    risks = safety.assess(
        caps, ProgramParams(img, options=["x=1"]), WriteScope.FLASH_ONLY, 1000, expert=False
    )
    by_id = {r.id: r for r in risks}
    assert by_id["options_requested"].hard
    assert by_id["options_requested"].title == "Changing options (-o) is not allowed"
    assert "does not guarantee" in by_id["erase_scope_unverified"].title
    text = safety.format_risks(risks)
    assert not POLISH.search(text)
    # twardy wynik zostaje identyczny jak po polsku
    assert [r.id for r in safety.unresolved(risks, frozenset())] == [
        r.id for r in risks if r.hard or r.id not in frozenset()
    ]


def test_all_views_build_in_english(qtbot, store, monkeypatch, en):
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [CH340])
    monkeypatch.setattr(mw_mod, "enumerate_ports", lambda **_: [CH340])
    w = build_window(MockBackend(), store)
    qtbot.addWidget(w)
    w.show()
    labels = [w.nav.item(i).text() for i in range(w.nav.count())]
    assert labels == [
        "Connection", "Microcontroller", "Programming", "Read and backup", "Diagnostics", "Settings"
    ]  # fmt: skip
    assert w.program.program_btn.text() == "Program"
    assert w.program.expert_cb.text() == "Expert mode"
    assert w.settings_tab.language.count() == 3
    assert "Warnings and errors" in [
        w.diagnostics.level_combo.itemText(i) for i in range(w.diagnostics.level_combo.count())
    ]
    for i in range(w.stack.count()):
        w.show_page(w.stack.widget(i))
        qtbot.wait(20)


def test_english_ui_has_no_polish_leftovers(qtbot, store, monkeypatch, en):
    """Teksty widgetów po wykryciu MCU i otwarciu trybu eksperta nie zawierają polskich liter."""
    from PySide6.QtWidgets import QLabel, QPushButton

    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [CH340])
    monkeypatch.setattr(mw_mod, "enumerate_ports", lambda **_: [CH340])
    w = build_window(MockBackend(wait_s=0.01), store)
    qtbot.addWidget(w)
    w.show()
    w.connection.detect()
    qtbot.waitUntil(lambda: w.ctx.mcu is not None, timeout=5000)
    w.program.expert_cb.setChecked(True)
    w.ctx.add_entry("INFO", "x")
    bad = []
    for cls in (QLabel, QPushButton):
        for wd in w.findChildren(cls):
            if POLISH.search(wd.text()) and wd is not w.settings_tab.lang_note:  # dwujęzyczna notka
                bad.append(wd.text())
            if POLISH.search(wd.toolTip()):
                bad.append(wd.toolTip())
    from PySide6.QtWidgets import QComboBox, QTableWidget

    for table in w.findChildren(QTableWidget):
        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                item = table.item(r, c)
                if item is not None and POLISH.search(item.text()):
                    bad.append(item.text())
        for c in range(table.columnCount()):
            hdr = table.horizontalHeaderItem(c)
            if hdr is not None and POLISH.search(hdr.text()):
                bad.append(hdr.text())
    for combo in w.findChildren(QComboBox):
        bad += [t for t in (combo.itemText(i) for i in range(combo.count())) if POLISH.search(t)]
    assert not bad, bad


def test_settings_language_note_after_change(qtbot, store, monkeypatch):
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [CH340])
    monkeypatch.setattr(mw_mod, "enumerate_ports", lambda **_: [CH340])
    w = build_window(MockBackend(), store)
    qtbot.addWidget(w)
    tab = w.settings_tab
    assert not tab.lang_note.isVisibleTo(tab)
    tab.language.setCurrentIndex(tab.language.findData("en"))
    tab.save()
    assert tab.lang_note.isVisibleTo(tab)
    assert SettingsStore(store._qs).load().language == "en"
    assert isinstance(AppSettings().language, str)


def test_write_confirmations_in_english_keep_cancel_default(
    qtbot, store, monkeypatch, tmp_path, en
):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [CH340])
    monkeypatch.setattr(mw_mod, "enumerate_ports", lambda **_: [CH340])
    backend = MockBackend(guarantees=False)
    w = build_window(backend, store)
    qtbot.addWidget(w)
    w.show()
    fw = tmp_path / "fw.bin"
    fw.write_bytes(b"\x12" * 1024)
    w.program.fw_edit.setText(str(fw))
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    shown: list[tuple[str, str, list[str], object]] = []

    def fake_exec(self):
        shown.append(
            (
                self.windowTitle(),
                self.text(),
                [b.text() for b in self.buttons()],
                self.standardButton(self.defaultButton()),
            )
        )
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: None)
    w.program.program_btn.click()
    assert backend.calls == []  # odmowa: nic nie zapisano
    assert len(shown) == 1
    title, text, buttons, default = shown[0]
    assert title == "Confirm Flash write"
    assert "ERASED" in text and "WRITTEN" in text
    assert "Erase and program" in buttons
    assert default == QMessageBox.StandardButton.Cancel
    assert not POLISH.search(text + " ".join(buttons))


@pytest.mark.parametrize("scenario", ["permission", "busy"])
def test_error_scenarios_have_english_messages(qtbot, store, monkeypatch, en, scenario):
    from PySide6.QtWidgets import QLabel

    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [CH340])
    monkeypatch.setattr(mw_mod, "enumerate_ports", lambda **_: [CH340])
    backend = MockBackend(wait_s=0.01, scenario=scenario)
    w = build_window(backend, store)
    qtbot.addWidget(w)
    w.show()
    s = w.ctx.settings
    s.timeout_s = 5
    w.ctx.update_settings(s)
    w.connection.detect()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=8000)
    res = w.ctx.last_result
    assert res is not None and not POLISH.search(res.message)
    w.show_page(w.diagnostics)
    texts = [lb.text() for lb in w.findChildren(QLabel)]
    assert not [t for t in texts if POLISH.search(t) and "Zmiana języka" not in t], texts
    assert not [e.text for e in w.ctx.entries if POLISH.search(e.text)]


def test_translation_catalog_is_up_to_date(tmp_path):
    """Każdy tekst z kodu jest w katalogu .ts (nikt nie zapomniał uruchomić lupdate)."""
    import shutil
    import subprocess
    import sys

    exe = shutil.which("pyside6-lupdate") or str(Path(sys.executable).parent / "pyside6-lupdate")
    if not Path(exe).exists():
        pytest.skip("brak pyside6-lupdate")
    root = Path(__file__).parent.parent
    out = tmp_path / "new.ts"
    files = sorted(str(p) for p in (root / "stcgal_gui").rglob("*.py"))
    subprocess.run(
        [exe, *files, "-ts", str(out), "-locations", "none"],
        check=True, capture_output=True, cwd=root,
    )  # fmt: skip
    new = {
        (c.findtext("name"), m.findtext("source"))
        for c in ET.parse(out).getroot().findall("context")
        for m in c.findall("message")
    }
    have = {(c, s) for c, s, _ in _messages()}
    assert new <= have, sorted(new - have)[:5]
    assert have <= new, f"nieużywane wpisy w .ts: {sorted(have - new)[:5]}"
