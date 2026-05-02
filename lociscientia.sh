#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

if [ -f ".env" ]; then
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
fi

DEVICE_NAME_PREFIX="${DEVICE_NAME_PREFIX:-aitje}"
DEVICE_NUMBER="${DEVICE_NUMBER:-1}"
if [ -n "${DEVICE_HOSTNAME:-}" ]; then
    DEVICE_HOSTNAME="${DEVICE_HOSTNAME}"
else
    DEVICE_HOSTNAME="${DEVICE_NAME_PREFIX}-${DEVICE_NUMBER}"
fi
DEVICE_MDNS="${DEVICE_MDNS:-${DEVICE_HOSTNAME}.local}"
ORIGINAL_HOSTNAME=""
ORIGINAL_LOCAL_HOSTNAME=""
ORIGINAL_COMPUTER_NAME=""
SUDO_KEEPALIVE_PID=""
HAVE_SUDO=0

ensure_sudo_session() {
    if ! command -v sudo >/dev/null 2>&1; then
        return 1
    fi
    if sudo -n true 2>/dev/null; then
        :
    else
        echo "🔐 sudo-toegang vereist voor hostname/mDNS-aanpassingen."
        sudo -v || return 1
    fi
    if [ -z "${SUDO_KEEPALIVE_PID:-}" ]; then
        (
            while true; do
                sleep 60
                sudo -n true >/dev/null 2>&1 || exit
            done
        ) &
        SUDO_KEEPALIVE_PID=$!
    fi
    HAVE_SUDO=1
    return 0
}

_trim() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf "%s" "$value"
}

_run_ollama() {
    env -u OLLAMA_MODELS ollama "$@"
}

_stop_ollama() {
    local pids=""
    if command -v pgrep >/dev/null 2>&1; then
        pids="$(pgrep -x ollama || true)"
    fi
    if [ -z "$pids" ]; then
        return 0
    fi
    if command -v pkill >/dev/null 2>&1; then
        if [ "$HAVE_SUDO" -eq 1 ]; then
            sudo pkill -x ollama >/dev/null 2>&1 || true
        else
            pkill -x ollama >/dev/null 2>&1 || true
        fi
    else
        for pid in $pids; do
            if [ "$HAVE_SUDO" -eq 1 ]; then
                sudo kill "$pid" >/dev/null 2>&1 || true
            else
                kill "$pid" >/dev/null 2>&1 || true
            fi
        done
    fi
    sleep 2
    if command -v pgrep >/dev/null 2>&1 && pgrep -x ollama >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

_wait_for_ollama() {
    local attempt
    for attempt in {1..30}; do
        if _run_ollama list >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

running_kernel_has_headers() {
    local kernel
    kernel="$(uname -r)"
    [ -d "/usr/src/linux-headers-$kernel" ]
}

report_gpu_runtime_status() {
    if command -v nvidia-smi >/dev/null 2>&1; then
        if nvidia-smi >/dev/null 2>&1; then
            echo "✅ NVIDIA driver actief"
            return 0
        fi
    fi

    if lspci 2>/dev/null | grep -qi 'NVIDIA'; then
        echo "⚠️  NVIDIA GPU gedetecteerd, maar driver/runtime is niet actief."
        if ! running_kernel_has_headers; then
            echo "⚠️  Kernel headers voor $(uname -r) ontbreken; NVIDIA DKMS kan daardoor niet bouwen."
        fi
    fi
    return 1
}

detect_platform() {
    local uname_s
    uname_s="$(uname -s 2>/dev/null || echo unknown)"
    case "$uname_s" in
        Linux*)
            if [ -f /etc/nv_tegra_release ]; then
                DEVICE_PLATFORM="jetson"
            else
                DEVICE_PLATFORM="linux"
            fi
            ;;
        Darwin*)
            DEVICE_PLATFORM="macos"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            DEVICE_PLATFORM="windows"
            ;;
        *)
            DEVICE_PLATFORM="unknown"
            ;;
    esac
}

