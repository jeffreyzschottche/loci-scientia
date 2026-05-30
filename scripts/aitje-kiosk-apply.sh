#!/usr/bin/env bash
# AITJE kioskmodus aan/uitzetten. Moet als root draaien (via sudo), behalve
# `status` dat zonder root werkt.
#
#   sudo scripts/aitje-kiosk-apply.sh enable    # device wordt een kiosk
#   sudo scripts/aitje-kiosk-apply.sh disable   # normale GNOME-desktop terug
#   scripts/aitje-kiosk-apply.sh status         # huidige staat (geen root nodig)
#
# `enable`:
#   * installeert + enabled de cage-kiosk systemd-service (aitje-kiosk.service);
#   * geeft de device-gebruiker passwordless sudo (NOPASSWD: ALL);
#   * schakelt GDM/GNOME uit zodat alleen de kiosk laadt;
#   * haalt `splash` uit GRUB (+ bgrt_disable) voor een zwarte boot zonder
#     Ubuntu-logo.
# `disable` draait dit alles terug (de NOPASSWD-regel blijft staan zodat de
# toggle zonder wachtwoord blijft werken; verwijder /etc/sudoers.d/aitje-kiosk
# handmatig als je dat ook wilt opruimen).
#
# Beide acties zijn idempotent. Zie docs/kiosk.md.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SERVICE_NAME="aitje-kiosk.service"
SERVICE_TEMPLATE="$PROJECT_ROOT/systemd/aitje-kiosk.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
SUDOERS_TEMPLATE="$PROJECT_ROOT/sudoers/aitje-kiosk.template"
SUDOERS_PATH="/etc/sudoers.d/aitje-kiosk"
SESSION_SCRIPT="$PROJECT_ROOT/scripts/kiosk-session.sh"
GRUB_FILE="/etc/default/grub"
GRUB_BACKUP="/etc/default/grub.aitje-backup"
DISPLAY_MANAGER="gdm3"

log() { printf '%s\n' "$*"; }
err() { printf '%s\n' "$*" >&2; }

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        err "❌ '$1' vereist root. Gebruik: sudo $0 $1"
        exit 1
    fi
}

