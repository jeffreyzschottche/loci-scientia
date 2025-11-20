#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Zorg dat er een virtuele omgeving is en dat requirements éénmaal geïnstalleerd zijn.
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Activateer de venv voordat we afhankelijkheden installeren of de app starten.
# shellcheck source=/dev/null
source .venv/bin/activate

if [ ! -f ".venv/.requirements_installed" ]; then
    python -m pip install -U pip
    python -m pip install -r app/requirements.txt
    touch .venv/.requirements_installed
fi

BACKEND_PORT=8000
BACKEND_HOST="127.0.0.1"
BACKEND_CMD=(python -m uvicorn app.backend.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT")

backend_log="$PROJECT_ROOT/backend.log"

echo "⏳ Backend starten (log: $backend_log)..."
"${BACKEND_CMD[@]}" >"$backend_log" 2>&1 &
backend_pid=$!

cleanup() {
    echo
    echo "🛑 Backend stoppen..."
    kill "$backend_pid" >/dev/null 2>&1 || true
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
