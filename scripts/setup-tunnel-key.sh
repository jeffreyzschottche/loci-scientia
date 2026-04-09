#!/usr/bin/env bash
set -euo pipefail

TARGET_USER="aitje"
DEFAULT_KEY_PATH="/home/aitje/.ssh/tunnel_key"
KEY_PATH="${TUNNEL_KEY_PATH:-$DEFAULT_KEY_PATH}"

current_user="$(id -un)"
if [ "$current_user" != "$TARGET_USER" ] && [ "$current_user" != "root" ]; then
    echo "Draai dit script als root of als ${TARGET_USER}." >&2
    exit 1
fi

target_home="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
if [ -z "$target_home" ]; then
    echo "Gebruiker ${TARGET_USER} bestaat niet op dit systeem." >&2
    exit 1
fi

KEY_PATH="${KEY_PATH/#\/home\/$TARGET_USER/$target_home}"
KEY_DIR="$(dirname "$KEY_PATH")"
PUB_PATH="${KEY_PATH}.pub"

run_as_target() {
    if [ "$(id -un)" = "$TARGET_USER" ]; then
        "$@"
        return
    fi
    if command -v sudo >/dev/null 2>&1; then
        sudo -u "$TARGET_USER" "$@"
        return
    fi
    if command -v runuser >/dev/null 2>&1; then
        runuser -u "$TARGET_USER" -- "$@"
        return
    fi
    su -s /bin/sh "$TARGET_USER" -c "$(printf '%q ' "$@")"
}

if [ -e "$KEY_PATH" ] || [ -e "$PUB_PATH" ]; then
    printf "Key bestaat al op %s. Overschrijven? [y/N] " "$KEY_PATH"
    read -r answer
    case "${answer}" in
        y|Y|yes|YES)
            rm -f "$KEY_PATH" "$PUB_PATH"
            ;;
        *)
            echo "Bestaande key behouden."
            exit 0
            ;;
    esac
fi

install -d -m 700 "$KEY_DIR"
if [ "$current_user" = "root" ]; then
    chown "$TARGET_USER:$TARGET_USER" "$KEY_DIR"
fi

run_as_target ssh-keygen -t ed25519 -N "" -f "$KEY_PATH" -C "aitje-support-tunnel"

if [ "$current_user" = "root" ]; then
    chown "$TARGET_USER:$TARGET_USER" "$KEY_PATH" "$PUB_PATH"
fi
chmod 600 "$KEY_PATH"
chmod 644 "$PUB_PATH"

echo
echo "Public key voor de jump server:"
cat "$PUB_PATH"
echo
echo "Voeg deze key toe aan /home/support-tunnel/.ssh/authorized_keys op de VPS met de gewenste restricties."
