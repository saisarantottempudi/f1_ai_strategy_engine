import os
import json
import time
import requests
from datetime import datetime, timezone

ERGAST_BASE = "https://ergast.com/api/f1"

HEADERS = {
    "User-Agent": "f1-ai-strategy/0.1 (contact: local-dev)",
    "Accept": "application/json,text/csv;q=0.9,*/*;q=0.8",
}

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def save_json(obj: dict, path: str) -> None:
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)

def save_text(text: str, path: str) -> None:
    with open(path, "w") as f:
        f.write(text)

def fetch_with_retries(url: str, params=None, expect_json: bool = True, retries: int = 5, backoff_s: float = 1.0):
    last_err = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=45)
            # Some services return 441/429 temporarily; retry with backoff
            if r.status_code in (429, 441, 500, 502, 503, 504):
                last_err = RuntimeError(f"HTTP {r.status_code} for {url}")
                time.sleep(backoff_s * (2 ** i))
                continue

            r.raise_for_status()

            if expect_json:
                return r.json()
            return r.text

        except Exception as e:
            last_err = e
            time.sleep(backoff_s * (2 ** i))

    raise last_err if last_err else RuntimeError("Unknown fetch error")

def fetch_json_or_csv(endpoint: str, params=None):
    # Try JSON first
    json_url = f"{ERGAST_BASE}/{endpoint}.json"
    try:
        return ("json", fetch_with_retries(json_url, params=params, expect_json=True))
    except Exception:
        # Fallback to CSV
        csv_url = f"{ERGAST_BASE}/{endpoint}.csv"
        text = fetch_with_retries(csv_url, params=params, expect_json=False)
        return ("csv", text)

def ingest_season(season: int, out_dir: str) -> None:
    ensure_dir(out_dir)

    # Season race calendar
    fmt, races = fetch_json_or_csv(f"{season}")
    if fmt == "json":
        save_json(races, os.path.join(out_dir, f"races_{season}.json"))
        race_list = races["MRData"]["RaceTable"]["Races"]
    else:
        save_text(races, os.path.join(out_dir, f"races_{season}.csv"))
        # If only CSV works, we won't parse rounds here (yet). We'll still save the file.
        print("[WARN] Only CSV endpoint worked for races. Saved races CSV. Next step will parse it.")
        return

    if not race_list:
        raise RuntimeError(f"No races found for season={season}")

    # Per-round endpoints (JSON preferred; CSV fallback saved if needed)
    for race in race_list:
        rnd = race["round"]

        fmt, results = fetch_json_or_csv(f"{season}/{rnd}/results")
        if fmt == "json":
            save_json(results, os.path.join(out_dir, f"results_{season}_round_{rnd}.json"))
        else:
            save_text(results, os.path.join(out_dir, f"results_{season}_round_{rnd}.csv"))

        fmt, pitstops = fetch_json_or_csv(f"{season}/{rnd}/pitstops", params={"limit": 2000})
        if fmt == "json":
            save_json(pitstops, os.path.join(out_dir, f"pitstops_{season}_round_{rnd}.json"))
        else:
            save_text(pitstops, os.path.join(out_dir, f"pitstops_{season}_round_{rnd}.csv"))

        fmt, laptimes = fetch_json_or_csv(f"{season}/{rnd}/laps", params={"limit": 5000})
        if fmt == "json":
            save_json(laptimes, os.path.join(out_dir, f"laptimes_{season}_round_{rnd}.json"))
        else:
            save_text(laptimes, os.path.join(out_dir, f"laptimes_{season}_round_{rnd}.csv"))

        time.sleep(0.25)

def main():
    import argparse
    p = argparse.ArgumentParser(description="Ingest Ergast F1 data into data/bronze/ergast/")
    p.add_argument("--season", type=int, required=True, help="e.g., 2023")
    p.add_argument("--out", type=str, default="data/bronze/ergast", help="base output folder")
    args = p.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(args.out, f"season_{args.season}_{stamp}")

    ingest_season(args.season, out_dir)
    print(f"[OK] Saved Ergast season {args.season} -> {out_dir}")

if __name__ == "__main__":
    main()
