"""Jedyny system budowania aplikacji (Windows natywnie, Windows pod Wine, Linux do walidacji).

    python scripts/pyi_build.py [--mode onefile|onedir] [--dist-root dist] [--clean] [--skip-verify]

1. backend.spec → build/backend-dist/stcgal-backend/   (stcgal 1.10, program konsolowy, onedir)
2. gui.spec     → onefile: dist/<cel>/STC-Programmer[.exe]   (backend zagnieżdżony jako dane)
                  onedir:  dist/<cel>-onedir/STC-Programmer/
   <cel> = „windows” na Windows (także pod Wine), „linux-native” na Linuksie.
3. Weryfikacja uruchomieniowa spakowanego wyniku (--selftest, --smoke-gui; w onedir także
   bezpośrednio backend) i raport build-report.json (rozmiar, SHA-256, wersje).

Używane identycznie przez scripts/build-windows.sh (Wine) i GitHub Actions.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stcgal_gui import __version__  # noqa: E402

IS_WIN = sys.platform == "win32"
EXE = ".exe" if IS_WIN else ""
TARGET = "windows" if IS_WIN else "linux-native"
SPECS = ROOT / "packaging" / "pyinstaller"


for _s in (sys.stdout, sys.stderr):  # konsola Windows/Wine bywa cp1252
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def log(msg: str) -> None:
    print(f"[pyi_build] {msg}", flush=True)


def run(cmd: list[str], *, env: dict[str, str] | None = None, timeout: int | None = None):
    log("$ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, env=env, timeout=timeout, check=False)  # noqa: S603


def pyinstaller(spec: Path, distpath: Path, workpath: Path, env: dict[str, str]) -> None:
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(distpath),
           "--workpath", str(workpath), str(spec)]  # fmt: skip
    if run(cmd, env=env).returncode != 0:
        raise SystemExit(f"PyInstaller nie powiódł się dla {spec.name}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _kill_tree(proc: subprocess.Popen[str]) -> None:
    """Zabija proces wraz z potomkami (onefile = bootloader + proces-dziecko)."""
    if IS_WIN:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False
        )  # noqa: S603, S607
    else:
        import signal

        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL)
    proc.kill()


def capture(
    cmd: list[str], env: dict[str, str], timeout: int = 180
) -> subprocess.CompletedProcess[str]:
    """Uruchamia polecenie z twardym limitem czasu (po przekroczeniu zabija całe drzewo procesów)."""
    kw: dict[str, object] = {} if IS_WIN else {"start_new_session": True}
    proc = subprocess.Popen(  # noqa: S603
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True,
        env=env, encoding="utf-8", errors="replace", **kw,
    )  # fmt: skip
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            out, err = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            out, err = "", ""
        return subprocess.CompletedProcess(
            cmd, 124, out, err + f"\n[pyi_build] przekroczono limit {timeout} s"
        )
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def verify(mode: str, app: Path, backend_exe: Path | None) -> list[str]:
    """Uruchamia spakowany wynik. Zwraca listę porażek (pusta = OK)."""
    fails: list[str] = []

    def check(cond: bool, msg: str) -> None:
        log(("OK   " if cond else "FAIL ") + msg)
        if not cond:
            fails.append(msg)

    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    check(app.is_file(), f"{app.name} istnieje")
    if not app.is_file():
        return fails
    with tempfile.TemporaryDirectory(prefix="stc-verify-") as tmp:
        tmpd = Path(tmp)
        report = tmpd / "selftest.json"
        r = capture([str(app), "--selftest", "--report", str(report)], env, timeout=300)
        try:
            rep = json.loads(report.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            rep = {"problems": [f"brak raportu (kod {r.returncode}): {r.stderr[-300:]!r}"]}
        check(
            r.returncode == 0 and not rep.get("problems"),
            f"--selftest → {rep.get('problems') or 'OK'}",
        )
        check(rep.get("frozen") is True, "uruchomiono jako spakowany program (frozen)")
        check(
            "stcgal 1.10" in str(rep.get("backend_version", "")),
            f"wersja backendu: {rep.get('backend_version')}",
        )
        bpath = str(rep.get("backend", ""))
        check(
            bool(bpath) and Path(bpath).name == "stcgal-backend" + EXE,
            f"GUI używa wbudowanego backendu: {bpath}",
        )
        r = capture([str(app), "--smoke-gui", str(tmpd / "smoke")], env, timeout=300)
        try:
            smoke = json.loads((tmpd / "smoke" / "smoke.json").read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            smoke = {"ok": False, "error": f"brak smoke.json (kod {r.returncode})"}
        check(r.returncode == 0 and smoke.get("ok") is True, f"--smoke-gui → {smoke}")
        png = tmpd / "smoke" / "smoke.png"
        check(png.is_file() and png.stat().st_size > 5000, "zrzut ekranu smoke.png wygenerowany")
    if backend_exe is not None:  # onedir: backend dostępny bezpośrednio
        r = capture([str(backend_exe), "-V"], env)
        check(
            r.returncode == 0 and r.stdout.strip() == "stcgal 1.10",
            f"backend -V → {r.stdout.strip()!r}",
        )
        r = capture([str(backend_exe), "-P", "zly"], env)
        check(
            r.returncode == 2 and "invalid choice" in r.stderr,
            "argumenty przekazywane jak w stcgal",
        )
        r = capture([str(backend_exe), "--backend-info"], env)
        check("pyserial" in r.stdout, "backend --backend-info")
    return fails


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--mode", choices=("onefile", "onedir"), default="onefile")
    ap.add_argument("--dist-root", default="dist")
    ap.add_argument(
        "--clean", action="store_true", help="usuń poprzednie wyniki i katalogi robocze"
    )
    ap.add_argument("--skip-verify", action="store_true")
    args = ap.parse_args()

    dist_root = (ROOT / args.dist_root).resolve()
    work = ROOT / "build" / f"pyi-{TARGET}-{args.mode}"
    backend_dist = work / "backend-dist"
    if args.mode == "onefile":
        out = dist_root / TARGET
        app = out / f"STC-Programmer{EXE}"
    else:
        out = dist_root / f"{TARGET}-onedir"
        app = out / "STC-Programmer" / f"STC-Programmer{EXE}"
    if args.clean:
        shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(out, ignore_errors=True)
    shutil.rmtree(backend_dist, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)

    if IS_WIN and not (ROOT / "packaging/windows/stcgal-gui.ico").is_file():
        run([sys.executable, "scripts/make_icon.py"])

    env = dict(os.environ)
    log(f"tryb: {args.mode}, cel: {TARGET}, wynik: {app}")
    pyinstaller(SPECS / "backend.spec", backend_dist, work / "backend-work", env)
    env.update(STC_PYI_MODE=args.mode, STC_BACKEND_DIR=str(backend_dist / "stcgal-backend"))
    pyinstaller(SPECS / "gui.spec", out, work / "gui-work", env)

    backend_exe: Path | None = None
    if args.mode == "onedir":
        found = list((out / "STC-Programmer").rglob(f"stcgal-backend{EXE}"))
        backend_exe = found[0] if found else None
    fails = [] if args.skip_verify else verify(args.mode, app, backend_exe)

    info = {
        "version": __version__, "mode": args.mode, "target": TARGET, "output": str(app),
        "size_bytes": app.stat().st_size if app.is_file() else None,
        "sha256": sha256(app) if app.is_file() else None,
        "python": sys.version.split()[0],
        "pyinstaller": subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True, text=True).stdout.strip(),  # noqa: S603, E501
        "stcgal": capture([str(backend_exe), "-V"], dict(os.environ)).stdout.strip() if backend_exe else None,
        "verified": not args.skip_verify, "failures": fails,
    }  # fmt: skip
    (out / "build-report.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), "utf-8")
    log(json.dumps(info, indent=2, ensure_ascii=False))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
