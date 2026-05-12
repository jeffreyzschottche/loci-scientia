#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_TEMPLATE="$PROJECT_ROOT/systemd/aitje-backend.service"
SERVICE_PATH="/etc/systemd/system/aitje-backend.service"
TMP_SERVICE="$(mktemp)"

cleanup() {
    rm -f "$TMP_SERVICE"
}
trap cleanup EXIT

sed "s#__PROJECT_ROOT__#$PROJECT_ROOT#g" "$SERVICE_TEMPLATE" >"$TMP_SERVICE"

sudo install -D -m 0644 "$TMP_SERVICE" "$SERVICE_PATH"
sudo systemctl daemon-reload
sudo systemctl enable --now aitje-backend.service
sudo systemctl status aitje-backend.service --no-pager -l
