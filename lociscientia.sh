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
RESTORE_HOSTNAME_ON_EXIT="${RESTORE_HOSTNAME_ON_EXIT:-0}"
ORIGINAL_HOSTNAME=""
ORIGINAL_LOCAL_HOSTNAME=""
ORIGINAL_COMPUTER_NAME=""
SUDO_KEEPALIVE_PID=""
HAVE_SUDO=0

SEARXNG_PORT="${SEARXNG_PORT:-8888}"
SEARXNG_CONTAINER_NAME="${SEARXNG_CONTAINER_NAME:-aitje-searxng}"
SEARXNG_IMAGE="${SEARXNG_IMAGE:-searxng/searxng:latest}"
SEARXNG_DATA_DIR="${SEARXNG_DATA_DIR:-$PROJECT_ROOT/searxng_data}"
DOCKER_CMD=()
searxng_started_by_us=0
DISABLED_APT_FILES=()

BACKEND_PORT="${BACKEND_PORT:-8000}"

CADDY_AUTOSTART="${CADDY_AUTOSTART:-1}"
CADDY_HTTP_PORT="${CADDY_HTTP_PORT:-80}"
CADDY_HTTPS_PORT="${CADDY_HTTPS_PORT:-443}"
CADDY_DATA_HOME="${CADDY_DATA_HOME:-$PROJECT_ROOT/devices_db}"
CADDY_TLS_DIR="$PROJECT_ROOT/devices_db/tls"
caddy_pid=""
caddy_started=0

ensure_sudo_session() {
    if ! command -v sudo >/dev/null 2>&1; then
        return 1
    fi
    if sudo -n true 2>/dev/null; then
        :
    elif [ "$(_normalize_bool "${AITJE_KIOSK:-0}")" = "1" ] || [ ! -t 0 ]; then
        # Onbeheerd (kioskmodus onder weston / geen interactieve terminal):
        # een wachtwoordprompt kan niemand beantwoorden en zou de boot laten
        # hangen. NOPASSWD moet vooraf staan (scripts/aitje-kiosk-apply.sh enable).
        echo "⚠️  Geen passwordless sudo beschikbaar (NOPASSWD ontbreekt?); sudo-stappen worden overgeslagen."
        return 1
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

_json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

_warm_ollama_model() {
    local model_name="$1"
    local ollama_host="$2"
    local keep_alive="${OLLAMA_KEEP_ALIVE:-24h}"
    local model_json keep_alive_json payload

    model_json="$(_json_escape "$model_name")"
    keep_alive_json="$(_json_escape "$keep_alive")"
    payload="{\"model\":\"$model_json\",\"prompt\":\" \",\"stream\":false,\"keep_alive\":\"$keep_alive_json\",\"options\":{\"num_predict\":1}}"

    echo "🔥 Model $model_name warm laden (keep_alive=$keep_alive)..."
    if curl -fsS -X POST "$ollama_host/api/generate" \
        -H "Content-Type: application/json" \
        -d "$payload" >/dev/null; then
        echo "✅ Model $model_name is warmgeladen"
        return 0
    fi
    echo "⚠️  Model $model_name kon niet vooraf warmgeladen worden."
    return 1
}

running_kernel_has_headers() {
    local kernel
    kernel="$(uname -r)"
    [ -d "/usr/src/linux-headers-$kernel" ]
}

_normalize_bool() {
    local value
    value="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
    case "$value" in
        1|true|yes|on|enable|enabled) printf '1' ;;
        0|false|no|off|disable|disabled) printf '0' ;;
        *) printf '' ;;
    esac
}

