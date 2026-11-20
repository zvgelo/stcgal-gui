#!/usr/bin/env bash
set -euo pipefail
PREFIX="${PREFIX:-$HOME/.local}"
rm -rf "$PREFIX/share/stcgal-gui" "$PREFIX/bin/stcgal-gui" \
  "$PREFIX/share/applications/stcgal-gui.desktop" \
  "$PREFIX/share/icons/hicolor/scalable/apps/stcgal-gui.svg"
echo "Usunięto. Ustawienia (~/.config/stcgal-gui) pozostawiono."
