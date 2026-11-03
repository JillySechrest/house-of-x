#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3.12 -m venv .venv 2>/dev/null || python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e "apps/api[dev]"
(cd apps/web && npm ci)
[ -f .env ] || cp .env.example .env
echo "Setup complete. Add your Marvel keys to .env."