ensure_mdns_support() {
    case "$DEVICE_PLATFORM" in
        linux|jetson)
            if [ "$HAVE_SUDO" -ne 1 ]; then
                echo "⚠️  Geen sudo, avahi-daemon wordt niet automatisch geïnstalleerd."
                return
            fi
            if ! command -v apt-get >/dev/null 2>&1; then
                echo "⚠️  apt-get niet beschikbaar, sla avahi-daemon installatie over."
                return
            fi
            if dpkg -s avahi-daemon >/dev/null 2>&1; then
                echo "✅ avahi-daemon is al geïnstalleerd"
            else
                echo "📦 avahi-daemon installeren..."
                sudo apt-get update -y
                sudo apt-get install -y avahi-daemon
            fi
            if command -v systemctl >/dev/null 2>&1; then
                sudo systemctl enable avahi-daemon >/dev/null 2>&1 || true
                sudo systemctl restart avahi-daemon >/dev/null 2>&1 || true
            fi
            ;;
        macos)
            echo "✅ macOS Bonjour is standaard beschikbaar voor mDNS."
            ;;
        windows)
            echo "⚠️  Windows detectie: installeer Bonjour/MDNS responder handmatig (Apple Bonjour of dnssd)."
            ;;
        *)
            echo "⚠️  Onbekend platform, sla mDNS setup over."
            ;;
    esac
}

ensure_remote_support_dependencies() {
    case "$DEVICE_PLATFORM" in
        linux|jetson)
            ;;
        *)
            return 0
            ;;
    esac
    if [ "$HAVE_SUDO" -ne 1 ] && [ "$(id -u)" -ne 0 ]; then
        echo "⚠️  Geen sudo/root; autossh en openssh-client worden niet automatisch geïnstalleerd."
        return 0
    fi
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "⚠️  apt-get niet beschikbaar, sla autossh/openssh-client installatie over."
        return 0
    fi
    local missing_packages=()
    local package=""
    for package in autossh openssh-client openssh-server; do
        if ! dpkg -s "$package" >/dev/null 2>&1; then
            missing_packages+=("$package")
        fi
    done
    if [ "${#missing_packages[@]}" -eq 0 ]; then
        echo "✅ Remote support dependencies zijn al geïnstalleerd"
    else
        echo "📦 Remote support dependencies installeren: ${missing_packages[*]}"
        if [ "$(id -u)" -eq 0 ]; then
            apt-get install -y "${missing_packages[@]}"
        else
            sudo apt-get install -y "${missing_packages[@]}"
        fi
    fi

    if command -v systemctl >/dev/null 2>&1 && dpkg -s openssh-server >/dev/null 2>&1; then
        if [ "$(id -u)" -eq 0 ]; then
            systemctl enable ssh >/dev/null 2>&1 || true
            systemctl restart ssh >/dev/null 2>&1 || true
        else
            sudo systemctl enable ssh >/dev/null 2>&1 || true
            sudo systemctl restart ssh >/dev/null 2>&1 || true
        fi
    fi
}