detect_kiosk_user() {
    if [ -n "${KIOSK_USER:-}" ]; then
        printf '%s' "$KIOSK_USER"
    elif [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
        printf '%s' "$SUDO_USER"
    else
        # Terugval: eigenaar van de projectmap (zo draait lociscientia.sh ook).
        stat -c '%U' "$PROJECT_ROOT" 2>/dev/null || printf 'aitje'
    fi
}

update_grub() {
    if command -v update-grub >/dev/null 2>&1; then
        update-grub
    elif command -v grub-mkconfig >/dev/null 2>&1; then
        grub-mkconfig -o /boot/grub/grub.cfg
    else
        err "⚠️  update-grub/grub-mkconfig niet gevonden; bootloader niet herschreven."
    fi
}

install_service() {
    local user="$1"
    local tmp
    tmp="$(mktemp)"
    sed -e "s#__PROJECT_ROOT__#$PROJECT_ROOT#g" \
        -e "s#__KIOSK_USER__#$user#g" \
        "$SERVICE_TEMPLATE" > "$tmp"
    install -D -m 0644 "$tmp" "$SERVICE_PATH"
    rm -f "$tmp"
    chmod +x "$SESSION_SCRIPT" 2>/dev/null || true
    systemctl daemon-reload
    log "🧩 systemd-service geïnstalleerd: $SERVICE_PATH"
}

install_sudoers() {
    local user="$1"
    local tmp
    tmp="$(mktemp)"
    sed -e "s#__KIOSK_USER__#$user#g" "$SUDOERS_TEMPLATE" > "$tmp"
    local visudo_bin=""
    if command -v visudo >/dev/null 2>&1; then
        visudo_bin="$(command -v visudo)"
    elif [ -x /usr/sbin/visudo ]; then
        visudo_bin="/usr/sbin/visudo"
    fi
    if [ -n "$visudo_bin" ] && "$visudo_bin" -cf "$tmp" >/dev/null 2>&1; then
        install -D -m 0440 "$tmp" "$SUDOERS_PATH"
        log "🔐 Passwordless sudo geïnstalleerd voor '$user' ($SUDOERS_PATH)."
    else
        err "⚠️  sudoers-validatie mislukte; NOPASSWD-regel NIET geïnstalleerd."
    fi
    rm -f "$tmp"
}

disable_splash() {
    if [ ! -f "$GRUB_FILE" ]; then
        log "ℹ️  Geen $GRUB_FILE; bootloader ongewijzigd."
        return 0
    fi
    [ -f "$GRUB_BACKUP" ] || cp -a "$GRUB_FILE" "$GRUB_BACKUP"
    GRUB_FILE="$GRUB_FILE" python3 - "$GRUB_FILE" <<'PY'
import re, sys
path = sys.argv[1]
with open(path) as fh:
    text = fh.read()

def fix(m):
    toks = [t for t in m.group(2).split() if t != "splash"]
    for needed in ("quiet", "loglevel=0", "vt.global_cursor_default=0", "bgrt_disable"):
        if needed not in toks:
            toks.append(needed)
    return '{}="{}"'.format(m.group(1), " ".join(toks))

new = re.sub(r'(GRUB_CMDLINE_LINUX_DEFAULT)="([^"]*)"', fix, text)
if new != text:
    with open(path, "w") as fh:
        fh.write(new)
PY
    log "🌑 GRUB: 'splash' verwijderd (zwarte boot, geen Ubuntu-logo)."
    update_grub
}

restore_splash() {
    [ -f "$GRUB_FILE" ] || return 0
    if [ -f "$GRUB_BACKUP" ]; then
        cp -a "$GRUB_BACKUP" "$GRUB_FILE"
        rm -f "$GRUB_BACKUP"
        log "🌕 GRUB hersteld uit back-up."
    else
        GRUB_FILE="$GRUB_FILE" python3 - "$GRUB_FILE" <<'PY'
import re, sys
path = sys.argv[1]
with open(path) as fh:
    text = fh.read()

def fix(m):
    toks = m.group(2).split()
    if "splash" not in toks:
        toks.append("splash")
    return '{}="{}"'.format(m.group(1), " ".join(toks))

new = re.sub(r'(GRUB_CMDLINE_LINUX_DEFAULT)="([^"]*)"', fix, text)
if new != text:
    with open(path, "w") as fh:
        fh.write(new)
PY
        log "🌕 GRUB: 'splash' teruggezet."
    fi
    update_grub
}

cmd_status() {
    local svc gdm grub_splash sudoers
    # 'systemctl is-enabled' print de status (enabled/disabled/static/masked/…)
    # naar stdout, óók als het nonzero exit (bv. 'disabled' → exit 1). Daarom
    # stdout opvangen en alleen op 'absent' terugvallen als die echt leeg is —
    # niet via '|| echo absent', want dat plakt 'absent' achter een geldige status.
    svc="$(systemctl is-enabled "$SERVICE_NAME" 2>/dev/null)"; [ -n "$svc" ] || svc="absent"
    gdm="$(systemctl is-enabled "$DISPLAY_MANAGER" 2>/dev/null)"; [ -n "$gdm" ] || gdm="absent"
    if grep -Eq '(^|[" ])splash([ "]|$)' "$GRUB_FILE" 2>/dev/null; then
        grub_splash=present
    else
        grub_splash=absent
    fi
    if [ -f "$SUDOERS_PATH" ]; then sudoers=present; else sudoers=absent; fi
    log "kiosk_service=$svc"
    log "display_manager=$gdm"
    log "grub_splash=$grub_splash"
    log "sudoers=$sudoers"
    if [ "$svc" = "enabled" ]; then log "kiosk=on"; else log "kiosk=off"; fi
}

ensure_cage() {
    if command -v cage >/dev/null 2>&1; then
        return 0
    fi
    log "📦 'cage' (Wayland-kioskcompositor) installeren…"
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -y >/dev/null 2>&1 || true
        if apt-get install -y cage; then
            log "✅ cage geïnstalleerd."
            return 0
        fi
    fi
    err "⚠️  Kon 'cage' niet automatisch installeren. Installeer handmatig: sudo apt-get install -y cage"
    return 1
}

ensure_kiosk_groups() {
    # Met een echte logind-seat regelt uaccess/ACL meestal toegang tot /dev/dri
    # en /dev/input. Lidmaatschap van video/input/render is een robuuste terugval
    # zodat cage altijd GPU + invoer kan openen.
    local user="$1" grp
    for grp in video input render; do
        if getent group "$grp" >/dev/null 2>&1 && ! id -nG "$user" 2>/dev/null | tr ' ' '\n' | grep -qx "$grp"; then
            if usermod -aG "$grp" "$user" 2>/dev/null; then
                log "👥 '$user' toegevoegd aan groep '$grp'."
            fi
        fi
    done
}

cmd_enable() {
    require_root enable
    ensure_cage || true
    local user
    user="$(detect_kiosk_user)"
    log "🖥  Kioskmodus inschakelen voor gebruiker '$user'…"
    install_sudoers "$user"
    install_service "$user"
    ensure_kiosk_groups "$user"
    # Geen display-manager nodig: boot naar multi-user, cage pakt tty1 zelf.
    systemctl set-default multi-user.target >/dev/null 2>&1 || true
    systemctl enable "$SERVICE_NAME" >/dev/null 2>&1 || true
    systemctl disable "$DISPLAY_MANAGER" >/dev/null 2>&1 || true
    # Voorkom dat de getty tty1 terugpakt (naast Conflicts= in de unit).
    systemctl mask getty@tty1.service >/dev/null 2>&1 || true
    log "🚫 $DISPLAY_MANAGER (GNOME-login) uitgeschakeld; getty@tty1 gemaskeerd."
    disable_splash
    log "✅ Kioskmodus ingeschakeld. Herstart om toe te passen."
}

cmd_disable() {
    require_root disable
    log "🖥  Kioskmodus uitschakelen…"
    systemctl disable "$SERVICE_NAME" >/dev/null 2>&1 || true
    systemctl stop "$SERVICE_NAME" >/dev/null 2>&1 || true
    systemctl unmask getty@tty1.service >/dev/null 2>&1 || true
    systemctl enable "$DISPLAY_MANAGER" >/dev/null 2>&1 || true
    systemctl set-default graphical.target >/dev/null 2>&1 || true
    log "✅ $DISPLAY_MANAGER (GNOME-login) weer ingeschakeld; getty@tty1 hersteld."
    restore_splash
    log "✅ Normale desktop hersteld. Herstart om toe te passen."
}

case "${1:-}" in
    enable) cmd_enable ;;
    disable) cmd_disable ;;
    status) cmd_status ;;
    *)
        err "Gebruik: $0 {enable|disable|status}"
        exit 2
        ;;
esac
