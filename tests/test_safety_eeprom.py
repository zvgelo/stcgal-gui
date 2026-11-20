"""Regresja: brak niejawnych zmian EEPROM/IAP, option bytes i konfiguracji MCU (Linux i Windows).

Fakty o stcgal 1.10 (docs/SAFETY.md): kasowanie „always seems to erase everything”, wariant 0x01
kasuje też EEPROM, a program_options ZAWSZE zapisuje opcje i trim. Backend nie gwarantuje ochrony,
więc zapis jest blokowany do czasu świadomego potwierdzenia ryzyka.
"""

import functools
import itertools
import re
import threading
from pathlib import Path

import pytest
from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QMessageBox, QSpinBox

import stcgal_gui.gui.main_window as mw_mod
import stcgal_gui.gui.tabs.connection as conn_mod
from stcgal_gui.__main__ import build_window
from stcgal_gui.backends.base import Callbacks, SafetyError, WriteConfirmation
from stcgal_gui.backends.mock import MockBackend
from stcgal_gui.backends.stcgal import (
    StcgalBackend,
    build_identify_command,
    build_program_command,
)
from stcgal_gui.core import safety
from stcgal_gui.models.data import (
    PROTOCOLS,
    ConnectionParams,
    McuInfo,
    PortInfo,
    ProgramParams,
    WriteScope,
)
from tests.conftest import risk_acknowledged

ROOT = Path(__file__).resolve().parents[1]
CONN = ConnectionParams(port="/dev/ttyUSB0", protocol="stc8d")
CH340 = PortInfo("/dev/ttyUSB0", "USB Serial", 0x1A86, 0x7523, is_ch340=True)
NOOP = Callbacks()
WC = functools.partial(
    WriteConfirmation, expected_model="STC8H8K64U"
)  # model zidentyfikowanego MCU jest wymagany


def conn_for(backend_conn=CONN):
    return backend_conn


# ------------------------------------------------------------------ identyfikacja


@pytest.mark.parametrize("protocol", PROTOCOLS)
@pytest.mark.parametrize("flags", list(itertools.product([False, True], repeat=2)))
def test_identify_command_never_modifies_anything(protocol, flags):
    debug, autoreset = flags
    argv = build_identify_command(
        "stcgal",
        ConnectionParams(port="COM10", protocol=protocol, debug=debug, autoreset=autoreset),
    )
    forbidden = {"-e", "--erase", "-o", "--option", "-t", "--trim", "-r", "--resetcmd"}
    assert not forbidden & set(argv)
    assert not any(a.lower().endswith((".bin", ".hex", ".ihx", ".ihex")) for a in argv)
    assert len(argv) <= 13  # exe + -p -P -b -l (+ -a -A dtr) (+ -D): tylko połączenie


def test_identify_via_backend_never_programs(fake_backend, argv_log):
    fake_backend.identify(CONN, NOOP, threading.Event())
    import json

    argv = json.loads(argv_log.read_text().splitlines()[-1])
    assert not {"-e", "--erase", "-o", "-t"} & set(argv)


# ------------------------------------------------------------------ zadeklarowane możliwości


def test_stcgal_does_not_claim_to_preserve_eeprom_or_options():
    caps = StcgalBackend("x").capabilities
    assert caps.preserves_eeprom is False and caps.preserves_options is False
    assert caps.verify is False and caps.read_firmware is False


# ------------------------------------------------------------------ egzekwowanie w backendzie


def test_write_without_acknowledgement_is_blocked_and_never_starts_process(
    fake_backend, argv_log, firmware_bin
):
    conf = WC("/dev/ttyUSB0", firmware_bin, mcu_code_bytes=65024)  # bez zaakceptowanych ryzyk
    with pytest.raises(SafetyError) as ex:
        fake_backend.program(CONN, ProgramParams(firmware_bin), conf, NOOP, threading.Event())
    assert "EEPROM" in str(ex.value) and "konfiguracji" in str(ex.value)
    assert not argv_log.exists()  # stcgal nie został uruchomiony


