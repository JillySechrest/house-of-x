#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/apps/api"
exec "$ROOT/.venv/bin/uvicorn" mock_marvel.app:app --port "${MOCK_MARVEL_PORT:-8001}"
