#!/usr/bin/env bash
# VEILIGE kiosk-test — draait `weston` (kiosk-shell) GENEST in je huidige sessie.
#
# Start je weston BINNEN een bestaande Wayland/X11-sessie, dan kiest het de
# wayland/x11-backend en opent het als een GEWOON VENSTER i.p.v. de tty over te
# nemen. Zo test je exact de kiosk-renderpad zonder GDM/GRUB/getty/systemd aan te
# raken. Sluit het venster of druk Ctrl+C in deze terminal om te stoppen — geen
# herstel nodig. (weston stopt automatisch zodra de client eindigt.)
#
# Draai dit NOOIT vanaf een kale tty (zonder WAYLAND_DISPLAY/DISPLAY): dan zou
# weston alsnog de tty grijpen. Daarom weigeren we dat hieronder.
#
#   scripts/kiosk-test.sh sanity     # minimaal Qt-venster onder weston (bewijst render + GPU)
#   scripts/kiosk-test.sh frontend   # de ECHTE PySide6-frontend onder weston (backend apart draaien)
#
# 'sanity' is de snelste check: werkt dat, dan kan Qt onder weston tekenen en zit
# een eventueel probleem in de boot-stack (lociscientia.sh), niet in de compositor.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

mode="${1:-sanity}"

if ! command -v weston >/dev/null 2>&1; then
    echo "❌ weston niet geïnstalleerd.  sudo apt-get install -y weston" >&2
    exit 1
fi

# Eis een bestaande grafische sessie, anders neemt weston de tty over (= onveilig).
if [ -z "${WAYLAND_DISPLAY:-}" ] && [ -z "${DISPLAY:-}" ]; then
    echo "❌ Geen Wayland/X11-sessie gevonden (WAYLAND_DISPLAY/DISPLAY leeg)." >&2
    echo "   Draai deze test BINNEN je normale desktop, niet vanaf een kale tty." >&2
    exit 1
fi

PYTHON="$PROJECT_ROOT/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
# Qt onder weston: native Wayland. weston zet WAYLAND_DISPLAY voor zijn client; deze
# export reist mee in de omgeving. Bewust GEEN AITJE_KIOSK=1: dat zou de afsluit/
# herstart-knop een echte device-poweroff/reboot laten doen — dit is enkel render.
export QT_QPA_PLATFORM=wayland

# Eigen socket zodat we niet botsen met de host-compositor; weston draait de '--'
# client en stopt automatisch zodra die eindigt.
SOCK="wayland-aitje-test"
WESTON_ARGS=(--socket="$SOCK" --shell=kiosk-shell.so --width=1280 --height=800)

case "$mode" in
    sanity)
        echo "▶  weston (genest) + minimaal Qt-venster — Ctrl+C of sluit het venster om te stoppen."
        exec weston "${WESTON_ARGS[@]}" -- "$PYTHON" -c '
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt
a = QApplication([])
l = QLabel("AITJE kiosk-test ✅\n\nweston + Qt renderen werkt.\n\nCtrl+C in de terminal om te stoppen.")
l.setAlignment(Qt.AlignCenter)
l.setStyleSheet("background:#1c1c1c; color:#facc15; font-size:28px; padding:40px;")
l.showFullScreen()
a.exec()
'
        ;;
    frontend)
        echo "▶  weston (genest) + de echte PySide6-frontend."
        echo "   Let op: de backend moet apart draaien (bv. './lociscientia.sh' in een andere terminal),"
        echo "   anders toont de UI een verbindingsfout — dat is voor deze test prima."
        exec weston "${WESTON_ARGS[@]}" -- "$PYTHON" -m app.frontend.main
        ;;
    *)
        echo "Gebruik: $0 {sanity|frontend}" >&2
        exit 2
        ;;
esac