def test_write_without_identified_mcu_is_hard_blocked(fake_backend, argv_log, firmware_bin):
    conf = risk_acknowledged("/dev/ttyUSB0", firmware_bin, mcu_code_bytes=None)
    with pytest.raises(SafetyError, match="nie został zidentyfikowany"):
        fake_backend.program(CONN, ProgramParams(firmware_bin), conf, NOOP, threading.Event())
    assert not argv_log.exists()


@pytest.mark.parametrize(
    "option",
    [
        "eeprom_erase_enabled=true", "program_eeprom_split=1024", "reset_pin_enabled=false",
        "clock_gain=true", "watchdog_por_enabled=true", "watchdog_prescale=256",
        "low_voltage_reset=true", "uart1_remap=true", "bsl_pindetect_enabled=false", "por_reset_delay=long",
    ],
)  # fmt: skip
def test_any_option_change_is_hard_blocked_even_with_all_risks_acknowledged(
    fake_backend, argv_log, firmware_bin, option
):
    conf = risk_acknowledged("/dev/ttyUSB0", firmware_bin)
    with pytest.raises(SafetyError, match="zabroniona"):
        fake_backend.program(
            CONN, ProgramParams(firmware_bin, options=[option]), conf, NOOP, threading.Event()
        )
    assert not argv_log.exists()


def test_trim_change_is_hard_blocked(fake_backend, firmware_bin):
    with pytest.raises(SafetyError, match="zabroniona"):
        fake_backend.program(
            CONN, ProgramParams(firmware_bin, trim_khz=24000),
            risk_acknowledged("/dev/ttyUSB0", firmware_bin), NOOP, threading.Event(),
        )  # fmt: skip


def test_flash_scope_never_accepts_eeprom_image(fake_backend, argv_log, firmware_bin, tmp_path):
    ee = tmp_path / "ee.bin"
    ee.write_bytes(b"\x01" * 16)
    with pytest.raises(SafetyError, match="osobnej operacji"):
        fake_backend.program(
            CONN, ProgramParams(firmware_bin, eeprom_image=ee),
            risk_acknowledged("/dev/ttyUSB0", firmware_bin, WriteScope.FLASH_ONLY), NOOP, threading.Event(),
        )  # fmt: skip
    assert not argv_log.exists()
    with pytest.raises(ValueError):  # także konstruktor polecenia odmawia
        build_program_command("stcgal", CONN, ProgramParams(firmware_bin, eeprom_image=ee))


def test_eeprom_scope_requires_image_and_explicit_overwrite_ack(
    fake_backend, firmware_bin, tmp_path
):
    ee = tmp_path / "ee.bin"
    ee.write_bytes(b"\x01" * 16)
    with pytest.raises(SafetyError, match="wymaga pliku"):  # brak obrazu EEPROM
        fake_backend.program(
            CONN, ProgramParams(firmware_bin),
            risk_acknowledged("/dev/ttyUSB0", firmware_bin, WriteScope.FLASH_AND_EEPROM), NOOP, threading.Event(),
        )  # fmt: skip
    partial = WC(
        "/dev/ttyUSB0", firmware_bin, scope=WriteScope.FLASH_AND_EEPROM,
        acknowledged=frozenset({"erase_scope_unverified", "option_rewrite"}), mcu_code_bytes=65024,
    )  # fmt: skip
    with pytest.raises(SafetyError, match="nadpisany"):  # brak potwierdzenia nadpisania EEPROM
        fake_backend.program(
            CONN, ProgramParams(firmware_bin, eeprom_image=ee), partial, NOOP, threading.Event()
        )


def test_flash_command_contains_only_flash_image(fake_backend, argv_log, firmware_bin):
    res = fake_backend.program(
        CONN, ProgramParams(firmware_bin), risk_acknowledged("/dev/ttyUSB0", firmware_bin),
        NOOP, threading.Event(),
    )  # fmt: skip
    assert res.ok
    import json

    argv = json.loads(argv_log.read_text().splitlines()[-1])
    assert argv[-1] == str(firmware_bin.resolve())
    assert not {"-e", "--erase", "-o", "-t"} & set(argv)
    assert sum(1 for a in argv if re.search(r"\.(bin|hex)$", a, re.I)) == 1  # dokładnie jeden obraz


# ------------------------------------------------------------------ rozmiar obrazu vs obszar kodu