ensure_remote_support_service() {
    case "$DEVICE_PLATFORM" in
        linux|jetson)
            ;;
        *)
            return 0
            ;;
    esac

    if [ "$HAVE_SUDO" -ne 1 ] && [ "$(id -u)" -ne 0 ]; then
        echo "⚠️  Geen sudo/root; aitje-tunnel systemd service wordt niet automatisch geïnstalleerd."
        return 0
    fi

    local service_template="$PROJECT_ROOT/systemd/aitje-tunnel.service"
    local sudoers_template="$PROJECT_ROOT/sudoers/aitje-tunnel"
    local install_dir="/etc/systemd/system"
    local install_path="$install_dir/aitje-tunnel.service"
    local sudoers_dir="/etc/sudoers.d"
    local sudoers_path="$sudoers_dir/aitje-tunnel"
    local tmp_service
    tmp_service="$(mktemp)"

    local visudo_bin=""
    if command -v visudo >/dev/null 2>&1; then
        visudo_bin="$(command -v visudo)"
    elif [ -x /usr/sbin/visudo ]; then
        visudo_bin="/usr/sbin/visudo"
    elif [ -x /sbin/visudo ]; then
        visudo_bin="/sbin/visudo"
    else
        echo "⚠️  visudo niet gevonden; sudoers-regel wordt niet automatisch gevalideerd/geïnstalleerd."
    fi

    sed "s#__PROJECT_ROOT__#$PROJECT_ROOT#g" "$service_template" >"$tmp_service"

    local service_changed=0
    if [ ! -f "$install_path" ] || ! cmp -s "$tmp_service" "$install_path"; then
        echo "🔧 aitje-tunnel systemd service installeren/updaten..."
        if [ "$(id -u)" -eq 0 ]; then
            install -D -m 0644 "$tmp_service" "$install_path"
        else
            sudo install -D -m 0644 "$tmp_service" "$install_path"
        fi
        service_changed=1
    else
        echo "✅ aitje-tunnel systemd service is al up-to-date"
    fi
    rm -f "$tmp_service"

    local sudoers_changed=0
    if [ -d "$sudoers_dir" ] && [ -n "$visudo_bin" ]; then
        if [ ! -f "$sudoers_path" ] || ! cmp -s "$sudoers_template" "$sudoers_path"; then
            echo "🔧 sudoers-regel voor aitje-tunnel installeren/updaten..."
            local tmp_sudoers
            tmp_sudoers="$(mktemp)"
            cp "$sudoers_template" "$tmp_sudoers"
            if [ "$(id -u)" -eq 0 ]; then
                "$visudo_bin" -cf "$tmp_sudoers" >/dev/null
                install -D -m 0440 "$tmp_sudoers" "$sudoers_path"
            else
                "$visudo_bin" -cf "$tmp_sudoers" >/dev/null
                sudo install -D -m 0440 "$tmp_sudoers" "$sudoers_path"
            fi
            rm -f "$tmp_sudoers"
            sudoers_changed=1
        else
            echo "✅ sudoers-regel voor aitje-tunnel is al up-to-date"
        fi
    elif [ ! -d "$sudoers_dir" ]; then
        echo "⚠️  /etc/sudoers.d ontbreekt; sudoers-regel niet geïnstalleerd."
    fi

    if [ "$service_changed" -eq 1 ] || [ "$sudoers_changed" -eq 1 ]; then
        echo "♻️  systemd configuratie herladen..."
        if [ "$(id -u)" -eq 0 ]; then
            systemctl daemon-reload
        else
            sudo systemctl daemon-reload
        fi
    fi
}

