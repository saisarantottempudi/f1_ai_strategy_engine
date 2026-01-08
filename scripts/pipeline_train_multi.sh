#!/usr/bin/env bash
set -euo pipefail

YEAR="${1:-2023}"
N_RACES="${2:-6}"          # start small (6). you can increase later: 12, 18, 22
SESSION="${3:-R}"

ROOT="$(pwd)"

source f1/bin/activate

# 1) Create helper: get first N EventName values for season
EVENTS_FILE=".events_${YEAR}.txt"

python - <<PY > "${EVENTS_FILE}"
import fastf1
fastf1.Cache.enable_cache(".fastf1_cache")
events = fastf1.get_event_schedule(${YEAR})
names = events["EventName"].tolist()
for n in names:
    print(n)
PY

echo "[OK] Saved event list -> ${EVENTS_FILE}"
echo "[INFO] Using first ${N_RACES} races"

# 2) Loop and ingest + build silver for each race
i=0
while IFS= read -r GP; do
  i=$((i+1))
  if [ "${i}" -gt "${N_RACES}" ]; then
    break
  fi
  echo "=============================="
  echo "[STEP] (${i}/${N_RACES}) Ingest: ${YEAR} | ${GP} | ${SESSION}"
  export PYTHONPATH=backend
  python backend/app/data/fastf1_ingest.py --year "${YEAR}" --gp "${GP}" --session "${SESSION}"

  OUT_DIR="data/bronze/fastf1/${YEAR}_$(echo "${GP}" | tr ' ' '_' )_${SESSION}"
  LAPS_CSV="${OUT_DIR}/laps.csv"

  echo "[STEP] Build Silver for ${GP}"
  python backend/app/data/build_silver_fastf1.py --laps_csv "${LAPS_CSV}"
done < "${EVENTS_FILE}"

# 3) Merge ALL bronze laps into one silver file (from everything in data/bronze/fastf1/*/laps.csv)
echo "=============================="
echo "[STEP] Merge Silver laps across races"

python - <<'PY'
import glob
import pandas as pd
import os

paths = sorted(glob.glob("data/bronze/fastf1/*/laps.csv"))
if not paths:
    raise SystemExit("No laps.csv found under data/bronze/fastf1/*/laps.csv")

dfs = []
for p in paths:
    # add race_id from folder name
    race_id = os.path.basename(os.path.dirname(p))
    df = pd.read_csv(p)
    df["race_id"] = race_id
    dfs.append(df)

all_df = pd.concat(dfs, ignore_index=True)

os.makedirs("data/silver", exist_ok=True)
out = "data/silver/laps_bronze_all.csv"
all_df.to_csv(out, index=False)
print("[OK] merged bronze laps ->", out, "rows=", len(all_df), "races=", all_df["race_id"].nunique())
PY

# 4) Build unified Silver (clean + normalize) from merged bronze laps
echo "=============================="
echo "[STEP] Build unified Silver from merged bronze laps"

python - <<'PY'
import pandas as pd
import os

from backend.app.data.build_silver_fastf1 import parse_time_to_seconds

bronze = pd.read_csv("data/silver/laps_bronze_all.csv")

# Keep stable cols if exist
keep_cols = [
    "race_id",
    "Driver", "LapNumber", "Stint", "Compound", "TyreLife",
    "LapTime", "Sector1Time", "Sector2Time", "Sector3Time",
    "SpeedI1", "SpeedI2", "SpeedFL", "SpeedST",
    "IsPersonalBest", "FreshTyre",
    "TrackStatus", "Position",
    "PitInTime", "PitOutTime"
]
existing = [c for c in keep_cols if c in bronze.columns]
df = bronze[existing].copy()

df = df.rename(columns={
    "Driver": "driver",
    "LapNumber": "lap",
    "Stint": "stint",
    "Compound": "compound",
    "TyreLife": "tyre_age",
    "LapTime": "lap_time",
    "Sector1Time": "s1",
    "Sector2Time": "s2",
    "Sector3Time": "s3",
    "TrackStatus": "track_status",
    "Position": "position",
    "PitInTime": "pit_in_time",
    "PitOutTime": "pit_out_time",
    "IsPersonalBest": "is_pb",
    "FreshTyre": "fresh_tyre"
})

for col in ["lap_time", "s1", "s2", "s3", "pit_in_time", "pit_out_time"]:
    if col in df.columns:
        df[col] = df[col].apply(parse_time_to_seconds)

for col in ["lap", "stint", "tyre_age", "position", "track_status"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["driver", "lap"]).copy()
df = df.sort_values(["race_id", "driver", "lap"]).reset_index(drop=True)

if "pit_in_time" in df.columns:
    df["pitted_this_lap"] = df["pit_in_time"].notna().astype(int)
else:
    df["pitted_this_lap"] = 0

os.makedirs("data/silver", exist_ok=True)
out = "data/silver/laps_silver_all.csv"
df.to_csv(out, index=False)
print("[OK] unified silver ->", out, "rows=", len(df), "races=", df["race_id"].nunique())
PY

# 5) Build Gold from unified Silver (small tweak: point gold builder at this file)
echo "=============================="
echo "[STEP] Build Gold from unified Silver"

export PYTHONPATH=backend
python backend/app/data/build_gold_features.py --laps_silver data/silver/laps_silver_all.csv --out data/gold/lap_features_gold_all.csv

# 6) Train model on Gold (multi-race)
echo "=============================="
echo "[STEP] Train model on multi-race Gold"

python backend/app/ml/train_pace_model.py --data data/gold/lap_features_gold_all.csv

echo "=============================="
echo "[DONE] Multi-race training complete."
echo "Model: backend/app/ml/models/pace_model.joblib"
