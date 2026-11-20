#!/usr/bin/env bash
# Lokalny build Windows 10/11 x64 z Fedory przez Wine (izolowany prefiks, bez sudo, bez ingerencji
# w systemowy Python i domyślny prefiks Wine).
#
#   ./scripts/build-windows.sh [--clean] [--verbose] [--skip-tests] [--onedir] [--reset-prefix] [--help]
#
# Wynik: dist/windows/STC-Programmer.exe (onefile) lub dist/windows-onedir/STC-Programmer/ (--onedir)
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_VERSION="${STC_WIN_PYTHON_VERSION:-3.13.12}"          # Windows Python (NuGet), zgodny z PySide6/PyInstaller
CACHE="${STC_WINBUILD_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/stcgal-gui-winbuild}"
PREFIX_DIR="$CACHE/prefix"
LOG_DIR="$CACHE/logs"
REQ="$ROOT/packaging/requirements-build.txt"

CLEAN=0 VERBOSE=0 SKIP_TESTS=0 MODE=onefile RESET_PREFIX=0

usage() {
  cat <<USAGE
Użycie: $(basename "$0") [opcje]

  --clean          usuń poprzednie wyniki i katalogi robocze buildu (cache Pythona/pip zostaje)
  --verbose        pokaż pełne wyjście (Wine, pip, PyInstaller); domyślnie tylko podsumowania
  --skip-tests     pomiń testy uruchomieniowe wyniku pod Wine (--selftest, --smoke-gui)
  --onedir         zbuduj wariant diagnostyczny onedir (dist/windows-onedir/STC-Programmer/)
  --reset-prefix   usuń i utwórz od nowa izolowany prefiks Wine projektu
  --help           ta pomoc

Cache/prefiks:  $CACHE   (zmiana: STC_WINBUILD_CACHE=...)
Python Windows: $PY_VERSION (zmiana: STC_WIN_PYTHON_VERSION=...)
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --clean) CLEAN=1 ;;
    --verbose) VERBOSE=1 ;;
    --skip-tests) SKIP_TESTS=1 ;;
    --onedir) MODE=onedir ;;
    --reset-prefix) RESET_PREFIX=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Nieznana opcja: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

mkdir -p "$CACHE/downloads" "$LOG_DIR"
LOG="$LOG_DIR/build-$(date +%Y%m%d-%H%M%S).log"
: > "$LOG"

say()  { printf '\033[1;34m[build-windows]\033[0m %s\n' "$*" | tee -a "$LOG" >&2; }
warn() { printf '\033[1;33m[build-windows] UWAGA:\033[0m %s\n' "$*" | tee -a "$LOG" >&2; }
die()  { printf '\033[1;31m[build-windows] BŁĄD:\033[0m %s\n' "$*" | tee -a "$LOG" >&2; echo "Pełny log: $LOG" >&2; exit 1; }
trap 'die "przerwano w linii $LINENO (kod $?)"' ERR

# Uruchamia polecenie: pełne wyjście do logu; na ekran tylko w trybie --verbose.
run() {
  echo "\$ $*" >> "$LOG"
  if [ "$VERBOSE" = 1 ]; then "$@" 2>&1 | tee -a "$LOG"; return "${PIPESTATUS[0]}"
  else "$@" >> "$LOG" 2>&1; fi
}

# ---------------------------------------------------------------- 1. zależności systemowe
say "1/8 Sprawdzanie zależności systemowych"
missing=()
for cmd in wine curl unzip sha256sum python3; do command -v "$cmd" >/dev/null || missing+=("$cmd"); done
if [ "${#missing[@]}" -gt 0 ]; then
  die "brak poleceń: ${missing[*]} - Fedora: sudo dnf install wine curl unzip coreutils python3 (jednorazowo)"
fi
WINE_VERSION="$(wine --version 2>/dev/null || true)"
[ -n "$WINE_VERSION" ] || die "wine nie działa"
say "    Wine: $WINE_VERSION; wolne miejsce w cache: $(df -h --output=avail "$CACHE" | tail -1 | tr -d ' ')"

# ---------------------------------------------------------------- 2. izolowany prefiks Wine
export WINEPREFIX="$PREFIX_DIR" WINEARCH=win64 WINEDLLOVERRIDES="mscoree,mshtml="
if [ "$VERBOSE" = 1 ]; then export WINEDEBUG="err+all"; else export WINEDEBUG="-all"; fi
unset WINEESYNC WINEFSYNC 2>/dev/null || true
if [ "$RESET_PREFIX" = 1 ] && [ -d "$PREFIX_DIR" ]; then
  say "    usuwanie prefiksu (--reset-prefix)"; rm -rf "$PREFIX_DIR"
