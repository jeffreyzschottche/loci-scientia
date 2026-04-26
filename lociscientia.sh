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
NPU_REBOOT_REQUIRED=0
NPU_STACK_READY=0
NPU_ACCEL_AVAILABLE=0

_os_release_field() {
    local field="$1"
    if [ ! -r /etc/os-release ]; then
        return 1
    fi
    # shellcheck disable=SC1091
    . /etc/os-release
    eval "printf '%s' \"\${$field:-}\""
}

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

_have_root_access() {
    [ "$HAVE_SUDO" -eq 1 ] || [ "$(id -u)" -eq 0 ]
}

_run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

_version_ge() {
    [ "$1" = "$2" ] && return 0
    local first
    first="$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1)"
    [ "$first" = "$2" ]
}

_npu_is_required() {
    local mode="${LEMONADE_REQUIRE_NPU:-auto}"
    case "$mode" in
        1|true|TRUE|yes|YES|on|ON)
            return 0
            ;;
        auto|AUTO|"")
            detect_npu >/dev/null 2>&1
            return $?
            ;;
        *)
            return 1
            ;;
    esac
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

ensure_wifi_ui() {
    case "$DEVICE_PLATFORM" in
        linux|jetson)
            if [ "$HAVE_SUDO" -ne 1 ]; then
                echo "⚠️  Geen sudo, iwgtk/iwd worden niet automatisch geïnstalleerd."
                return 1
            fi
            if ! command -v apt-get >/dev/null 2>&1; then
                echo "⚠️  apt-get niet beschikbaar, sla iwgtk/iwd installatie over."
                return 1
            fi
            if command -v iwgtk >/dev/null 2>&1; then
                echo "✅ iwgtk is al geïnstalleerd"
            else
                echo "📦 iwgtk installeren..."
                sudo apt-get update -y
                sudo apt-get install -y iwgtk
            fi
            if command -v iwd >/dev/null 2>&1; then
                echo "✅ iwd is al geïnstalleerd"
            else
                echo "📦 iwd installeren (nodig voor iwgtk)..."
                sudo apt-get install -y iwd
            fi
            if command -v systemctl >/dev/null 2>&1 && ! systemctl is-active NetworkManager >/dev/null 2>&1; then
                sudo systemctl enable iwd >/dev/null 2>&1 || true
                sudo systemctl restart iwd >/dev/null 2>&1 || true
            fi
            ;;
        *)
            return 0
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
ensure_wifi_ui
ensure_remote_support_dependencies
ensure_remote_support_service
configure_hostname
echo "🌐 Publieke hostnaam: ${DEVICE_MDNS}"
echo "============================="
echo

LLM_PROVIDER="${LLM_PROVIDER:-ollama}"
case "$LLM_PROVIDER" in
    ollama|lemonade) ;;
    *)
        echo "⚠️  Onbekende LLM_PROVIDER '$LLM_PROVIDER'; terugvallen op ollama."
        LLM_PROVIDER="ollama"
        ;;
esac
export LLM_PROVIDER

lemonade_pid=""

_lemonade_bin_dir="$PROJECT_ROOT/bin/lemonade"

_find_cpp_lemonade_bin() {
    # Zoek expliciet de C++ binaries (lemond of de lemonade-server shim).
    # De Python `lemonade-server-dev` is gedeprecateerd en wordt hier bewust genegeerd.
    local candidate
    for candidate in \
        "$_lemonade_bin_dir/lemond" \
        "$_lemonade_bin_dir/lemonade-server" \
        "/opt/bin/lemond" \
        "/opt/bin/lemonade-server"; do
        if [ -x "$candidate" ]; then
            printf '%s' "$candidate"
            return 0
        fi
    done
    if command -v lemond >/dev/null 2>&1; then
        command -v lemond
        return 0
    fi
    if command -v lemonade-server >/dev/null 2>&1; then
        local path
        path="$(command -v lemonade-server)"
        # Shim in de project-venv is de Python-variant; die willen we niet.
        case "$path" in
            "$PROJECT_ROOT/.venv/"*) ;;
            *) printf '%s' "$path"; return 0 ;;
        esac
    fi
    return 1
}

