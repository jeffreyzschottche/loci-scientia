#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_TEMPLATE="$PROJECT_ROOT/systemd/aitje-backend.user.service"
SERVICE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SERVICE_PATH="$SERVICE_DIR/aitje-backend.service"

mkdir -p "$SERVICE_DIR"
sed "s#__PROJECT_ROOT__#$PROJECT_ROOT#g" "$SERVICE_TEMPLATE" >"$SERVICE_PATH"

systemctl --user daemon-reload
systemctl --user enable --now aitje-backend.service
systemctl --user status aitje-backend.service --no-pager -l
