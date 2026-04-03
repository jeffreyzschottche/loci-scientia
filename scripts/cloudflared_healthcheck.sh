#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/cloudflared_common.sh"

load_cloudflared_env

config_exists=0
credentials_exists=0
service_active=0
ready=0
tunnel_id=""
error_message=""

if [[ -f "${CLOUDFLARED_CONFIG_PATH}" ]]; then
  config_exists=1
  tunnel_id="$(awk '/^tunnel:/{print $2; exit}' "${CLOUDFLARED_CONFIG_PATH}" 2>/dev/null || true)"
fi

if [[ -f "${CLOUDFLARED_CREDENTIALS_PATH}" ]]; then
  credentials_exists=1
fi

if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet cloudflared.service; then
  service_active=1
fi

if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 3 "${CLOUDFLARED_METRICS_URL}" >/dev/null 2>&1; then
    ready=1
  elif [[ "${service_active}" == "1" ]]; then
    error_message="metrics endpoint niet ready"
  fi
elif [[ "${service_active}" == "1" ]]; then
  error_message="curl ontbreekt voor health check"
fi

status="disabled"
if [[ "${config_exists}" == "1" || "${credentials_exists}" == "1" ]]; then
  status="degraded"
fi
if [[ "${service_active}" == "1" && "${ready}" == "1" ]]; then
  status="connected"
elif [[ "${service_active}" == "0" && ( "${config_exists}" == "1" || "${credentials_exists}" == "1" ) ]]; then
  status="stopped"
fi

python3 - <<PY
import json

payload = {
    "status": "${status}",
    "config_exists": ${config_exists},
    "credentials_exists": ${credentials_exists},
    "service_active": ${service_active},
    "ready": ${ready},
    "ssh_enabled": $(support_ssh_enabled),
    "device_id": "$(resolve_device_id)",
    "domain": "$(resolve_domain)",
    "tunnel_id": "${tunnel_id}",
    "metrics_url": "${CLOUDFLARED_METRICS_URL}",
    "error": "${error_message}",
}
print(json.dumps(payload))
PY