def test_image_exactly_code_size_ok_one_byte_more_is_hard_blocked(tmp_path):
    caps = MockBackend(guarantees=True).capabilities
    exact, over = tmp_path / "a.bin", tmp_path / "b.bin"
    exact.write_bytes(b"\x01" * 65024)
    over.write_bytes(b"\x01" * 65025)
    assert safety.assess(caps, ProgramParams(exact), WriteScope.FLASH_ONLY, 65024) == []
    ids = {
        r.id
        for r in safety.assess(caps, ProgramParams(over), WriteScope.FLASH_ONLY, 65024)
        if r.hard
    }
    assert ids == {"image_exceeds_flash"}


def test_effective_code_size_respects_split_read_from_chip():
    mcu = McuInfo(code_flash_kb=63.5, eeprom_kb=0.5, options={"program_eeprom_split": "32768"})
    assert safety.effective_code_bytes(mcu) == 32768  # ostrożniej: mniejsza z wartości
    assert safety.effective_code_bytes(McuInfo(code_flash_kb=63.5)) == 65024
    assert safety.effective_code_bytes(None) is None


# ------------------------------------------------------------------ backend symulowany stosuje tę samą politykę


def test_mock_backend_enforces_same_policy(firmware_bin):
    blind = MockBackend(guarantees=False, wait_s=0.01, write_s=0.01)
    with pytest.raises(SafetyError):
        blind.program(
            CONN,
            ProgramParams(firmware_bin),
            WC("/dev/ttyUSB0", firmware_bin, mcu_code_bytes=65024),
            NOOP,
            threading.Event(),
        )
    ok = MockBackend(guarantees=True, wait_s=0.01, write_s=0.01).program(
        CONN, ProgramParams(firmware_bin), WC("/dev/ttyUSB0", firmware_bin, mcu_code_bytes=65024), NOOP, threading.Event(),
    )  # fmt: skip
    assert ok.ok


# ------------------------------------------------------------------ GUI


@pytest.fixture
def ports(monkeypatch):
    monkeypatch.setattr(conn_mod, "enumerate_ports", lambda **_: [CH340])
    monkeypatch.setattr(mw_mod, "enumerate_ports", lambda **_: [CH340])


def make(qtbot, store, backend):
    w = build_window(backend, store)
    qtbot.addWidget(w)
    w.show()
    return w


def accept_all(monkeypatch, titles):
    def exec_(self):
        titles.append(self.windowTitle())
        return 0

    monkeypatch.setattr(QMessageBox, "exec", exec_)
    monkeypatch.setattr(
        QMessageBox,
        "clickedButton",
        lambda self: next(
            b for b in self.buttons() if b.text() not in ("Cancel", "&Cancel", "Anuluj")
        ),
    )


def test_gui_flash_write_never_includes_eeprom_image(
    qtbot, store, ports, firmware_bin, tmp_path, monkeypatch
):
    backend = MockBackend(wait_s=0.01, write_s=0.01)
    w = make(qtbot, store, backend)
    ee = tmp_path / "ee.bin"
    ee.write_bytes(b"\x02" * 32)
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    w.program.fw_edit.setText(str(firmware_bin))
    w.program.ee_edit.setText(str(ee))  # plik EEPROM wskazany, ale zapis Flash go ignoruje
    accept_all(monkeypatch, [])
    w.program.program_btn.click()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    prog = backend.calls[0].prog
    assert prog.eeprom_image is None and prog.options == [] and prog.trim_khz is None


def test_mcu_view_is_strictly_read_only(qtbot, store, ports):
    w = make(qtbot, store, MockBackend())
    w.ctx.set_mcu(MockBackend().mcu, "/dev/ttyUSB0")
    for cls in (QLineEdit, QComboBox, QSpinBox, QCheckBox):
        assert w.mcu.findChildren(cls) == []  # żadnych kontrolek edycji opcji/konfiguracji


# ------------------------------------------------------------------ skrypty budowania/CI nie dotykają sprzętu


def _build_files():
    files = [*ROOT.glob("scripts/*.sh"), *ROOT.glob("scripts/*.ps1"), ROOT / "scripts/pyi_build.py"]
    files += list((ROOT / ".github/workflows").glob("*.yml"))
    return [f for f in files if f.is_file()]