_install_lemonade_from_tarball() {
    if ! command -v curl >/dev/null 2>&1; then
        echo "⚠️  curl ontbreekt; kan embeddable tarball niet downloaden."
        return 1
    fi
    local api_url="https://api.github.com/repos/lemonade-sdk/lemonade/releases/latest"
    local tarball_url
    tarball_url="$(curl -fsSL "$api_url" \
        | grep -oE '"browser_download_url":[[:space:]]*"[^"]*lemonade-embeddable-[0-9.]+-ubuntu-x64\.tar\.gz"' \
        | head -n1 | sed -E 's/.*"(https[^"]+)"/\1/')"
    if [ -z "$tarball_url" ]; then
        echo "⚠️  Kon embeddable tarball URL niet vinden in GitHub releases."
        return 1
    fi
    mkdir -p "$_lemonade_bin_dir"
    local tmp_tgz
    tmp_tgz="$(mktemp --suffix=.tar.gz)"
    echo "⬇️  Download embeddable Lemonade: $(basename "$tarball_url")"
    if ! curl -fSL "$tarball_url" -o "$tmp_tgz"; then
        rm -f "$tmp_tgz"
        echo "⚠️  Download embeddable Lemonade mislukt."
        return 1
    fi
    if ! tar -xzf "$tmp_tgz" -C "$_lemonade_bin_dir" --strip-components=1; then
        rm -f "$tmp_tgz"
        echo "⚠️  Uitpakken embeddable tarball mislukt."
        return 1
    fi
    rm -f "$tmp_tgz"
    if [ ! -x "$_lemonade_bin_dir/lemond" ]; then
        echo "⚠️  lemond binary niet gevonden in embeddable tarball."
        return 1
    fi
    echo "✅ C++ Lemonade (lemond) geïnstalleerd in $_lemonade_bin_dir"
    return 0
}

_install_lemonade_from_ppa() {
    if ! command -v apt-get >/dev/null 2>&1; then
        return 1
    fi
    if [ "$HAVE_SUDO" -ne 1 ] && [ "$(id -u)" -ne 0 ]; then
        echo "⚠️  Geen sudo; kan Lemonade PPA niet toevoegen."
        return 1
    fi
    local sudo_cmd=()
    if [ "$(id -u)" -ne 0 ]; then
        sudo_cmd=(sudo)
    fi
    if ! command -v add-apt-repository >/dev/null 2>&1; then
        echo "📦 software-properties-common installeren voor add-apt-repository..."
        "${sudo_cmd[@]}" apt-get update -y || true
        "${sudo_cmd[@]}" apt-get install -y software-properties-common || return 1
    fi
    echo "🍋 PPA ppa:lemonade-team/stable toevoegen..."
    if ! "${sudo_cmd[@]}" add-apt-repository -y ppa:lemonade-team/stable; then
        return 1
    fi
    "${sudo_cmd[@]}" apt-get update -y || return 1
    if ! "${sudo_cmd[@]}" apt-get install -y lemonade-server; then
        return 1
    fi
    return 0
}

_find_flm_bin() {
    local candidate
    for candidate in \
        "$PROJECT_ROOT/bin/flm/flm" \
        "/opt/bin/flm"; do
        if [ -x "$candidate" ]; then
            printf '%s' "$candidate"
            return 0
        fi
    done
    if command -v flm >/dev/null 2>&1; then
        command -v flm
        return 0
    fi
    return 1
}

_install_linux_npu_packages() {
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "⚠️  apt-get niet beschikbaar; Linux NPU packages worden niet automatisch geïnstalleerd."
        return 1
    fi
    if ! _have_root_access; then
        echo "⚠️  Geen sudo/root; libxrt-npu2, amdxdna-dkms en linux-firmware worden niet automatisch geïnstalleerd."
        return 1
    fi
    local missing_packages=()
    local package
    for package in libxrt-npu2 amdxdna-dkms linux-firmware; do
        if ! dpkg -s "$package" >/dev/null 2>&1; then
            missing_packages+=("$package")
        fi
    done
    if [ "${#missing_packages[@]}" -eq 0 ]; then
        echo "✅ Linux NPU packages zijn al aanwezig"
        return 0
    fi
    echo "📦 Linux NPU packages installeren: ${missing_packages[*]}"
    _run_privileged apt-get update -y
    _run_privileged apt-get install -y "${missing_packages[@]}"
}

