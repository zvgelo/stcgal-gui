import os

import pytest
from PySide6.QtWidgets import QMessageBox

import stcgal_gui.gui.main_window as mw_mod
import stcgal_gui.gui.tabs.connection as conn_mod
from stcgal_gui.__main__ import build_window
from stcgal_gui.backends.mock import MockBackend
from stcgal_gui.core.linkstate import LinkState
from stcgal_gui.core.settings import AppSettings
from stcgal_gui.gui.tabs.backup import FIRMWARE_UNSUPPORTED
from stcgal_gui.gui.tabs.connection import POWER_CYCLE_TEXT
from stcgal_gui.models.data import PortInfo

CH340 = PortInfo(
    "/dev/ttyUSB0", "USB Serial", 0x1A86, 0x7523,
    by_id="/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0", is_ch340=True,
)  # fmt: skip


@pytest.fixture
def ports(monkeypatch):
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [CH340])
    monkeypatch.setattr(mw_mod, "enumerate_ports", lambda **_: [CH340])


def make(qtbot, store, backend=None):
    w = build_window(backend or MockBackend(), store)
    qtbot.addWidget(w)
    w.show()
    return w


def page(w):
    return w.stack.currentWidget()


def test_starts_without_programmer(qtbot, store, monkeypatch):
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [])
    w = make(qtbot, store)
    assert w.connection.port_combo.count() == 0
    assert not w.connection.detect_btn.isEnabled()
    assert "Nie wykryto adaptera" in w.connection.adapter_badge.text()
    assert w.ctx.link is LinkState.NO_ADAPTER
    assert "Brak adaptera" in w.header.badge.text()
    assert w.nav.count() == 6 and w.stack.count() == 6


def test_shows_ch340_and_selects_ttyusb0(qtbot, store, ports):
    w = make(qtbot, store)
    assert w.connection.selected_port() == "/dev/ttyUSB0"
    assert "1a86:7523" in w.connection.port_combo.currentText()
    assert "CH340" in w.connection.adapter_badge.text()
    assert "by-id" in w.connection.port_note.text()
    assert "nie oznacza wykrycia mikrokontrolera" in w.connection.adapter_card.info_text
    assert w.ctx.link is LinkState.ADAPTER_READY  # adapter ≠ wykryty MCU
    assert "nie zidentyfikowany" in w.header.summary.text()


def test_advanced_params_collapsed_by_default(qtbot, store, ports):
    w = make(qtbot, store)
    adv = w.connection.advanced
    assert not adv.content.isVisible()
    adv.toggle.click()
    assert adv.content.isVisible() and w.connection.baud_combo.isVisible()


def test_detect_flow_states_and_mcu_view(qtbot, store, ports):
    backend = MockBackend(wait_s=0.4)
    w = make(qtbot, store, backend)
    links = []
    w.ctx.link_changed.connect(links.append)
    w.connection.detect()
    qtbot.waitUntil(lambda: LinkState.WAITING_MCU in links, timeout=3000)
    assert POWER_CYCLE_TEXT in w.connection.wait_label.text()
    assert w.connection.wait_label.isVisible() and w.connection.cancel_btn.isEnabled()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    assert LinkState.IDENTIFYING in links and w.ctx.link is LinkState.MCU_DETECTED
    assert w.mcu.fields["model"].text() == "STC8H8K64U"
    assert w.mcu.fields["magic"].text() == "0xF784"
    assert w.mcu.fields["freq"].text() == "24.0 MHz"
    assert [c.kind for c in backend.calls] == ["identify"]
    assert page(w) is w.mcu
    assert "STC8H8K64U" in w.header.summary.text()
    assert "Mikrokontroler wykryty" in w.header.badge.text()


