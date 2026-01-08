import os
import argparse
import pandas as pd
import numpy as np

GOLD_DIR = "data/gold"

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def rolling_slope(y: np.ndarray) -> float:
    n = len(y)
    if n < 2:
        return np.nan
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    y_mean = y.mean()
    denom = ((x - x_mean) ** 2).sum()
    if denom == 0:
        return np.nan
    return float(((x - x_mean) * (y - y_mean)).sum() / denom)

def main():
    p = argparse.ArgumentParser(description="Build Gold lap-level feature table from Silver laps")
    p.add_argument("--laps_silver", type=str, default="data/silver/laps_silver.csv")
    p.add_argument("--out", type=str, default=os.path.join(GOLD_DIR, "lap_features_gold.csv"))
    p.add_argument("--window", type=int, default=5)
    args = p.parse_args()

    ensure_dir(GOLD_DIR)

    df = pd.read_csv(args.laps_silver)

    # If race_id doesn't exist (single race), create it
    if "race_id" not in df.columns:
        df["race_id"] = "single_race"

    # Clean
    df = df.dropna(subset=["driver", "lap", "lap_time", "compound", "tyre_age"]).copy()
    df["lap"] = df["lap"].astype(int)
    df["tyre_age"] = pd.to_numeric(df["tyre_age"], errors="coerce")
    df["lap_time"] = pd.to_numeric(df["lap_time"], errors="coerce")
    df["position"] = pd.to_numeric(df.get("position"), errors="coerce")
    df["track_status"] = pd.to_numeric(df.get("track_status"), errors="coerce").fillna(1).astype(int)
    df["pitted_this_lap"] = pd.to_numeric(df.get("pitted_this_lap"), errors="coerce").fillna(0).astype(int)

    df["compound"] = df["compound"].astype(str).str.upper()
    df["driver"] = df["driver"].astype(str).str.upper()
    df["race_id"] = df["race_id"].astype(str)

    # Sort by race+driver+lap
    df = df.sort_values(["race_id", "driver", "lap"]).reset_index(drop=True)

    w = args.window
    grp = df.groupby(["race_id", "driver"])

    df["pace_roll_mean"] = grp["lap_time"].transform(lambda s: s.rolling(w, min_periods=2).mean())
    df["pace_roll_std"]  = grp["lap_time"].transform(lambda s: s.rolling(w, min_periods=2).std())

    df["deg_roll_slope"] = grp["lap_time"].transform(
        lambda s: s.rolling(w, min_periods=2).apply(lambda x: rolling_slope(np.array(x)), raw=False)
    )

    # Target
    df["lap_time_next"] = grp["lap_time"].shift(-1)
    df = df.dropna(subset=["lap_time_next"]).copy()

    gold = df[[
        "race_id", "driver",
        "lap", "stint", "compound", "tyre_age",
        "lap_time", "pace_roll_mean", "pace_roll_std", "deg_roll_slope",
        "position", "track_status", "pitted_this_lap",
        "lap_time_next"
    ]].copy()

    gold.to_csv(args.out, index=False)

    print("[OK] Gold features built:")
    print(f" - {args.out}")
    print(f"[INFO] rows={len(gold)} races={gold['race_id'].nunique()} drivers={gold['driver'].nunique()} window={w}")

if __name__ == "__main__":
    main()
