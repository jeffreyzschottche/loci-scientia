#!/bin/bash
#
# TensorRT-LLM Setup Script for Jetson Orin Nano (JetPack 6.2)
# Downloads Gemma 3 1B, converts to TensorRT-LLM INT4 engine, and starts OpenAI-compatible API
#
set -e

# ==================== CONFIGURATION ====================
MODEL_NAME="google/gemma-3-1b-it"
MODEL_DIR="/opt/tensorrt-llm/models"
ENGINE_DIR="/opt/tensorrt-llm/engines/gemma3-1b-int4"
CACHE_DIR="/opt/tensorrt-llm/cache"
LOG_FILE="/var/log/tensorrt-llm.log"

# API Server Configuration
API_HOST="0.0.0.0"
API_PORT="8000"

# Quantization settings for Orin Nano 8GB
QUANTIZATION="int4_awq"
MAX_BATCH_SIZE=1
MAX_INPUT_LEN=2048
MAX_OUTPUT_LEN=1024

# Container settings
CONTAINER_NAME="tensorrt-llm-server"
JETSON_CONTAINER="dustynv/tensorrt_llm:0.12-r36.4.0"

# HuggingFace token for gated models
HF_TOKEN="${HF_TOKEN:-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}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==================== HELPER FUNCTIONS ====================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_jetson() {
    log_info "Checking Jetson platform..."

    if [ ! -f /etc/nv_tegra_release ]; then
        log_error "This script is designed for NVIDIA Jetson platforms only."
    fi

    # Check JetPack version
    JETPACK_VERSION=$(cat /etc/nv_tegra_release | head -1 | grep -oP 'R\d+' | sed 's/R//')
    log_info "Detected L4T R${JETPACK_VERSION} (JetPack 6.x)"

    # Check available memory
    TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
    log_info "Total system memory: ${TOTAL_MEM}GB"

    if [ "$TOTAL_MEM" -lt 7 ]; then
        log_warn "Less than 8GB RAM detected. Performance may be limited."
    fi
}

check_docker() {
    log_info "Checking Docker installation..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first:
        sudo apt-get update
        sudo apt-get install -y docker.io
        sudo usermod -aG docker \$USER"
    fi

    # Check NVIDIA runtime
    if ! docker info 2>/dev/null | grep -q "nvidia"; then
        log_warn "NVIDIA Docker runtime not detected. Installing..."
        sudo apt-get update
        sudo apt-get install -y nvidia-container-toolkit
        sudo systemctl restart docker
    fi

    log_info "Docker is ready with NVIDIA runtime."
}

setup_directories() {
    log_info "Setting up directories..."

    sudo mkdir -p "$MODEL_DIR"
    sudo mkdir -p "$ENGINE_DIR"
    sudo mkdir -p "$CACHE_DIR"
    sudo mkdir -p "$(dirname $LOG_FILE)"

    sudo chown -R $USER:$USER "$MODEL_DIR"
    sudo chown -R $USER:$USER "$ENGINE_DIR"
    sudo chown -R $USER:$USER "$CACHE_DIR"

    log_info "Directories created successfully."
}

pull_container() {
    log_info "Pulling TensorRT-LLM container for Jetson..."
    log_info "Container: $JETSON_CONTAINER"
    log_info "This may take a while on first run..."

    docker pull "$JETSON_CONTAINER"

    log_info "Container pulled successfully."
}

download_model() {
    log_info "Downloading Gemma 3 1B model from HuggingFace..."

    # Check if model already exists
    if [ -d "$MODEL_DIR/gemma-3-1b-it" ] && [ "$(ls -A $MODEL_DIR/gemma-3-1b-it 2>/dev/null)" ]; then
        log_info "Model already downloaded. Skipping..."
        return
    fi

    # Download using huggingface-cli inside container
    docker run --rm \
        --runtime=nvidia \
        -v "$MODEL_DIR:/models" \
        -v "$CACHE_DIR:/root/.cache" \
        -e HF_HOME=/root/.cache/huggingface \
        -e HF_TOKEN="$HF_TOKEN" \
        "$JETSON_CONTAINER" \
        bash -c "
            pip install -q huggingface_hub[cli] &&
            huggingface-cli download $MODEL_NAME --local-dir /models/gemma-3-1b-it --local-dir-use-symlinks False --token \$HF_TOKEN
        "

    log_info "Model downloaded successfully to $MODEL_DIR/gemma-3-1b-it"
}

