#!/usr/bin/env bash
set -euo pipefail

SEASON="${1:-2023}"

# Make sure you're in repo root
if [[ ! -d backend/app ]]; then
  echo "[ERR] Run this from repo root (f1-ai-strategy)."
  exit 1
fi

export PYTHONPATH=backend
python backend/app/data/ergast_ingest.py --season "${SEASON}"
