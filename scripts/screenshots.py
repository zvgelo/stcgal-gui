"""Zrzuty ekranu widoków (backend symulowany, wartości MCU jak z potwierdzonego testu sprzętowego).

Użycie: python scripts/screenshots.py OUT_DIR THEME(system|light|dark) WIDTH HEIGHT TAG [LANG(pl|en)]
"""

import dataclasses
import os
import sys

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

import stcgal_gui.gui.main_window as mm
import stcgal_gui.gui.tabs.connection as cm
from stcgal_gui.__main__ import build_window
from stcgal_gui.backends.mock import DEMO_MCU, MockBackend
from stcgal_gui.core.i18n import install_translators
from stcgal_gui.core.settings import SettingsStore
from stcgal_gui.models.data import PortInfo

out, theme, w_, h_, tag = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
os.makedirs(out, exist_ok=True)
app = QApplication(sys.argv)
app.setApplicationName("shot")
install_translators(app, sys.argv[6] if len(sys.argv) > 6 else "pl")
CH = PortInfo("/dev/ttyUSB0", "USB Serial", 0x1A86, 0x7523,
              by_id="/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0", is_ch340=True)  # fmt: skip
cm.enumerate_ports = lambda **_: [CH]
mm.enumerate_ports = lambda **_: [CH]
mcu = dataclasses.replace(
    DEMO_MCU, frequency_mhz=11.05, bsl_version="7.4.12U", wakeup_khz=34.4, ref_voltage_mv=1185,
    mfg_date="2025-09-26",
    options={"reset_pin_enabled": "False", "clock_gain": "False", "watchdog_por_enabled": "False",
             "watchdog_prescale": "256", "low_voltage_reset": "False", "low_voltage_threshold": "2.0",
             "eeprom_erase_enabled": "False", "bsl_pindetect_enabled": "False",
             "por_reset_delay": "long", "uart1_remap": "False", "program_eeprom_split": "65024"},
)  # fmt: skip
be = MockBackend(wait_s=1.0)
be.mcu = mcu
w = build_window(be, SettingsStore(QSettings(f"{out}/s_{tag}.ini", QSettings.Format.IniFormat)))
s = w.ctx.settings
s.theme = theme
w.ctx.update_settings(s)
fw = f"{out}/blink.bin"
with open(fw, "wb") as fh:
    fh.write(bytes(range(256)) * 38)
w.program.fw_edit.setText(fw)
w.resize(w_, h_)
w.show()
steps = [
    (lambda: w.grab().save(f"{out}/{tag}_1_connection.png"), 300),
    (lambda: w.connection.detect(), 500),
    (lambda: w.grab().save(f"{out}/{tag}_2_waiting.png"), 100),
    (lambda: None, 1500),
    (lambda: w.grab().save(f"{out}/{tag}_3_mcu.png"), 300),
    (lambda: w.show_page(w.program), 300),
    (lambda: w.grab().save(f"{out}/{tag}_4_program.png"), 300),
    (lambda: w.program.expert_cb.setChecked(True), 300),
    (lambda: w.grab().save(f"{out}/{tag}_4b_expert.png"), 300),
    (lambda: w.program.expert_cb.setChecked(False), 200),
    (lambda: w.show_page(w.backup), 300),
    (lambda: w.grab().save(f"{out}/{tag}_5_backup.png"), 300),
    (
        lambda: (
            w.ctx.add_entry("WARNING", "code_image overflows (przykład)"),
            w.ctx.add_entry("ERROR", "Serial port error: [Errno 13] Permission denied (przykład)"),
            w.show_page(w.diagnostics),
        ),
        300,
    ),  # fmt: skip
    (lambda: w.grab().save(f"{out}/{tag}_6_diagnostics.png"), 300),
    (lambda: w.show_page(w.settings_tab), 300),
    (lambda: w.grab().save(f"{out}/{tag}_7_settings.png"), 300),
    (lambda: app.quit(), 0),
]
i = [0]


def tick() -> None:
    fn, _ = steps[i[0]]
    i[0] += 1
    fn()
    if i[0] < len(steps):
        QTimer.singleShot(steps[i[0]][1], tick)


QTimer.singleShot(600, tick)
app.exec()
