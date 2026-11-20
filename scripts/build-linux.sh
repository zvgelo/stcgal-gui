#!/usr/bin/env bash
# Pakiety Linux z jednego buildu PyInstaller (onedir): tar.gz, .deb, .rpm, AppDir/AppImage.
#   ./scripts/build-linux.sh [--clean] [--skip-tests] [--formats tar,deb,rpm,appimage]
# Wynik: dist/linux/. Python z PySide6, PyInstaller, pyserial i stcgal: STC_PYTHON (domyślnie
# venv build/linux-venv tworzony z packaging/requirements-build.txt).
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLEAN=0 SKIP_TESTS=0 EXPLICIT=0 FORMATS="tar,deb,rpm,appimage"
while [ $# -gt 0 ]; do
  case "$1" in
    --clean) CLEAN=1 ;;
    --skip-tests) SKIP_TESTS=1 ;;
    --formats) [ $# -ge 2 ] || { echo "--formats wymaga listy" >&2; exit 2; }; FORMATS="$2"; EXPLICIT=1; shift ;;
    -h|--help) sed -n '2,6p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "Nieznana opcja: $1" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '[build-linux] %s\n' "$*" >&2; }
die() { printf '[build-linux] BŁĄD: %s\n' "$*" >&2; exit 1; }
missing_tool() { [ "$EXPLICIT" = 1 ] && die "brak narzędzia: $1 (format wymagany jawnie)"; say "   pominięto: brak $1"; }
TMPS=()
cleanup() { [ "${#TMPS[@]}" -gt 0 ] && rm -rf "${TMPS[@]}"; return 0; }
trap cleanup EXIT
has_fmt() { case ",$FORMATS," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }

cd "$ROOT"
mkdir -p "$ROOT/build"
PY="${STC_PYTHON:-}"
if [ -z "$PY" ]; then
  VENV="$ROOT/build/linux-venv"
  [ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install -q -r packaging/requirements-build.txt
  PY="$VENV/bin/python"
fi
"$PY" -c "import PyInstaller, PySide6, serial, stcgal" 2>/dev/null || die "brak modułów w $PY (PyInstaller, PySide6, pyserial, stcgal)"

VERSION="$("$PY" scripts/appversion.py)"
ARCH="$(uname -m)"
case "$ARCH" in x86_64) DEBARCH=amd64 ;; aarch64) DEBARCH=arm64 ;; *) DEBARCH="$ARCH" ;; esac
DIST="$ROOT/dist/linux"
APPSRC="$ROOT/dist/linux-native-onedir/STC-Programmer"
PKG="$ROOT/packaging/linux"
[ "$CLEAN" = 1 ] && rm -rf "$DIST" "$ROOT/build/pyi-linux-native-onedir"
mkdir -p "$DIST"

[ -f "$PKG/stc-programmer.png" ] || "$PY" scripts/make_icon.py >/dev/null 2>&1 || true
say "1/5 Build PyInstaller (onedir), wersja $VERSION"
BUILD_ARGS=(scripts/pyi_build.py --mode onedir)
[ "$SKIP_TESTS" = 1 ] && BUILD_ARGS+=(--skip-verify)
"$PY" "${BUILD_ARGS[@]}" > "$ROOT/build/build-linux.log" 2>&1 || { tail -20 "$ROOT/build/build-linux.log" >&2; die "PyInstaller/testy nie powiodły się"; }
grep -E "^\[pyi_build\] (OK|FAIL)" "$ROOT/build/build-linux.log" | sed 's/^\[pyi_build\]/   /' >&2 || true
[ -x "$APPSRC/STC-Programmer" ] || die "brak $APPSRC/STC-Programmer"

if has_fmt tar; then
  say "2/5 tar.gz"
  T="$DIST/STC-Programmer-$VERSION-linux-$ARCH.tar.gz"
  STAGE="$(mktemp -d)"; TMPS+=("$STAGE"); mkdir -p "$STAGE/STC-Programmer"
  cp -a "$APPSRC/." "$STAGE/STC-Programmer/"
  install -m 0755 "$PKG/launcher.sh" "$STAGE/STC-Programmer/stc-programmer"
  tar -C "$STAGE" -czf "$T" STC-Programmer; rm -rf "$STAGE"
  say "   $T"
fi