ensure_active_wifi_profile_persistence() {
    case "$DEVICE_PLATFORM" in
        linux|jetson)
            ;;
        *)
            return 0
            ;;
    esac

    if [ "${ENABLE_WIFI_PERSISTENCE_FIX:-1}" = "0" ]; then
        echo "ℹ️  WiFi-profiel normalisatie is uitgeschakeld via ENABLE_WIFI_PERSISTENCE_FIX=0"
        return 0
    fi

    if [ "$HAVE_SUDO" -ne 1 ] && [ "$(id -u)" -ne 0 ]; then
        echo "⚠️  Geen sudo/root; actieve WiFi-profielen worden niet automatisch genormaliseerd."
        return 0
    fi

    if ! command -v nmcli >/dev/null 2>&1; then
        echo "⚠️  nmcli niet beschikbaar, sla WiFi-profiel normalisatie over."
        return 0
    fi

    local -a nmcli_cmd=()
    local -a active_wifi_connections=()
    local connection=""
    local profile_file=""
    local psk=""
    local update_result=0
    if [ "$(id -u)" -eq 0 ]; then
        nmcli_cmd=(nmcli)
    else
        nmcli_cmd=(sudo nmcli)
    fi

    mapfile -t active_wifi_connections < <(
        "${nmcli_cmd[@]}" -t -f NAME,TYPE connection show --active 2>/dev/null \
        | awk -F: '$2=="802-11-wireless"{print $1}'
    )

    if [ "${#active_wifi_connections[@]}" -eq 0 ]; then
        echo "ℹ️  Geen actieve WiFi-verbinding gevonden om te normaliseren."
        return 0
    fi

    for connection in "${active_wifi_connections[@]}"; do
        [ -n "$connection" ] || continue
        echo "📶 Actief WiFi-profiel normaliseren: ${connection}"

        psk="$("${nmcli_cmd[@]}" -s -g 802-11-wireless-security.psk connection show "$connection" 2>/dev/null || true)"
        profile_file="$("${nmcli_cmd[@]}" -s -g connection.filename connection show "$connection" 2>/dev/null || true)"

        if [ -n "$psk" ]; then
            if "${nmcli_cmd[@]}" connection modify "$connection" \
                connection.permissions "" \
                connection.autoconnect yes \
                802-11-wireless-security.psk-flags 0 \
                802-11-wireless-security.psk "$psk" >/dev/null 2>&1; then
                :
            else
                update_result=1
            fi
        else
            if "${nmcli_cmd[@]}" connection modify "$connection" \
                connection.permissions "" \
                connection.autoconnect yes >/dev/null 2>&1; then
                :
            else
                update_result=1
            fi
        fi

        if [ "$update_result" -ne 0 ]; then
            echo "⚠️  Kon WiFi-profiel ${connection} niet volledig bijwerken."
            update_result=0
            continue
        fi

        if [[ "$profile_file" == /run/NetworkManager/system-connections/netplan-* ]]; then
            echo "✅ WiFi-profiel ${connection} is live genormaliseerd (netplan-beheerd runtime-profiel)."
        else
            echo "✅ WiFi-profiel ${connection} is persistent gemaakt voor NetworkManager."
        fi
    done
}

configure_hostname() {
    desired="${DEVICE_HOSTNAME}"
    case "$DEVICE_PLATFORM" in
        linux|jetson)
            if [ "$HAVE_SUDO" -ne 1 ]; then
                echo "⚠️  Geen sudo, hostname blijft ongewijzigd."
                return
            fi
            if ! command -v hostnamectl >/dev/null 2>&1; then
                echo "⚠️  hostnamectl niet beschikbaar, huidige hostname blijft ongewijzigd."
                return
            fi
            current="$(hostnamectl --static 2>/dev/null || hostname)"
            if [ "$current" != "$desired" ]; then
                ORIGINAL_HOSTNAME="${ORIGINAL_HOSTNAME:-$current}"
                echo "🔧 Hostname instellen op ${desired}"
                sudo hostnamectl set-hostname "$desired"
            else
                echo "✅ Hostname staat al op ${desired}"
            fi
            ;;
        macos)
            if [ "$HAVE_SUDO" -ne 1 ]; then
                echo "⚠️  Geen sudo, hostname blijft ongewijzigd."
                return
            fi
            if ! command -v scutil >/dev/null 2>&1; then
                echo "⚠️  scutil niet beschikbaar, hostname kan niet automatisch worden ingesteld."
                return
            fi
            current="$(scutil --get HostName 2>/dev/null || hostname)"
            if [ "$current" != "$desired" ]; then
                ORIGINAL_HOSTNAME="${ORIGINAL_HOSTNAME:-$current}"
                echo "🔧 macOS hostname instellen op ${desired}"
                sudo scutil --set HostName "$desired"
            else
                echo "✅ Hostname staat al op ${desired}"
            fi
            local_current="$(scutil --get LocalHostName 2>/dev/null || echo "")"
            if [ "$local_current" != "$desired" ]; then
                ORIGINAL_LOCAL_HOSTNAME="${ORIGINAL_LOCAL_HOSTNAME:-$local_current}"
                sudo scutil --set LocalHostName "$desired"
            fi
            computer_current="$(scutil --get ComputerName 2>/dev/null || echo "")"
            if [ "$computer_current" != "$desired" ]; then
                ORIGINAL_COMPUTER_NAME="${ORIGINAL_COMPUTER_NAME:-$computer_current}"
                sudo scutil --set ComputerName "$desired"
            else
                echo "✅ Computernaam staat al op ${desired}"
            fi
            ;;
        windows)
            echo "⚠️  Windows: stel de computernaam handmatig in op '${desired}' (bijv. via PowerShell: Rename-Computer -NewName ${desired})."
            ;;
        *)
            echo "⚠️  Onbekend platform, hostname blijft ongewijzigd."
            ;;
    esac
}