@pytest.mark.parametrize("path", _build_files(), ids=lambda p: p.name)
def test_build_and_ci_scripts_never_touch_hardware(path):
    text = path.read_text(encoding="utf-8")
    assert "--erase" not in text
    assert not re.search(r"(stcgal|backend)[^\n]*\s-p\s", text)  # żaden port szeregowy
    assert not re.search(r"(stcgal|backend)[^\n]*\s-o\s", text)  # żadne opcje
    assert not re.search(r"\.identify\(|\.program\(", text)


# ------------------------------------------------------------------ poprawki z przeglądu bezpieczeństwa


def _hex_rec(rtype, addr, data=b""):
    import struct

    body = struct.pack(">BHB", len(data), addr, rtype) + data
    return ":" + (body + bytes([(-sum(body)) & 0xFF])).hex().upper()


def test_hex_size_matches_stcgal_even_with_overlapping_records(tmp_path):
    """Rozmiar HEX w GUI = rozmiar z prawdziwego stcgal.ihex (splice nakładających się rekordów)."""
    from stcgal.ihex import IHex

    from stcgal_gui.core.firmware import load_firmware

    lines = [_hex_rec(0, 0xFDF0, b"\x11" * 32), _hex_rec(0, 0xFDF0, b"\x22" * 16), ":00000001FF"]
    path = tmp_path / "overlap.hex"
    path.write_text("\n".join(lines) + "\n")
    ref = IHex.read([ln.encode() + b"\n" for ln in lines]).extract_data()
    assert load_firmware(path).size == len(ref) == 0xFDF0 + 32


def test_hex_parser_matches_stcgal_on_random_files(tmp_path):
    import random

    from stcgal.ihex import IHex

    from stcgal_gui.core.firmware import parse_ihex

    rnd = random.Random(7)
    for _ in range(150):
        lines = [
            _hex_rec(
                0,
                rnd.randint(0, 300),
                bytes(rnd.randint(0, 255) for _ in range(rnd.randint(1, 40))),
            )
            for _ in range(rnd.randint(1, 10))
        ] + [":00000001FF"]
        ref = IHex.read([ln.encode() + b"\n" for ln in lines]).extract_data()
        assert parse_ihex("\n".join(lines) + "\n") == ref


def test_command_does_not_resolve_symlinks_stcgal_picks_format_by_name(tmp_path):
    real = tmp_path / "image.bin"
    real.write_bytes(b"\x01" * 100)
    link = tmp_path / "fw.hex"
    link.symlink_to(real)
    argv = build_program_command("stcgal", CONN, ProgramParams(link))
    assert argv[-1].endswith(
        "fw.hex"
    )  # nazwa z rozszerzeniem widoczna dla stcgal = taka sama jak sprawdzona w GUI


def test_write_confirmation_is_immutable_and_type_checked(firmware_bin):
    import dataclasses

    conf = WC("/dev/ttyUSB0", firmware_bin, mcu_code_bytes=65024)
    with pytest.raises(dataclasses.FrozenInstanceError):
        conf.mcu_code_bytes = 10**9  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        conf.acknowledged = frozenset({"x"})  # type: ignore[misc]
    with pytest.raises(TypeError):
        WC("p", firmware_bin, scope="flash_only")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        WC("p", firmware_bin, acknowledged={"a"})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        WC("p", firmware_bin, mcu_code_bytes=-1)


def test_backend_aborts_before_erase_when_connected_chip_differs(
    fake_backend, argv_log, firmware_bin, monkeypatch
):
    """Wymiana układu bez ponownego wykrycia: stcgal zgłasza inny model → przerwanie PRZED kasowaniem."""
    monkeypatch.setenv("FAKE_STCGAL_MODEL_PAUSE", "1.5")
    conf = WC(
        "/dev/ttyUSB0", firmware_bin,
        acknowledged=frozenset({"erase_scope_unverified", "option_rewrite"}),
        mcu_code_bytes=65024, expected_model="STC8H8K32U",
    )  # fmt: skip
    res = fake_backend.program(CONN, ProgramParams(firmware_bin), conf, NOOP, threading.Event())
    assert res.state.value == "cancelled"
    assert "różni się od zidentyfikowanego" in res.message and "STC8H8K64U" in res.message
    assert "Erasing flash" not in res.stdout


