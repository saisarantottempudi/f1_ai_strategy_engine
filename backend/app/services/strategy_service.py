from typing import Dict, Any, List

from app.simulator.strategy_simulator import evaluate_candidates

COMPOUNDS = ["SOFT", "MEDIUM", "HARD"]

def _build_candidate_grid(cur_lap: int, horizon_laps: int) -> List[Dict[str, Any]]:
    start = cur_lap + 1
    end = cur_lap + horizon_laps
    laps = list(range(start, end + 1))  # every lap
    cand = []
    for pit_lap in laps:
        for comp in COMPOUNDS:
            cand.append({"pit_lap": pit_lap, "compound": comp})
    return cand

def recommend_strategy(live: Dict[str, Any], horizon_laps: int = 15, candidates: int = 30) -> Dict[str, Any]:
    cur_lap = int(live["lap"])

    # Build full grid then truncate to desired size by taking evenly spaced pit laps
    grid = _build_candidate_grid(cur_lap, min(horizon_laps, 20))

    # If user asked for fewer candidates, take a spread:
    # pick pit laps every k steps and include all compounds
    if candidates and candidates < len(grid):
        # candidates should be multiple of 3 ideally (for 3 compounds)
        per_comp = max(1, candidates // 3)
        pit_laps = list(range(cur_lap + 1, cur_lap + min(horizon_laps, 20) + 1))
        step = max(1, len(pit_laps) // per_comp)
        chosen_laps = pit_laps[::step][:per_comp]

        grid = []
        for pit_lap in chosen_laps:
            for comp in COMPOUNDS:
                grid.append({"pit_lap": pit_lap, "compound": comp})

    results = evaluate_candidates(live, grid, horizon_laps=horizon_laps)
    results.sort(key=lambda x: (x["expected_finish_pos"], x["expected_delta_s"]))
    top = results[:3]

    best = top[0] if top else None
    action = "STAY_OUT"
    if best and best["strategy"]["pit_lap"] <= cur_lap + 2:
        in_laps = best["strategy"]["pit_lap"] - cur_lap
        action = f"PIT in {in_laps} laps for {best['strategy']['compound']}"

    return {
        "action_now": action,
        "top_strategies": top,
        "context": {
            "driver": live["driver"],
            "lap": cur_lap,
            "tyre": f"{live['tyre_compound']} age {live['tyre_age_laps']}",
            "sc_status": live.get("sc_status", "GREEN"
        )
        }
    }
