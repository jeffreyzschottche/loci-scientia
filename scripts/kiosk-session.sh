#!/usr/bin/env bash
# AITJE kiosk-sessie — dit is het ENIGE commando dat `cage` start.
#
# Cage is een Wayland-kioskcompositor: het toont precies de vensters die dit
# commando opent en niets anders (geen GNOME, geen panelen, geen alt-tab). Wij
# exec'en hier lociscientia.sh, dat de backend-stack opstart en als laatste de
# PySide6-frontend toont. Die frontend wordt zo het enige zichtbare venster.
#
# Wordt aangeroepen door systemd/aitje-kiosk.service via:
#     /usr/bin/cage -- <project>/scripts/kiosk-session.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Markeer dat we in kioskmodus draaien. lociscientia.sh en de frontend lezen dit
# (frontend verbergt o.a. afsluit/herstart-acties en stopt netjes zodat systemd
# de hele stack opnieuw kan starten).
export AITJE_KIOSK=1

# PAMName=login in de systemd-unit zet normaal XDG_RUNTIME_DIR; val terug op de
# conventionele waarde als pam_systemd dat (nog) niet deed, anders vindt cage/Qt
# geen runtime-dir/socket.
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Qt: gebruik de Wayland-display van cage, met xcb (XWayland) als terugval.
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland;xcb}"

exec "$PROJECT_ROOT/lociscientia.sh"