def test_backend_proceeds_when_model_matches(fake_backend, firmware_bin):
    conf = WC(
        "/dev/ttyUSB0", firmware_bin,
        acknowledged=frozenset({"erase_scope_unverified", "option_rewrite"}),
        mcu_code_bytes=65024, expected_model="STC8H8K64U",
    )  # fmt: skip
    assert fake_backend.program(CONN, ProgramParams(firmware_bin), conf, NOOP, threading.Event()).ok


def test_mock_only_via_explicit_flag_and_banner(qtbot, store, ports):
    import stcgal_gui.__main__ as entry

    src = Path(entry.__file__).read_text(encoding="utf-8")
    assert "STCGAL_GUI_MOCK" not in src  # żadnej zmiennej środowiskowej włączającej symulację
    w = make(qtbot, store, MockBackend(guarantees=False))
    assert "SYMULACJA" in w.windowTitle() and "SYMULACJA" in w.header.summary.text()


def test_gui_aborts_when_port_changes_during_confirmation(
    qtbot, store, ports, firmware_bin, monkeypatch
):
    backend = MockBackend(wait_s=0.01, write_s=0.01)
    w = make(qtbot, store, backend)
    p = w.program
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    p.fw_edit.setText(str(firmware_bin))

    def exec_(self):  # w trakcie dialogu adapter „znika”
        w.ctx.invalidate_mcu("test: odłączono adapter")

    monkeypatch.setattr(QMessageBox, "exec", exec_)
    monkeypatch.setattr(
        QMessageBox,
        "clickedButton",
        lambda self: next(b for b in self.buttons() if "Kasuj" in b.text()),
    )
    p.program_btn.click()
    assert backend.calls == []  # zapis nie wystartował mimo zaakceptowanego dialogu


def test_stale_identification_is_not_trusted(qtbot, store, ports, firmware_bin):
    backend = MockBackend()
    w = make(qtbot, store, backend)
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    w.program.fw_edit.setText(str(firmware_bin))
    assert w.program.program_btn.isEnabled()
    w.ctx.mcu_time -= 10_000  # identyfikacja sprzed godzin
    w.program.revalidate()
    assert (
        not w.program.program_btn.isEnabled()
        and "nie został zidentyfikowany" in w.program.risk_label.text()
    )


def test_detect_clears_previous_identification(qtbot, store, ports):
    w = make(qtbot, store, MockBackend(scenario="no_mcu"))
    w.ctx.set_mcu(MockBackend().mcu, "/dev/ttyUSB0")
    w.connection.detect()
    assert w.ctx.mcu is None  # nieudane ponowne wykrywanie nie zostawia starego MCU
    w.ctx.controller.cancel()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)


def test_gui_snapshot_is_what_backend_receives(qtbot, store, ports, firmware_bin, monkeypatch):
    backend = MockBackend(wait_s=0.01, write_s=0.01)
    w = make(qtbot, store, backend)
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    w.program.fw_edit.setText(str(firmware_bin))
    accept_all(monkeypatch, [])
    w.program.program_btn.click()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    used = backend.calls[0].prog.code_image
    assert used != firmware_bin and used.suffix == ".bin"  # kopia w prywatnym katalogu
    assert not used.exists()  # katalog migawki sprzątany po operacji


# ------------------------------------------------------------------ GUI: tryb podstawowy i ekspert


def test_basic_mode_is_simple_and_hides_expert_controls(qtbot, store, ports):
    w = make(qtbot, store, MockBackend())
    p = w.program
    assert not p.expert_cb.isChecked() and not p.expert_box.isVisibleTo(p)
    assert p.option_list() == [] and p._trim() is None and p._offset() == 0
    w.ctx.set_mcu(MockBackend().mcu, "/dev/ttyUSB0")
    assert not p.erase_btn.isEnabled()  # kasowanie tylko w trybie eksperta