detect_platform
echo "🖥  Gedetecteerd platform: ${DEVICE_PLATFORM}"
export DEVICE_NAME_PREFIX DEVICE_NUMBER DEVICE_HOSTNAME DEVICE_MDNS DEVICE_PLATFORM

case "$DEVICE_PLATFORM" in
    linux|jetson|macos)
        if ! ensure_sudo_session; then
            echo "⚠️  Geen sudo-toegang beschikbaar; hostname/mDNS-aanpassingen worden overgeslagen."
        fi
        ;;
esac

install_ollama() {
    if ! command -v ollama >/dev/null 2>&1; then
        echo "📦 Ollama niet gevonden, proberen te installeren..."
        if curl -fsSL https://ollama.com/install.sh | sh; then
            echo "✅ Ollama geïnstalleerd"
        else
            echo "⚠️  Ollama installatie mislukt. Mogelijk netwerk restrictie."
            echo "    Installeer Ollama handmatig: https://ollama.com/download"
            echo "    Of gebruik de mock mode voor testing."
            return 1
        fi
    else
        echo "✅ Ollama is al geïnstalleerd"
    fi
    return 0
}

ollama_pid=""
start_ollama() {
    if ! command -v ollama >/dev/null 2>&1; then
        echo "⚠️  Ollama niet beschikbaar, overslaan..."
        return 1
    fi

    report_gpu_runtime_status || true

    MODEL_NAME="${OLLAMA_MODEL:-gemma3:4b}"
    ollama_host="${OLLAMA_BASE_URL:-${OLLAMA_HOST:-http://127.0.0.1:11434}}"
    kv_cache_type_raw="${OLLAMA_KV_CACHE_TYPE:-${OLLAMA_KV_QUANT:-}}"
    kv_cache_type="$(_trim "${kv_cache_type_raw%%,*}")"
    kv_cache_type="$(printf '%s' "$kv_cache_type" | tr '[:upper:]' '[:lower:]')"
    case "$kv_cache_type" in
        f16|q8_0|q4_0) ;;
        *) kv_cache_type="";;
    esac

    if pgrep -x "ollama" >/dev/null 2>&1; then
        if [ -n "$kv_cache_type" ]; then
            echo "♻️  Ollama herstarten om OLLAMA_KV_CACHE_TYPE=$kv_cache_type toe te passen..."
            if ! _stop_ollama; then
                echo "⚠️  Ollama kon niet worden gestopt; herstart overslaan."
                return 1
            fi
        else
            echo "✅ Ollama draait al"
            return 0
        fi
    fi

    echo "⏳ Ollama server starten..."
    export OLLAMA_HOST="$ollama_host"
    if [ -n "$kv_cache_type" ]; then
        export OLLAMA_KV_CACHE_TYPE="$kv_cache_type"
        echo "✅ OLLAMA_KV_CACHE_TYPE=$OLLAMA_KV_CACHE_TYPE"
    else
        unset OLLAMA_KV_CACHE_TYPE
    fi
    echo "✅ OLLAMA_HOST=$OLLAMA_HOST"
    _run_ollama serve > "$PROJECT_ROOT/ollama.log" 2>&1 &
    ollama_pid=$!
    echo "$ollama_pid" > "$PROJECT_ROOT/ollama.pid" 2>/dev/null || true
    echo "✅ Ollama server gestart (PID: $ollama_pid)"
    if ! _wait_for_ollama; then
        echo "⚠️  Ollama kwam niet op tijd op."
        return 1
    fi
    if ! _run_ollama list | grep -q "$MODEL_NAME"; then
        echo "📥 Model $MODEL_NAME downloaden (dit kan even duren bij eerste keer)..."
        if _run_ollama pull "$MODEL_NAME"; then
            echo "✅ Model $MODEL_NAME gedownload"
        else
            echo "⚠️  Model download mislukt. Check netwerk verbinding."
            return 1
        fi
    else
        echo "✅ Model $MODEL_NAME is al beschikbaar"
    fi
    return 0
}

