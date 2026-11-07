#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
SIM_URL="${1:?usage: ./run.sh <SIM_URL>}"
PYTHON="${PYTHON:-python3}"
if [[ -x .venv/bin/python ]]; then PYTHON=.venv/bin/python; fi
if [[ -n "${CONTROLLER_DB:-}" ]]; then
  exec "$PYTHON" -m controller run --url "$SIM_URL" --db "$CONTROLLER_DB"
fi
exec "$PYTHON" -m controller run --url "$SIM_URL" --auto-db
