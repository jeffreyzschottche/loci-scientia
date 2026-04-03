#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/cloudflared_common.sh"

load_cloudflared_env
render_cloudflared_runtime

if [[ "${1:-}" == "--render-only" ]]; then
  exit 0
fi

exec cloudflared \
  --config "${CLOUDFLARED_CONFIG_PATH}" \
  --metrics "${CLOUDFLARED_METRICS_HOST}:${CLOUDFLARED_METRICS_PORT}" \
  tunnel run