def test_write_without_guarantees_needs_risk_dialog_not_a_checkbox(
    qtbot, store, ports, firmware_bin, monkeypatch
):
    backend = MockBackend(guarantees=False, wait_s=0.05, write_s=0.05)  # jak stcgal
    w = make(qtbot, store, backend)
    p = w.program
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    p.fw_edit.setText(str(firmware_bin))
    assert p.program_btn.isEnabled()  # prosty przepływ: jeden przycisk
    assert "nie gwarantuje zachowania EEPROM" in p.risk_info.info_text
    titles = []
    accept_all(monkeypatch, titles)
    p.program_btn.click()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    assert titles == ["Potwierdź zapis Flash", "Potwierdź ryzyko dla EEPROM i konfiguracji"]
    assert [c.kind for c in backend.calls] == ["program"]


def test_declining_risk_dialog_cancels_write(qtbot, store, ports, firmware_bin, monkeypatch):
    backend = MockBackend(guarantees=False)
    w = make(qtbot, store, backend)
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    w.program.fw_edit.setText(str(firmware_bin))
    calls = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: calls.append(self.windowTitle()))

    def clicked(self):  # pierwszy dialog akceptowany, drugi (ryzyko) odrzucony
        return next(b for b in self.buttons() if "Kasuj" in b.text()) if len(calls) == 1 else None

    monkeypatch.setattr(QMessageBox, "clickedButton", clicked)
    w.program.program_btn.click()
    assert len(calls) == 2 and backend.calls == []


def test_expert_options_trim_and_offset_reach_backend_after_extra_risk_dialog(
    qtbot, store, ports, firmware_bin, monkeypatch
):
    backend = MockBackend(guarantees=False, wait_s=0.01, write_s=0.01)
    w = make(qtbot, store, backend)
    p = w.program
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    p.fw_edit.setText(str(firmware_bin))
    p.expert_cb.setChecked(True)
    assert p.expert_box.isVisibleTo(p) and p.options_table.rowCount() == len(backend.mcu.options)
    row = next(
        r
        for r in range(p.options_table.rowCount())
        if "reset_pin_enabled" in p.options_table.item(r, 0).text()
    )
    p.options_table.item(row, 2).setText("True")
    p.trim_spin.setValue(24000)
    p.offset_edit.setText("0x100")
    assert p.option_list() == ["reset_pin_enabled=True"]
    assert (
        "Zmiana opcji MCU" in p.risk_info.info_text
        and "Zmiana częstotliwości" in p.risk_info.info_text
    )
    titles = []
    accept_all(monkeypatch, titles)
    p.program_btn.click()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    prog = backend.calls[0].prog
    assert prog.options == ["reset_pin_enabled=True"] and prog.trim_khz == 24000
    assert titles[-1] == "Potwierdź ryzyko dla EEPROM i konfiguracji"


def test_offset_pads_image_with_fill_byte(qtbot, store, ports, firmware_bin, monkeypatch):
    backend = MockBackend(wait_s=0.01, write_s=0.01)
    w = make(qtbot, store, backend)
    p = w.program
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    p.fw_edit.setText(str(firmware_bin))
    p.expert_cb.setChecked(True)
    p.offset_edit.setText("16")
    p.fill_combo.setCurrentIndex(1)  # 0x00
    seen = {}
    orig = backend.program

    def spy(conn, prog, conf, cb, cancel):
        seen["data"] = prog.code_image.read_bytes()
        return orig(conn, prog, conf, cb, cancel)

    monkeypatch.setattr(backend, "program", spy)
    accept_all(monkeypatch, [])
    p.program_btn.click()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    assert seen["data"][:16] == bytes(16) and seen["data"][16:] == firmware_bin.read_bytes()


def test_erase_only_available_in_expert_with_two_confirmations(qtbot, store, ports, monkeypatch):
    backend = MockBackend(guarantees=False, wait_s=0.01, write_s=0.01)
    w = make(qtbot, store, backend)
    p = w.program
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    assert not p.erase_btn.isEnabled()
    p.expert_cb.setChecked(True)
    assert p.erase_btn.isEnabled()
    titles = []
    accept_all(monkeypatch, titles)
    p.erase_btn.click()
    qtbot.waitUntil(lambda: not w.ctx.controller.busy, timeout=5000)
    assert titles == ["Potwierdź kasowanie Flash", "Potwierdź ryzyko dla EEPROM i konfiguracji"]
    assert [c.kind for c in backend.calls] == ["erase"] and w.ctx.mcu is None


