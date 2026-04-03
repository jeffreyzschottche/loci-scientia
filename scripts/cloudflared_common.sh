#!/usr/bin/env bash
set -euo pipefail

CLOUDFLARED_ENV_FILE="${AITJE_CLOUDFLARED_ENV_FILE:-/etc/default/cloudflared}"
CLOUDFLARED_CONFIG_PATH="${AITJE_CLOUDFLARED_CONFIG_PATH:-/etc/cloudflared/config.yml}"
CLOUDFLARED_CREDENTIALS_PATH="${AITJE_CLOUDFLARED_CREDENTIALS_PATH:-/etc/cloudflared/credentials.json}"
CLOUDFLARED_STATE_DIR="${AITJE_CLOUDFLARED_STATE_DIR:-/var/lib/aitje/cloudflared}"
CLOUDFLARED_SUPPORT_STATE_FILE="${AITJE_CLOUDFLARED_SUPPORT_STATE_FILE:-${CLOUDFLARED_STATE_DIR}/support_ssh_enabled}"
CLOUDFLARED_METRICS_PORT="${AITJE_CLOUDFLARED_METRICS_PORT:-45231}"
CLOUDFLARED_METRICS_HOST="${AITJE_CLOUDFLARED_METRICS_HOST:-127.0.0.1}"
CLOUDFLARED_METRICS_URL="http://${CLOUDFLARED_METRICS_HOST}:${CLOUDFLARED_METRICS_PORT}/ready"

load_cloudflared_env() {
  if [[ -f "${CLOUDFLARED_ENV_FILE}" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${CLOUDFLARED_ENV_FILE}"
    set +a
  fi

  CLOUDFLARED_ENV_FILE="${AITJE_CLOUDFLARED_ENV_FILE:-${CLOUDFLARED_ENV_FILE}}"
  CLOUDFLARED_CONFIG_PATH="${AITJE_CLOUDFLARED_CONFIG_PATH:-${CLOUDFLARED_CONFIG_PATH}}"
  CLOUDFLARED_CREDENTIALS_PATH="${AITJE_CLOUDFLARED_CREDENTIALS_PATH:-${CLOUDFLARED_CREDENTIALS_PATH}}"
  CLOUDFLARED_STATE_DIR="${AITJE_CLOUDFLARED_STATE_DIR:-${CLOUDFLARED_STATE_DIR}}"
  CLOUDFLARED_SUPPORT_STATE_FILE="${AITJE_CLOUDFLARED_SUPPORT_STATE_FILE:-${CLOUDFLARED_SUPPORT_STATE_FILE}}"
  CLOUDFLARED_METRICS_PORT="${AITJE_CLOUDFLARED_METRICS_PORT:-${CLOUDFLARED_METRICS_PORT}}"
  CLOUDFLARED_METRICS_HOST="${AITJE_CLOUDFLARED_METRICS_HOST:-${CLOUDFLARED_METRICS_HOST}}"
  CLOUDFLARED_METRICS_URL="http://${CLOUDFLARED_METRICS_HOST}:${CLOUDFLARED_METRICS_PORT}/ready"
}

resolve_device_id() {
  if [[ -n "${AITJE_DEVICE_ID:-}" ]]; then
    printf '%s\n' "${AITJE_DEVICE_ID}"
    return
  fi
  if [[ -n "${DEVICE_HOSTNAME:-}" ]]; then
    printf '%s\n' "${DEVICE_HOSTNAME}"
    return
  fi
  if [[ -n "${DEVICE_NAME_PREFIX:-}" && -n "${DEVICE_NUMBER:-}" ]]; then
    printf '%s-%s\n' "${DEVICE_NAME_PREFIX}" "${DEVICE_NUMBER}"
    return
  fi
  printf 'aitje-device\n'
}

resolve_domain() {
  printf '%s\n' "${AITJE_DOMAIN:-aitje.nl}"
}

decode_tunnel_token() {
  if [[ -z "${AITJE_TUNNEL_TOKEN:-}" ]]; then
    echo "AITJE_TUNNEL_TOKEN ontbreekt" >&2
    return 1
  fi

  python3 - "${AITJE_TUNNEL_TOKEN}" <<'PY'
import base64
import json
import sys

token = sys.argv[1]
parts = token.split(".")
if len(parts) != 3:
    raise SystemExit("AITJE_TUNNEL_TOKEN is geen JWT-token")

payload = parts[1]
payload += "=" * (-len(payload) % 4)
try:
    data = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
except Exception as exc:  # noqa: BLE001
    raise SystemExit(f"Kon tunnel token niet decoderen: {exc}") from exc

tunnel_id = data.get("t") or data.get("TunnelID") or data.get("tunnel_id")
secret = data.get("s") or data.get("TunnelSecret") or data.get("tunnel_secret")
account_tag = data.get("a") or data.get("AccountTag") or data.get("account_tag")

if not tunnel_id or not secret or not account_tag:
    raise SystemExit("Tunnel token mist tunnel/account claims")

print(json.dumps({
    "TunnelID": tunnel_id,
    "TunnelSecret": secret,
    "AccountTag": account_tag,
}))
PY
}

extract_tunnel_id() {
  decode_tunnel_token | python3 -c 'import json,sys; print(json.load(sys.stdin)["TunnelID"])'
}

support_ssh_enabled() {
  if [[ -f "${CLOUDFLARED_SUPPORT_STATE_FILE}" ]]; then
    local raw
    raw="$(tr -d '[:space:]' < "${CLOUDFLARED_SUPPORT_STATE_FILE}" 2>/dev/null || true)"
    if [[ "${raw}" == "1" ]]; then
      printf '1\n'
      return
    fi
  fi
  printf '%s\n' "${AITJE_SUPPORT_SSH_DEFAULT:-0}"
}

ensure_cloudflared_layout() {
  mkdir -p "$(dirname "${CLOUDFLARED_CONFIG_PATH}")"
  mkdir -p "$(dirname "${CLOUDFLARED_CREDENTIALS_PATH}")"
  mkdir -p "${CLOUDFLARED_STATE_DIR}"
}

render_cloudflared_credentials() {
  local token_payload
  token_payload="$(decode_tunnel_token)"
  printf '%s\n' "${token_payload}" > "${CLOUDFLARED_CREDENTIALS_PATH}"
  chmod 600 "${CLOUDFLARED_CREDENTIALS_PATH}"
}

render_cloudflared_config() {
  local tunnel_id
  local device_id
  local domain
  local ssh_service
  tunnel_id="$(extract_tunnel_id)"
  device_id="$(resolve_device_id)"
  domain="$(resolve_domain)"
  ssh_service="http_status:404"
  if [[ "$(support_ssh_enabled)" == "1" ]]; then
    ssh_service="ssh://localhost:22"
  fi

  cat > "${CLOUDFLARED_CONFIG_PATH}" <<EOF
tunnel: ${tunnel_id}
credentials-file: ${CLOUDFLARED_CREDENTIALS_PATH}

ingress:
  - hostname: ssh-${device_id}.${domain}
    service: ${ssh_service}
  - hostname: ${device_id}.${domain}
    service: http://localhost:8000
  - service: http_status:404
EOF
  chmod 600 "${CLOUDFLARED_CONFIG_PATH}"
}

render_cloudflared_runtime() {
  ensure_cloudflared_layout
  render_cloudflared_credentials
  render_cloudflared_config
}
