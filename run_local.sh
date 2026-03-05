#!/bin/bash
# Start ContextGate locally without Docker (uses SQLite)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔧 ContextGate — Local Startup"
echo "================================"

if ! command -v uv &> /dev/null; then
  echo "📦 Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "📦 Syncing dependencies..."
uv sync --all-extras

echo ""
echo "✅ Starting ContextGate on http://localhost:8001"
echo "   Docs     → http://localhost:8001/docs"
echo "   Audit    → http://localhost:8001/api/v1/audit/logs"
echo "   Stats    → http://localhost:8001/api/v1/audit/stats"
echo "   Profiles → http://localhost:8001/api/v1/profiles"
echo ""
echo "Press Ctrl+C to stop."
echo ""

DATABASE_URL="sqlite+aiosqlite:///./dev.db" \
PROFILES_PATH="profiles.yaml" \
uv run uvicorn app.main:app --reload --port 8001