def test_backend_refuses_erase_and_options_without_expert(fake_backend, firmware_bin):
    conf = WC("/dev/ttyUSB0", Path("-"), scope=WriteScope.ERASE_ONLY, mcu_code_bytes=65024,
              acknowledged=frozenset({"erase_destructive", "erase_scope_unverified"}))  # fmt: skip
    with pytest.raises(SafetyError, match="trybu eksperta"):
        fake_backend.erase(CONN, conf, NOOP, threading.Event())
    with pytest.raises(SafetyError, match="zabroniona"):
        fake_backend.program(
            CONN, ProgramParams(firmware_bin, options=["clock_gain=true"]),
            risk_acknowledged("/dev/ttyUSB0", firmware_bin), NOOP, threading.Event(),
        )  # fmt: skip


def test_expert_erase_command_is_only_connection_plus_e(fake_backend, argv_log):
    conf = WC(
        "/dev/ttyUSB0", Path("-"), scope=WriteScope.ERASE_ONLY, mcu_code_bytes=65024, expert=True,
        acknowledged=frozenset({"erase_destructive", "erase_scope_unverified"}),
    )  # fmt: skip
    res = fake_backend.erase(CONN, conf, NOOP, threading.Event())
    assert res.kind.value == "erase"
    import json

    argv = json.loads(argv_log.read_text().splitlines()[-1])
    assert "-e" in argv and "-o" not in argv and "-t" not in argv
    assert not any(a.lower().endswith((".bin", ".hex")) for a in argv)


# ------------------------------------------------------------------ poprawki z review trybu eksperta


def test_requested_split_limits_code_area_in_expert_mode(tmp_path):
    caps = MockBackend(guarantees=True).capabilities
    big = tmp_path / "big.bin"
    big.write_bytes(b"\x01" * 40000)
    prog = ProgramParams(big, options=["program_eeprom_split=1024"])
    ids = {r.id for r in safety.assess(caps, prog, WriteScope.FLASH_ONLY, 65024, expert=True)}
    assert (
        "image_exceeds_flash" in ids and "options_requested" in ids
    )  # split 1024 B: obraz 40 KB nachodzi na EEPROM


def test_erase_scope_is_rejected_by_program_and_model_is_required(
    fake_backend, argv_log, firmware_bin
):
    wrong = risk_acknowledged("/dev/ttyUSB0", firmware_bin, WriteScope.ERASE_ONLY)
    with pytest.raises(SafetyError):
        fake_backend.program(CONN, ProgramParams(firmware_bin), wrong, NOOP, threading.Event())
    no_model = WriteConfirmation(
        "/dev/ttyUSB0", firmware_bin, mcu_code_bytes=65024,
        acknowledged=frozenset({"erase_scope_unverified", "option_rewrite"}),
    )  # fmt: skip
    with pytest.raises(SafetyError, match="znanego modelu"):
        fake_backend.program(CONN, ProgramParams(firmware_bin), no_model, NOOP, threading.Event())
    assert not argv_log.exists()


def test_gui_offset_is_limited_and_erase_needs_expert(
    qtbot, store, ports, firmware_bin, monkeypatch
):
    backend = MockBackend()
    w = make(qtbot, store, backend)
    p = w.program
    w.ctx.set_mcu(backend.mcu, "/dev/ttyUSB0")
    p.fw_edit.setText(str(firmware_bin))
    p.expert_cb.setChecked(True)
    p.offset_edit.setText("0x200000000")
    assert not p.program_btn.isEnabled() and p._offset() is None  # brak alokacji ogromnego obrazu
    p.offset_edit.setText("0x400")
    assert p._offset() == 0x400
    p.expert_cb.setChecked(
        False
    )  # wyłączony ekspert: kasowanie niemożliwe, także przez wywołanie wprost
    monkeypatch.setattr(
        QMessageBox, "exec", lambda self: pytest.fail("dialog nie powinien się pojawić")
    )
    p.start_erase()
    assert backend.calls == []