def test_mcu_view_states_data_sources(qtbot, store, ports):
    w = make(qtbot, store)
    assert w.mcu.empty.isVisibleTo(w.mcu) and not w.mcu.content.isVisibleTo(w.mcu)
    w.ctx.set_mcu(MockBackend().mcu, "/dev/ttyUSB0")
    assert w.mcu.content.isVisibleTo(w.mcu)
    texts = " ".join(lab.text() for lab in w.mcu.findChildren(type(w.mcu.title)))
    sources = " ".join(c.info_text for c in w.mcu.cards)  # źródła danych są pod przyciskami „i”
    assert "baza modeli stcgal" in sources and "odpowiedź bootloadera" in sources
    assert "reset_pin_enabled" in texts and "Watchdog" not in texts  # tylko grupy z danymi
    assert "Reset i zasilanie" in texts
    assert "Flash (kod)" in texts and "65024 B" in w.mcu.fields["code"].text()
    assert w.mcu.copy_btn.isEnabled()
    assert "Raport MCU" in w.mcu.report_text() and "baza modeli" in w.mcu.report_text()


def test_report_copy_to_clipboard(qtbot, store, ports):
    from PySide6.QtGui import QGuiApplication

    w = make(qtbot, store)
    w.ctx.set_mcu(MockBackend().mcu, "/dev/ttyUSB0")
    w.mcu.copy_btn.click()
    assert "STC8H8K64U" in QGuiApplication.clipboard().text()


def test_mcu_data_cleared_when_port_changes_or_adapter_unplugged(qtbot, store, monkeypatch):
    other = PortInfo("/dev/ttyUSB1", "x", 0x10C4, 0xEA60)
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [CH340, other])
    monkeypatch.setattr(mw_mod, "enumerate_ports", lambda **_: [CH340, other])
    w = make(qtbot, store)
    w.ctx.set_mcu(MockBackend().mcu, "/dev/ttyUSB0")
    assert w.ctx.link is LinkState.MCU_DETECTED
    w.connection.port_combo.setCurrentIndex(w.connection.port_combo.findData("/dev/ttyUSB1"))
    assert w.ctx.mcu is None and not w.mcu.content.isVisibleTo(w.mcu)
    assert w.ctx.link is LinkState.ADAPTER_READY
    # odłączenie adaptera po ponownym wykryciu
    w.connection.port_combo.setCurrentIndex(w.connection.port_combo.findData("/dev/ttyUSB0"))
    w.ctx.set_mcu(MockBackend().mcu, "/dev/ttyUSB0")
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [])
    w.connection.refresh_ports()
    assert w.ctx.mcu is None and w.ctx.link is LinkState.NO_ADAPTER


def test_repeated_detection_replaces_data(qtbot, store, ports):
    backend = MockBackend(wait_s=0.05)
    w = make(qtbot, store, backend)
    for _ in range(2):
        w.connection.detect()
        qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    assert len(backend.calls) == 2 and w.ctx.link is LinkState.MCU_DETECTED


def test_detect_can_be_cancelled(qtbot, store, ports):
    w = make(qtbot, store, MockBackend(scenario="no_mcu"))
    w.connection.detect()
    qtbot.waitUntil(lambda: w.connection.cancel_btn.isEnabled(), timeout=2000)
    assert not w.connection.detect_btn.isEnabled()
    w.connection.cancel_btn.click()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    assert w.ctx.link is LinkState.ADAPTER_READY
    assert "Anulowano" in w.connection.status_detail.text()


def test_timeout_state(qtbot, store, ports):
    w = make(qtbot, store, MockBackend(scenario="no_mcu"))
    w.connection.timeout_spin.setValue(5)
    w.ctx.settings.timeout_s = 5
    params = w.connection.current_params()
    params.timeout_s = 0.3
    w.ctx.controller.start_identify(params)
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    assert w.ctx.link is LinkState.TIMEOUT
    assert "Przekroczono" in w.connection.status.text()
    assert "Timeout" in w.diagnostics.diag.text() or "zasilanie" in w.diagnostics.diag.text()


def test_second_operation_rejected_while_busy(qtbot, store, ports):
    w = make(qtbot, store, MockBackend(scenario="no_mcu"))
    params = w.connection.current_params()
    assert w.ctx.controller.start_identify(params) is True
    assert w.ctx.controller.start_identify(params) is False
    w.ctx.controller.cancel()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)


def test_permission_error_in_diagnostics(qtbot, store, ports):
    w = make(qtbot, store, MockBackend(scenario="permission"))
    w.connection.detect()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=3000)
    assert w.ctx.link is LinkState.ERROR
    assert "Błąd komunikacji" in w.header.badge.text()
    assert "Permission denied" in w.diagnostics.raw.toPlainText()  # surowe dane zachowane
    levels = {e.level for e in w.ctx.entries}
    assert "ERROR" in levels


