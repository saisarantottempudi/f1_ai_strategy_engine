#!/usr/bin/env bash
set -e

export PYTHONPATH=backend

CMD=$1
shift || true

case "$CMD" in

  serve)
    echo "[F1] Starting API server..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ;;

  telemetry)
    FILE=$1
    if [[ -z "$FILE" ]]; then
      echo "Usage: ./scripts/f1.sh telemetry telemetry.json"
      exit 1
    fi
    echo "[F1] Sending telemetry from $FILE"
    curl -sS -X POST http://localhost:8000/api/telemetry \
      -H "Content-Type: application/json" \
      -d @"$FILE" | python -m json.tool
    ;;

  recommend)
    RACE_ID=$1
    DRIVER=$2
    if [[ -z "$RACE_ID" || -z "$DRIVER" ]]; then
      echo "Usage: ./scripts/f1.sh recommend <race_id> <driver>"
      exit 1
    fi
    echo "[F1] Getting strategy recommendation..."
    curl -sS -X POST http://localhost:8000/api/recommend \
      -H "Content-Type: application/json" \
      -d "{
        \"race_id\": \"$RACE_ID\",
        \"driver\": \"$DRIVER\",
        \"horizon_laps\": 15,
        \"candidates\": 30
      }" | python -m json.tool
    ;;

  train-multi)
    echo "[F1] Training multi-race pace model..."
    python backend/app/data/build_gold_features.py \
      --laps_silver data/silver/laps_silver_all.csv \
      --out data/gold/lap_features_gold_all.csv

    python backend/app/ml/train_pace_model.py \
      --data data/gold/lap_features_gold_all.csv
    ;;

  *)
    echo "F1 AI Strategy CLI"
    echo ""
    echo "Available commands:"
    echo "  serve                 Start FastAPI server"
    echo "  telemetry <file.json> Send telemetry"
    echo "  recommend <race> <driver> Get strategy"
    echo "  train-multi           Train ML model"
    ;;
esac