fi
say "2/8 Prefiks Wine: $PREFIX_DIR"
if [ ! -f "$PREFIX_DIR/system.reg" ]; then
  say "    inicjalizacja prefiksu (jednorazowo, ok. 10 s)"
  run timeout 300 wineboot --init || die "wineboot nie powiódł się"
  run wineserver -w || true
fi

# ---------------------------------------------------------------- 3. Windows Python (NuGet, bez instalatora GUI)
PY_DIR="$PREFIX_DIR/drive_c/py"
WPY='C:\py\tools\python.exe'
NUPKG="$CACHE/downloads/python-$PY_VERSION.nupkg"
# Przypięta suma SHA-256 pakietu NuGet (łańcuch dostaw); dla innych wersji: STC_WIN_PYTHON_SHA256=...
declare -A KNOWN_SHA=( ["3.13.12"]="389c0228afbb3530f6cd079f5cec44139b1441dd51c85ec704f7a63f1c9f3802" )
PY_SHA="${STC_WIN_PYTHON_SHA256:-${KNOWN_SHA[$PY_VERSION]:-}}"
say "3/8 Windows Python $PY_VERSION x64"
if [ ! -f "$PY_DIR/tools/python.exe" ] || ! grep -q "^$PY_VERSION\$" "$PY_DIR/.version" 2>/dev/null; then
  if [ ! -s "$NUPKG" ]; then
    say "    pobieranie pakietu NuGet python $PY_VERSION"
    curl -fSL --retry 3 -o "$NUPKG.part" "https://www.nuget.org/api/v2/package/python/$PY_VERSION" >> "$LOG" 2>&1 \
      || die "nie udało się pobrać Pythona $PY_VERSION (sieć? wersja?)"
    mv "$NUPKG.part" "$NUPKG"
  fi
  unzip -tq "$NUPKG" >> "$LOG" 2>&1 || { rm -f "$NUPKG"; die "uszkodzony pakiet $NUPKG (usunięto - uruchom ponownie)"; }
  if [ -n "$PY_SHA" ]; then
    ACTUAL_SHA="$(sha256sum "$NUPKG" | cut -d' ' -f1)"
    [ "$ACTUAL_SHA" = "$PY_SHA" ] || { rm -f "$NUPKG"; die "SHA-256 pakietu Pythona nie zgadza się (oczekiwano $PY_SHA, jest $ACTUAL_SHA) - pakiet usunięto"; }
  else
    warn "brak przypiętej sumy SHA-256 dla Pythona $PY_VERSION (ustaw STC_WIN_PYTHON_SHA256)"
  fi
  rm -rf "$PY_DIR"; mkdir -p "$PY_DIR"
  unzip -qo "$NUPKG" 'tools/*' -d "$PY_DIR"
  echo "$PY_VERSION" > "$PY_DIR/.version"
  rm -f "$CACHE/deps.stamp"
fi
wpy() { run wine "$WPY" "$@"; }
WPY_OUT="$(wine "$WPY" -c 'import sys;print(sys.version.split()[0])' 2>>"$LOG" | tr -d '\r')"
[ "$WPY_OUT" = "$PY_VERSION" ] || die "Python w Wine zgłasza '$WPY_OUT', oczekiwano $PY_VERSION"
say "    Python w Wine: $WPY_OUT"

# ---------------------------------------------------------------- 4-5. pip + zależności + PyInstaller + stcgal
say "4/8 Zależności Windows (PySide6, pyserial, PyInstaller, stcgal) wg packaging/requirements-build.txt"
STAMP_NOW="$(sha256sum "$REQ" | cut -d' ' -f1)-$PY_VERSION"
if [ "$(cat "$CACHE/deps.stamp" 2>/dev/null || true)" != "$STAMP_NOW" ]; then
  wpy -m ensurepip --upgrade || die "ensurepip nie powiódł się"
  WREQ="$(winepath -w "$REQ" 2>/dev/null | tr -d '\r')"
  PIP_DISABLE_PIP_VERSION_CHECK=1 wpy -m pip install --only-binary=:all: --no-warn-script-location -r "$WREQ" \
    || die "pip install nie powiódł się (patrz log)"
  echo "$STAMP_NOW" > "$CACHE/deps.stamp"
else
  say "    zależności aktualne (cache) - pomijam"
