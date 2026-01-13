#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
action="$(
  python3 - <<'PY'
import json
import sys

try:
    data = json.loads(sys.stdin.read() or "{}")
except json.JSONDecodeError:
    data = {}
print(data.get("action", "") or "")
PY
)"

if [[ -z "${action}" ]]; then
  echo "Missing action in hook payload" >&2
  exit 2
fi

tailscale_bin="${TAILSCALE_BIN:-tailscale}"
if [[ "${TAILSCALE_USE_SUDO:-0}" == "1" ]]; then
  run_cmd=(sudo -n "${tailscale_bin}")
else
  run_cmd=("${tailscale_bin}")
fi

if ! command -v "${tailscale_bin}" >/dev/null 2>&1; then
  echo "tailscale binary not found (set TAILSCALE_BIN if needed)" >&2
  exit 127
fi

auth_key="${TAILSCALE_AUTHKEY:-}"
hostname="${TAILSCALE_HOSTNAME:-}"
tags="${TAILSCALE_TAGS:-}"
login_server="${TAILSCALE_LOGIN_SERVER:-}"
enable_ssh="${TAILSCALE_ENABLE_SSH:-1}"
ephemeral="${TAILSCALE_EPHEMERAL:-0}"
logout_on_disable="${TAILSCALE_LOGOUT_ON_DISABLE:-0}"

extra_args=()
if [[ -n "${TAILSCALE_EXTRA_ARGS:-}" ]]; then
  read -r -a extra_args <<<"${TAILSCALE_EXTRA_ARGS}"
fi

case "${action}" in
  enable)
    if [[ -z "${auth_key}" && "${TAILSCALE_ALLOW_NO_AUTHKEY:-0}" != "1" ]]; then
      echo "TAILSCALE_AUTHKEY ontbreekt (of zet TAILSCALE_ALLOW_NO_AUTHKEY=1)" >&2
      exit 3
    fi
    args=(up)
    if [[ -n "${auth_key}" ]]; then
      args+=(--authkey "${auth_key}" --reset)
    fi
    if [[ -n "${hostname}" ]]; then
      args+=(--hostname "${hostname}")
    fi
    if [[ -n "${tags}" ]]; then
      args+=(--advertise-tags "${tags}")
    fi
    if [[ -n "${login_server}" ]]; then
      args+=(--login-server "${login_server}")
    fi
    if [[ "${enable_ssh}" != "0" ]]; then
      args+=(--ssh)
    fi
    if [[ "${ephemeral}" == "1" ]]; then
      args+=(--ephemeral)
    fi
    "${run_cmd[@]}" "${args[@]}" "${extra_args[@]}"
    ;;
  disable)
    "${run_cmd[@]}" down
    if [[ "${logout_on_disable}" == "1" ]]; then
      "${run_cmd[@]}" logout
    fi
    ;;
  *)
    echo "Onbekende actie: ${action}" >&2
    exit 2
    ;;
esac