_install_flm_from_release() {
    if ! command -v curl >/dev/null 2>&1; then
        echo "⚠️  curl ontbreekt; kan FastFlowLM release niet downloaden."
        return 1
    fi
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "⚠️  apt-get ontbreekt; kan FastFlowLM .deb niet installeren."
        return 1
    fi
    if ! _have_root_access; then
        echo "⚠️  Geen sudo/root; kan FastFlowLM niet automatisch installeren."
        return 1
    fi

    local api_url="https://api.github.com/repos/FastFlowLM/FastFlowLM/releases/latest"
    local release_json=""
    local flm_url=""
    local arch_regex='(amd64|x86_64)'
    local os_id="" version_id="" version_codename="" ubuntu_version_no_dots=""
    local ubuntu_major_minor="" asset_regex="" fallback_regex="" available_assets=""
    local exact_markers=""
    local require_exact_asset=0

    if [ -n "${FASTFLOWLM_DEB_URL:-}" ]; then
        flm_url="${FASTFLOWLM_DEB_URL}"
    else
        release_json="$(curl -fsSL "$api_url")" || return 1
        os_id="$(_os_release_field ID | tr '[:upper:]' '[:lower:]')"
        version_id="$(_os_release_field VERSION_ID)"
        version_codename="$(_os_release_field VERSION_CODENAME | tr '[:upper:]' '[:lower:]')"
        ubuntu_version_no_dots="${version_id//./}"
        ubuntu_major_minor="$(printf '%s' "$version_id" | cut -d. -f1,2)"

        case "$os_id" in
            ubuntu)
                asset_regex="\"browser_download_url\":[[:space:]]*\"[^\"]*(ubuntu|noble|oracular|plucky|questing)[^\"]*${arch_regex}[^\"]*\\.deb\""
                if [ "$version_id" = "25.10" ] || [ "$version_codename" = "questing" ]; then
                    require_exact_asset=1
                    exact_markers="questing|25\\.10|2510"
                    asset_regex="\"browser_download_url\":[[:space:]]*\"[^\"]*(${exact_markers})[^\"]*${arch_regex}[^\"]*\\.deb\""
                elif [ -n "$version_id" ] || [ -n "$version_codename" ]; then
                    asset_regex="\"browser_download_url\":[[:space:]]*\"[^\"]*(${version_codename}|${version_id}|${ubuntu_version_no_dots}|${ubuntu_major_minor}|ubuntu)[^\"]*${arch_regex}[^\"]*\\.deb\""
                fi
                fallback_regex="\"browser_download_url\":[[:space:]]*\"[^\"]*ubuntu[^\"]*${arch_regex}[^\"]*\\.deb\""
                ;;
            debian)
                asset_regex="\"browser_download_url\":[[:space:]]*\"[^\"]*(debian|bookworm|trixie|forky)[^\"]*${arch_regex}[^\"]*\\.deb\""
                fallback_regex="\"browser_download_url\":[[:space:]]*\"[^\"]*debian[^\"]*${arch_regex}[^\"]*\\.deb\""
                ;;
            *)
                fallback_regex="\"browser_download_url\":[[:space:]]*\"[^\"]*(linux|ubuntu|debian)[^\"]*${arch_regex}[^\"]*\\.deb\""
                ;;
        esac

        if [ -n "$asset_regex" ]; then
            flm_url="$(printf '%s' "$release_json" \
                | grep -oE "$asset_regex" \
                | head -n1 | sed -E 's/.*"(https[^"]+)"/\1/')"
        fi
        if [ -z "$flm_url" ] && [ "$require_exact_asset" -eq 0 ] && [ -n "$fallback_regex" ]; then
            flm_url="$(printf '%s' "$release_json" \
                | grep -oE "$fallback_regex" \
                | head -n1 | sed -E 's/.*"(https[^"]+)"/\1/')"
        fi
        available_assets="$(printf '%s' "$release_json" \
            | grep -oE '"browser_download_url":[[:space:]]*"[^"]+\.deb"' \
            | sed -E 's/.*\/([^\/"]+)"$/\1/' \
            | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
    fi
    if [ -z "$flm_url" ]; then
        echo "⚠️  Kon geen FastFlowLM .deb vinden die past bij $( _os_release_field PRETTY_NAME || printf '%s' 'dit systeem' )."
        if [ "$require_exact_asset" -eq 1 ]; then
            echo "    Voor Ubuntu 25.10/questing accepteert dit script geen Ubuntu 24.04 fallback-package."
        fi
        if [ -n "$available_assets" ]; then
            echo "    Beschikbare release-assets: $available_assets"
        fi
        return 1
    fi

    local tmp_deb
    tmp_deb="$(mktemp --suffix=.deb)"
    echo "⬇️  Download FastFlowLM: $(basename "$flm_url")"
    if ! curl -fSL "$flm_url" -o "$tmp_deb"; then
        rm -f "$tmp_deb"
        echo "⚠️  Download FastFlowLM mislukt."
        return 1
    fi
    if ! _run_privileged apt-get install -y "$tmp_deb"; then
        rm -f "$tmp_deb"
        echo "⚠️  FastFlowLM installatie mislukt."
        return 1
    fi
    rm -f "$tmp_deb"
    return 0
}

_install_flm_from_source() {
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "⚠️  apt-get ontbreekt; kan build-dependencies voor FastFlowLM niet automatisch installeren."
        return 1
    fi
    if ! _have_root_access; then
        echo "⚠️  Geen sudo/root; kan FastFlowLM build-dependencies niet automatisch installeren."
        return 1
    fi

    local build_packages=(
        git
        cmake
        ninja-build
        build-essential
        pkg-config
    )
    local tmp_dir=""
    local source_ref="${FASTFLOWLM_SOURCE_REF:-}"
    local clone_url="${FASTFLOWLM_GIT_URL:-https://github.com/FastFlowLM/FastFlowLM.git}"
    local cmake_preset="${FASTFLOWLM_CMAKE_PRESET:-linux-default}"

    echo "📦 Build-dependencies voor FastFlowLM installeren..."
    _run_privileged apt-get update -y
    _run_privileged apt-get install -y "${build_packages[@]}"

    if ! command -v git >/dev/null 2>&1; then
        echo "⚠️  git ontbreekt nog steeds na installatie van build-dependencies."
        return 1
    fi
    if ! command -v cmake >/dev/null 2>&1; then
        echo "⚠️  cmake ontbreekt nog steeds na installatie van build-dependencies."
        return 1
    fi

    tmp_dir="$(mktemp -d)"
    echo "⬇️  FastFlowLM broncode ophalen..."
    if ! git clone --depth=1 "$clone_url" "$tmp_dir/FastFlowLM"; then
        rm -rf "$tmp_dir"
        echo "⚠️  FastFlowLM broncode ophalen mislukt."
        return 1
    fi

    if [ -n "$source_ref" ]; then
        echo "📍 FastFlowLM checkout: $source_ref"
        if ! git -C "$tmp_dir/FastFlowLM" fetch --depth=1 origin "$source_ref" \
            || ! git -C "$tmp_dir/FastFlowLM" checkout "$source_ref"; then
            rm -rf "$tmp_dir"
            echo "⚠️  FastFlowLM checkout naar $source_ref mislukt."
            return 1
        fi
    fi

    echo "🛠️  FastFlowLM bouwen vanaf broncode..."
    if ! (
        cd "$tmp_dir/FastFlowLM/src" \
        && cmake --preset "$cmake_preset" \
        && cmake --build --preset "$cmake_preset" -j"$(nproc)" \
        && _run_privileged cmake --install --preset "$cmake_preset"
    ); then
        rm -rf "$tmp_dir"
        echo "⚠️  FastFlowLM build/install vanaf broncode mislukt."
        return 1
    fi

    rm -rf "$tmp_dir"
    return 0
}

_install_flm() {
    if _install_flm_from_release; then
        return 0
    fi

    local os_id="" version_id="" version_codename=""
    os_id="$(_os_release_field ID | tr '[:upper:]' '[:lower:]')"
    version_id="$(_os_release_field VERSION_ID)"
    version_codename="$(_os_release_field VERSION_CODENAME | tr '[:upper:]' '[:lower:]')"

    if [ "$os_id" = "ubuntu" ] && { [ "$version_id" = "25.10" ] || [ "$version_codename" = "questing" ]; }; then
        echo "ℹ️  Geen geschikte FastFlowLM .deb gevonden voor Ubuntu 25.10; val terug op build vanaf broncode."
        _install_flm_from_source
        return $?
    fi

    return 1
}

_ensure_amdxdna_module() {
    if command -v lsmod >/dev/null 2>&1 && lsmod | grep -q '^amdxdna'; then
        return 0
    fi
    if ! command -v modprobe >/dev/null 2>&1; then
        return 1
    fi
    if ! _have_root_access; then
        return 1
    fi
    echo "🔧 amdxdna kernelmodule laden..."
    if ! _run_privileged modprobe amdxdna >/dev/null 2>&1; then
        echo "⚠️  modprobe amdxdna faalde."
        if command -v modinfo >/dev/null 2>&1; then
            local module_path=""
            module_path="$(modinfo -F filename amdxdna 2>/dev/null || true)"
            if [ -n "$module_path" ]; then
                echo "ℹ️  amdxdna modulepad: $module_path"
            fi
        fi
        if command -v dkms >/dev/null 2>&1; then
            local dkms_status=""
            dkms_status="$(dkms status amdxdna 2>/dev/null || true)"
            if [ -n "$dkms_status" ]; then
                echo "ℹ️  DKMS status: $dkms_status"
            fi
        fi
        if [ -r /sys/firmware/efi/efivars/SecureBoot-* ] || command -v mokutil >/dev/null 2>&1; then
            local secure_boot_state="unknown"
            if command -v mokutil >/dev/null 2>&1; then
                secure_boot_state="$(mokutil --sb-state 2>/dev/null | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
            fi
            if [ "$secure_boot_state" != "unknown" ] && [ -n "$secure_boot_state" ]; then
                echo "ℹ️  Secure Boot: $secure_boot_state"
            fi
        fi
        if _have_root_access && command -v dmesg >/dev/null 2>&1; then
            local dmesg_excerpt=""
            dmesg_excerpt="$(_run_privileged dmesg 2>/dev/null | tail -n 120 | grep -iE 'amdxdna|npu|xdna|secure boot|module verification' | tail -n 12 || true)"
            if [ -n "$dmesg_excerpt" ]; then
                echo "ℹ️  Relevante kernelmeldingen:"
                printf '%s\n' "$dmesg_excerpt" | sed 's/^/    /'
                if printf '%s' "$dmesg_excerpt" | grep -q 'SVA bind device failed, ret -95'; then
                    echo "💡 Hint: ret -95 betekent doorgaans dat IOMMU SVA/SVM niet beschikbaar is voor de NPU."
                    echo "    Controleer in BIOS/UEFI dat SVM en IOMMU aan staan, en reboot daarna."
                    echo "    Controleer ook dat de kernel niet met iommu=off of amd_iommu=off gestart is."
                fi
            fi
        fi
        return 1
    fi
    sleep 1
    if command -v lsmod >/dev/null 2>&1 && lsmod | grep -q '^amdxdna'; then
        return 0
    fi
    echo "⚠️  modprobe amdxdna gaf geen fout, maar de module staat niet in lsmod."
    if _have_root_access && command -v dmesg >/dev/null 2>&1; then
        local post_dmesg_excerpt=""
        post_dmesg_excerpt="$(_run_privileged dmesg 2>/dev/null | tail -n 120 | grep -iE 'amdxdna|npu|xdna|secure boot|module verification' | tail -n 12 || true)"
        if [ -n "$post_dmesg_excerpt" ]; then
            echo "ℹ️  Relevante kernelmeldingen:"
            printf '%s\n' "$post_dmesg_excerpt" | sed 's/^/    /'
            if printf '%s' "$post_dmesg_excerpt" | grep -q 'SVA bind device failed, ret -95'; then
                echo "💡 Hint: ret -95 betekent doorgaans dat IOMMU SVA/SVM niet beschikbaar is voor de NPU."
                echo "    Controleer in BIOS/UEFI dat SVM en IOMMU aan staan, en reboot daarna."
                echo "    Controleer ook dat de kernel niet met iommu=off of amd_iommu=off gestart is."
            fi
        fi
    fi
    return 1
}

_read_npu_fw_version() {
    local version=""
    if compgen -G '/sys/bus/pci/drivers/amdxdna/*/fw_version' >/dev/null 2>&1; then
        version="$(cat /sys/bus/pci/drivers/amdxdna/*/fw_version 2>/dev/null | head -n1)"
    fi
    printf '%s' "$version"
}

_configure_lemonade_for_npu() {
    local flm_model="${LEMONADE_NPU_MODEL:-gemma3:4b}"
    local raw_models="${LEMONADE_MODELS:-}"
    if [ -z "${LEMONADE_MODEL:-}" ] || printf '%s' "${LEMONADE_MODEL:-}" | grep -qi 'gguf'; then
        export LEMONADE_MODEL="$flm_model"
        echo "✅ Lemonade NPU-model geselecteerd: $LEMONADE_MODEL"
    fi
    if [ -z "$raw_models" ] || printf '%s' "$raw_models" | grep -qi 'gguf'; then
        export LEMONADE_MODELS="$LEMONADE_MODEL"
    elif ! printf ',%s,' "$raw_models" | grep -q ",$LEMONADE_MODEL,"; then
        export LEMONADE_MODELS="$LEMONADE_MODEL,$raw_models"
    fi
}

ensure_lemonade_npu_stack() {
    NPU_STACK_READY=0
    NPU_ACCEL_AVAILABLE=0

    if [ "${LEMONADE_PREFER_NPU:-1}" = "0" ]; then
        echo "ℹ️  LEMONADE_PREFER_NPU=0; NPU setup expliciet overgeslagen."
        return 0
    fi

    case "$DEVICE_PLATFORM" in
        linux|jetson) ;;
        *)
            echo "ℹ️  NPU setup is alleen geautomatiseerd voor Linux."
            return 0
            ;;
    esac

    if ! detect_npu; then
        return 0
    fi

    _install_linux_npu_packages || true

    if ! _ensure_amdxdna_module; then
        echo "⚠️  amdxdna kernelmodule is niet geladen."
        NPU_REBOOT_REQUIRED=1
    fi

    local fw_version=""
    fw_version="$(_read_npu_fw_version)"
    if [ -n "$fw_version" ]; then
        echo "ℹ️  Gedetecteerde NPU firmware: $fw_version"
        if ! _version_ge "$fw_version" "1.1.0.0"; then
            echo "⚠️  NPU firmware is ouder dan 1.1.0.0; Linux FLM/NPU inference zal waarschijnlijk niet werken."
            echo "    Werk linux-firmware/NPU firmware bij en reboot daarna."
            NPU_REBOOT_REQUIRED=1
        fi
    else
        echo "⚠️  NPU firmwareversie kon niet worden gelezen via amdxdna."
    fi

    if [ ! -e /dev/accel/accel0 ] && [ ! -e /dev/amdxdna ]; then
        echo "⚠️  NPU device-node ontbreekt; reboot of driver setup kan nog nodig zijn."
        NPU_REBOOT_REQUIRED=1
    fi

    if ! _find_flm_bin >/dev/null 2>&1; then
        echo "📦 FastFlowLM (flm) niet gevonden; proberen te installeren..."
        _install_flm || true
    fi

    if _find_flm_bin >/dev/null 2>&1; then
        echo "✅ FastFlowLM gevonden ($(_find_flm_bin))"
    else
        echo "⚠️  FastFlowLM ontbreekt nog; Lemonade zal zonder FLM niet op de NPU draaien."
    fi

    if [ "$NPU_REBOOT_REQUIRED" -eq 0 ] && _find_flm_bin >/dev/null 2>&1; then
        NPU_STACK_READY=1
        NPU_ACCEL_AVAILABLE=1
        _configure_lemonade_for_npu
    else
        echo "ℹ️  Lemonade blijft voor nu op CPU/GPU totdat FLM + firmware + driver compleet zijn."
        if _npu_is_required; then
            echo "❌ NPU is verplicht voor deze run, maar FastFlowLM/NPU stack is niet klaar."
            return 1
        fi
    fi

    return 0
}

install_lemonade() {
    # Hard eis: de C++ Lemonade Server (lemond). De Python `lemonade-server-dev`
    # is gedeprecateerd (zie lemonade.log) en wordt niet meer gebruikt.
    if _find_cpp_lemonade_bin >/dev/null; then
        echo "✅ C++ Lemonade Server is al geïnstalleerd ($(_find_cpp_lemonade_bin))"
        return 0
    fi

    echo "📦 C++ Lemonade Server niet gevonden; installeren..."
    case "$DEVICE_PLATFORM" in
        linux|jetson)
            local distro_id=""
            if [ -r /etc/os-release ]; then
                # shellcheck disable=SC1091
                distro_id="$(. /etc/os-release; echo "${ID:-} ${ID_LIKE:-}")"
            fi
            if echo "$distro_id" | grep -qiE 'ubuntu|debian'; then
                if _install_lemonade_from_ppa; then
                    if _find_cpp_lemonade_bin >/dev/null; then
                        echo "✅ lemonade-server geïnstalleerd via PPA"
                        return 0
                    fi
                fi
                echo "ℹ️  PPA-installatie niet gelukt; val terug op embeddable tarball."
            fi
            if _install_lemonade_from_tarball; then
                return 0
            fi
            echo "⚠️  Automatische installatie mislukt."
            echo "    Installeer handmatig via https://lemonade-server.ai/install_options.html"
            return 1
            ;;
        *)
            echo "⚠️  Automatische installatie voor ${DEVICE_PLATFORM} niet ondersteund."
            echo "    Installeer handmatig via https://lemonade-server.ai/install_options.html"
            return 1
            ;;
    esac
}

detect_npu() {
    if [ -e /dev/accel/accel0 ] || [ -e /dev/amdxdna ]; then
        echo "✅ AMD NPU device-node gedetecteerd (Ryzen AI)"
        return 0
    fi
    if command -v lspci >/dev/null 2>&1 && lspci 2>/dev/null | grep -iq -E 'IPU|XDNA|Ryzen AI'; then
        echo "✅ AMD NPU gedetecteerd via lspci"
        return 0
    fi
    echo "ℹ️  Geen AMD NPU gedetecteerd; Lemonade zal terugvallen op CPU/GPU backend."
    return 1
}

_warmup_lemonade_model() {
    local base_url="$1"
    local model="${LEMONADE_MODEL:-}"
    if [ -z "$model" ]; then
        echo "ℹ️  LEMONADE_MODEL niet ingesteld; warm-up overgeslagen."
        return 0
    fi
    echo "🔥 Lemonade warm-up: model $model preloaden (achtergrond)..."
    (
        curl -fsS -X POST "$base_url/api/v1/load" \
            -H "Content-Type: application/json" \
            -d "{\"model_name\":\"$model\"}" \
            >>"$PROJECT_ROOT/lemonade.log" 2>&1 \
            && echo "✅ Lemonade warm-up voltooid voor $model" >>"$PROJECT_ROOT/lemonade.log" \
            || echo "⚠️  Lemonade warm-up faalde voor $model" >>"$PROJECT_ROOT/lemonade.log"
    ) &
}

_reap_orphan_llama_servers() {
    # Bij een onverwachte exit blijft soms een llama-server subprocess hangen
    # dat VRAM vasthoudt (PPID 1). Dat blokkeert het herladen van het model.
    # Ruim alleen échte orphans op — processen waarvan de parent (lemond) al weg is.
    if ! command -v pgrep >/dev/null 2>&1; then
        return 0
    fi
    local pids
    pids="$(pgrep -f 'lemonade/bin/llamacpp/.*llama-server' 2>/dev/null || true)"
    [ -z "$pids" ] && return 0
    local pid ppid
    for pid in $pids; do
        ppid="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d '[:space:]')"
        if [ "$ppid" = "1" ]; then
            echo "🧹 Orphan llama-server (pid $pid) opruimen om VRAM vrij te maken..."
            kill "$pid" >/dev/null 2>&1 || true
            sleep 1
            if kill -0 "$pid" >/dev/null 2>&1; then
                kill -9 "$pid" >/dev/null 2>&1 || true
            fi
        fi
    done
}

start_lemonade() {
    local host port
    local base_url="${LEMONADE_BASE_URL:-http://127.0.0.1:8020}"
    host="$(printf '%s' "$base_url" | sed -E 's#https?://##; s#/.*##; s#:[0-9]+$##')"
    port="$(printf '%s' "$base_url" | sed -nE 's#.*:([0-9]+).*#\1#p')"
    port="${port:-8020}"
    host="${host:-127.0.0.1}"

    if ! ensure_lemonade_npu_stack; then
        echo "⚠️  Lemonade start niet omdat NPU-acceleratie verplicht is maar niet beschikbaar."
        return 1
    fi

    local bin=""
    bin="$(_find_cpp_lemonade_bin || true)"
    if [ -z "$bin" ]; then
        echo "⚠️  C++ Lemonade binary niet gevonden na installatie."
        return 1
    fi

    _reap_orphan_llama_servers

    if curl -fsS "$base_url/api/v1/health" >/dev/null 2>&1; then
        echo "✅ Lemonade Server draait al op $base_url"
        _warmup_lemonade_model "$base_url"
        return 0
    fi

    echo "⏳ C++ Lemonade Server starten ($bin) op $host:$port..."
    if [ "$NPU_ACCEL_AVAILABLE" -eq 1 ]; then
        echo "🚀 NPU-stack klaar; Lemonade krijgt FLM-geschikte modelconfiguratie mee."
    elif detect_npu >/dev/null 2>&1; then
        echo "ℹ️  NPU hardware aanwezig, maar stack/model is nog niet volledig klaar; Lemonade kan terugvallen op GPU/CPU."
    fi
    case "$(basename "$bin")" in
        lemond)
            # Native C++ server; cache_dir wordt bewust niet doorgegeven zodat
            # lemond zijn default runtime-dir (~/.cache/lemonade, $XDG_RUNTIME_DIR)
            # gebruikt en niet in /opt of vergelijkbare read-only paden schrijft.
            "$bin" --host "$host" --port "$port" \
                > "$PROJECT_ROOT/lemonade.log" 2>&1 &
            ;;
        lemonade-server)
            # Legacy shim die delegeert naar lemond; accepteert `serve`.
            "$bin" serve --host "$host" --port "$port" \
                > "$PROJECT_ROOT/lemonade.log" 2>&1 &
            ;;
        *)
            echo "⚠️  Onbekende Lemonade binary: $bin"
            return 1
            ;;
    esac
    lemonade_pid=$!
    echo "$lemonade_pid" > "$PROJECT_ROOT/lemonade.pid" 2>/dev/null || true
    echo "✅ Lemonade Server gestart (PID: $lemonade_pid)"

    local attempt
    for attempt in {1..40}; do
        if curl -fsS "$base_url/api/v1/health" >/dev/null 2>&1; then
            echo "✅ Lemonade health OK"
            _warmup_lemonade_model "$base_url"
            return 0
        fi
        sleep 1
    done
    echo "⚠️  Lemonade Server kwam niet op tijd op (zie lemonade.log)."
    return 1
}