if has_fmt deb; then
  if command -v dpkg-deb >/dev/null; then
    say "3/5 .deb"
    D="$(mktemp -d)"; TMPS+=("$D"); R="$D/stc-programmer_${VERSION}-1_${DEBARCH}"
    mkdir -p "$R/opt/stc-programmer" "$R/usr/bin" "$R/usr/share/applications" "$R/usr/share/icons/hicolor/256x256/apps" "$R/DEBIAN"
    cp -a "$APPSRC/." "$R/opt/stc-programmer/"
    install -m 0755 "$PKG/launcher.sh" "$R/opt/stc-programmer/launcher.sh"
    ln -s /opt/stc-programmer/launcher.sh "$R/usr/bin/stc-programmer"
    install -m 0644 "$PKG/stc-programmer.desktop" "$R/usr/share/applications/"
    install -m 0644 "$PKG/stc-programmer.png" "$R/usr/share/icons/hicolor/256x256/apps/"
    SIZE="$(du -sk "$R/opt" | cut -f1)"
    cat > "$R/DEBIAN/control" <<CTL
Package: stc-programmer
Version: $VERSION-1
Section: electronics
Priority: optional
Architecture: $DEBARCH
Installed-Size: $SIZE
Maintainer: stcgal-gui <stcgal-gui@users.noreply.github.com>
Depends: libc6 (>= 2.31), libegl1, libgl1, libxkbcommon0, libfontconfig1, libdbus-1-3, libxcb-cursor0
Description: Graficzny programator mikrokontrolerow STC (stcgal)
 Identyfikacja i programowanie mikrokontrolerow STC przez UART/ISP.
 Zawiera wbudowany backend stcgal 1.10.
CTL
    dpkg-deb --root-owner-group --build "$R" "$DIST/stc-programmer_${VERSION}-1_${DEBARCH}.deb" >/dev/null
    rm -rf "$D"; say "   $DIST/stc-programmer_${VERSION}-1_amd64.deb"
  else missing_tool dpkg-deb; fi
fi

if has_fmt rpm; then
  if command -v rpmbuild >/dev/null; then
    say "4/5 .rpm"
    TOP="$(mktemp -d)"; TMPS+=("$TOP")
    rpmbuild -bb "$PKG/stc-programmer.spec" --define "_topdir $TOP" --define "app_version $VERSION" \
      --define "app_dir $APPSRC" --define "pkg_dir $PKG" > "$ROOT/build/rpmbuild.log" 2>&1 \
      || { tail -20 "$ROOT/build/rpmbuild.log" >&2; die "rpmbuild nie powiódł się"; }
    cp "$TOP"/RPMS/*/stc-programmer-*.rpm "$DIST/"; rm -rf "$TOP"
    say "   $(ls "$DIST"/stc-programmer-*.rpm)"
  else missing_tool rpmbuild; fi
fi

if has_fmt appimage; then
  say "5/5 AppDir/AppImage"
  AD="$ROOT/build/STC-Programmer.AppDir"; rm -rf "$AD"; mkdir -p "$AD/usr/lib/stc-programmer"
  cp -a "$APPSRC/." "$AD/usr/lib/stc-programmer/"
  install -m 0644 "$PKG/stc-programmer.desktop" "$AD/stc-programmer.desktop"
  install -m 0644 "$PKG/stc-programmer.png" "$AD/stc-programmer.png"
  cp "$PKG/stc-programmer.png" "$AD/.DirIcon"
  cat > "$AD/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export STC_APP_DIR="$HERE/usr/lib/stc-programmer"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland;xcb}"
exec "$STC_APP_DIR/STC-Programmer" "$@"
RUN
  chmod +x "$AD/AppRun"
  if [ "$SKIP_TESTS" = 0 ]; then
    QT_QPA_PLATFORM=offscreen "$AD/AppRun" --selftest --report "$ROOT/build/appdir-selftest.json" >/dev/null 2>&1 \
      && say "   AppDir: --selftest OK" || die "AppDir: --selftest nie przeszedł"
  fi
  if command -v appimagetool >/dev/null; then
    ARCH="$ARCH" appimagetool --appimage-extract-and-run "$AD" "$DIST/STC-Programmer-$VERSION-$ARCH.AppImage" >/dev/null 2>&1 \
      && say "   $DIST/STC-Programmer-$VERSION-$ARCH.AppImage" || die "appimagetool nie powiódł się"
  else say "   appimagetool niedostępny: AppImage zbuduje CI (AppDir: $AD)"; fi
fi
(cd "$DIST" && rm -f SHA256SUMS && sha256sum -- *.tar.gz *.deb *.rpm *.AppImage 2>/dev/null > SHA256SUMS || true)
say "Gotowe: $DIST"; ls -l "$DIST" >&2
