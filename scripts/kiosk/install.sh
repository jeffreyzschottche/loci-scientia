#!/usr/bin/env bash
# install.sh — set up an AITJE device for kiosk mode.
#
# Idempotent: re-running the script does not duplicate state. Defaults assume
# Ubuntu 25.10/26.04 with GDM3 as display manager.
#
# Usage: sudo bash scripts/kiosk/install.sh
#
# State after install: kiosk mode is *disabled*. Toggle from the AITJE UI or
# run `sudo aitje-kiosk-toggle enable --reboot` to switch the device over.
set -euo pipefail

# ---------------------------------------------------------------------------
# Configurable paths (override via environment if needed)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

AITJE_PROJECT_ROOT="${AITJE_PROJECT_ROOT:-${DEFAULT_PROJECT_ROOT}}"
AITJE_USER="${AITJE_USER:-aitje}"
AITJE_USER_SHELL="${AITJE_USER_SHELL:-/bin/bash}"
AITJE_STATE_DIR="${AITJE_STATE_DIR:-/etc/aitje}"
AITJE_STATE_FILE="${AITJE_STATE_FILE:-${AITJE_STATE_DIR}/kiosk-mode}"
AITJE_LOG_FILE="${AITJE_LOG_FILE:-/var/log/aitje-kiosk-toggle.log}"
AITJE_TOGGLE_BIN="${AITJE_TOGGLE_BIN:-/usr/local/bin/aitje-kiosk-toggle}"
AITJE_PLYMOUTH_THEME="${AITJE_PLYMOUTH_THEME:-aitje}"
AITJE_PLYMOUTH_FALLBACK="${AITJE_PLYMOUTH_FALLBACK:-spinner}"
AITJE_PLYMOUTH_THEME_DIR="${AITJE_PLYMOUTH_THEME_DIR:-/usr/share/plymouth/themes/${AITJE_PLYMOUTH_THEME}}"

UNIT_TEMPLATE="${SCRIPT_DIR}/../../systemd/aitje-kiosk.service"
UNIT_DEST="/etc/systemd/system/aitje-kiosk.service"
SUDOERS_TEMPLATE="${SCRIPT_DIR}/../../sudoers/aitje-kiosk-toggle"
SUDOERS_DEST="/etc/sudoers.d/aitje-kiosk-toggle"
TOGGLE_TEMPLATE="${SCRIPT_DIR}/aitje-kiosk-toggle"
GRUB_FILE="/etc/default/grub"
GDM_CONF="/etc/gdm3/custom.conf"
PLYMOUTH_REPO_DIR="${SCRIPT_DIR}/../../assets/plymouth/${AITJE_PLYMOUTH_THEME}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() { printf '\n\033[1;36m[kiosk-install]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[kiosk-install]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[kiosk-install]\033[0m %s\n' "$*" >&2; exit 1; }

require_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        fail "Run met sudo: sudo bash $0"
    fi
}

ensure_user() {
    if id -u "$AITJE_USER" >/dev/null 2>&1; then
        log "User '${AITJE_USER}' bestaat al"
    else
        log "User '${AITJE_USER}' aanmaken"
        useradd --create-home --shell "$AITJE_USER_SHELL" "$AITJE_USER"
    fi
    AITJE_UID="$(id -u "$AITJE_USER")"
    AITJE_GID="$(id -g "$AITJE_USER")"
}

