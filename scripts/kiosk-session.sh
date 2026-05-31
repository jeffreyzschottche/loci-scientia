#!/usr/bin/env bash
# AITJE kiosk-sessie — dit is het ENIGE commando dat `cage` start.
#
# Cage is een Wayland-kioskcompositor: het toont precies de vensters die dit
# commando opent en niets anders (geen GNOME, geen panelen, geen alt-tab). Wij
# draaien hier lociscientia.sh, dat de backend-stack opstart en als laatste de
# PySide6-frontend toont. Die frontend wordt zo het enige zichtbare venster.
#
# Wordt aangeroepen door systemd/aitje-kiosk.service via:
#     /usr/bin/cage -- <project>/scripts/kiosk-session.sh
#
# BELANGRIJK — geen flikker-loop bij een boot-fout:
# lociscientia.sh draait met `set -euo pipefail`. Faalt er iets vóór de frontend
# (Caddy op :80/:443, hostname/mDNS, apt-lock, …), dan stopt dat script met een
# non-zero exit. Zouden we het via `exec` draaien, dan sterft cage mee en herstart
# systemd (Restart=always) elke 2s → een knipperende cursor zonder uitleg. Daarom
# draaien we het NIET met exec, vangen we de exitcode af en tonen we bij een fout
# een leesbaar fullscreen-scherm (cage blijft leven zolang dat venster open staat).
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

SESSION_LOG="$PROJECT_ROOT/kiosk-session.log"

# Toon een leesbare foutmelding fullscreen i.p.v. cage te laten crashen. Houdt het
# scherm vast tot de gebruiker het venster sluit; zo blijft cage in leven en is er
# geen 2s-herstart-storm. Lukt Qt niet (venv nog niet gebouwd), val terug op een
# console-melding + pauze.
show_boot_error() {
    local rc="$1"
    local py="$PROJECT_ROOT/.venv/bin/python"
    [ -x "$py" ] || py="python3"
    if "$py" -c 'import PySide6' >/dev/null 2>&1; then
        AITJE_BOOT_RC="$rc" AITJE_BOOT_LOG="$SESSION_LOG" "$py" - <<'PY' || true
import os
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit
rc = os.environ.get("AITJE_BOOT_RC", "?")
log = os.environ.get("AITJE_BOOT_LOG", "")
try:
    with open(log, "r", errors="replace") as fh:
        tail = "".join(fh.readlines()[-40:]) or "(log is leeg)"
except Exception:
    tail = "(geen log beschikbaar)"
app = QApplication([])
w = QWidget()
w.setStyleSheet("background:#1c1c1c; color:#f5f5f5;")
lay = QVBoxLayout(w)
title = QLabel(f"AITJE kon niet opstarten  (exit {rc})")
title.setStyleSheet("color:#facc15; font-size:30px; font-weight:bold;")
lay.addWidget(title)
hint = QLabel(
    "Druk Ctrl+Alt+F3 voor een console, log in en draai:\n"
    "    sudo scripts/aitje-kiosk-apply.sh disable\n"
    "om terug te keren naar een normale desktop.\n"
    "Sluit dit venster (Alt+F4) om opnieuw te proberen. Laatste logregels:"
)
hint.setStyleSheet("font-size:18px;")
lay.addWidget(hint)
box = QTextEdit()
box.setReadOnly(True)
box.setPlainText(tail)
box.setStyleSheet("background:#000; color:#cfcfcf; font-family:monospace; font-size:14px;")
lay.addWidget(box, 1)
w.showFullScreen()
app.exec()
PY
    else
        printf '❌ AITJE-boot faalde (exit %s). Ctrl+Alt+F3 → console → "sudo scripts/aitje-kiosk-apply.sh disable".\n' "$rc" >&2
        sleep 60
    fi
}

# Draai de stack; leg alles vast in kiosk-session.log zodat het foutscherm de
# laatste regels kan tonen. De procesvervanging (> >(tee)) bewaart de exitcode van
# lociscientia.sh in $? (i.t.t. een pipe). Normaal blijft lociscientia.sh draaien
# zolang de frontend leeft en eindigt 0; een non-zero exit = boot/stack faalde.
"$PROJECT_ROOT/lociscientia.sh" > >(tee "$SESSION_LOG") 2>&1
rc=$?

if [ "$rc" -ne 0 ]; then
    show_boot_error "$rc"
fi

exit "$rc"