case "$LLM_PROVIDER" in
    ollama)
        echo "=== Ollama Setup ==="
        if install_ollama; then
            start_ollama || echo "⚠️  Kon Ollama niet starten, app draait zonder LLM support"
        else
            echo "⚠️  App draait zonder Ollama support"
        fi
        echo "===================="
        ;;
    lemonade)
        echo "=== Lemonade Setup ==="
        if install_lemonade; then
            if ! start_lemonade; then
                if _npu_is_required; then
                    echo "❌ Lemonade vereist NPU-acceleratie op deze machine; afbreken."
                    exit 1
                fi
                echo "⚠️  Kon Lemonade niet starten, app draait zonder LLM support"
            fi
            if [ -n "${LEMONADE_MODEL:-}" ]; then
                echo "ℹ️  Actief Lemonade model voor deze run: ${LEMONADE_MODEL}"
            fi
            if [ "$NPU_REBOOT_REQUIRED" -eq 1 ]; then
                echo "⚠️  NPU stack is aangepast maar een reboot lijkt nog nodig voordat FLM/NPU inference werkt."
            fi
        else
            echo "⚠️  App draait zonder Lemonade support"
        fi
        echo "======================"
        ;;
esac
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

    if [ -n "${lemonade_pid:-}" ]; then
        echo "🛑 Lemonade stoppen..."
        # Kill de hele procesgroep zodat llama-server subprocessen niet als
        # orphans blijven draaien (zouden anders VRAM vasthouden bij restart).
        local lemonade_children
        lemonade_children="$(pgrep -P "$lemonade_pid" 2>/dev/null || true)"
        kill "$lemonade_pid" >/dev/null 2>&1 || true
        for lpid in $lemonade_children; do
            kill "$lpid" >/dev/null 2>&1 || true
        done
        sleep 2
        if kill -0 "$lemonade_pid" >/dev/null 2>&1; then
            kill -9 "$lemonade_pid" >/dev/null 2>&1 || true
        fi
        # Vang eventuele achtergebleven llama-server processen af.
        if command -v pgrep >/dev/null 2>&1; then
            local stragglers
            stragglers="$(pgrep -f 'lemonade/bin/llamacpp/.*llama-server' 2>/dev/null || true)"
            for lpid in $stragglers; do
                kill -9 "$lpid" >/dev/null 2>&1 || true
            done
        fi
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
