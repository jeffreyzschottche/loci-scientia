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

    if pgrep -x "ollama" >/dev/null 2>&1; then
        echo "✅ Ollama draait al"
    else
        echo "⏳ Ollama server starten..."
        ollama serve > "$PROJECT_ROOT/ollama.log" 2>&1 &
        ollama_pid=$!
        echo "✅ Ollama server gestart (PID: $ollama_pid)"
        sleep 3
    fi

    if ! ollama list | grep -q "mistral:7b"; then
        echo "📥 Model mistral:7b downloaden (dit kan even duren bij eerste keer)..."
        if ollama pull mistral:7b; then
            echo "✅ Model mistral:7b gedownload"
        else
            echo "⚠️  Model download mislukt. Check netwerk verbinding."
            return 1
        fi
    else
        echo "✅ Model mistral:7b is al beschikbaar"
    fi
    return 0
}

echo "=== Ollama Setup ==="
if install_ollama; then
    start_ollama || echo "⚠️  Kon Ollama niet starten, app draait zonder LLM support"
else
    echo "⚠️  App draait zonder Ollama support"
fi
echo "===================="
echo

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
BACKEND_HTTP="${BACKEND_HTTP:-http://$BACKEND_HOST:$BACKEND_PORT}"
if [ -z "${BACKEND_WS:-}" ]; then
    if [[ "$BACKEND_HTTP" == https://* ]]; then
        BACKEND_WS="wss://${BACKEND_HTTP#https://}"
    elif [[ "$BACKEND_HTTP" == http://* ]]; then
        BACKEND_WS="ws://${BACKEND_HTTP#http://}"
    else
        BACKEND_WS="ws://$BACKEND_HOST:$BACKEND_PORT/ws"
    fi
fi
export BACKEND_HOST BACKEND_PORT BACKEND_HTTP BACKEND_WS

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

BACKEND_CMD=(python -m uvicorn app.backend.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT")
backend_log="$PROJECT_ROOT/backend.log"

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

PMTILES_HOST="${PMTILES_HOST:-127.0.0.1}"
PMTILES_PORT="${PMTILES_PORT:-8080}"
PMTILES_TILESET="${PMTILES_TILESET:-europe}"
DEFAULT_PMTILES_DIR="$PROJECT_ROOT/app/maps"
PMTILES_DIR_RAW="${PMTILES_DATA_DIR:-$DEFAULT_PMTILES_DIR}"
PMTILES_DIR="$PMTILES_DIR_RAW"
if command -v python3 >/dev/null 2>&1; then
    PMTILES_DIR="$(PMTILES_DIR_RAW="$PMTILES_DIR_RAW" python3 - <<'PY' 2>/dev/null || true
import os
from pathlib import Path
raw = os.environ.get("PMTILES_DIR_RAW")
print(Path(raw).expanduser().resolve())
PY
)"
    PMTILES_DIR="${PMTILES_DIR:-$PMTILES_DIR_RAW}"
fi
PMTILES_DATA_DIR="$PMTILES_DIR"
if [ ! -d "$PMTILES_DIR" ]; then
    echo "⚠️  opgegeven PMTiles-pad '$PMTILES_DIR' bestaat niet."
    echo "    Pas PMTILES_DATA_DIR in .env aan of controleer of de schijf aangekoppeld is."
fi
export PMTILES_HOST PMTILES_PORT PMTILES_TILESET PMTILES_DATA_DIR
PMTILES_BASE_URL="${PMTILES_BASE_URL:-http://$PMTILES_HOST:$PMTILES_PORT}"
export PMTILES_BASE_URL
if [ -z "${MAP_GLYPHS_URL:-}" ]; then
    MAP_GLYPHS_URL="${BACKEND_HTTP%/}/fonts/{fontstack}/{range}.pbf"
fi
if [ -z "${MAP_SPRITE_URL:-}" ]; then
    MAP_SPRITE_URL="${BACKEND_HTTP%/}/sprites/v4/light"
fi
if [ -z "${PMTILES_STATUS_HINT:-}" ]; then
    PMTILES_STATUS_HINT="Kaartdata kon niet geladen worden. Controleer of de pmtiles-server draait op ${PMTILES_HOST}:${PMTILES_PORT} en dat ${PMTILES_TILESET}.pmtiles beschikbaar is."
fi
export MAP_GLYPHS_URL MAP_SPRITE_URL PMTILES_STATUS_HINT
pmtiles_log="$PROJECT_ROOT/pmtiles.log"
pmtiles_pid=""

if lsof -ti:"$PMTILES_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    old_pid=$(lsof -ti:"$PMTILES_PORT" -sTCP:LISTEN)
    echo "⚠️  bestaand proces op poort $PMTILES_PORT gevonden (pid $old_pid), stoppen…"
    kill "$old_pid" >/dev/null 2>&1 || true
    sleep 1
fi

echo "⏳ pmtiles server starten voor $PMTILES_DIR (log: $pmtiles_log)..."
pmtiles serve "$PMTILES_DIR" --port="$PMTILES_PORT" --cors='*' >"$pmtiles_log" 2>&1 &
pmtiles_pid=$!

cleanup() {
    echo
    echo "🛑 Backend stoppen..."
    kill "$backend_pid" >/dev/null 2>&1 || true

    echo "🛑 pmtiles server stoppen..."
    if [ -n "${pmtiles_pid:-}" ]; then
        kill "$pmtiles_pid" >/dev/null 2>&1 || true
    fi

    if [ -n "${ollama_pid:-}" ]; then
        echo "🛑 Ollama stoppen..."
        kill "$ollama_pid" >/dev/null 2>&1 || true
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
