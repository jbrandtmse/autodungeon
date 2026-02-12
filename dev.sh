#!/usr/bin/env bash
# autodungeon dev startup script
# Starts both the FastAPI backend and SvelteKit frontend dev servers.
# Usage: bash dev.sh

set -euo pipefail

# ── Prerequisite checks ──────────────────────────────────────────

PYTHON_CMD=""
# Try each candidate and verify it actually runs (Windows Store stubs exist but fail)
for candidate in python3 python; do
  if command -v "$candidate" &>/dev/null && "$candidate" --version &>/dev/null 2>&1; then
    PYTHON_CMD="$candidate"
    break
  fi
done
if [ -z "$PYTHON_CMD" ]; then
  echo "ERROR: Python is not installed. Please install Python 3.10+ and try again."
  exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
  echo "ERROR: Python 3.10+ is required (found $PYTHON_VERSION)."
  exit 1
fi

if ! command -v node &>/dev/null; then
  echo "ERROR: Node.js is not installed. Please install Node.js 18+ and try again."
  exit 1
fi

NODE_MAJOR=$(node -e "console.log(process.versions.node.split('.')[0])")
if [ "$NODE_MAJOR" -lt 18 ]; then
  echo "ERROR: Node.js 18+ is required (found $(node --version))."
  exit 1
fi

if ! command -v npm &>/dev/null; then
  echo "ERROR: npm is not installed. Please install npm and try again."
  exit 1
fi

# ── Determine uvicorn command ─────────────────────────────────────

UVICORN_CMD=""
if command -v uvicorn &>/dev/null; then
  UVICORN_CMD="uvicorn"
elif $PYTHON_CMD -m uvicorn --version &>/dev/null 2>&1; then
  UVICORN_CMD="$PYTHON_CMD -m uvicorn"
else
  echo "ERROR: uvicorn is not available. Run 'uv sync' to install dependencies."
  exit 1
fi

# ── Start servers ─────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Start FastAPI backend
$UVICORN_CMD api.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start SvelteKit frontend
cd frontend && npm run dev &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

# ── Startup banner ────────────────────────────────────────────────

echo ""
echo "  autodungeon dev servers starting..."
echo ""
echo "    Backend  (FastAPI):    http://localhost:8000"
echo "    Frontend (SvelteKit):  http://localhost:5173"
echo "    API docs:              http://localhost:8000/docs"
echo ""
echo "    Legacy (Streamlit):    Run 'streamlit run app.py' separately"
echo ""
echo "  Press Ctrl+C to stop both servers."
echo ""

# ── Cleanup on exit ───────────────────────────────────────────────

cleanup() {
  echo ""
  echo "  Stopping dev servers..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
  echo "  Done."
  exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for both background processes
wait
