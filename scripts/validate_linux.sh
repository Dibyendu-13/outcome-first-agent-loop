#!/usr/bin/env bash
# External evaluation harness; the controller inside still consumes only HTTP.
set -euo pipefail
cd "$(dirname "$0")/.."
NAME="${1:-linux_submission_load}"
BASELINE="${2:-$PWD/runs/public_03_load/baseline}"
BASELINE="$(cd "$BASELINE" && pwd)"
docker build -t outcome-loop:validation .
docker run --rm --cpus=4 --memory=8g --memory-swap=8g outcome-loop:validation python -m pytest -q tests
docker run --name "outcome-loop-$NAME" --rm --cpus=4 --memory=8g --memory-swap=8g \
  --mount type=volume,source=outcome-loop-runs-native,target=/app/runs \
  --mount type=volume,source=outcome-loop-state-native,target=/app/controller-data \
  --mount "type=bind,source=$PWD/reports,target=/app/reports" \
  --mount "type=bind,source=$BASELINE,target=/baseline,readonly" \
  outcome-loop:validation python scripts/evaluate.py --name "$NAME" --scenario scenarios/public_03_load.yaml --port 8705 --reuse-baseline /baseline