echo "=== Netwerk & mDNS setup ==="
ensure_mdns_support
ensure_active_wifi_profile_persistence
ensure_remote_support_dependencies
ensure_remote_support_service
configure_hostname
echo "🌐 Publieke hostnaam: ${DEVICE_MDNS}"
echo "============================="
echo

echo "=== Ollama Setup ==="
if install_ollama; then
    start_ollama || echo "⚠️  Kon Ollama niet starten, app draait zonder LLM support"
else
    echo "⚠️  App draait zonder Ollama support"
fi
echo "===================="
echo

BACKEND_HOST="${BACKEND_HOST:-}"
auto_backend_host=0
if [ -z "$BACKEND_HOST" ] || [ "$BACKEND_HOST" = "127.0.0.1" ] || [ "$BACKEND_HOST" = "localhost" ]; then
    BACKEND_HOST="$DEVICE_MDNS"
    auto_backend_host=1
fi
if [ "$auto_backend_host" -eq 1 ]; then
    host_check_failed=0
    if command -v python3 >/dev/null 2>&1; then
        if ! CHECK_HOST="$BACKEND_HOST" python3 - <<'PY' >/dev/null 2>&1; then
import os, socket, sys
host = os.environ.get("CHECK_HOST", "")
try:
    socket.getaddrinfo(host, None)
except OSError:
    sys.exit(1)
PY
            host_check_failed=1
        fi
    elif ! getent hosts "$BACKEND_HOST" >/dev/null 2>&1; then
        host_check_failed=1
    fi
    if [ "$host_check_failed" -eq 1 ]; then
        echo "⚠️  Hostname ${BACKEND_HOST} niet bereikbaar, val terug op 127.0.0.1"
        BACKEND_HOST="127.0.0.1"
    fi
