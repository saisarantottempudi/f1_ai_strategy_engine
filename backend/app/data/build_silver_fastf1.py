import os
import argparse
import pandas as pd

SILVER_DIR = "data/silver"

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def parse_time_to_seconds(x):
    """
    FastF1 exports some time columns as strings like '0 days 00:01:32.123000'
    or NaN. We convert to float seconds.
    """
    if pd.isna(x):
        return None
    try:
        td = pd.to_timedelta(x)
        return float(td.total_seconds())
    except Exception:
        # Sometimes already numeric
        try:
            return float(x)
        except Exception:
            return None

def main():
    p = argparse.ArgumentParser(description="Build Silver tables from FastF1 laps.csv")
    p.add_argument("--laps_csv", type=str, required=True, help="Path to bronze laps.csv")
    args = p.parse_args()

    ensure_dir(SILVER_DIR)

    laps = pd.read_csv(args.laps_csv)

    # Keep only columns that are stable/useful for strategy & ML
    keep_cols = [
        "Driver", "LapNumber", "Stint", "Compound", "TyreLife",
        "LapTime", "Sector1Time", "Sector2Time", "Sector3Time",
        "SpeedI1", "SpeedI2", "SpeedFL", "SpeedST",
        "IsPersonalBest", "FreshTyre",
        "TrackStatus", "Position",
        "PitInTime", "PitOutTime"
    ]
    existing = [c for c in keep_cols if c in laps.columns]
    laps = laps[existing].copy()

    # Standardize column names
    laps.rename(columns={
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
    }, inplace=True)

    # Convert times to seconds
    for col in ["lap_time", "s1", "s2", "s3", "pit_in_time", "pit_out_time"]:
        if col in laps.columns:
            laps[col] = laps[col].apply(parse_time_to_seconds)

    # Ensure numeric types
    for col in ["lap", "stint", "tyre_age", "position", "track_status"]:
        if col in laps.columns:
            laps[col] = pd.to_numeric(laps[col], errors="coerce")

    # Drop rows missing driver or lap
    laps = laps.dropna(subset=["driver", "lap"]).copy()

    # Sort
    laps = laps.sort_values(["driver", "lap"]).reset_index(drop=True)

    # Basic "pit lap" flag (if PitInTime exists)
    if "pit_in_time" in laps.columns:
        laps["pitted_this_lap"] = laps["pit_in_time"].notna().astype(int)
    else:
        laps["pitted_this_lap"] = 0

    # Save laps_silver
    laps_out = os.path.join(SILVER_DIR, "laps_silver.csv")
    laps.to_csv(laps_out, index=False)

    # Build stints table: one row per (driver, stint)
    if "stint" in laps.columns:
        stints = (
            laps.dropna(subset=["stint"])
                .groupby(["driver", "stint"], as_index=False)
                .agg(
                    start_lap=("lap", "min"),
                    end_lap=("lap", "max"),
                    compound=("compound", "first"),
                    tyre_age_start=("tyre_age", "min"),
                    tyre_age_end=("tyre_age", "max"),
                    laps_in_stint=("lap", "count"),
                    pit_lap=("pitted_this_lap", lambda s: int((s == 1).any()))
                )
        )
        stints_out = os.path.join(SILVER_DIR, "stints_silver.csv")
        stints.to_csv(stints_out, index=False)
    else:
        stints_out = None

    print("[OK] Silver built:")
    print(f" - {laps_out}")
    if stints_out:
        print(f" - {stints_out}")
    print(f"[INFO] rows: laps={len(laps)}")

if __name__ == "__main__":
    main()