fi
PIP_FREEZE="$(wine "$WPY" -m pip list --format=freeze 2>>"$LOG" | tr -d '\r')"
ver_of() { printf '%s\n' "$PIP_FREEZE" | grep -i "^$1==" | cut -d= -f3; }
PYI_VERSION="$(ver_of pyinstaller)"; STCGAL_VERSION="$(ver_of stcgal)"; PYSIDE_VERSION="$(ver_of PySide6)"
say "    PySide6 $PYSIDE_VERSION · PyInstaller $PYI_VERSION · stcgal $STCGAL_VERSION"
[ "$STCGAL_VERSION" = "1.10" ] || die "oczekiwano stcgal 1.10, jest '$STCGAL_VERSION'"

# ---------------------------------------------------------------- 6-7. build + testy
say "5/8 Ikona aplikacji"
[ -f "$ROOT/packaging/windows/stcgal-gui.ico" ] || {
  run python3 "$ROOT/scripts/make_icon.py" || die "brak ikony i nie można jej wygenerować"; }

say "6/8 Budowanie ($MODE) - PyInstaller pod Wine (kilka minut; log: $LOG)"
BUILD_ARGS=(scripts/pyi_build.py --mode "$MODE")
[ "$CLEAN" = 1 ] && BUILD_ARGS+=(--clean)
if [ "$SKIP_TESTS" = 1 ]; then BUILD_ARGS+=(--skip-verify); say "    (testy uruchomieniowe pominięte: --skip-tests)"; fi
if [ "$CLEAN" = 1 ]; then rm -rf "$ROOT/dist/windows" "$ROOT/dist/windows-onedir" "$ROOT/build/pyi-windows-onefile" "$ROOT/build/pyi-windows-onedir"; fi
cd "$ROOT"
export PYTHONPYCACHEPREFIX='C:\pycache' PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 PYTHONIOENCODING=utf-8
trap - ERR
set +e
if [ "$VERBOSE" = 1 ]; then wine "$WPY" "${BUILD_ARGS[@]}" 2>&1 | tee -a "$LOG"; BUILD_RC="${PIPESTATUS[0]}"
else wine "$WPY" "${BUILD_ARGS[@]}" 2>&1 | tee -a "$LOG" | grep --line-buffered -E '^\[pyi_build\] (OK|FAIL|tryb)' | sed 's/^\[pyi_build\]/    /' >&2; BUILD_RC="${PIPESTATUS[0]}"; fi
set -e
trap 'die "przerwano w linii $LINENO (kod $?)"' ERR
wineserver -w || true

# ---------------------------------------------------------------- 8. raport
if [ "$MODE" = onefile ]; then OUT_DIR="$ROOT/dist/windows"; else OUT_DIR="$ROOT/dist/windows-onedir"; fi
JSON="$OUT_DIR/build-report.json"
[ -f "$JSON" ] || die "nie powstał raport buildu ($JSON) - build nieudany (kod $BUILD_RC)"
say "7/8 Raport buildu"
REPORT="$OUT_DIR/BUILD-REPORT.txt"
python3 - "$JSON" "$REPORT" "$WINE_VERSION" "$PYSIDE_VERSION" "$BUILD_RC" "$SKIP_TESTS" <<'PY'
import json, sys, time
j = json.load(open(sys.argv[1])); wine, pyside, rc, skipped = sys.argv[3], sys.argv[4], int(sys.argv[5]), sys.argv[6] == "1"
size = j["size_bytes"]
lines = [
    f"STC Programmer GUI {j['version']} - build Windows x64 ({j['mode']}) {time.strftime('%Y-%m-%d %H:%M:%S')}",
    f"Status kompilacji : {'OK' if size else 'BŁĄD'}",
    f"Plik              : {j['output']}",
    f"Rozmiar           : {size:,} B ({size/1048576:.1f} MiB)" if size else "Rozmiar           : -",
    f"SHA-256           : {j['sha256']}",
    f"Testy pod Wine    : " + ("POMINIĘTE (--skip-tests)" if skipped else ("PRZESZŁY" if not j['failures'] and rc == 0 else "NIEPOWODZENIE: " + "; ".join(j['failures']))),
    f"Python (Windows)  : {j['python']}",
    f"PyInstaller       : {j['pyinstaller']}",
    f"PySide6           : {pyside}",
    f"stcgal (backend)  : {j.get('stcgal') or '1.10 (wbudowany; wersja potwierdzona w --selftest)'}",
    f"Wine              : {wine}",
    "UWAGA: testy pod Wine NIE dowodzą poprawnego działania na prawdziwym Windows 10/11.",
]
open(sys.argv[2], "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
PY
say "8/8 Gotowe. Raport: $REPORT; log: $LOG"
[ "$BUILD_RC" = 0 ] || die "build lub testy zakończone niepowodzeniem (kod $BUILD_RC)"
