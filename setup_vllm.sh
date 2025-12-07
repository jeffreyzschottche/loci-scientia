#!/bin/bash
#
# vLLM Docker Setup Script
# Gebruikt de officiële vLLM Docker container met NVIDIA GPU support
#

set -e

# Kleuren voor output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuratie
MODEL_NAME="${MODEL_NAME:-microsoft/phi-2}"
VLLM_PORT="${VLLM_PORT:-8000}"
HF_TOKEN="${HF_TOKEN:-}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check voor Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is niet geïnstalleerd. Installeer Docker eerst:"
        echo "  https://docs.docker.com/engine/install/debian/"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon draait niet of je hebt geen toegang."
        echo "  Probeer: sudo usermod -aG docker \$USER && newgrp docker"
        exit 1
    fi

    log_info "Docker gevonden: $(docker --version)"
}

# Check voor NVIDIA Container Toolkit
check_nvidia_docker() {
    if ! docker run --rm --gpus all nvidia/cuda:12.4.0-runtime-ubuntu22.04 nvidia-smi &> /dev/null; then
        log_warn "NVIDIA Container Toolkit niet geconfigureerd of geen GPU beschikbaar."
        log_info "Installeer de NVIDIA Container Toolkit:"
        echo ""
        echo "  # Voeg NVIDIA repo toe"
        echo "  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg"
        echo "  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \\"
        echo "    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \\"
        echo "    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list"
        echo ""
        echo "  # Installeer"
        echo "  sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit"
        echo "  sudo nvidia-ctk runtime configure --runtime=docker"
        echo "  sudo systemctl restart docker"
        echo ""
        exit 1
    fi

    log_info "NVIDIA Container Toolkit werkt"
}

# Check voor docker-compose
check_compose() {
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    elif docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        log_error "docker-compose niet gevonden. Installeer het:"
        echo "  sudo apt-get install docker-compose-plugin"
        exit 1
    fi

    log_info "Compose gevonden: $COMPOSE_CMD"
}

# Genereer docker-compose.yml
generate_compose() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    COMPOSE_FILE="$SCRIPT_DIR/docker-compose.vllm.yml"

    log_info "Docker Compose configuratie genereren..."

    cat > "$COMPOSE_FILE" << EOF
version: '3.8'

services:
  vllm:
    image: vllm/vllm-openai:latest
    container_name: vllm-server
    runtime: nvidia
    ports:
      - "${VLLM_PORT}:8000"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
    command: ["--model", "${MODEL_NAME}", "--trust-remote-code"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
EOF

    log_info "Compose file aangemaakt: $COMPOSE_FILE"
}

# Start vLLM
start_vllm() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    COMPOSE_FILE="$SCRIPT_DIR/docker-compose.vllm.yml"

    log_info "vLLM container starten met model: $MODEL_NAME"
    log_info "Dit kan even duren bij de eerste keer (model wordt gedownload)..."

    cd "$SCRIPT_DIR"
    $COMPOSE_CMD -f docker-compose.vllm.yml up -d

    log_info "Container gestart!"
    echo ""
    echo "=========================================="
    echo -e "${GREEN}vLLM is gestart!${NC}"
    echo "=========================================="
    echo ""
    echo "API endpoint: http://localhost:${VLLM_PORT}"
    echo "Model: ${MODEL_NAME}"
    echo ""
    echo "Bekijk logs:"
    echo "  $COMPOSE_CMD -f docker-compose.vllm.yml logs -f"
    echo ""
    echo "Stop de server:"
    echo "  $COMPOSE_CMD -f docker-compose.vllm.yml down"
    echo ""
    echo "Test de API:"
    echo '  curl http://localhost:'"${VLLM_PORT}"'/v1/completions \'
    echo '    -H "Content-Type: application/json" \'
    echo '    -d '\''{"model": "'"${MODEL_NAME}"'", "prompt": "Hello, ", "max_tokens": 50}'\'
    echo ""
    echo "=========================================="
}

# Stop vLLM
stop_vllm() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    log_info "vLLM container stoppen..."
    cd "$SCRIPT_DIR"
    $COMPOSE_CMD -f docker-compose.vllm.yml down
    log_info "Container gestopt"
}

# Toon status
status_vllm() {
    if docker ps | grep -q vllm-server; then
        log_info "vLLM draait"
        docker ps | grep vllm-server
    else
        log_warn "vLLM draait niet"
    fi
}

# Toon logs
logs_vllm() {
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"
    $COMPOSE_CMD -f docker-compose.vllm.yml logs -f
}

# Help
show_help() {
    echo "vLLM Docker Setup Script"
    echo ""
    echo "Gebruik: $0 [commando]"
    echo ""
    echo "Commando's:"
    echo "  start   - Start vLLM server (standaard)"
    echo "  stop    - Stop vLLM server"
    echo "  restart - Herstart vLLM server"
    echo "  status  - Toon status"
    echo "  logs    - Toon container logs"
    echo "  help    - Toon deze help"
    echo ""
    echo "Environment variabelen:"
    echo "  MODEL_NAME  - Model om te laden (standaard: microsoft/phi-2)"
    echo "  VLLM_PORT   - Poort voor API (standaard: 8000)"
    echo "  HF_TOKEN    - Hugging Face token (optioneel)"
    echo ""
    echo "Voorbeelden:"
    echo "  $0 start"
    echo "  MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0 $0 start"
    echo "  HF_TOKEN=hf_xxx MODEL_NAME=google/gemma-3-4b-it $0 start"
}

# Main
main() {
    local cmd="${1:-start}"

    case "$cmd" in
        start)
            check_docker
            check_nvidia_docker
            check_compose
            generate_compose
            start_vllm
            ;;
        stop)
            check_compose
            stop_vllm
            ;;
        restart)
            check_compose
            stop_vllm
            check_docker
            check_nvidia_docker
            generate_compose
            start_vllm
            ;;
        status)
            status_vllm
            ;;
        logs)
            check_compose
            logs_vllm
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Onbekend commando: $cmd"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
