import os
import time
import csv
import requests
from datetime import datetime, timezone

ERGAST_BASE = "https://ergast.com/api/f1"

HEADERS = {
    "User-Agent": "f1-ai-strategy/0.1 (contact: local-dev)",
    "Accept": "text/csv,*/*;q=0.8",
}

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def save_text(text: str, path: str) -> None:
    with open(path, "w") as f:
        f.write(text)

def fetch_csv(endpoint: str, params=None, retries: int = 6, backoff_s: float = 1.0) -> str:
    url = f"{ERGAST_BASE}/{endpoint}.csv"
    last_err = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=45)
            if r.status_code in (429, 441, 500, 502, 503, 504):
                last_err = RuntimeError(f"HTTP {r.status_code} for {url}")
                time.sleep(backoff_s * (2 ** i))
                continue
            r.raise_for_status()
            return r.text
        except Exception as e:
            last_err = e
            time.sleep(backoff_s * (2 ** i))
    raise last_err if last_err else RuntimeError("Unknown fetch error")

def read_rounds_from_races_csv(races_csv_path: str) -> list[int]:
    rounds = []
    with open(races_csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        # Ergast CSV typically contains "round"
        if "round" not in reader.fieldnames:
            raise RuntimeError(f"'round' column not found in {races_csv_path}. Found: {reader.fieldnames}")
        for row in reader:
            try:
                rounds.append(int(row["round"]))
            except Exception:
                continue
    rounds = sorted(list(set(rounds)))
    if not rounds:
        raise RuntimeError(f"No rounds parsed from {races_csv_path}")
    return rounds

def ingest_season_csv(season: int, out_dir: str) -> None:
    ensure_dir(out_dir)

    races_csv_path = os.path.join(out_dir, f"races_{season}.csv")
    if not os.path.exists(races_csv_path):
        # download races csv if missing
        races_csv = fetch_csv(f"{season}")
        save_text(races_csv, races_csv_path)

    rounds = read_rounds_from_races_csv(races_csv_path)
    print(f"[OK] Parsed {len(rounds)} rounds from {races_csv_path}: {rounds[0]}..{rounds[-1]}")

    for rnd in rounds:
        # results
        results = fetch_csv(f"{season}/{rnd}/results")
        save_text(results, os.path.join(out_dir, f"results_{season}_round_{rnd}.csv"))

        # pitstops (limit param supported)
        pitstops = fetch_csv(f"{season}/{rnd}/pitstops", params={"limit": 2000})
        save_text(pitstops, os.path.join(out_dir, f"pitstops_{season}_round_{rnd}.csv"))

        # laptimes (limit param supported)
        laptimes = fetch_csv(f"{season}/{rnd}/laps", params={"limit": 5000})
        save_text(laptimes, os.path.join(out_dir, f"laptimes_{season}_round_{rnd}.csv"))

        print(f"[OK] round {rnd}: results/pitstops/laptimes saved")
        time.sleep(0.25)

def main():
    import argparse
    p = argparse.ArgumentParser(description="Ingest full season via Ergast CSV (round-by-round).")
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--out_dir", type=str, required=True, help="Existing season folder under data/bronze/ergast/ ...")
    args = p.parse_args()

    ingest_season_csv(args.season, args.out_dir)

if __name__ == "__main__":
    main()
