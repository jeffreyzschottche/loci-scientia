#!/usr/bin/env bash
# VEILIGE kiosk-test — draait `cage` GENEST in je huidige desktopsessie.
#
# cage is wlroots-gebaseerd: start je het BINNEN een bestaande Wayland/X11-sessie,
# dan opent het als een GEWOON VENSTER (Wayland/X11-backend) i.p.v. de tty over te
# nemen. Zo test je exact de kiosk-renderpad zonder GDM/GRUB/getty/systemd aan te
# raken. Sluit het venster (of Ctrl+C in deze terminal) om te stoppen — geen
# herstel nodig.
#
# Draai dit NOOIT vanaf een kale tty (zonder WAYLAND_DISPLAY/DISPLAY): dan zou cage
# alsnog de tty grijpen. Daarom weigeren we dat hieronder.
#
#   scripts/kiosk-test.sh sanity     # minimaal Qt-venster onder cage (bewijst render + GPU)
#   scripts/kiosk-test.sh frontend   # de ECHTE PySide6-frontend onder cage (backend moet apart draaien)
#
# 'sanity' is de snelste check: werkt dat, dan kan Qt onder cage tekenen en zit het
# probleem in de boot-stack (lociscientia.sh), niet in de compositor.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

mode="${1:-sanity}"

if ! command -v cage >/dev/null 2>&1; then
    echo "❌ cage niet geïnstalleerd.  sudo apt-get install -y cage" >&2
    exit 1
fi

# Eis een bestaande grafische sessie, anders neemt cage de tty over (= onveilig).
if [ -z "${WAYLAND_DISPLAY:-}" ] && [ -z "${DISPLAY:-}" ]; then
    echo "❌ Geen Wayland/X11-sessie gevonden (WAYLAND_DISPLAY/DISPLAY leeg)." >&2
    echo "   Draai deze test BINNEN je normale desktop, niet vanaf een kale tty." >&2
    exit 1
fi

PYTHON="$PROJECT_ROOT/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"

# Qt in de geneste cage: gebruik wayland (cage levert zijn eigen WAYLAND_DISPLAY
# aan child-processen), met xcb/XWayland als terugval.
export QT_QPA_PLATFORM="wayland;xcb"
# Bewust GEEN AITJE_KIOSK=1 hier: dat zou de afsluit/herstart-knop een echte
# device-poweroff/reboot laten doen. Dit is enkel een render-test.

case "$mode" in
    sanity)
        echo "▶  cage (genest) + minimaal Qt-venster — sluit het venster om te stoppen."
        exec cage -- "$PYTHON" - <<'PY'
import sys
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt
app = QApplication(sys.argv)
lbl = QLabel("AITJE kiosk-test ✅\n\ncage + Qt renderen werkt.\n\nSluit dit venster (Alt+F4) om te stoppen.")
lbl.setAlignment(Qt.AlignCenter)
lbl.setStyleSheet("background:#1c1c1c; color:#facc15; font-size:28px; padding:40px;")
lbl.showFullScreen()
sys.exit(app.exec())
PY
        ;;
    frontend)
        echo "▶  cage (genest) + de echte PySide6-frontend."
        echo "   Let op: de backend moet apart draaien (bv. './lociscientia.sh' in een andere terminal),"
        echo "   anders toont de UI een verbindingsfout — dat is voor deze test prima."
        exec cage -- "$PYTHON" -m app.frontend.main
        ;;
    *)
        echo "Gebruik: $0 {sanity|frontend}" >&2
        exit 2
        ;;
esac
