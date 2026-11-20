#!/bin/sh
# Uruchamia spakowaną aplikację; Wayland, a w razie braku X11.
HERE="$(dirname "$(readlink -f "$0")")"
APP="${STC_APP_DIR:-$HERE}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland;xcb}"
exec "$APP/STC-Programmer" "$@"
