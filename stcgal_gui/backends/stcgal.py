"""Backend oparty o zewnętrzny program ``stcgal`` (uruchamiany jako kontrolowany podproces)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QCoreApplication as Q

from stcgal_gui import platform_support as ps
from stcgal_gui.backends import procctl
from stcgal_gui.backends.base import (
    Backend,
    Callbacks,
    Capabilities,
    SafetyError,
    WriteConfirmation,
)
from stcgal_gui.backends.process import ProcessOutcome, run_process
from stcgal_gui.core import diagnosis, safety
from stcgal_gui.core.i18n import fmt
from stcgal_gui.models.data import (
    PROTOCOLS,
    ConnectionParams,
    ErrorKind,
    McuInfo,
    OperationKind,
    OperationResult,
    OperationState,
    ProgramParams,
    Progress,
    WriteScope,
)

OPTION_RE = re.compile(r"^[a-z0-9_]+=[A-Za-z0-9_.\-]+$")
_WAITING_RE = re.compile(r"Waiting for MCU")
_CONNECTED_RE = re.compile(r"Waiting for MCU[^\n]*?:\s*done")
_PROGRESS_RE = re.compile(r"(Writing flash)[^\r\n]*?(\d+)%\|[^|]*\|\s*(\d+)/(\d+)")
_FLASH_ONLY = WriteScope.FLASH_ONLY
_MODEL_RE = re.compile(r"^\s*Name:\s*(\S+)", re.M)
_FORBIDDEN_IN_IDENTIFY = ("-e", "--erase", "-o", "--option", "-t", "--trim")


def _which(name: str) -> str | None:
    """Szuka w PATH bez bieżącego katalogu (na Windows `which` domyślnie przeszukuje CWD)."""
    found = shutil.which(name, path=os.environ.get("PATH", os.defpath))
    return os.path.abspath(found) if found else None


def find_stcgal(configured: str = "") -> str | None:
    """Zwraca ścieżkę backendu: z ustawień → dołączony do aplikacji → PATH → ~/.local/bin (Linux)."""
    if configured:
        p = Path(configured).expanduser()
        return str(p) if p.is_file() else _which(configured)
    bundled = ps.bundled_backend()
    if bundled is not None:
        return str(bundled)
    found = _which("stcgal")
    if found:
        return found
    if not ps.IS_WINDOWS:
        fallback = Path.home() / ".local" / "bin" / "stcgal"
        if fallback.is_file():
            return str(fallback)
    return None


def _common_args(conn: ConnectionParams) -> list[str]:
    if conn.protocol not in PROTOCOLS:
        raise ValueError(fmt(Q.translate("StcgalBackend", "Nieznany protokół: %1"), conn.protocol))
    if not conn.port:
        raise ValueError(Q.translate("StcgalBackend", "Nie wybrano portu"))
    args = [
        "-p", conn.port,
        "-P", conn.protocol,
        "-b", str(conn.baud),
        "-l", str(conn.handshake_baud),
    ]  # fmt: skip
    if conn.autoreset:
        args += ["-a", "-A", conn.resetpin]
    if conn.debug:
        args.append("-D")
    return args


def _head(exe: str | Sequence[str]) -> list[str]:
    return [exe] if isinstance(exe, str) else list(exe)


def build_identify_command(exe: str | Sequence[str], conn: ConnectionParams) -> list[str]:
    """Polecenie identyfikacji: wyłącznie połączenie, bez pliku, ``-e``, ``-o`` ani ``-t``.

    Bez obrazu kodu i bez ``--erase`` stcgal tylko łączy się, drukuje informacje o MCU
    i rozłącza się (patrz docs/ARCHITECTURE.md).
    """
    head = _head(exe)
    argv = [*head, *_common_args(conn)]
    assert not any(a in _FORBIDDEN_IN_IDENTIFY for a in argv[len(head) :]), (
        "identyfikacja musi być niedestrukcyjna"
    )
    return argv


def build_program_command(
    exe: str | Sequence[str],
    conn: ConnectionParams,
    prog: ProgramParams,
    scope: WriteScope = _FLASH_ONLY,
    expert: bool = False,
) -> list[str]:
    """Polecenie zapisu. Ścieżki plików są bezwzględne (unika interpretacji jako opcji)."""
    argv = [*_head(exe), *_common_args(conn)]
    if scope is _FLASH_ONLY and prog.eeprom_image:
        raise ValueError(
            Q.translate("StcgalBackend", "Zapis tylko-Flash nie może zawierać obrazu EEPROM")
        )
    if (prog.options or prog.trim_khz is not None) and not expert:
        raise ValueError(
            Q.translate("StcgalBackend", "Opcje -o i -t są dostępne wyłącznie w trybie eksperta")
        )
    if prog.trim_khz is not None:
        argv += ["-t", f"{prog.trim_khz:g}"]
    for opt in prog.options:
        if not OPTION_RE.match(opt):
            raise ValueError(
                fmt(
                    Q.translate(
                        "StcgalBackend", "Niepoprawna opcja: %1 (oczekiwano klucz=wartość)"
                    ),
                    repr(opt),
                )
            )
        argv += ["-o", opt]
    argv.append(os.path.abspath(prog.code_image))  # bez resolve(): stcgal wybiera HEX/BIN po nazwie
    if prog.eeprom_image is not None:
        argv.append(os.path.abspath(prog.eeprom_image))
    return argv


def build_erase_command(exe: str | Sequence[str], conn: ConnectionParams) -> list[str]:
    """Polecenie samego kasowania Flash (``stcgal -e``); bez pliku i bez opcji."""
    return [*_head(exe), *_common_args(conn), "-e"]


# --------------------------------------------------------------------------- parsowanie


def parse_mcu_info(text: str) -> McuInfo:
    """Parsuje wyjście stcgal. Wypełnia tylko pola, które backend rzeczywiście wypisał."""
    info = McuInfo()
    section: str | None = None
    for raw in text.replace("\r", "\n").splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if m := re.match(r"Protocol detected:\s*(\S+)", line):
            info.protocol = m.group(1)
            continue
        if line.startswith("Target model:"):
            section = "model"
            continue
        if line.startswith("Target options:"):
            section = "options"
            continue
        if section and line.startswith("  "):
            body = line.strip()
            if section == "model":
                if m := re.match(r"Name:\s*(.+)", body):
                    info.model = m.group(1).strip()
                elif m := re.match(r"Magic:\s*([0-9A-Fa-f]+)", body):
                    info.magic = m.group(1).upper()
                elif m := re.match(r"Code flash:\s*([\d.]+)\s*KB", body):
                    info.code_flash_kb = float(m.group(1))
                elif m := re.match(r"EEPROM flash:\s*([\d.]+)\s*KB", body):
                    info.eeprom_kb = float(m.group(1))
            elif section == "options" and "=" in body:
                k, v = body.split("=", 1)
                info.options[k.strip()] = v.strip()
            continue
        section = None
        if m := re.match(r"Target frequency:\s*([\d.]+)\s*MHz", line):
            info.frequency_mhz = float(m.group(1))
        elif m := re.match(r"Target BSL version:\s*(\S+)", line):
            info.bsl_version = m.group(1)
        elif m := re.match(r"Target wakeup frequency:\s*([\d.]+)\s*KHz", line, re.I):
            info.wakeup_khz = float(m.group(1))
        elif m := re.match(r"Target ref\. voltage:\s*(\d+)\s*mV", line):
            info.ref_voltage_mv = int(m.group(1))
        elif m := re.match(r"Target mfg\. date:\s*(\S+)", line):
            info.mfg_date = m.group(1)
        elif m := re.match(r"Target ([^:]+):\s*(.+)", line):
            info.extra[m.group(1).strip()] = m.group(2).strip()
    return info


def parse_progress(text: str) -> Progress | None:
    """Ostatni rzeczywisty postęp z paska tqdm stcgal (stderr), jeśli występuje."""
    last: Progress | None = None
    for m in _PROGRESS_RE.finditer(text.replace("\r", "\n")):
        last = Progress(int(m.group(3)), int(m.group(4)), m.group(1))
    return last


def classify_error(text: str, windows: bool | None = None) -> tuple[ErrorKind, str]:
    """Zamienia komunikat błędu stcgal/pyserial na kategorię i czytelną wskazówkę (PL).

    Rozpoznaje komunikaty Linuksa (Errno 13/16/2) i Windows (``PermissionError(13, 'Access is
    denied.')``, ``FileNotFoundError(2, ...)``, ``OSError(22, ...)`` przy utracie urządzenia).
    """
    low = text.lower()
    kind = _match_kind(low, windows)
    msg = diagnosis.user_message(kind, windows)
    if msg:
        return kind, msg
    fixed = {
        ErrorKind.HANDSHAKE: Q.translate(
            "StcgalBackend",
            "stcgal nie rozpoznał protokołu dla tego układu. Wybierz protokół ręcznie.",
        ),
        ErrorKind.PROTOCOL: Q.translate(
            "StcgalBackend",
            "Błąd protokołu ISP. Sprawdź zasilanie, przewody TX/RX, poziomy logiczne "
            "i spróbuj niższej prędkości transferu.",
        ),
        ErrorKind.OPTION: Q.translate("StcgalBackend", "Niepoprawna opcja konfiguracyjna."),
    }
    if kind in fixed:
        return kind, fixed[kind]
    if "serial port error" in low or "i/o error" in low:
        return ErrorKind.UNKNOWN, Q.translate("StcgalBackend", "Błąd portu szeregowego.")
    return ErrorKind.UNKNOWN, Q.translate("StcgalBackend", "Operacja zakończona błędem.")


def _match_kind(low: str, windows: bool | None = None) -> ErrorKind:
    win = ps.IS_WINDOWS if windows is None else windows
    if win and re.search(r"oserror\(22\b", low):
        return (
            ErrorKind.DEVICE_LOST
        )  # Windows: EINVAL z WriteFile/ClearCommError = utrata urządzenia
    if (
        "device attached to the system is not functioning" in low
        or "clearcommerror failed" in low
        or "device disconnected" in low
        or re.search(r"\[?errno\s*5\b", low)
        or "input/output error" in low
        or "device reports readiness to read but returned no data" in low
    ):
        return ErrorKind.DEVICE_LOST
    if "access is denied" in low or "winerror 5" in low:
        return ErrorKind.PORT_BUSY  # Windows: port otwarty przez inny proces
    if "permission denied" in low or re.search(r"errno\s*13\b", low):
        return ErrorKind.PERMISSION
    if "resource busy" in low or re.search(r"errno\s*16\b", low) or "exclusively lock" in low:
        return ErrorKind.PORT_BUSY
    if (
        "no such file or directory" in low
        or re.search(r"errno\s*2\b", low)
        or "could not open port" in low
        or "cannot find the file specified" in low
        or "winerror 2" in low
    ):
        return ErrorKind.PORT_MISSING
    if "cannot detect protocol" in low:
        return ErrorKind.HANDSHAKE
    if "protocol error" in low or "framing" in low or "incorrect magic" in low:
        return ErrorKind.PROTOCOL
    if "option error" in low or ("unknown" in low and "option" in low):
        return ErrorKind.OPTION
    return ErrorKind.UNKNOWN


class StcgalBackend(Backend):
    """Backend ``stcgal`` - niezależny podproces, brak powiązania z wewnętrznymi API."""

    def __init__(self, executable: str | None = None, command_prefix: Sequence[str] = ()) -> None:
        """``command_prefix`` zastępuje plik wykonywalny, np. ``[python, '-m', 'stcgal_gui.backend_entry']``
        (uruchomienie z kodu źródłowego bez zainstalowanego stcgal; używane też w testach)."""
        self.name = "stcgal"
        self._configured = executable or ""
        self._prefix = list(command_prefix)
        self._version_cache: tuple[str, str | None] | None = None
        self._lock = threading.Lock()  # jedna operacja na raz (jeden port)

    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(
            identify=True,
            program_flash=True,
            program_eeprom=True,
            verify=False,
            read_firmware=False,
            real_progress=True,
            read_options=True,
            preserves_eeprom=False,  # kasowanie 0x03: „always seems to erase everything”
            preserves_options=False,  # program_options zawsze zapisuje opcje + trim
            erase_only=True,
            notes=(
                Q.translate(
                    "StcgalBackend",
                    "stcgal nie wykonuje odczytu zawartości flash ani weryfikacji po zapisie.",
                ),
                Q.translate(
                    "StcgalBackend",
                    "Zapis zawsze zapisuje też bajty opcji (bieżące wartości z układu + zmiany -o).",
                ),
            ),
        )

    def executable(self) -> str | None:
        if self._prefix:
            return self._prefix[0]
        return find_stcgal(self._configured)

    def _command_head(self) -> list[str] | None:
        if self._prefix:
            return list(self._prefix)
        exe = self.executable()
        return [exe] if exe else None

    def version(self) -> str | None:
        head = self._command_head()
        if not head:
            return None
        exe = " ".join(head)
        if self._version_cache is not None and self._version_cache[0] == exe:
            return self._version_cache[1]
        kw = procctl.popen_kwargs()
        kw["stdin"] = subprocess.DEVNULL
        try:
            out = subprocess.run(  # noqa: S603 - brak powłoki, stałe argumenty
                [*head, "-V"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
                env={
                    **procctl.sanitize_env(dict(os.environ)),
                    **procctl.extra_env(cancel_via_stdin=False),
                },
                **kw,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        ver = (out.stdout or out.stderr).strip() or None
        self._version_cache = (exe, ver)
        return ver

    # ------------------------------------------------------------------ operacje

    def identify(
        self, conn: ConnectionParams, cb: Callbacks, cancel: threading.Event
    ) -> OperationResult:
        head = self._command_head()
        if not head:
            return _missing(OperationKind.IDENTIFY)
        argv = build_identify_command(head, conn)
        return self._execute(OperationKind.IDENTIFY, argv, conn, cb, cancel)

    def program(
        self,
        conn: ConnectionParams,
        prog: ProgramParams,
        confirmation: WriteConfirmation | None,
        cb: Callbacks,
        cancel: threading.Event,
    ) -> OperationResult:
        if confirmation is None or not confirmation.matches(conn, prog):
            raise SafetyError(
                Q.translate(
                    "StcgalBackend",
                    "Zapis wymaga jawnego potwierdzenia użytkownika dla tego portu i pliku.",
                )
            )
        # ochrona EEPROM/IAP i konfiguracji - niezależnie od GUI (twarde i niepotwierdzone ryzyka)
        if confirmation.scope is WriteScope.ERASE_ONLY:
            raise SafetyError(
                Q.translate("StcgalBackend", "Zakres kasowania nie dotyczy zapisu (użyj erase).")
            )
        safety.enforce(self.capabilities, prog, confirmation)
        head = self._command_head()
        if not head:
            return _missing(OperationKind.PROGRAM)
        argv = build_program_command(head, conn, prog, confirmation.scope, confirmation.expert)
        return self._execute(
            OperationKind.PROGRAM,
            argv,
            conn,
            cb,
            cancel,
            expected_model=confirmation.expected_model,
        )

    def erase(
        self,
        conn: ConnectionParams,
        confirmation: WriteConfirmation | None,
        cb: Callbacks,
        cancel: threading.Event,
    ) -> OperationResult:
        if (
            confirmation is None
            or confirmation.scope is not WriteScope.ERASE_ONLY
            or confirmation.port != conn.port
        ):
            raise SafetyError(
                Q.translate(
                    "StcgalBackend",
                    "Kasowanie wymaga jawnego potwierdzenia (zakres: kasowanie) dla tego portu.",
                )
            )
        safety.enforce_erase(self.capabilities, confirmation)
        head = self._command_head()
        if not head:
            return _missing(OperationKind.ERASE)
        argv = build_erase_command(head, conn)
        return self._execute(
            OperationKind.ERASE, argv, conn, cb, cancel, expected_model=confirmation.expected_model
        )

    def _execute(
        self,
        kind: OperationKind,
        argv: Sequence[str],
        conn: ConnectionParams,
        cb: Callbacks,
        cancel: threading.Event,
        expected_model: str | None = None,
    ) -> OperationResult:
        if not self._lock.acquire(blocking=False):
            raise RuntimeError(
                Q.translate("StcgalBackend", "Inna operacja jest już w toku na tym backendzie")
            )
        try:
            return self._run(kind, argv, conn, cb, cancel, expected_model)
        finally:
            self._lock.release()

    def _run(
        self,
        kind: OperationKind,
        argv: Sequence[str],
        conn: ConnectionParams,
        cb: Callbacks,
        cancel: threading.Event,
        expected_model: str | None = None,
    ) -> OperationResult:
        cb.on_log("info", "$ " + " ".join(argv) + "\n")
        buf = {"stdout": "", "stderr": ""}
        state = {"s": OperationState.RUNNING}

        def set_state(s: OperationState) -> None:
            if state["s"] is not s:
                state["s"] = s
                cb.on_state(s)

        cb.on_state(OperationState.RUNNING)

        def connected() -> bool:
            return bool(_CONNECTED_RE.search(buf["stdout"])) or (
                "Waiting for MCU" not in buf["stdout"] and "Target model" in buf["stdout"]
            )

        mismatch: list[str] = []

        def on_chunk(stream: str, text: str) -> None:
            buf[stream] += text
            cb.on_log(stream, text)
            if expected_model and not mismatch and stream == "stdout":
                m = _MODEL_RE.search(buf["stdout"])
                if m and m.group(1) != expected_model and "Erasing flash" not in buf["stdout"]:
                    mismatch.append(
                        m.group(1)
                    )  # inny układ niż zidentyfikowany - przerwij PRZED kasowaniem
                    cancel.set()
            if stream == "stdout":
                if connected():
                    set_state(OperationState.RUNNING)
                elif _WAITING_RE.search(buf["stdout"]):
                    set_state(OperationState.WAITING_FOR_MCU)
            elif (p := parse_progress(text)) is not None:
                cb.on_progress(p)

        outcome = run_process(
            argv,
            on_chunk=on_chunk,
            cancel=cancel,
            connect_timeout_s=conn.timeout_s,
            is_connected=connected,
            env={"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
        )
        res = _build_result(kind, list(argv), outcome)
        if mismatch:
            res.message = fmt(
                Q.translate(
                    "StcgalBackend",
                    "Zapis przerwany przed kasowaniem: podłączony układ (%1) różni się od "
                    "zidentyfikowanego (%2). Wykryj mikrokontroler ponownie.",
                ),
                mismatch[0],
                expected_model,
            )
        return res


def _incomplete_warning() -> str:
    return Q.translate(
        "StcgalBackend",
        " Przerwano po rozpoczęciu kasowania/zapisu - firmware w układzie może być niekompletny. "
        "Bootloader ISP pozostaje dostępny; zaprogramuj układ ponownie.",
    )


def _missing(kind: OperationKind) -> OperationResult:
    return OperationResult(
        kind=kind,
        state=OperationState.FAILED,
        error_kind=ErrorKind.BACKEND_MISSING,
        message=diagnosis.backend_missing_message(),
    )


def _build_result(kind: OperationKind, argv: list[str], o: ProcessOutcome) -> OperationResult:
    res = OperationResult(
        kind=kind, state=OperationState.FAILED, return_code=o.return_code,
        argv=argv, stdout=o.stdout, stderr=o.stderr,
    )  # fmt: skip
    if o.start_failed is not None:
        res.error_kind = ErrorKind.BACKEND_MISSING
        res.message = fmt(
            Q.translate("StcgalBackend", "Nie można uruchomić stcgal: %1"), o.start_failed
        )
        return res
    res.mcu = parse_mcu_info(o.stdout)
    if o.cancelled:
        res.state = OperationState.CANCELLED
        res.error_kind = ErrorKind.CANCELLED
        res.message = Q.translate("StcgalBackend", "Operacja anulowana przez użytkownika.")
        if kind is not OperationKind.IDENTIFY and "Erasing flash" in o.stdout:
            res.message += (
                Q.translate("StcgalBackend", " Anulowano po rozpoczęciu kasowania/zapisu.")
                + _incomplete_warning()
            )
        return res
    if o.timed_out:
        res.state = OperationState.TIMEOUT
        res.error_kind = ErrorKind.TIMEOUT
        waiting = "Waiting for MCU" in o.stdout and not _CONNECTED_RE.search(o.stdout)
        res.message = (
            Q.translate(
                "StcgalBackend",
                "Przekroczono czas oczekiwania na MCU. Wyłącz i ponownie włącz zasilanie układu "
                "docelowego po rozpoczęciu wykrywania; sprawdź TX/RX, masę i poziomy logiczne.",
            )
            if waiting
            else Q.translate("StcgalBackend", "Przekroczono czas oczekiwania na odpowiedź układu.")
        )
        if kind is not OperationKind.IDENTIFY and "Erasing flash" in o.stdout:
            res.message += _incomplete_warning()
        return res
    if o.return_code == 0:
        res.state = OperationState.FINISHED
        res.error_kind = ErrorKind.NONE
        if kind is OperationKind.PROGRAM:
            res.programmed = "Disconnected!" in o.stdout
            res.verified = False  # stcgal nie weryfikuje zawartości po zapisie
            res.message = Q.translate(
                "StcgalBackend",
                "Zapis zakończony. stcgal nie wykonuje weryfikacji zawartości flash.",
            )
        else:
            res.message = Q.translate("StcgalBackend", "Identyfikacja zakończona.")
            if res.mcu.is_empty:
                res.state = OperationState.FAILED
                res.error_kind = ErrorKind.PROTOCOL
                res.message = Q.translate(
                    "StcgalBackend", "stcgal zakończył pracę bez informacji o układzie."
                )
        return res
    kind_, hint = classify_error(o.stderr + "\n" + o.stdout)
    res.error_kind = kind_
    first = next((ln for ln in (o.stderr or o.stdout).splitlines() if ln.strip()), "")
    res.message = f"{hint}\n({first.strip()})" if first else hint
    return res