fi
BACKEND_BIND_HOST="${BACKEND_BIND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
if [ -z "${BACKEND_HTTP:-}" ] || [[ "$BACKEND_HTTP" == http://127.0.0.1* ]] || [[ "$BACKEND_HTTP" == http://localhost* ]]; then
    BACKEND_HTTP="http://$BACKEND_HOST:$BACKEND_PORT"
fi
if [ -z "${BACKEND_WS:-}" ]; then
    if [[ "$BACKEND_HTTP" == https://* ]]; then
        BACKEND_WS="wss://${BACKEND_HTTP#https://}"
    elif [[ "$BACKEND_HTTP" == http://* ]]; then
        BACKEND_WS="ws://${BACKEND_HTTP#http://}"
    else
        BACKEND_WS="ws://$BACKEND_HOST:$BACKEND_PORT/ws"
    fi
fi
if [ -z "${PUBLIC_BASE_URL:-}" ] || [[ "$PUBLIC_BASE_URL" == http://127.0.0.1* ]] || [[ "$PUBLIC_BASE_URL" == http://localhost* ]]; then
    PUBLIC_BASE_URL="http://$DEVICE_MDNS:$BACKEND_PORT"
fi
export BACKEND_HOST BACKEND_BIND_HOST BACKEND_PORT BACKEND_HTTP BACKEND_WS PUBLIC_BASE_URL

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

if [ ! -f ".venv/.requirements_installed" ]; then
    python -m pip install -U pip
    python -m pip install -r app/requirements.txt
    touch .venv/.requirements_installed
fi

BACKEND_CMD=(python -m uvicorn app.backend.main:app --reload --host "$BACKEND_BIND_HOST" --port "$BACKEND_PORT")
backend_log="$PROJECT_ROOT/backend.log"

if pgrep -f "uvicorn app.backend.main:app" >/dev/null 2>&1; then
    echo "⚠️  bestaand uvicorn backend-proces gevonden, stoppen…"
    pkill -f "uvicorn app.backend.main:app" >/dev/null 2>&1 || true
    sleep 1
fi

if lsof -ti:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    backend_pids="$(lsof -ti:"$BACKEND_PORT" -sTCP:LISTEN)"
    for pid in $backend_pids; do
        echo "⚠️  bestaand backend-proces op poort $BACKEND_PORT gevonden (pid $pid), stoppen…"
        kill "$pid" >/dev/null 2>&1 || true
    done
    sleep 1
    if lsof -ti:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
        echo "⚠️  backend-proces reageert niet, force kill."
        lsof -ti:"$BACKEND_PORT" -sTCP:LISTEN | xargs kill -9 >/dev/null 2>&1 || true
        sleep 1
    fi
fi

echo "⏳ Backend starten (log: $backend_log)..."
"${BACKEND_CMD[@]}" >"$backend_log" 2>&1 &
backend_pid=$!

cleanup() {
    echo
    echo "🛑 Backend stoppen..."
    kill "$backend_pid" >/dev/null 2>&1 || true

    if [ -n "${ollama_pid:-}" ]; then
        echo "🛑 Ollama stoppen..."
        kill "$ollama_pid" >/dev/null 2>&1 || true
    fi

    case "$DEVICE_PLATFORM" in
        linux|jetson)
            if [ -n "${ORIGINAL_HOSTNAME:-}" ]; then
                echo "♻️  Hostname terugzetten naar ${ORIGINAL_HOSTNAME}"
                sudo hostnamectl set-hostname "$ORIGINAL_HOSTNAME" >/dev/null 2>&1 || true
            fi
            ;;
        macos)
            if [ -n "${ORIGINAL_HOSTNAME:-}" ]; then
                echo "♻️  macOS HostName terugzetten naar ${ORIGINAL_HOSTNAME}"
                sudo scutil --set HostName "$ORIGINAL_HOSTNAME" >/dev/null 2>&1 || true
            fi
            if [ -n "${ORIGINAL_LOCAL_HOSTNAME:-}" ]; then
                sudo scutil --set LocalHostName "$ORIGINAL_LOCAL_HOSTNAME" >/dev/null 2>&1 || true
            fi
            if [ -n "${ORIGINAL_COMPUTER_NAME:-}" ]; then
                sudo scutil --set ComputerName "$ORIGINAL_COMPUTER_NAME" >/dev/null 2>&1 || true
            fi
            ;;
    esac

    if [ -n "${SUDO_KEEPALIVE_PID:-}" ]; then
        kill "$SUDO_KEEPALIVE_PID" >/dev/null 2>&1 || true
        SUDO_KEEPALIVE_PID=""
    fi
    if [ "$HAVE_SUDO" -eq 1 ]; then
        sudo -k >/dev/null 2>&1 || true
    fi
}

trap cleanup EXIT

health_url="http://$BACKEND_HOST:$BACKEND_PORT/health"
for i in {1..40}; do
    if curl -fs "$health_url" >/dev/null 2>&1; then
        echo "✅ Backend reagerend, start frontend."
        break
    fi
    sleep 0.5
done

if ! curl -fs "$health_url" >/dev/null 2>&1; then
    echo "❌ Backend reageert niet; kijk in $backend_log"
    exit 1
fi

python -m app.frontend.main

wait "$backend_pid"
