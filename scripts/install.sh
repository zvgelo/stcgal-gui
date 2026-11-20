#!/usr/bin/env bash
# Instalacja użytkownika (bez sudo): venv + launcher + .desktop + ikona.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
APPDIR="${APPDIR:-$PREFIX/share/stcgal-gui}"
VENV="$APPDIR/venv"
PY="${PYTHON:-python3}"

# Jeżeli systemowy PySide6 (RPM python3-pyside6) jest dostępny, użyj go: daje natywny styl Breeze.
if "$PY" -c "import PySide6" 2>/dev/null; then
  echo ">> Wykryto systemowy PySide6 - venv z --system-site-packages (styl Breeze)"
  "$PY" -m venv --system-site-packages "$VENV"
else
  echo ">> Brak systemowego PySide6 - zostanie zainstalowany z PyPI (styl Fusion)"
  "$PY" -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet "$SRC"

mkdir -p "$PREFIX/bin" "$PREFIX/share/applications" "$PREFIX/share/icons/hicolor/scalable/apps"
install -m 0755 "$SRC/scripts/stcgal-gui" "$PREFIX/bin/stcgal-gui"
sed -i "s|@VENV@|$VENV|g" "$PREFIX/bin/stcgal-gui"
sed "s|@BIN@|$PREFIX/bin/stcgal-gui|g" "$SRC/packaging/stcgal-gui.desktop" \
  > "$PREFIX/share/applications/stcgal-gui.desktop"
install -m 0644 "$SRC/stcgal_gui/resources/stcgal-gui.svg" \
  "$PREFIX/share/icons/hicolor/scalable/apps/stcgal-gui.svg"
command -v update-desktop-database >/dev/null && update-desktop-database "$PREFIX/share/applications" || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q "$PREFIX/share/icons/hicolor" || true

if ! command -v stcgal >/dev/null && [ ! -x "$HOME/.local/bin/stcgal" ]; then
  echo "!! Nie znaleziono stcgal. Zainstaluj: pipx install stcgal"
fi
if ! id -nG | tr ' ' '\n' | grep -qx dialout; then
  echo "!! Użytkownik nie należy do grupy dialout: sudo usermod -aG dialout \$USER (i ponowne logowanie)"
fi
echo "Gotowe. Uruchom: stcgal-gui  (lub z menu aplikacji)"