def test_diagnostics_filter_and_search(qtbot, store, ports):
    w = make(qtbot, store)
    d = w.diagnostics
    w.ctx.add_entry("INFO", "info jeden")
    w.ctx.add_entry("WARNING", "uwaga dwa")
    w.ctx.add_entry("ERROR", "błąd trzy")
    base = d.model.rowCount()
    d.level_combo.setCurrentIndex(1)
    assert d.proxy.rowCount() == 2
    d.level_combo.setCurrentIndex(2)
    assert d.proxy.rowCount() == 1
    d.level_combo.setCurrentIndex(0)
    d.search.setText("DWA")
    assert d.proxy.rowCount() == 1
    d.search.clear()
    assert d.proxy.rowCount() == base
    d.table.selectRow(0)
    assert d.text(selected=True).count("\n") == 0
    assert "[INFO]" in d.text() or "[ERROR]" in d.text()


def test_structured_log_from_streams(qtbot, store, ports):
    w = make(qtbot, store)
    n = len(w.ctx.entries)
    w.ctx._on_log("stdout", "Waiting for MCU, please cycle power: ")
    assert len(w.ctx.entries) == n  # linia niedokończona
    w.ctx._on_log("stdout", "done\n")
    w.ctx._on_log("stderr", "Serial port error: [Errno 13] Permission denied\n")
    new = w.ctx.entries[n:]
    assert [e.level for e in new] == ["INFO", "ERROR"]
    assert w.ctx.log_entries[-1] == ("stderr", "Serial port error: [Errno 13] Permission denied\n")


def test_backup_tab_is_honest_about_firmware_read(qtbot, store, ports):
    w = make(qtbot, store)
    assert FIRMWARE_UNSUPPORTED in w.backup.msg.text()
    assert w.backup.rows["Firmware aplikacji"] == "Nieobsługiwane"
    assert w.backup.rows["Dane pamięci (Flash/EEPROM)"] == "Nieobsługiwane"
    assert not w.backup.save_btn.isEnabled()
    texts = [b.text().lower() for b in w.backup.findChildren(type(w.backup.save_btn))]
    assert not any("firmware" in t and "zapisz" in t for t in texts)


def test_program_flow_validation_confirmation_and_report(
    qtbot, store, ports, tmp_path, firmware_bin, monkeypatch
):
    backend = MockBackend()
    w = make(qtbot, store, backend)
    p = w.program
    assert not p.program_btn.isEnabled()
    p.fw_edit.setText(str(tmp_path / "missing.bin"))
    assert not p.program_btn.isEnabled() and "nie istnieje" in p.info.text()
    p.fw_edit.setText(str(firmware_bin))
    assert "1024 B" in p.file_summary.text()
    assert "nie został porównany" in p.usage_label.text()  # brak MCU → brak zgadywania
    assert not p.program_btn.isEnabled()  # twarda blokada: MCU niezidentyfikowany
    assert "nie został zidentyfikowany" in p.risk_label.text()

    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    assert (
        p.program_btn.isEnabled()
    )  # backend deklaruje gwarancje (symulacja) → brak ryzyk miękkich
    assert p.membar.isVisibleTo(p) and "1024 z 65024 B" in p.usage_label.text()

    # odmowa w oknie potwierdzenia => zero wywołań backendu
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: None)
    p.program_btn.click()
    assert backend.calls == [] and not w.ctx.controller.busy

    # akceptacja => pojedynczy zapis z potwierdzeniem
    monkeypatch.setattr(
        QMessageBox,
        "clickedButton",
        lambda self: next(b for b in self.buttons() if "Kasuj" in b.text()),
    )
    p.program_btn.click()
    assert p.progress.maximum() in (0, 100)
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    assert [c.kind for c in backend.calls] == ["program"]
    assert backend.calls[0].prog.eeprom_image is None and not backend.calls[0].prog.options
    assert "NIE wykonano" in p.report.toPlainText()
    assert "poprawna" not in p.report.toPlainText().lower()
    assert "bez weryfikacji" in p.stage.text()
    assert p.progress.value() == 100


