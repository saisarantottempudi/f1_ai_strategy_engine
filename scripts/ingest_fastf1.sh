#!/usr/bin/env bash
set -euo pipefail

YEAR="${1:-2023}"
GP="${2:-Monza}"
SESSION="${3:-R}"

export PYTHONPATH=backend
python backend/app/data/fastf1_ingest.py --year "${YEAR}" --gp "${GP}" --session "${SESSION}"
