#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
action="$(
  python3 - "$payload" <<'PY'
import json
import sys

raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    data = json.loads(raw or "{}")
except json.JSONDecodeError:
    data = {}
print(data.get("action", "") or "")
PY
)"

if [[ -z "${action}" ]]; then
  echo "Missing action in hook payload" >&2
  exit 2
fi

support_state_file="${AITJE_CLOUDFLARED_SUPPORT_STATE_FILE:-/var/lib/aitje/cloudflared/support_ssh_enabled}"
service_name="${AITJE_CLOUDFLARED_SERVICE_NAME:-cloudflared.service}"
metrics_port="${AITJE_CLOUDFLARED_METRICS_PORT:-45231}"
metrics_host="${AITJE_CLOUDFLARED_METRICS_HOST:-127.0.0.1}"
healthcheck_bin="${AITJE_CLOUDFLARED_HEALTHCHECK_BIN:-/usr/local/bin/cloudflared_healthcheck.sh}"
use_sudo="${AITJE_CLOUDFLARED_USE_SUDO:-1}"

if [[ "${use_sudo}" == "1" ]]; then
  sudo_prefix=(sudo -n)
else
  sudo_prefix=()
fi

if [[ "${use_sudo}" == "1" ]] && ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is vereist voor cloudflared beheer" >&2
  exit 127
fi

write_state() {
  local value="$1"
  "${sudo_prefix[@]}" install -d -m 755 "$(dirname "${support_state_file}")"
  printf '%s\n' "${value}" | "${sudo_prefix[@]}" tee "${support_state_file}" >/dev/null
}

restart_service() {
  "${sudo_prefix[@]}" systemctl restart "${service_name}"
}

case "${action}" in
  enable)
    write_state 1
    restart_service
    ;;
  disable)
    write_state 0
    restart_service
    ;;
  *)
    echo "Onbekende actie: ${action}" >&2
    exit 2
    ;;
esac

if [[ -x "${healthcheck_bin}" ]]; then
  "${healthcheck_bin}"
else
  python3 - <<PY
import json
print(json.dumps({
    "status": "unknown",
    "service": "${service_name}",
    "metrics_url": "http://${metrics_host}:${metrics_port}/ready"
}))
PY
fi
