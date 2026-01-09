# AI-Driven Formula 1 Race Strategy & Performance Optimization System

A terminal-first, end-to-end F1 race strategy engine that learns lap-time behaviour from historical race data and recommends pit-stop strategies from live telemetry.

It combines:
- FastF1 historical session ingestion (multi-race)
- Medallion architecture (Bronze → Silver → Gold)
- ML next-lap time prediction (regression)
- Model-driven Monte Carlo strategy simulation (uncertainty + risk)
- FastAPI service endpoints
- CLI wrapper: ./scripts/f1.sh

---

## What this project does

Inputs:
- Historical session data via FastF1
- Live telemetry updates (driver, lap, tyre compound/age, etc.)

Outputs:
- Recommended action: PIT now / PIT in N laps / STAY_OUT
- Top ranked strategies:
  - pit lap
  - compound
  - expected delta time vs baseline
  - uncertainty (Monte Carlo)
  - risk score

---

## Architecture

Pipeline:
  FastF1 (historical sessions)
      ↓
  data/bronze (raw session exports)
      ↓
  data/silver (cleaned laps + stints)
      ↓
  data/gold (rolling pace + degradation features + next-lap target)
      ↓
  ML model (pace_model.joblib)
      ↓
  Monte Carlo strategy simulator (stable)
      ↓
  FastAPI (/api/telemetry, /api/recommend)
      ↓
  CLI (./scripts/f1.sh)

---

## Repository Structure (key parts)

- backend/app/api/
  FastAPI routes (/api/telemetry, /api/recommend)

- backend/app/data/
  FastF1 ingest + Silver/Gold builders

- backend/app/ml/
  Training scripts + saved model pipeline

- backend/app/services/
  Live state store, model service, strategy service

- backend/app/simulator/
  Model + Monte Carlo strategy simulation

- scripts/
  CLI and helper scripts

- data/
  Medallion tables (ignored by git):
  - data/bronze/
  - data/silver/
  - data/gold/

---

## Requirements

- macOS / Linux terminal
- Python 3.x
- Virtualenv created as: ./f1 (in project root)

---

## Setup

From project root:

  python3 -m venv f1
  source f1/bin/activate
  python -m pip install --upgrade pip setuptools wheel
  pip install -r backend/requirements.txt

---

## Run API Server

Option A (manual):

  source f1/bin/activate
  export PYTHONPATH=backend
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Option B (CLI):

  ./scripts/f1.sh serve

Health check:

  curl -sS http://localhost:8000/api/health | python -m json.tool

---

## CLI Usage (recommended)

Send telemetry:

  ./scripts/f1.sh telemetry scripts/telemetry_demo.json

Get recommendation:

  ./scripts/f1.sh recommend 2023_British_Grand_Prix_R VER

Train model (multi-race):

  ./scripts/f1.sh train-multi

---

## API Endpoints

Base URL: http://localhost:8000

GET /api/health
- Returns API status

POST /api/telemetry
- Stores current telemetry for a driver

Example:

  curl -sS -X POST "http://localhost:8000/api/telemetry" \
    -H "Content-Type: application/json" \
    -d '{
      "race_id":"2023_British_Grand_Prix_R",
      "driver":"VER",
      "lap":12,
      "lap_time_s":92.4,
      "position":3,
      "gap_ahead_s":1.8,
      "gap_behind_s":0.9,
      "tyre_compound":"MEDIUM",
      "tyre_age_laps":14,
      "sc_status":"GREEN"
    }' | python -m json.tool

POST /api/recommend
- Computes recommendation using stored telemetry

Example:

  curl -sS -X POST "http://localhost:8000/api/recommend" \
    -H "Content-Type: application/json" \
    -d '{"race_id":"2023_British_Grand_Prix_R","driver":"VER","horizon_laps":15,"candidates":30}' \
    | python -m json.tool

---

## Modeling Notes

Lap-time ML:
- Target: next lap time (lap_time_next)
- Features include:
  - lap, tyre_age, lap_time
  - rolling pace mean/std
  - degradation slope proxy
  - track_status, pitted_this_lap
  - compound
  - driver, race_id (categorical context)

Strategy engine:
- Baseline: no pit
- Candidates: pit lap grid + compound variants
- Monte Carlo outputs:
  - expected delta vs baseline
  - uncertainty (std dev)
  - risk score

---

## Data Source

- FastF1 (historical F1 session timing/lap metadata)

Data completeness can vary by session/driver; the pipeline is robust to missing values.

---

## Troubleshooting

uvicorn: command not found
- Activate venv:

  source f1/bin/activate

JSON tool: Extra data
- Happens if non-JSON text is appended to stdout. Keep HTTP codes separate from JSON output.

Model not found
- Train first:

  ./scripts/f1.sh train-multi

