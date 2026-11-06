#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
SIM_URL="${1:?usage: ./run.sh <SIM_URL>}"
PYTHON="${PYTHON:-python3}"
if [[ -x .venv/bin/python ]]; then PYTHON=.venv/bin/python; fi
exec "$PYTHON" -m controller run --url "$SIM_URL" --db "${CONTROLLER_DB:-controller-data/state.sqlite}"