def test_program_progress_indeterminate_until_real_progress(
    qtbot, store, ports, firmware_bin, monkeypatch
):
    backend = MockBackend(wait_s=0.5, write_s=0.3)
    w = make(qtbot, store, backend)
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    w.program.fw_edit.setText(str(firmware_bin))
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(
        QMessageBox,
        "clickedButton",
        lambda self: next(b for b in self.buttons() if "Kasuj" in b.text()),
    )
    w.program.program_btn.click()
    assert w.program.progress.maximum() == 0  # wskaźnik nieokreślony - brak fikcyjnych procentów
    qtbot.waitUntil(lambda: w.program._got_progress, timeout=4000)
    assert w.program.progress.maximum() == 100
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)


def test_program_blocked_for_oversized_firmware(qtbot, store, ports, tmp_path):
    w = make(qtbot, store)
    w.ctx.set_mcu(MockBackend().mcu, "/dev/ttyUSB0")
    big = tmp_path / "big.bin"
    big.write_bytes(b"\x00" * 70000)
    w.program.fw_edit.setText(str(big))
    assert not w.program.program_btn.isEnabled()
    assert "przekracza" in w.program.info.text()


def test_settings_persist(qtbot, store, ports):
    w = make(qtbot, store)
    w.settings_tab.baud.setValue(57600)
    w.settings_tab.protocol.setCurrentText("stc8d")
    w.settings_tab.save()
    w.close()
    loaded = store.load()
    assert loaded.baud == 57600 and loaded.protocol == "stc8d"
    w2 = make(qtbot, store)
    assert w2.connection.baud_combo.currentText() == "57600"
    assert w2.connection.protocol_combo.currentText() == "stc8d"


def test_protocol_mismatch_warning(qtbot, store, ports):
    w = make(qtbot, store)
    w.ctx.set_mcu(MockBackend().mcu, "/dev/ttyUSB0")
    w.connection.protocol_combo.setCurrentText("stc8g")
    assert "stc8d" in w.connection.proto_warn.text()


def test_log_redaction_toggle(qtbot, store, ports):
    w = make(qtbot, store)
    home = os.path.expanduser("~")
    w.ctx.add_info(f"plik {home}/fw.bin")
    assert home not in w.diagnostics.text()
    w.diagnostics.redact_cb.setChecked(False)
    assert home in w.diagnostics.text()


def test_settings_defaults_roundtrip(store):
    s = AppSettings(default_port="/dev/ttyUSB0", theme="dark", debug=True)
    store.save(s)
    assert store.load() == s


def test_auto_refresh_does_not_spam_log_with_builtin_ports(qtbot, store, monkeypatch):
    many = [PortInfo(f"/dev/ttyS{i}") for i in range(30)] + [CH340]
    fn = lambda include_builtin=False: many if include_builtin else [CH340]  # noqa: E731
    monkeypatch.setattr(conn_mod, "enumerate_ports", fn)
    monkeypatch.setattr(mw_mod, "enumerate_ports", fn)
    w = make(qtbot, store)
    w.connection.all_ports_cb.setChecked(True)
    before = len(w.ctx.log_entries)
    w._port_timer.setInterval(50)
    qtbot.wait(400)
    assert len(w.ctx.log_entries) == before


def test_by_id_default_port_is_honoured(qtbot, store, monkeypatch):
    other = PortInfo("/dev/ttyUSB1", "x", 0x10C4, 0xEA60)
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [other, CH340])
    monkeypatch.setattr(
        conn_mod.ps, "normalize_port", lambda p: "/dev/ttyUSB0" if "by-id" in p else p
    )
    s = store.load()
    s.default_port = CH340.by_id
    store.save(s)
    w = make(qtbot, store)
    assert w.connection.selected_port() == "/dev/ttyUSB0"


def test_debug_toggle_keeps_unsaved_connection_choices(qtbot, store, ports):
    w = make(qtbot, store)
    w.connection.protocol_combo.setCurrentText("stc8d")
    w.diagnostics.debug_cb.setChecked(True)
    assert w.connection.protocol_combo.currentText() == "stc8d"


