#!/usr/bin/env bash
# Start the FGO Bot dev stack (macOS/Linux): FastAPI backend + Vite frontend.
# Usage: ./scripts/start-dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Prefer the project venv if present.
if [ -f "$ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

export PYTHONUNBUFFERED=1
python -m uvicorn backend.app:app --reload --host localhost --port 8765 &
BACKEND_PID=$!

if [ -f "$ROOT/frontend/package.json" ]; then
  cd "$ROOT/frontend"
  [ -d node_modules ] || npm install
  npm run dev &
fi

echo "Backend:  http://localhost:8765/docs"
echo "Frontend: http://localhost:5173"
wait "$BACKEND_PID"
