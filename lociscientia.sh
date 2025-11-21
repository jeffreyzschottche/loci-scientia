#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Zorg dat er een virtuele omgeving is en dat requirements éénmaal geïnstalleerd zijn.
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Activeer de venv voordat we afhankelijkheden installeren of de app starten.
# shellcheck source=/dev/null
source .venv/bin/activate

if [ ! -f ".venv/.requirements_installed" ]; then
    python -m pip install -U pip
    python -m pip install -r app/requirements.txt
    touch .venv/.requirements_installed
fi

# Backend config
BACKEND_PORT=8000
BACKEND_HOST="127.0.0.1"
BACKEND_CMD=(python -m uvicorn app.backend.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT")
backend_log="$PROJECT_ROOT/backend.log"

echo "⏳ Backend starten (log: $backend_log)..."
"${BACKEND_CMD[@]}" >"$backend_log" 2>&1 &
backend_pid=$!

# pmtiles config – serve app/maps zodat tiles altijd gevonden worden
PMTILES_PORT=8080
PMTILES_DIR="$PROJECT_ROOT/app/maps"
pmtiles_log="$PROJECT_ROOT/pmtiles.log"

# voorkom dat een oude pmtiles-server op dezelfde poort blijft draaien
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
    kill "$pmtiles_pid" >/dev/null 2>&1 || true
}

trap cleanup EXIT

# Wachten tot backend reageert
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

# Frontend starten (blokkerend)
python -m app.frontend.main

# Wacht op backend-proces (zodat EXIT-trap netjes afgaat)
wait "$backend_pid"