def test_keyboard_shortcuts_navigate(qtbot, store, ports):
    from PySide6.QtGui import QKeySequence, QShortcut

    w = make(qtbot, store)
    shortcuts = {sc.key().toString(): sc for sc in w.findChildren(QShortcut)}
    for key in ("Ctrl+1", "Ctrl+6", "F5", "Ctrl+D", "Esc", "Ctrl+O", "Ctrl+F", "Ctrl+Shift+P"):
        assert QKeySequence(key).toString() in shortcuts, key
    shortcuts["Ctrl+3"].activated.emit()
    assert page(w) is w.program
    shortcuts["Ctrl+5"].activated.emit()
    assert page(w) is w.diagnostics
    shortcuts["Ctrl+F"].activated.emit()
    assert page(w) is w.diagnostics


def test_compact_window_collapses_navigation(qtbot, store, ports):
    w = make(qtbot, store)
    w.resize(1000, 700)
    qtbot.waitUntil(lambda: not w._compact)
    assert w.nav.item(0).text() == "Połączenie"
    w.resize(640, 500)
    qtbot.waitUntil(lambda: w._compact)
    assert w.nav.item(0).text() == "" and w.nav.item(0).toolTip()
    assert w.nav.width() <= 60


@pytest.mark.parametrize("size", [(580, 440), (940, 700), (1920, 1040)])
def test_no_hidden_controls_at_sizes(qtbot, store, ports, size):
    w = make(qtbot, store)
    w.resize(*size)
    for i in range(w.stack.count()):
        w.nav.setCurrentRow(i)
        qtbot.wait(20)
        assert w.stack.currentWidget().minimumSizeHint().width() <= w.stack.width() + 40


def test_theme_switch_forces_light_and_dark(qtbot, store, ports):
    from PySide6.QtWidgets import QApplication

    w = make(qtbot, store)
    app = QApplication.instance()
    for theme, light in (("light", True), ("dark", False)):
        s = w.ctx.settings
        s.theme = theme
        w.ctx.update_settings(s)
        assert (app.palette().window().color().lightness() > 128) is light
    s = w.ctx.settings
    s.theme = "system"
    w.ctx.update_settings(s)


def test_diagnostics_usable_with_large_font_small_window(qtbot, store, ports):
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QScrollArea

    app = QApplication.instance()
    old = app.font()
    try:
        f = QFont(old)
        f.setPointSize(16)
        app.setFont(f)
        w = make(qtbot, store)
        w.resize(580, 440)
        w.show_page(w.diagnostics)
        qtbot.wait(50)
        assert w.diagnostics.findChild(QScrollArea) is not None
        assert w.diagnostics.table.height() >= 60 or w.diagnostics.tabs.minimumHeight() >= 200
    finally:
        app.setFont(old)


def test_log_memory_is_capped(qtbot, store, ports):
    from stcgal_gui.gui.context import MAX_ENTRIES

    w = make(qtbot, store)
    for i in range(MAX_ENTRIES + 50):
        w.ctx.add_entry("INFO", f"e{i}", raw=False)
    assert len(w.ctx.entries) <= MAX_ENTRIES
    assert w.diagnostics.model.rowCount() <= MAX_ENTRIES


def test_close_during_operation_cancels_and_waits(qtbot, store, ports, monkeypatch):
    w = make(qtbot, store, MockBackend(scenario="no_mcu"))
    w.connection.detect()
    qtbot.waitUntil(lambda: w.ctx.controller.busy)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    w.close()
    assert w.ctx.controller.busy  # użytkownik odmówił - operacja trwa, okno zostaje
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    w.close()
    assert w.isVisible()  # okno nie blokuje GUI: zamknie się po zakończeniu operacji
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=8000)
    qtbot.waitUntil(lambda: not w.isVisible(), timeout=5000)


def test_muted_label_follows_theme(qtbot, store, ports):

    w = make(qtbot, store)
    lab = w.connection.port_note
    colors = []
    for theme in ("light", "dark"):
        s = w.ctx.settings
        s.theme = theme
        w.ctx.update_settings(s)
        qtbot.wait(20)
        colors.append(lab.styleSheet())
    assert colors[0] != colors[1]
    s = w.ctx.settings
    s.theme = "system"
    w.ctx.update_settings(s)


