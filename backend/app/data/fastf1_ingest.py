import os
import argparse
import pandas as pd
import fastf1

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def to_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)

def main():
    p = argparse.ArgumentParser(description="Ingest FastF1 session data into data/bronze/fastf1/")
    p.add_argument("--year", type=int, required=True, help="e.g., 2023")
    p.add_argument("--gp", type=str, required=True, help="e.g., 'Monza' or 'British Grand Prix'")
    p.add_argument("--session", type=str, default="R", help="R/Q/SR/FP1/FP2/FP3")
    p.add_argument("--out", type=str, default="data/bronze/fastf1")
    args = p.parse_args()

    # Cache speeds up repeated runs
    cache_dir = ".fastf1_cache"
    ensure_dir(cache_dir)
    fastf1.Cache.enable_cache(cache_dir)

    sess = fastf1.get_session(args.year, args.gp, args.session)
    sess.load()  # downloads & parses timing/telemetry metadata

    out_dir = os.path.join(args.out, f"{args.year}_{args.gp.replace(' ', '_')}_{args.session}")
    ensure_dir(out_dir)

    # Laps table (includes compounds/stints/tyre life for many sessions)
    laps = sess.laps.copy()
    to_csv(laps, os.path.join(out_dir, "laps.csv"))

    # Weather (if available)
    try:
        weather = sess.weather_data.copy()
        to_csv(weather, os.path.join(out_dir, "weather.csv"))
    except Exception:
        pass

    # Results/summary tables
    try:
        results = sess.results.copy()
        to_csv(results, os.path.join(out_dir, "results.csv"))
    except Exception:
        pass

    print(f"[OK] Saved FastF1 session -> {out_dir}")
    print(f"      laps: {os.path.join(out_dir, 'laps.csv')}")

if __name__ == "__main__":
    main()