convert_model() {
    log_info "Converting model to TensorRT-LLM INT4 engine..."
    log_info "This process may take 10-30 minutes on Jetson Orin Nano."

    # Check if engine already exists
    if [ -f "$ENGINE_DIR/rank0.engine" ]; then
        log_info "Engine already exists. Skipping conversion..."
        return
    fi

    # Convert model to TensorRT-LLM format with INT4 AWQ quantization
    docker run --rm \
        --runtime=nvidia \
        -v "$MODEL_DIR:/models" \
        -v "$ENGINE_DIR:/engines" \
        -v "$CACHE_DIR:/root/.cache" \
        "$JETSON_CONTAINER" \
        bash -c "
            cd /opt/TensorRT-LLM/examples/gemma

            # Convert checkpoint with INT4 AWQ quantization
            python convert_checkpoint.py \
                --model_dir /models/gemma-3-1b-it \
                --output_dir /engines/checkpoint \
                --dtype float16 \
                --use_weight_only \
                --weight_only_precision int4_awq \
                --per_group

            # Build TensorRT engine optimized for Orin Nano
            trtllm-build \
                --checkpoint_dir /engines/checkpoint \
                --output_dir /engines \
                --gemm_plugin float16 \
                --max_batch_size $MAX_BATCH_SIZE \
                --max_input_len $MAX_INPUT_LEN \
                --max_seq_len $((MAX_INPUT_LEN + MAX_OUTPUT_LEN)) \
                --max_num_tokens $((MAX_BATCH_SIZE * MAX_INPUT_LEN)) \
                --strongly_typed \
                --workers 1

            # Cleanup checkpoint to save space
            rm -rf /engines/checkpoint
        "

    log_info "Model converted successfully to $ENGINE_DIR"
}

start_server() {
    log_info "Starting TensorRT-LLM OpenAI-compatible server..."

    # Stop existing container if running
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true

    # Start the server with OpenAI-compatible API
    docker run -d \
        --name "$CONTAINER_NAME" \
        --runtime=nvidia \
        --restart=unless-stopped \
        -p "$API_PORT:8000" \
        -v "$ENGINE_DIR:/engines" \
        -v "$MODEL_DIR:/models" \
        -v "$CACHE_DIR:/root/.cache" \
        "$JETSON_CONTAINER" \
        python -m tensorrt_llm.serve \
            --model_dir /engines \
            --tokenizer_dir /models/gemma-3-1b-it \
            --host 0.0.0.0 \
            --port 8000

    log_info "Server starting... Waiting for initialization..."

    # Wait for server to be ready
    MAX_WAIT=120
    WAIT_COUNT=0
    while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
        if curl -s "http://localhost:$API_PORT/health" > /dev/null 2>&1; then
            log_info "TensorRT-LLM server is ready!"
            log_info "OpenAI-compatible API available at: http://localhost:$API_PORT"
            return
        fi
        sleep 2
        WAIT_COUNT=$((WAIT_COUNT + 2))
        echo -n "."
    done

    log_error "Server failed to start within ${MAX_WAIT} seconds. Check logs: docker logs $CONTAINER_NAME"
}

stop_server() {
    log_info "Stopping TensorRT-LLM server..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    log_info "Server stopped."
}

show_status() {
    echo ""
    echo "==================== STATUS ===================="

    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "Server Status: ${GREEN}RUNNING${NC}"
        echo "Container: $CONTAINER_NAME"
        echo "API Endpoint: http://localhost:$API_PORT"
        echo ""
        echo "Test with:"
        echo "  curl http://localhost:$API_PORT/v1/models"
        echo ""
        echo "  curl http://localhost:$API_PORT/v1/chat/completions \\"
        echo "    -H 'Content-Type: application/json' \\"
        echo "    -d '{\"model\": \"gemma-3-1b-it\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}'"
    else
        echo -e "Server Status: ${RED}STOPPED${NC}"
    fi

    echo ""
    echo "Logs: docker logs -f $CONTAINER_NAME"
    echo "==============================================="
}

print_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install   - Full installation (download, convert, start)"
    echo "  download  - Download Gemma 3 1B model only"
    echo "  convert   - Convert model to TensorRT-LLM engine"
    echo "  start     - Start the API server"
    echo "  stop      - Stop the API server"
    echo "  status    - Show server status"
    echo "  logs      - Show server logs"
    echo "  clean     - Remove all models and engines"
    echo ""
    echo "Environment Variables:"
    echo "  HF_TOKEN  - HuggingFace token (required for gated models)"
    echo ""
}

# ==================== MAIN ====================

case "${1:-install}" in
    install)
        log_info "Starting full TensorRT-LLM installation for Jetson Orin Nano..."
        check_jetson
        check_docker
        setup_directories
        pull_container
        download_model
        convert_model
        start_server
        show_status
        ;;
    download)
        check_docker
        setup_directories
        pull_container
        download_model
        ;;
    convert)
        check_docker
        convert_model
        ;;
    start)
        start_server
        show_status
        ;;
    stop)
        stop_server
        ;;
    status)
        show_status
        ;;
    logs)
        docker logs -f "$CONTAINER_NAME"
        ;;
    clean)
        log_warn "This will remove all models and engines!"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            stop_server
            sudo rm -rf "$MODEL_DIR"
            sudo rm -rf "$ENGINE_DIR"
            log_info "Cleaned up successfully."
        fi
        ;;
    *)
        print_usage
        exit 1
        ;;
esac