def test_escape_cancels_identify_but_asks_before_aborting_write(
    qtbot, store, ports, firmware_bin, monkeypatch
):
    w = make(qtbot, store, MockBackend(scenario="no_mcu"))
    w.connection.detect()
    qtbot.waitUntil(lambda: w.ctx.controller.busy)
    w._escape()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)

    asked = []
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: asked.append(a) or QMessageBox.StandardButton.No
    )
    w2 = make(qtbot, store, MockBackend(wait_s=1.0))
    w2.ctx.controller.current_kind = None
    from stcgal_gui.backends.base import WriteConfirmation
    from stcgal_gui.models.data import ProgramParams

    conn = w2.connection.current_params()
    w2.ctx.controller.start_program(
        conn, ProgramParams(firmware_bin), WriteConfirmation(conn.port, firmware_bin)
    )
    w2._escape()
    assert asked and w2.ctx.controller.busy  # odmowa → zapis trwa
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    w2._escape()
    qtbot.waitUntil(lambda: not w2.ctx.controller.busy, timeout=5000)


def test_program_rechecks_file_before_confirmation(qtbot, store, ports, tmp_path, monkeypatch):
    backend = MockBackend()
    w = make(qtbot, store, backend)
    fw = tmp_path / "a.bin"
    fw.write_bytes(b"\x01" * 100)
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    w.program.fw_edit.setText(str(fw))
    assert w.program.program_btn.isEnabled()
    fw.write_bytes(b"\x01" * 70000)  # zmiana na dysku bez zmiany pola
    shown = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append(1) or 0)
    w.program.start_program()
    assert not shown and backend.calls == []  # blokada przed oknem potwierdzenia


def test_port_change_after_timeout_updates_views(qtbot, store, monkeypatch):
    other = PortInfo("/dev/ttyUSB1", "x", 0x10C4, 0xEA60)
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [CH340, other])
    monkeypatch.setattr(mw_mod, "enumerate_ports", lambda **_: [CH340, other])
    w = make(qtbot, store, MockBackend(scenario="no_mcu"))
    params = w.connection.current_params()
    params.timeout_s = 0.2
    w.ctx.controller.start_identify(params)
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    assert w.ctx.link is LinkState.TIMEOUT
    w.connection.port_combo.setCurrentIndex(w.connection.port_combo.findData("/dev/ttyUSB1"))
    assert "Adapter dostępny" in w.connection.status.text()


def test_mcu_invalidated_after_write(qtbot, store, ports, firmware_bin, monkeypatch):
    backend = MockBackend()
    w = make(qtbot, store, backend)
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    w.program.fw_edit.setText(str(firmware_bin))
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(
        QMessageBox,
        "clickedButton",
        lambda self: next(b for b in self.buttons() if "Kasuj" in b.text()),
    )
    w.program.program_btn.click()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    assert w.ctx.mcu is None and w.ctx.link is LinkState.ADAPTER_READY


def test_raw_export_is_complete_even_beyond_widget_limit(qtbot, store, ports):
    w = make(qtbot, store)
    w.diagnostics.redact_cb.setChecked(False)
    w.ctx._on_log("stdout", "pierwsza linia\n")
    assert "pierwsza linia" in w.diagnostics.raw_text()


def test_serial_number_never_logged_and_redacted_after_unplug(qtbot, store, monkeypatch):
    p = PortInfo(
        "/dev/ttyUSB0", "USB Serial", 0x1A86, 0x7523, serial_number="SN12345678", is_ch340=True
    )
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [p])
    monkeypatch.setattr(mw_mod, "enumerate_ports", lambda **_: [p])
    w = make(qtbot, store)
    assert all("SN12345678" not in e.text for e in w.ctx.entries)  # nie trafia do dziennika
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [])
    w.connection.refresh_ports()  # adapter odłączony
    w.ctx.add_info("stcgal: usb-1a86_x serial SN12345678 gone")
    w.diagnostics.redact_cb.setChecked(True)
    assert "SN12345678" not in w.diagnostics.text()  # redakcja działa także po odłączeniu