apt_install() {
    local pkgs=("$@")
    local missing=()
    for pkg in "${pkgs[@]}"; do
        if ! dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "ok installed"; then
            missing+=("$pkg")
        fi
    done
    if [[ ${#missing[@]} -eq 0 ]]; then
        log "Pakketten al geïnstalleerd: ${pkgs[*]}"
        return
    fi
    log "Pakketten installeren: ${missing[*]}"
    DEBIAN_FRONTEND=noninteractive apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing[@]}"
}

# Replace or append a KEY=VALUE line in a shell-style config file.
set_kv() {
    local file="$1" key="$2" value="$3"
    if grep -qE "^${key}=" "$file" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
        printf '%s=%s\n' "$key" "$value" >>"$file"
    fi
}

# Set a key under a given INI section. Creates the section if missing.
set_ini_kv() {
    local file="$1" section="$2" key="$3" value="$4"
    if [[ ! -f "$file" ]]; then
        printf '[%s]\n%s=%s\n' "$section" "$key" "$value" >"$file"
        return
    fi
    if ! grep -q "^\[${section}\]" "$file"; then
        printf '\n[%s]\n%s=%s\n' "$section" "$key" "$value" >>"$file"
        return
    fi
    python3 - "$file" "$section" "$key" "$value" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
section, key, value = sys.argv[2], sys.argv[3], sys.argv[4]
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

target = f"[{section}]"
out: list[str] = []
in_section = False
section_done = False
key_set = False
i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    if not in_section and stripped == target:
        in_section = True
        out.append(line)
        i += 1
        continue
    if in_section and stripped.startswith("[") and stripped.endswith("]"):
        if not key_set:
            out.append(f"{key}={value}\n")
            key_set = True
        section_done = True
        in_section = False
        out.append(line)
        i += 1
        continue
    if in_section and stripped.startswith(f"{key}="):
        out.append(f"{key}={value}\n")
        key_set = True
        i += 1
        continue
    out.append(line)
    i += 1

if in_section and not key_set:
    if out and not out[-1].endswith("\n"):
        out[-1] += "\n"
    out.append(f"{key}={value}\n")

path.write_text("".join(out), encoding="utf-8")
PY
}

# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

install_packages() {
    apt_install cage qt6-wayland plymouth plymouth-themes
}

configure_grub() {
    if [[ ! -f "$GRUB_FILE" ]]; then
        warn "${GRUB_FILE} ontbreekt — GRUB-config overgeslagen"
        return
    fi
    log "GRUB stil configureren"
    cp -a "$GRUB_FILE" "${GRUB_FILE}.aitje.bak.$(date +%s)" 2>/dev/null || true
    set_kv "$GRUB_FILE" "GRUB_TIMEOUT" "0"
    set_kv "$GRUB_FILE" "GRUB_TIMEOUT_STYLE" "hidden"
    set_kv "$GRUB_FILE" "GRUB_CMDLINE_LINUX_DEFAULT" '"quiet splash loglevel=0 vt.global_cursor_default=0"'
    update-grub
}

configure_plymouth() {
    log "Plymouth-thema instellen"
    if [[ -d "$PLYMOUTH_REPO_DIR" ]]; then
        log "Custom AITJE-thema kopieren naar ${AITJE_PLYMOUTH_THEME_DIR}"
        mkdir -p "$AITJE_PLYMOUTH_THEME_DIR"
        cp -a "${PLYMOUTH_REPO_DIR}/." "$AITJE_PLYMOUTH_THEME_DIR/"
    fi

    local theme="$AITJE_PLYMOUTH_FALLBACK"
    if [[ -f "${AITJE_PLYMOUTH_THEME_DIR}/${AITJE_PLYMOUTH_THEME}.plymouth" ]]; then
        theme="$AITJE_PLYMOUTH_THEME"
    fi

    if command -v plymouth-set-default-theme >/dev/null 2>&1; then
        plymouth-set-default-theme -R "$theme"
    else
        warn "plymouth-set-default-theme ontbreekt — plymouth-config overgeslagen"
    fi
}

configure_gdm() {
    log "GDM3 auto-login configureren voor user '${AITJE_USER}'"
    install -d -m 0755 "$(dirname "$GDM_CONF")"
    set_ini_kv "$GDM_CONF" "daemon" "AutomaticLoginEnable" "true"
    set_ini_kv "$GDM_CONF" "daemon" "AutomaticLogin" "$AITJE_USER"
}

install_systemd_unit() {
    [[ -f "$UNIT_TEMPLATE" ]] || fail "Unit template ontbreekt: ${UNIT_TEMPLATE}"
    log "Systemd unit installeren in ${UNIT_DEST}"
    sed \
        -e "s|__PROJECT_ROOT__|${AITJE_PROJECT_ROOT}|g" \
        -e "s|__AITJE_USER__|${AITJE_USER}|g" \
        -e "s|__AITJE_UID__|${AITJE_UID}|g" \
        "$UNIT_TEMPLATE" >"$UNIT_DEST"
    chmod 0644 "$UNIT_DEST"
    systemctl daemon-reload
}

install_toggle_script() {
    [[ -f "$TOGGLE_TEMPLATE" ]] || fail "Toggle template ontbreekt: ${TOGGLE_TEMPLATE}"
    log "Toggle script installeren naar ${AITJE_TOGGLE_BIN}"
    install -m 0755 "$TOGGLE_TEMPLATE" "$AITJE_TOGGLE_BIN"
}

install_sudoers() {
    [[ -f "$SUDOERS_TEMPLATE" ]] || fail "Sudoers template ontbreekt: ${SUDOERS_TEMPLATE}"
    log "Sudoers drop-in installeren in ${SUDOERS_DEST}"
    install -m 0440 "$SUDOERS_TEMPLATE" "$SUDOERS_DEST"
    if ! visudo -c -f "$SUDOERS_DEST" >/dev/null; then
        rm -f "$SUDOERS_DEST"
        fail "visudo validatie faalde voor ${SUDOERS_DEST}"
    fi
}

initialize_state() {
    install -d -m 0755 "$AITJE_STATE_DIR"
    if [[ -f "$AITJE_STATE_FILE" ]]; then
        log "State file bestaat al: ${AITJE_STATE_FILE}"
    else
        log "State file aanmaken: ${AITJE_STATE_FILE} (default: disabled)"
        printf 'disabled\n' >"$AITJE_STATE_FILE"
        chmod 0644 "$AITJE_STATE_FILE"
    fi
    install -d -m 0755 "$(dirname "$AITJE_LOG_FILE")"
    touch "$AITJE_LOG_FILE"
    chmod 0644 "$AITJE_LOG_FILE"
}

print_summary() {
    cat <<EOF

==========================================================================
AITJE kiosk-mode installatie afgerond.

Wat is geconfigureerd:
  - User           : ${AITJE_USER} (uid ${AITJE_UID})
  - Project root   : ${AITJE_PROJECT_ROOT}
  - Systemd unit   : ${UNIT_DEST}
  - Toggle script  : ${AITJE_TOGGLE_BIN}
  - Sudoers        : ${SUDOERS_DEST}
  - State          : ${AITJE_STATE_FILE} ($(cat "$AITJE_STATE_FILE"))
  - Log            : ${AITJE_LOG_FILE}

Kiosk mode staat standaard UIT — gdm3 blijft actief tot je toggled.

Inschakelen vanuit de UI: Instellingen → Systeem → Kiosk mode.
Inschakelen via CLI:
    sudo aitje-kiosk-toggle enable --reboot

Recovery (als de UI vastloopt):
    1. Druk Ctrl+Alt+F2 voor een tty
    2. Login als ${AITJE_USER}
    3. sudo aitje-kiosk-toggle disable --reboot

==========================================================================
EOF
}

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
require_root
log "Project root: ${AITJE_PROJECT_ROOT}"

ensure_user
install_packages
configure_grub
configure_plymouth
configure_gdm
install_toggle_script
install_sudoers
install_systemd_unit
initialize_state
print_summary
