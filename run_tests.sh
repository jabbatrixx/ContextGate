#!/bin/bash
# Run the full pytest suite (no server, no Docker needed)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🧪 DataPrune — Test Suite"
echo "================================"

if ! command -v uv &> /dev/null; then
  echo "📦 Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "📦 Syncing dependencies..."
uv sync --all-extras

echo ""
echo "Running tests..."
echo ""
uv run python -m pytest tests/ -v --tb=short

echo ""
echo "✅ All tests complete."