_detect_vulkan_runtime() {
    if [ -e /usr/lib/x86_64-linux-gnu/libvulkan.so.1 ] \
        || [ -e /usr/lib64/libvulkan.so.1 ] \
        || [ -e /usr/lib/aarch64-linux-gnu/libvulkan.so.1 ]; then
        return 0
    fi
    if command -v ldconfig >/dev/null 2>&1 && ldconfig -p 2>/dev/null | grep -q 'libvulkan\.so\.1'; then
        return 0
    fi
    if [ -d /usr/share/vulkan/icd.d ] && ls /usr/share/vulkan/icd.d/*.json >/dev/null 2>&1; then
        return 0
    fi
    return 1
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
            if command -v ufw >/dev/null 2>&1 && sudo ufw status 2>/dev/null | grep -q "Status: active"; then
                echo "🔓 UFW-regel voor mDNS toestaan (UDP 5353 op lokaal netwerk)..."
                sudo ufw allow in on wlan0 proto udp from 192.168.0.0/16 to any port 5353 comment "AITJE mDNS" >/dev/null 2>&1 || true
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

ensure_kiosk_dependencies() {
    # Kioskmodus draait de frontend onder 'weston' (Wayland-kioskcompositor met
    # kiosk-shell). We gebruiken weston i.p.v. cage: cage 0.2.1 in Ubuntu is gelinkt
    # tegen wlroots 0.19 en crasht op een Qt-surface. Installeer weston zodat een vers
    # kastje alles in huis heeft. Alleen relevant als de dev-toggle aanstaat
    # (SHOW_KIOSK_TOGGLE=1) of we al onder weston draaien (AITJE_KIOSK=1).
    case "$DEVICE_PLATFORM" in
        linux|jetson) ;;
        *) return 0 ;;
    esac

    if [ "$(_normalize_bool "${SHOW_KIOSK_TOGGLE:-0}")" != "1" ] \
        && [ "$(_normalize_bool "${AITJE_KIOSK:-0}")" != "1" ]; then
        return 0
    fi

    if command -v weston >/dev/null 2>&1 \
        && find /usr/lib -name 'kiosk-shell.so' 2>/dev/null | grep -q .; then
        echo "✅ weston (kioskcompositor + kiosk-shell) is al geïnstalleerd"
        return 0
    fi

    if [ "$HAVE_SUDO" -ne 1 ] && [ "$(id -u)" -ne 0 ]; then
        echo "⚠️  Geen sudo/root; 'weston' wordt niet automatisch geïnstalleerd."
        return 0
    fi
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "⚠️  apt-get niet beschikbaar; sla 'weston' installatie over."
        return 0
    fi

    echo "📦 weston (Wayland-kioskcompositor) installeren..."
    if ! _wait_for_apt_lock 180; then
        echo "⚠️  apt blijft bezet; 'weston' installatie overgeslagen."
        return 0
    fi
    _disable_broken_apt_repos || true
    if [ "$(id -u)" -eq 0 ]; then
        apt-get install -y weston || echo "⚠️  weston installatie mislukt."
    else
        sudo apt-get install -y weston || echo "⚠️  weston installatie mislukt."
    fi
    _restore_disabled_apt_repos
}

ensure_kiosk_enabled() {
    # Kiosk-ACTIVATIE-beleid (systemd-service, GDM uit, GRUB zwart, NOPASSWD, marker):
    #   * SHOW_KIOSK_TOGGLE=1  → dev-/onderhoudskastje: NIET automatisch. Je zet de
    #     kiosk handmatig aan via de Qt-toggle of 'aitje-kiosk-apply.sh'.
    #   * anders (toggle verborgen) → echte appliance: kiosk wordt AUTOMATISCH
    #     geactiveerd, zodat een vers kastje met enkel './lociscientia.sh' een kiosk
    #     wordt (na een herstart).
    case "$DEVICE_PLATFORM" in
        linux|jetson) ;;
        *) return 0 ;;
    esac
    # Draaien we al ÓNDER de kiosk (weston → kiosk-session.sh → hier)? Dan is alles
    # al gezet; niets doen (anders draait elke boot opnieuw update-grub).
    if [ "$(_normalize_bool "${AITJE_KIOSK:-0}")" = "1" ]; then
        return 0
    fi
    # Dev-toggle zichtbaar → handmatig; hier niets automatisch doen.
    if [ "$(_normalize_bool "${SHOW_KIOSK_TOGGLE:-0}")" = "1" ]; then
        echo "ℹ️  SHOW_KIOSK_TOGGLE=1 → kiosk niet automatisch; gebruik de Qt-toggle."
        return 0
    fi

    local apply="$PROJECT_ROOT/scripts/aitje-kiosk-apply.sh"
    if [ ! -x "$apply" ]; then
        echo "⚠️  $apply ontbreekt/niet uitvoerbaar; kioskmodus niet geactiveerd."
        return 0
    fi
    # Al ingeschakeld? Niets doen (idempotent, geen onnodige update-grub per boot).
    if systemctl is-enabled aitje-kiosk.service >/dev/null 2>&1; then
        echo "✅ Kiosk-service is al ingeschakeld"
        return 0
    fi

    echo "🖥  Geen dev-toggle (SHOW_KIOSK_TOGGLE≠1) → kioskmodus automatisch activeren…"
    if [ "$(id -u)" -eq 0 ]; then
        "$apply" enable --force || echo "⚠️  kiosk-activatie mislukte."
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$apply" enable --force || echo "⚠️  kiosk-activatie mislukte (sudo)."
    else
        echo "⚠️  Geen root/sudo beschikbaar; draai eenmalig: sudo $apply enable --force"
        return 0
    fi
    echo "🔁 Kioskmodus ingeschakeld — HERSTART om te activeren (sudo reboot)."
}

ensure_base_dependencies() {
    # Basispakketten die het opstartscript zelf nodig heeft op een vers kastje:
    # python3-venv (anders faalt 'python3 -m venv'), pip, en een paar CLI-tools
    # die elders in dit script gebruikt worden. Idempotent: alleen ontbrekende
    # pakketten worden geïnstalleerd.
    case "$DEVICE_PLATFORM" in
        linux|jetson) ;;
        *) return 0 ;;
    esac
    if ! command -v apt-get >/dev/null 2>&1; then
        return 0
    fi
    if [ "$HAVE_SUDO" -ne 1 ] && [ "$(id -u)" -ne 0 ]; then
        echo "⚠️  Geen sudo/root; basis-dependencies worden niet automatisch geïnstalleerd."
        return 0
    fi
    local pkgs=(python3-venv python3-pip curl ca-certificates git lsof psmisc procps libcap2-bin)
    local missing=()
    local p=""
    for p in "${pkgs[@]}"; do
        if ! dpkg -s "$p" >/dev/null 2>&1; then
            missing+=("$p")
        fi
    done
    if [ "${#missing[@]}" -eq 0 ]; then
        echo "✅ Basis-dependencies zijn al geïnstalleerd"
        return 0
    fi
    echo "📦 Basis-dependencies installeren: ${missing[*]}"
    if ! _wait_for_apt_lock 180; then
        echo "⚠️  apt blijft bezet; basis-dependencies overgeslagen."
        return 0
    fi
    _disable_broken_apt_repos || true
    if [ "$(id -u)" -eq 0 ]; then
        apt-get install -y "${missing[@]}" || echo "⚠️  Installatie basis-dependencies (deels) mislukt."
    else
        sudo apt-get install -y "${missing[@]}" || echo "⚠️  Installatie basis-dependencies (deels) mislukt."
    fi
    _restore_disabled_apt_repos
}

ensure_node() {
    # Node.js + npm zijn nodig om de Nuxt webclient (/) en de embedder-SPA
    # (/embedder/) te bouwen. Zonder deze stap werd dat alleen overgeslagen met
    # een waarschuwing. We gebruiken de distro-pakketten (geen externe repo);
    # heb je een specifieke Node-versie nodig, gebruik dan NodeSource.
    case "$DEVICE_PLATFORM" in
        linux|jetson) ;;
        *) return 0 ;;
    esac
    if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        echo "✅ Node.js/npm zijn al geïnstalleerd ($(node -v 2>/dev/null))"
        return 0
    fi
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "⚠️  apt-get niet beschikbaar; Node.js/npm niet automatisch geïnstalleerd."
        return 0
    fi
    if [ "$HAVE_SUDO" -ne 1 ] && [ "$(id -u)" -ne 0 ]; then
        echo "⚠️  Geen sudo/root; Node.js/npm worden niet automatisch geïnstalleerd."
        return 0
    fi
    echo "📦 Node.js + npm installeren (voor webclient & embedder SPA)..."
    if ! _wait_for_apt_lock 180; then
        echo "⚠️  apt blijft bezet; Node.js installatie overgeslagen."
        return 0
    fi
    _disable_broken_apt_repos || true
    if [ "$(id -u)" -eq 0 ]; then
        apt-get install -y nodejs npm || echo "⚠️  Node.js/npm installatie mislukt; webclient/embedder worden niet gebouwd."
    else
        sudo apt-get install -y nodejs npm || echo "⚠️  Node.js/npm installatie mislukt; webclient/embedder worden niet gebouwd."
    fi
    _restore_disabled_apt_repos
    if command -v node >/dev/null 2>&1; then
        echo "✅ Node.js $(node -v 2>/dev/null) geïnstalleerd"
    fi
}

ensure_no_sleep_mode() {
    case "$DEVICE_PLATFORM" in
        linux|jetson)
            ;;
        *)
            return 0
            ;;
    esac

    if [ "${ENABLE_NO_SLEEP_MODE:-1}" = "0" ]; then
        echo "ℹ️  Slaapstand blokkeren is uitgeschakeld via ENABLE_NO_SLEEP_MODE=0"
        return 0
    fi

    if [ "$HAVE_SUDO" -ne 1 ] && [ "$(id -u)" -ne 0 ]; then
        echo "⚠️  Geen sudo/root; slaapstand wordt niet automatisch geblokkeerd."
        return 0
    fi

    if ! command -v systemctl >/dev/null 2>&1; then
        echo "⚠️  systemctl niet beschikbaar, slaapstand blokkeren overgeslagen."
        return 0
    fi

    echo "🔧 Slaapstand/hibernation blokkeren voor deze machine..."
    local -a systemctl_cmd=()
    if [ "$(id -u)" -eq 0 ]; then
        systemctl_cmd=(systemctl)
    else
        systemctl_cmd=(sudo systemctl)
    fi

    "${systemctl_cmd[@]}" mask sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null 2>&1 || true

    local logind_dir="/etc/systemd/logind.conf.d"
    local logind_path="$logind_dir/10-loci-scientia-no-sleep.conf"
    local tmp_logind
    tmp_logind="$(mktemp)"
    cat >"$tmp_logind" <<'EOF'
[Login]
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore
IdleAction=ignore
EOF

    if [ "$(id -u)" -eq 0 ]; then
        install -D -m 0644 "$tmp_logind" "$logind_path"
    else
        sudo install -D -m 0644 "$tmp_logind" "$logind_path"
    fi
    rm -f "$tmp_logind"

    # Restarting systemd-logind can terminate the active graphical session.
    # SIGHUP reloads logind configuration without forcing a new login.
    "${systemctl_cmd[@]}" kill -s HUP systemd-logind.service >/dev/null 2>&1 || true

    if command -v gsettings >/dev/null 2>&1; then
        gsettings set org.gnome.desktop.session idle-delay 0 >/dev/null 2>&1 || true
        gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing' >/dev/null 2>&1 || true
        gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'nothing' >/dev/null 2>&1 || true
    fi

    if command -v xset >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
        xset s off >/dev/null 2>&1 || true
        xset s noblank >/dev/null 2>&1 || true
        xset -dpms >/dev/null 2>&1 || true
    fi

    echo "✅ Slaapstand/schermblanking is geblokkeerd zonder logind herstart"
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

ensure_bluetooth_support() {
    case "$DEVICE_PLATFORM" in
        linux|jetson)
            ;;
        *)
            return 0
            ;;
    esac

    if [ "${ENABLE_BLUETOOTH_SETUP:-1}" = "0" ]; then
        echo "ℹ️  Bluetooth setup is uitgeschakeld via ENABLE_BLUETOOTH_SETUP=0"
        return 0
    fi

    if [ "$HAVE_SUDO" -ne 1 ] && [ "$(id -u)" -ne 0 ]; then
        echo "⚠️  Geen sudo/root; Bluetooth wordt niet automatisch voorbereid."
        return 0
    fi

    if command -v apt-get >/dev/null 2>&1; then
        local missing_packages=()
        local package=""
        for package in bluez bluez-obexd rfkill pipewire pipewire-pulse wireplumber libspa-0.2-bluetooth pulseaudio-utils; do
            if ! dpkg -s "$package" >/dev/null 2>&1; then
                missing_packages+=("$package")
            fi
        done
        if [ "${#missing_packages[@]}" -gt 0 ]; then
            echo "📦 Bluetooth dependencies installeren: ${missing_packages[*]}"
            if [ "$(id -u)" -eq 0 ]; then
                apt-get install -y "${missing_packages[@]}"
            else
                sudo apt-get install -y "${missing_packages[@]}"
            fi
        else
            echo "✅ Bluetooth dependencies zijn al geïnstalleerd"
        fi
    fi

    local target_user="${SUDO_USER:-${USER:-}}"
    if [ -n "$target_user" ] && id "$target_user" >/dev/null 2>&1; then
        local group=""
        for group in bluetooth netdev; do
            if getent group "$group" >/dev/null 2>&1 && ! id -nG "$target_user" | tr ' ' '\n' | grep -qx "$group"; then
                echo "🔧 Gebruiker ${target_user} toevoegen aan groep ${group}"
                if [ "$(id -u)" -eq 0 ]; then
                    usermod -aG "$group" "$target_user" || true
                else
                    sudo usermod -aG "$group" "$target_user" || true
                fi
            fi
        done
    fi

    if command -v systemctl >/dev/null 2>&1; then
        echo "🔧 Bluetooth service inschakelen en starten"
        if [ "$(id -u)" -eq 0 ]; then
            systemctl enable bluetooth >/dev/null 2>&1 || true
            systemctl start bluetooth >/dev/null 2>&1 || true
        else
            sudo systemctl enable bluetooth >/dev/null 2>&1 || true
            sudo systemctl start bluetooth >/dev/null 2>&1 || true
        fi
    fi

    if command -v rfkill >/dev/null 2>&1; then
        echo "🔓 Bluetooth rfkill blokkering opheffen"
        if [ "$(id -u)" -eq 0 ]; then
            rfkill unblock bluetooth >/dev/null 2>&1 || true
        else
            sudo rfkill unblock bluetooth >/dev/null 2>&1 || true
        fi
    fi

    if command -v bluetoothctl >/dev/null 2>&1; then
        echo "📡 Bluetooth adapter inschakelen"
        bluetoothctl power on >/dev/null 2>&1 || true
        bluetoothctl agent KeyboardDisplay >/dev/null 2>&1 || true
        bluetoothctl default-agent >/dev/null 2>&1 || true
    fi

    if command -v systemctl >/dev/null 2>&1 && [ -n "$target_user" ] && id "$target_user" >/dev/null 2>&1; then
        local uid=""
        uid="$(id -u "$target_user" 2>/dev/null || true)"
        if [ -n "$uid" ] && [ -d "/run/user/$uid" ]; then
            echo "🔊 Bluetooth audio services voor ${target_user} starten"
            if [ "$(id -u)" -eq 0 ]; then
                sudo -u "$target_user" XDG_RUNTIME_DIR="/run/user/$uid" systemctl --user enable --now pipewire pipewire-pulse wireplumber >/dev/null 2>&1 || true
            else
                sudo -u "$target_user" XDG_RUNTIME_DIR="/run/user/$uid" systemctl --user enable --now pipewire pipewire-pulse wireplumber >/dev/null 2>&1 || true
            fi
        else
            echo "ℹ️  Geen actieve user runtime gevonden; PipeWire user services starten na login."
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
                if command -v systemctl >/dev/null 2>&1; then
                    echo "♻️  avahi-daemon herstarten voor mDNS-hostname ${desired}.local"
                    sudo systemctl restart avahi-daemon >/dev/null 2>&1 || true
                fi
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

_ollama_installed_version() {
    # Print de kale versie ("0.30.5") of niets als ollama ontbreekt.
    command -v ollama >/dev/null 2>&1 || return 1
    ollama --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
}

_version_lt() {
    # _version_lt A B → waar (0) als A strikt kleiner is dan B (semver via sort -V).
    [ "$1" = "$2" ] && return 1
    local lowest
    lowest="$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -1)"
    [ "$lowest" = "$1" ]
}

_run_ollama_installer() {
    # Installeert/upgradet Ollama en pint op $OLLAMA_PIN_VERSION via OLLAMA_VERSION
    # (install.sh leest die env var: regel `VER_PARAM="${OLLAMA_VERSION:+?version=...}"`).
    # De installer upgradet in-place: hij ruimt de oude lib/ollama op en herinstalleert.
    curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION="$OLLAMA_PIN_VERSION" sh
}

install_ollama() {
    # Vanaf Ollama 0.30.0 (PR #16031) is de Go-"new engine" voor GGUF-modellen verwijderd
    # en draait ALLES via llama-server (upstream llama.cpp). Daarmee verdwijnt de bug waarbij
    # gemma4:e2b/e4b (en gemma3n) onzin produceerden op de Vulkan-iGPU — die zat in de oude
    # new-engine Vulkan-kernels. Daarom forceren we minstens 0.30.x.
    OLLAMA_MIN_VERSION="${OLLAMA_MIN_VERSION:-0.30.0}"
    # Versie die we installeren/naartoe upgraden. Overschrijfbaar via OLLAMA_VERSION in .env.
    OLLAMA_PIN_VERSION="${OLLAMA_VERSION:-0.30.5}"

    local current=""
    current="$(_ollama_installed_version || true)"

    if [ -z "$current" ]; then
        echo "📦 Ollama niet gevonden, installeren (v$OLLAMA_PIN_VERSION)..."
        if _run_ollama_installer; then
            echo "✅ Ollama v$(_ollama_installed_version) geïnstalleerd"
        else
            echo "⚠️  Ollama installatie mislukt. Mogelijk netwerk restrictie."
            echo "    Installeer Ollama handmatig: https://ollama.com/download"
            echo "    Of gebruik de mock mode voor testing."
            return 1
        fi
        return 0
    fi

    if _version_lt "$current" "$OLLAMA_MIN_VERSION"; then
        echo "♻️  Ollama $current is ouder dan $OLLAMA_MIN_VERSION → upgraden naar v$OLLAMA_PIN_VERSION"
        echo "    (op <0.30 geven gemma4/gemma3n onzin op de Vulkan-iGPU; 0.30 lost dit op via llama-server)."
        _stop_ollama || true
        if _run_ollama_installer; then
            echo "✅ Ollama geüpgraded naar v$(_ollama_installed_version)"
        else
            echo "⚠️  Ollama upgrade mislukt; huidige versie ($current) blijft actief."
            echo "    Probeer handmatig: curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=$OLLAMA_PIN_VERSION sh"
            return 1
        fi
    else
        echo "✅ Ollama $current is up-to-date (≥ $OLLAMA_MIN_VERSION)"
    fi
    return 0
}

_disable_ollama_systemd_service() {
    # install.sh maakt+enablet een systemd 'ollama'-service (luistert op :11434 met
    # Restart=always). Dit project draait ollama echter ZELF op :11435 met eigen env
    # (Vulkan/iGPU/KV-cache). De systemd-unit is dus niet alleen overbodig maar vecht
    # door Restart=always tegen onze eigen lifecycle: start_ollama doet pkill om
    # KV/Vulkan toe te passen, waarna systemd 'm meteen weer opstart op 11434 → twee
    # servers en mogelijk niets op 11435. We zetten 'm daarom uit zodat onze serve op
    # :11435 de enige bron is. Idempotent.
    command -v systemctl >/dev/null 2>&1 || return 0
    systemctl list-unit-files ollama.service >/dev/null 2>&1 || return 0
    if ! systemctl is-enabled ollama >/dev/null 2>&1 && ! systemctl is-active ollama >/dev/null 2>&1; then
        return 0
    fi
    local sysctl=(systemctl)
    if [ "$(id -u)" -ne 0 ]; then
        if [ "$HAVE_SUDO" -eq 1 ]; then
            sysctl=(sudo systemctl)
        else
            echo "ℹ️  systemd 'ollama'-service staat aan (poort 11434) maar geen sudo om 'm uit te zetten; dit project gebruikt 11435."
            return 0
        fi
    fi
    echo "🛑 systemd 'ollama'-service uitschakelen — dit project beheert ollama zelf op 11435."
    "${sysctl[@]}" disable --now ollama >/dev/null 2>&1 || true
}

ollama_pid=""
start_ollama() {
    if ! command -v ollama >/dev/null 2>&1; then
        echo "⚠️  Ollama niet beschikbaar, overslaan..."
        return 1
    fi

    _disable_ollama_systemd_service

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

    # OLLAMA_VULKAN-semantiek op Ollama ≥0.30: Vulkan is standaard AAN (auto-detect) en
    # gemma4/gemma3n draaien nu via llama-server, dus geen onzin meer op de iGPU. We forceren
    # daarom niets in auto-modus; alleen een EXPLICIETE waarde uit .env wordt doorgegeven:
    #   OLLAMA_VULKAN=""  → auto: Ollama kiest zelf (CUDA/ROCm-dGPU indien aanwezig, anders iGPU)
    #   OLLAMA_VULKAN=1   → Vulkan forceren
    #   OLLAMA_VULKAN=0   → escape-hatch: Vulkan UIT (CPU/CUDA/ROCm) als een iGPU tóch hapert
    # Belangrijk: op 0.30 móét je voor "uit" expliciet OLLAMA_VULKAN=0 exporteren — alleen
    # unsetten laat Vulkan aan, want dat is de nieuwe default.
    vulkan_pref="$(_normalize_bool "${OLLAMA_VULKAN:-}")"

    export OLLAMA_HOST="$ollama_host"
    if pgrep -x "ollama" >/dev/null 2>&1; then
        restart_reason=""
        if [ -n "$kv_cache_type" ]; then
            restart_reason="OLLAMA_KV_CACHE_TYPE=$kv_cache_type"
        fi
        if [ -n "$vulkan_pref" ]; then
            if [ -n "$restart_reason" ]; then
                restart_reason="$restart_reason, OLLAMA_VULKAN=$vulkan_pref"
            else
                restart_reason="OLLAMA_VULKAN=$vulkan_pref"
            fi
        fi
        if [ -n "$restart_reason" ]; then
            echo "♻️  Ollama herstarten om $restart_reason toe te passen..."
            if ! _stop_ollama; then
                echo "⚠️  Ollama kon niet worden gestopt; herstart overslaan."
                return 1
            fi
        else
            echo "✅ Ollama draait al"
            _warm_ollama_model "$MODEL_NAME" "$ollama_host" || true
            return 0
        fi
    fi

    echo "⏳ Ollama server starten..."
    if [ -n "$kv_cache_type" ]; then
        export OLLAMA_KV_CACHE_TYPE="$kv_cache_type"
        echo "✅ OLLAMA_KV_CACHE_TYPE=$OLLAMA_KV_CACHE_TYPE"
    else
        unset OLLAMA_KV_CACHE_TYPE
    fi
    if [ -n "$vulkan_pref" ]; then
        export OLLAMA_VULKAN="$vulkan_pref"
        if [ "$vulkan_pref" = "1" ]; then
            echo "✅ OLLAMA_VULKAN=1 (Vulkan geforceerd)"
        else
            echo "✅ OLLAMA_VULKAN=0 (Vulkan uit → CPU/CUDA/ROCm)"
        fi
    else
        unset OLLAMA_VULKAN
        echo "🟣 OLLAMA_VULKAN niet gezet → Ollama auto-detect (Vulkan standaard aan op ≥0.30; iGPU wordt gepakt indien nodig)"
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
    _warm_ollama_model "$MODEL_NAME" "$ollama_host" || true
    return 0
}

detect_docker_cmd() {
    DOCKER_CMD=()
    if ! command -v docker >/dev/null 2>&1; then
        return 1
    fi
    if [ "$(id -u)" -eq 0 ] || (id -nG 2>/dev/null | tr ' ' '\n' | grep -qx docker); then
        DOCKER_CMD=(docker)
        return 0
    fi
    if docker info >/dev/null 2>&1; then
        DOCKER_CMD=(docker)
        return 0
    fi
    if [ "$HAVE_SUDO" -eq 1 ]; then
        DOCKER_CMD=(sudo docker)
        return 0
    fi
    return 1
}

_disable_broken_apt_repos() {
    DISABLED_APT_FILES=()
    if [ "$HAVE_SUDO" -ne 1 ]; then
        return 0
    fi
    local update_output
    update_output="$(sudo apt-get update 2>&1 || true)"
    local broken
    broken="$(printf '%s\n' "$update_output" \
        | grep -E "does not have a Release file|404\s+Not Found|NO_PUBKEY|Failed to fetch" \
        || true)"
    if [ -z "$broken" ]; then
        return 0
    fi
    local urls
    urls="$(printf '%s\n' "$broken" \
        | grep -oE "https?://[^[:space:]'\"]+" \
        | sed -E 's|^https?://||' \
        | sort -u)"
    [ -z "$urls" ] && return 0
    while IFS= read -r prefix; do
        [ -z "$prefix" ] && continue
        for f in /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
            [ -e "$f" ] || continue
            case "$f" in *.disabled-aitje) continue ;; esac
            if sudo grep -Fq "$prefix" "$f" 2>/dev/null; then
                if sudo mv "$f" "$f.disabled-aitje" 2>/dev/null; then
                    DISABLED_APT_FILES+=("$f.disabled-aitje")
                    echo "ℹ️  Tijdelijk uitgezet: $(basename "$f") (gebroken repo: $prefix)"
                fi
            fi
        done
    done <<< "$urls"
    return 0
}

_restore_disabled_apt_repos() {
    if [ "${#DISABLED_APT_FILES[@]}" -eq 0 ]; then
        return 0
    fi
    for f in "${DISABLED_APT_FILES[@]}"; do
        local original="${f%.disabled-aitje}"
        if [ -e "$f" ]; then
            sudo mv "$f" "$original" >/dev/null 2>&1 || true
            echo "ℹ️  Hersteld: $(basename "$original")"
        fi
    done
    DISABLED_APT_FILES=()
}

_wait_for_apt_lock() {
    local max_wait=${1:-180}
    local waited=0
    local locks=(
        /var/lib/dpkg/lock-frontend
        /var/lib/dpkg/lock
        /var/lib/apt/lists/lock
        /var/cache/apt/archives/lock
    )
    if ! command -v fuser >/dev/null 2>&1; then
        return 0
    fi
    while [ "$waited" -lt "$max_wait" ]; do
        local busy=0
        local owner=""
        for lock in "${locks[@]}"; do
            [ -e "$lock" ] || continue
            if sudo fuser "$lock" >/dev/null 2>&1; then
                busy=1
                owner="$(sudo fuser "$lock" 2>/dev/null | awk '{print $1}')"
                break
            fi
        done
        if [ "$busy" -eq 0 ]; then
            if [ "$waited" -gt 0 ]; then
                echo "✅ apt-lock vrijgegeven, doorgaan."
            fi
            return 0
        fi
        if [ "$waited" -eq 0 ]; then
            local owner_cmd=""
            if [ -n "$owner" ]; then
                owner_cmd="$(ps -p "$owner" -o cmd= 2>/dev/null || true)"
            fi
            if [ -n "$owner_cmd" ]; then
                echo "⏳ apt is bezet door PID $owner ($owner_cmd); wachten tot het klaar is (max ${max_wait}s)..."
            else
                echo "⏳ apt is bezet door een ander proces; wachten tot het klaar is (max ${max_wait}s)..."
            fi
        fi
        sleep 3
        waited=$((waited + 3))
    done
    return 1
}

install_docker() {
    case "$DEVICE_PLATFORM" in
        linux|jetson)
            if command -v docker >/dev/null 2>&1; then
                echo "✅ Docker is al geïnstalleerd"
            else
                echo "📦 Docker niet gevonden, proberen te installeren via get.docker.com..."
                if [ "$HAVE_SUDO" -ne 1 ]; then
                    echo "⚠️  Geen sudo-toegang; kan Docker niet automatisch installeren."
                    return 1
                fi
                if ! _wait_for_apt_lock 180; then
                    echo "⚠️  apt blijft bezet (waarschijnlijk unattended-upgrade). Probeer het script later opnieuw, of stop het andere proces handmatig."
                    return 1
                fi
                _disable_broken_apt_repos || true
                local docker_install_rc=0
                if ! curl -fsSL https://get.docker.com | sudo sh; then
                    docker_install_rc=1
                fi
                _restore_disabled_apt_repos
                if [ "$docker_install_rc" -ne 0 ]; then
                    echo "⚠️  Docker installatie mislukt. Installeer Docker handmatig: https://docs.docker.com/engine/install/"
                    return 1
                fi
                echo "✅ Docker geïnstalleerd"
            fi
            if command -v systemctl >/dev/null 2>&1; then
                if ! systemctl is-active --quiet docker 2>/dev/null; then
                    if [ "$HAVE_SUDO" -eq 1 ]; then
                        echo "⏳ Docker daemon starten..."
                        sudo systemctl enable --now docker >/dev/null 2>&1 || true
                    fi
                fi
            fi
            if [ -n "${USER:-}" ] && ! id -nG "$USER" 2>/dev/null | tr ' ' '\n' | grep -qx docker; then
                if [ "$HAVE_SUDO" -eq 1 ]; then
                    if sudo usermod -aG docker "$USER" >/dev/null 2>&1; then
                        echo "ℹ️  $USER toegevoegd aan docker-group (effect na uitloggen; sudo wordt gebruikt voor nu)."
                    fi
                fi
            fi
            return 0
            ;;
        macos)
            if command -v docker >/dev/null 2>&1; then
                return 0
            fi
            echo "⚠️  Docker niet gevonden. Installeer Docker Desktop voor macOS:"
            echo "    https://www.docker.com/products/docker-desktop"
            return 1
            ;;
        *)
            command -v docker >/dev/null 2>&1
            ;;
    esac
}

ensure_searxng_settings() {
    mkdir -p "$SEARXNG_DATA_DIR"
    local settings="$SEARXNG_DATA_DIR/settings.yml"
    if [ -s "$settings" ]; then
        return 0
    fi
    local secret=""
    if command -v openssl >/dev/null 2>&1; then
        secret="$(openssl rand -hex 32 2>/dev/null || true)"
    fi
    if [ -z "$secret" ] && command -v python3 >/dev/null 2>&1; then
        secret="$(python3 -c 'import secrets;print(secrets.token_hex(32))' 2>/dev/null || true)"
    fi
    if [ -z "$secret" ]; then
        secret="$(date +%s%N | sha256sum | cut -c1-64)"
    fi
    cat > "$settings" <<EOF
use_default_settings: true
server:
  secret_key: "$secret"
  limiter: false
  image_proxy: true
  bind_address: "0.0.0.0"
search:
  formats:
    - html
    - json
ui:
  default_locale: nl
EOF
    chmod 0644 "$settings" 2>/dev/null || true
}

_wait_for_searxng() {
    local url="http://127.0.0.1:${SEARXNG_PORT}/search?q=ping&format=json"
    for _ in {1..40}; do
        if curl -fs -o /dev/null "$url"; then
            return 0
        fi
        sleep 0.5
    done
    return 1
}

start_searxng() {
    if [ -n "${SEARXNG_URL:-}" ]; then
        echo "ℹ️  SEARXNG_URL al gezet ($SEARXNG_URL); externe instance wordt gebruikt."
        return 0
    fi
    local autostart_raw
    autostart_raw="$(_normalize_bool "${SEARXNG_AUTOSTART:-1}")"
    if [ "$autostart_raw" = "0" ]; then
        echo "ℹ️  SEARXNG_AUTOSTART=0; web search blijft uit."
        return 1
    fi
    if ! detect_docker_cmd; then
        if ! install_docker; then
            echo "⚠️  Docker niet beschikbaar; SearXNG wordt niet gestart."
            return 1
        fi
        if ! detect_docker_cmd; then
            echo "⚠️  Docker is geïnstalleerd maar nog niet bruikbaar (mogelijk opnieuw inloggen voor docker-group)."
            return 1
        fi
    fi
    if ! "${DOCKER_CMD[@]}" info >/dev/null 2>&1; then
        echo "⚠️  Docker daemon reageert niet; SearXNG overslaan."
        return 1
    fi

    ensure_searxng_settings

    local existing
    existing="$("${DOCKER_CMD[@]}" ps -aq -f "name=^${SEARXNG_CONTAINER_NAME}$" 2>/dev/null || true)"
    if [ -n "$existing" ]; then
        if "${DOCKER_CMD[@]}" ps -q -f "name=^${SEARXNG_CONTAINER_NAME}$" | grep -q .; then
            echo "✅ SearXNG container '${SEARXNG_CONTAINER_NAME}' draait al"
        else
            echo "⏳ SearXNG container '${SEARXNG_CONTAINER_NAME}' herstarten..."
            "${DOCKER_CMD[@]}" start "$SEARXNG_CONTAINER_NAME" >/dev/null
            searxng_started_by_us=1
        fi
    else
        echo "📦 SearXNG image ophalen ($SEARXNG_IMAGE)..."
        "${DOCKER_CMD[@]}" pull "$SEARXNG_IMAGE" >/dev/null 2>&1 || true
        echo "⏳ SearXNG container starten op poort $SEARXNG_PORT..."
        if ! "${DOCKER_CMD[@]}" run -d \
            --name "$SEARXNG_CONTAINER_NAME" \
            --restart unless-stopped \
            -p "127.0.0.1:${SEARXNG_PORT}:8080" \
            -v "$SEARXNG_DATA_DIR:/etc/searxng" \
            -e "BASE_URL=http://127.0.0.1:${SEARXNG_PORT}/" \
            -e "INSTANCE_NAME=aitje" \
            "$SEARXNG_IMAGE" >/dev/null; then
            echo "⚠️  Kon SearXNG container niet starten."
            return 1
        fi
        searxng_started_by_us=1
    fi

    if ! _wait_for_searxng; then
        echo "⚠️  SearXNG kwam niet binnen tijd online (poort $SEARXNG_PORT). Check 'docker logs $SEARXNG_CONTAINER_NAME'."
        return 1
    fi
    export SEARXNG_URL="http://127.0.0.1:${SEARXNG_PORT}"
    echo "✅ SearXNG online → SEARXNG_URL=$SEARXNG_URL"
    return 0
}

ensure_caddy() {
    # Returns 0 if a foreground Caddy was started successfully (CA cert ready);
    # nonzero otherwise. On success: $caddy_pid is set, $caddy_started=1,
    # CA cert lives at $CADDY_TLS_DIR/ca.crt.
    if [ "$(_normalize_bool "$CADDY_AUTOSTART")" = "0" ]; then
        echo "ℹ️  CADDY_AUTOSTART=0; HTTPS reverse proxy uitgeschakeld."
        return 1
    fi
    case "$DEVICE_PLATFORM" in
        linux|jetson) ;;
        *)
            echo "ℹ️  Caddy autostart wordt alleen op Linux ondersteund; HTTPS overgeslagen."
            return 1
            ;;
    esac

    if ! command -v caddy >/dev/null 2>&1; then
        if [ "$HAVE_SUDO" -ne 1 ] || ! command -v apt-get >/dev/null 2>&1; then
            echo "⚠️  Caddy niet gevonden en kan niet via apt geïnstalleerd worden."
            return 1
        fi
        echo "📦 Caddy installeren via apt..."
        if ! _wait_for_apt_lock 180; then
            echo "⚠️  apt blijft bezet; Caddy installatie overgeslagen."
            return 1
        fi
        _disable_broken_apt_repos || true
        local apt_rc=0
        if ! sudo apt-get install -y caddy 2>/dev/null; then
            apt_rc=1
            echo "📦 Caddy zit niet in de default repos, voeg cloudsmith toe..."
            if ! command -v gpg >/dev/null 2>&1; then
                sudo apt-get install -y gnupg >/dev/null 2>&1 || true
            fi
            if ! command -v curl >/dev/null 2>&1; then
                sudo apt-get install -y curl >/dev/null 2>&1 || true
            fi
            sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https >/dev/null 2>&1 || true
            local key_path=/usr/share/keyrings/caddy-stable-archive-keyring.gpg
            local list_path=/etc/apt/sources.list.d/caddy-stable.list
            if [ ! -f "$key_path" ]; then
                curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
                    | sudo gpg --dearmor -o "$key_path" >/dev/null 2>&1 || true
            fi
            if [ ! -f "$list_path" ]; then
                curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
                    | sudo tee "$list_path" >/dev/null 2>&1 || true
            fi
            sudo apt-get update -y >/dev/null 2>&1 || true
            if sudo apt-get install -y caddy; then
                apt_rc=0
            fi
        fi
        _restore_disabled_apt_repos
        if [ "$apt_rc" -ne 0 ]; then
            echo "⚠️  Caddy installatie mislukt."
            return 1
        fi
    fi

    local caddy_bin
    caddy_bin="$(command -v caddy)"

    # setcap so a non-root Caddy can bind privileged ports (80/443).
    if [ "$CADDY_HTTP_PORT" -lt 1024 ] || [ "$CADDY_HTTPS_PORT" -lt 1024 ]; then
        if command -v setcap >/dev/null 2>&1 && [ "$HAVE_SUDO" -eq 1 ]; then
            local current_caps
            current_caps="$(sudo getcap "$caddy_bin" 2>/dev/null || true)"
            if [[ "$current_caps" != *"cap_net_bind_service"* ]]; then
                if sudo setcap cap_net_bind_service=+ep "$caddy_bin" 2>/dev/null; then
                    echo "🔒 setcap cap_net_bind_service op ${caddy_bin}."
                else
                    echo "⚠️  setcap mislukt; Caddy kan poort <1024 mogelijk niet binden."
                fi
            fi
        fi
    fi

    # The apt package enables caddy.service by default; stop it so we own
    # the listening sockets ourselves (and write data under our project tree).
    if [ "$HAVE_SUDO" -eq 1 ] && command -v systemctl >/dev/null 2>&1; then
        if systemctl is-active --quiet caddy 2>/dev/null; then
            echo "🛑 Bestaande caddy.service stoppen (we runnen onze eigen instance)..."
            sudo systemctl stop caddy >/dev/null 2>&1 || true
            sudo systemctl disable caddy >/dev/null 2>&1 || true
        fi
    fi

    # Kill a foreground caddy left behind by a previous run (otherwise it
    # would already hold :80/:443 and our new instance would fail to bind).
    if [ -f "$PROJECT_ROOT/caddy.pid" ]; then
        local prev_pid
        prev_pid="$(cat "$PROJECT_ROOT/caddy.pid" 2>/dev/null || true)"
        if [ -n "$prev_pid" ] && kill -0 "$prev_pid" 2>/dev/null; then
            echo "🛑 Eerder gestarte Caddy (pid $prev_pid) stoppen..."
            kill "$prev_pid" 2>/dev/null || true
            sleep 1
        fi
        rm -f "$PROJECT_ROOT/caddy.pid" >/dev/null 2>&1 || true
    fi

    mkdir -p "$CADDY_DATA_HOME" "$CADDY_TLS_DIR"

    local caddyfile="$CADDY_TLS_DIR/Caddyfile"
    cat > "$caddyfile" <<EOF
{
    auto_https disable_redirects
    admin off
}

(bootstrap_paths) {
    @bootstrap path /connect /connect/* /ca.crt /aitje-ca.mobileconfig
    handle @bootstrap {
        reverse_proxy 127.0.0.1:${BACKEND_PORT:-8000}
    }
}

http://${DEVICE_MDNS}:${CADDY_HTTP_PORT} {
    import bootstrap_paths
    handle {
        redir https://${DEVICE_MDNS}{uri} permanent
    }
}

http://:${CADDY_HTTP_PORT} {
    import bootstrap_paths
    handle {
        redir https://${DEVICE_MDNS}{uri} permanent
    }
}

https://${DEVICE_MDNS}:${CADDY_HTTPS_PORT} {
    tls internal
    encode zstd gzip
    reverse_proxy 127.0.0.1:${BACKEND_PORT:-8000} {
        header_up X-Forwarded-Proto https
        header_up X-Forwarded-Host {host}
    }
}
EOF

    if ! XDG_DATA_HOME="$CADDY_DATA_HOME" "$caddy_bin" validate \
            --config "$caddyfile" --adapter caddyfile >/dev/null 2>&1; then
        echo "⚠️  Caddyfile validatie mislukt:"
        XDG_DATA_HOME="$CADDY_DATA_HOME" "$caddy_bin" validate \
            --config "$caddyfile" --adapter caddyfile 2>&1 | sed 's/^/    /'
        return 1
    fi

    echo "⏳ Caddy starten op :${CADDY_HTTP_PORT}/:${CADDY_HTTPS_PORT}..."
    XDG_DATA_HOME="$CADDY_DATA_HOME" \
        "$caddy_bin" run --config "$caddyfile" --adapter caddyfile \
        > "$PROJECT_ROOT/caddy.log" 2>&1 &
    caddy_pid=$!
    echo "$caddy_pid" > "$PROJECT_ROOT/caddy.pid" 2>/dev/null || true

    local ca_src="$CADDY_DATA_HOME/caddy/pki/authorities/local/root.crt"
    local i
    for i in {1..30}; do
        if ! kill -0 "$caddy_pid" 2>/dev/null; then
            echo "⚠️  Caddy crashte tijdens start — check caddy.log."
            return 1
        fi
        if [ -f "$ca_src" ]; then
            cp -f "$ca_src" "$CADDY_TLS_DIR/ca.crt" 2>/dev/null || true
            chmod 0644 "$CADDY_TLS_DIR/ca.crt" 2>/dev/null || true
            echo "✅ Caddy actief; root CA → http://${DEVICE_MDNS}/ca.crt"
            export AITJE_CA_CERT_PATH="$CADDY_TLS_DIR/ca.crt"
            export CADDY_HTTP_PORT CADDY_HTTPS_PORT
            caddy_started=1
            return 0
        fi
        sleep 0.5
    done
    echo "⚠️  Caddy startte maar het interne CA-cert kwam niet op tijd."
    return 1
}

echo "=== Netwerk & mDNS setup ==="
ensure_mdns_support
ensure_active_wifi_profile_persistence
ensure_bluetooth_support
ensure_no_sleep_mode
ensure_remote_support_dependencies
ensure_remote_support_service
ensure_kiosk_dependencies
ensure_kiosk_enabled
configure_hostname
echo "🌐 Publieke hostnaam: ${DEVICE_MDNS}"
echo "============================="
echo

echo "=== Basis-dependencies (Python venv, Node.js, CLI-tools) ==="
ensure_base_dependencies
ensure_node
echo "============================================================"
echo

echo "=== Ollama Setup ==="
if install_ollama; then
    start_ollama || echo "⚠️  Kon Ollama niet starten, app draait zonder LLM support"
else
    echo "⚠️  App draait zonder Ollama support"
fi
echo "===================="
echo

echo "=== SearXNG Setup ==="
if ! start_searxng; then
    echo "⚠️  Web search blijft uit (toggle in de UI heeft dan geen effect)."
fi
echo "====================="
echo

# Caddy must be probed *before* uvicorn so we know whether to bind loopback
# (HTTPS via reverse proxy) or 0.0.0.0 (fallback, plain HTTP on $BACKEND_PORT).
echo "=== Caddy HTTPS reverse proxy ==="
ensure_caddy || true
echo "================================="
echo

BACKEND_PORT="${BACKEND_PORT:-8000}"

if [ "$caddy_started" -eq 1 ]; then
    # LAN clients reach the device via Caddy on :80/:443 only. Uvicorn binds
    # loopback so plain HTTP on :8000 isn't exposed beyond the device itself.
    BACKEND_BIND_HOST="${BACKEND_BIND_HOST:-127.0.0.1}"
    BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
    BACKEND_HTTP="${BACKEND_HTTP:-http://127.0.0.1:$BACKEND_PORT}"
    BACKEND_WS="${BACKEND_WS:-ws://127.0.0.1:$BACKEND_PORT/ws}"
    if [ "$CADDY_HTTPS_PORT" = "443" ]; then
        PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://$DEVICE_MDNS}"
    else
        PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://$DEVICE_MDNS:$CADDY_HTTPS_PORT}"
    fi
    if [ "$CADDY_HTTP_PORT" = "80" ]; then
        SETUP_URL="${SETUP_URL:-http://$DEVICE_MDNS/connect}"
    else
        SETUP_URL="${SETUP_URL:-http://$DEVICE_MDNS:$CADDY_HTTP_PORT/connect}"
    fi
else
    # Fallback: no TLS, bind uvicorn publicly on $BACKEND_PORT (legacy path).
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
    if [ -z "${BACKEND_HTTP:-}" ] || [[ "$BACKEND_HTTP" == http://127.0.0.1* ]] || [[ "$BACKEND_HTTP" == http://localhost* ]]; then
        BACKEND_HTTP="http://$BACKEND_HOST:$BACKEND_PORT"
    fi
    if [ -z "${BACKEND_WS:-}" ]; then
        BACKEND_WS="ws://$BACKEND_HOST:$BACKEND_PORT/ws"
    fi
    if [ -z "${PUBLIC_BASE_URL:-}" ] || [[ "$PUBLIC_BASE_URL" == http://127.0.0.1* ]] || [[ "$PUBLIC_BASE_URL" == http://localhost* ]]; then
        PUBLIC_BASE_URL="http://$DEVICE_MDNS:$BACKEND_PORT"
    fi
    SETUP_URL="${SETUP_URL:-http://$DEVICE_MDNS:$BACKEND_PORT/connect}"
fi
export BACKEND_HOST BACKEND_BIND_HOST BACKEND_PORT BACKEND_HTTP BACKEND_WS PUBLIC_BASE_URL SETUP_URL
export CADDY_HTTP_PORT CADDY_HTTPS_PORT

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

if [ ! -f ".venv/.requirements_installed" ] || [ "app/requirements.txt" -nt ".venv/.requirements_installed" ]; then
    python -m pip install -U pip
    python -m pip install -r app/requirements.txt
    touch .venv/.requirements_installed
fi

if ! python - <<'PY' >/dev/null 2>&1
import fastembed
import qdrant_client
import uvicorn
import PySide6
PY
then
    echo "⚠️  .venv mist backend/RAG dependencies; requirements opnieuw installeren..."
    python -m pip install -U pip
    python -m pip install -r app/requirements.txt
    touch .venv/.requirements_installed
fi

# --- LAN web client (Nuxt SPA) build -----------------------------------------
# Static SPA mounted by FastAPI at /. We build only when source changed since
# the last successful generate, so normal restarts stay fast.
WEBCLIENT_DIR="$PROJECT_ROOT/app/webclient"
WEBCLIENT_DIST_INDEX="$WEBCLIENT_DIR/.output/public/index.html"
if [ -d "$WEBCLIENT_DIR" ]; then
    if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
        echo "⚠️  Node.js/npm niet gevonden — sla webclient-build over. Installeer Node 20+ om de browserclient op ${PUBLIC_BASE_URL}/ te hosten."
    else
        webclient_stamp="$WEBCLIENT_DIR/.output/.build-stamp"
        webclient_inputs=(
            "$WEBCLIENT_DIR/package.json"
            "$WEBCLIENT_DIR/package-lock.json"
            "$WEBCLIENT_DIR/nuxt.config.ts"
            "$WEBCLIENT_DIR/tailwind.config.ts"
            "$WEBCLIENT_DIR/tsconfig.json"
        )
        webclient_needs_build=0
        if [ ! -f "$WEBCLIENT_DIST_INDEX" ] || [ ! -f "$webclient_stamp" ]; then
            webclient_needs_build=1
        else
            for input in "${webclient_inputs[@]}"; do
                if [ -f "$input" ] && [ "$input" -nt "$webclient_stamp" ]; then
                    webclient_needs_build=1
                    break
                fi
            done
            if [ "$webclient_needs_build" -eq 0 ]; then
                if find "$WEBCLIENT_DIR/app" "$WEBCLIENT_DIR/public" -type f -newer "$webclient_stamp" 2>/dev/null | grep -q .; then
                    webclient_needs_build=1
                fi
            fi
        fi

        if [ "$webclient_needs_build" -eq 1 ]; then
            echo "📦 Webclient build (Nuxt) — kan even duren…"
            (
                cd "$WEBCLIENT_DIR" || exit 1
                if [ ! -d "node_modules" ]; then
                    npm install --no-audit --no-fund
                fi
                npm run generate
            )
            if [ -f "$WEBCLIENT_DIST_INDEX" ]; then
                touch "$webclient_stamp"
                echo "✅ Webclient klaar — bereikbaar op ${PUBLIC_BASE_URL}/"
            else
                echo "⚠️  Webclient build mislukt; FastAPI start zonder SPA."
            fi
        else
            echo "✅ Webclient up-to-date — bereikbaar op ${PUBLIC_BASE_URL}/"
        fi
    fi
fi

# --- Embedder app (Nuxt SPA, FastAPI backend in-process) ----------------------
# De Aitje Embedding Application is volledig geport naar FastAPI
# (zie app/backend/embedder/). Er draait geen los Laravel-proces meer; de API
# wordt mee gestart door uvicorn onder /embedder/api/v1/*. Dit blok bouwt nog
# alleen de Nuxt SPA, statisch gegenereerd naar
# app/embedder/frontend/.output/public en gemount op /embedder/ door FastAPI.

EMBEDDER_FRONTEND_DIR="$PROJECT_ROOT/app/embedder/frontend"
EMBEDDER_FRONTEND_DIST_INDEX="$EMBEDDER_FRONTEND_DIR/.output/public/index.html"

build_embedder_spa() {
    if [ ! -d "$EMBEDDER_FRONTEND_DIR" ]; then
        echo "ℹ️  Geen app/embedder/frontend gevonden, embedder-SPA overslaan."
        return 1
    fi
    if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
        echo "⚠️  Node.js/npm niet gevonden — embedder SPA wordt niet gebouwd."
        return 1
    fi

    local stamp="$EMBEDDER_FRONTEND_DIR/.output/.build-stamp"
    local inputs=(
        "$EMBEDDER_FRONTEND_DIR/package.json"
        "$EMBEDDER_FRONTEND_DIR/package-lock.json"
        "$EMBEDDER_FRONTEND_DIR/nuxt.config.ts"
        "$EMBEDDER_FRONTEND_DIR/tailwind.config.ts"
        "$EMBEDDER_FRONTEND_DIR/tsconfig.json"
    )
    local needs_build=0
    if [ ! -f "$EMBEDDER_FRONTEND_DIST_INDEX" ] || [ ! -f "$stamp" ]; then
        needs_build=1
    else
        for input in "${inputs[@]}"; do
            if [ -f "$input" ] && [ "$input" -nt "$stamp" ]; then
                needs_build=1
                break
            fi
        done
        if [ "$needs_build" -eq 0 ]; then
            if find \
                "$EMBEDDER_FRONTEND_DIR/app.vue" \
                "$EMBEDDER_FRONTEND_DIR/pages" \
                "$EMBEDDER_FRONTEND_DIR/components" \
                "$EMBEDDER_FRONTEND_DIR/composables" \
                "$EMBEDDER_FRONTEND_DIR/layouts" \
                "$EMBEDDER_FRONTEND_DIR/middleware" \
                "$EMBEDDER_FRONTEND_DIR/plugins" \
                "$EMBEDDER_FRONTEND_DIR/services" \
                "$EMBEDDER_FRONTEND_DIR/stores" \
                "$EMBEDDER_FRONTEND_DIR/types" \
                "$EMBEDDER_FRONTEND_DIR/assets" \
                "$EMBEDDER_FRONTEND_DIR/public" \
                -type f -newer "$stamp" 2>/dev/null | grep -q .; then
                needs_build=1
            fi
        fi
    fi

    if [ "$needs_build" -eq 1 ]; then
        echo "📦 Embedder SPA build (Nuxt) — kan even duren…"
        (
            cd "$EMBEDDER_FRONTEND_DIR" || exit 1
            if [ ! -d "node_modules" ]; then
                npm install --no-audit --no-fund
            fi
            npm run generate
        )
        if [ -f "$EMBEDDER_FRONTEND_DIST_INDEX" ]; then
            touch "$stamp"
            echo "✅ Embedder SPA klaar"
            return 0
        fi
        echo "⚠️  Embedder SPA build mislukt; /embedder wordt niet gemount."
        return 1
    fi
    echo "✅ Embedder SPA up-to-date"
    return 0
}

echo "=== Embedder Setup ==="
if ! build_embedder_spa; then
    echo "⚠️  /embedder is niet beschikbaar in deze sessie."
fi
echo "======================"
echo

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
    if [ -n "${backend_pid:-}" ]; then
        echo "🛑 Backend stoppen..."
        kill "$backend_pid" >/dev/null 2>&1 || true
    fi

    if [ -n "${caddy_pid:-}" ]; then
        echo "🛑 Caddy stoppen..."
        kill "$caddy_pid" >/dev/null 2>&1 || true
        rm -f "$PROJECT_ROOT/caddy.pid" >/dev/null 2>&1 || true
    fi

    if [ -n "${ollama_pid:-}" ]; then
        echo "🛑 Ollama stoppen..."
        kill "$ollama_pid" >/dev/null 2>&1 || true
    fi

    if [ "$searxng_started_by_us" -eq 1 ] && [ "$(_normalize_bool "${SEARXNG_STOP_ON_EXIT:-0}")" = "1" ]; then
        if [ ${#DOCKER_CMD[@]} -gt 0 ]; then
            echo "🛑 SearXNG container stoppen..."
            "${DOCKER_CMD[@]}" stop "$SEARXNG_CONTAINER_NAME" >/dev/null 2>&1 || true
        fi
    fi

    _restore_disabled_apt_repos >/dev/null 2>&1 || true

    case "$DEVICE_PLATFORM" in
        linux|jetson)
            if [ "$RESTORE_HOSTNAME_ON_EXIT" = "1" ] && [ -n "${ORIGINAL_HOSTNAME:-}" ]; then
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

health_host="$BACKEND_HOST"
if [ "$BACKEND_BIND_HOST" = "127.0.0.1" ] || [ "$BACKEND_BIND_HOST" = "localhost" ]; then
    health_host="127.0.0.1"
fi
health_url="http://$health_host:$BACKEND_PORT/health"
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

# In kioskmodus beheert systemd (via weston) de levenscyclus: zodra de frontend
# stopt of crasht, laten we dit script ook stoppen zodat de cleanup-trap draait
# en systemd de hele stack opnieuw start. Buiten kiosk blijven we wachten op de
# backend, zoals voorheen.
if [ "$(_normalize_bool "${AITJE_KIOSK:-0}")" = "1" ]; then
    exit 0
fi

wait "$backend_pid"
