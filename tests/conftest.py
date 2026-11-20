import os
import stat
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402

from stcgal_gui.core.settings import SettingsStore  # noqa: E402


@pytest.fixture(autouse=True)
def _source_language():
    """Testy sprawdzają teksty polskie (źródłowe): żaden test nie zostawia tłumaczenia EN."""
    from PySide6.QtCore import QCoreApplication

    from stcgal_gui.core.i18n import remove_translators

    app = QCoreApplication.instance()
    if app is not None:
        remove_translators(app)
    yield
    app = QCoreApplication.instance()
    if app is not None:
        remove_translators(app)


FAKE = Path(__file__).parent / "fake_stcgal.py"
SAMPLE_OUTPUT = """Waiting for MCU, please cycle power: done
Protocol detected: stc8d
Target model:
  Name: STC8H8K64U
  Magic: F784
  Code flash: 63.5 KB
  EEPROM flash: 0.5 KB
Target frequency: 24.000 MHz
Target BSL version: 7.4.4U
Target wakeup frequency: 32.768 KHz
Target ref. voltage: 1190 mV
Target mfg. date: 2023-05-01
Target options:
  reset_pin_enabled=False
  program_eeprom_split=65024
Disconnected!
"""


@pytest.fixture
def fake_backend(tmp_path: Path):
    """Backend z atrapą stcgal; argv trafia do FAKE_STCGAL_LOG.

    Linux: skrypt wykonywalny (pełna ścieżka „programu”). Windows: ``command_prefix`` =
    ``python fake_stcgal.py`` - bez pośredniego ``cmd.exe``, więc anulowanie/timeout dotyczą
    właściwego procesu.
    """
    from stcgal_gui.backends.stcgal import StcgalBackend

    if sys.platform == "win32":
        return StcgalBackend(command_prefix=[sys.executable, str(FAKE)])
    exe = tmp_path / "fake-stcgal"
    exe.write_text(f'#!/bin/sh\nexec {sys.executable} {FAKE} "$@"\n')
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return StcgalBackend(str(exe))


@pytest.fixture
def argv_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "argv.log"
    monkeypatch.setenv("FAKE_STCGAL_LOG", str(path))
    return path


@pytest.fixture
def store(tmp_path: Path) -> SettingsStore:
    return SettingsStore(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))


@pytest.fixture
def firmware_bin(tmp_path: Path) -> Path:
    p = tmp_path / "fw.bin"
    p.write_bytes(bytes(range(256)) * 4)
    return p


def risk_acknowledged(port: str, code_image: Path, scope=None, mcu_code_bytes: int | None = 65024):
    """Potwierdzenie zapisu z jawnie zaakceptowanymi ryzykami miękkimi (jak po dwóch dialogach GUI)."""
    from stcgal_gui.backends.base import WriteConfirmation
    from stcgal_gui.models.data import WriteScope

    return WriteConfirmation(
        port,
        code_image,
        scope=scope or WriteScope.FLASH_ONLY,
        acknowledged=frozenset({"erase_scope_unverified", "option_rewrite", "eeprom_overwrite"}),
        mcu_code_bytes=mcu_code_bytes,
        expected_model="STC8H8K64U",
    )
