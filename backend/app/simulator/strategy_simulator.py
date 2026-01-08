from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import math

from app.services.model_service import predict_next_lap

PIT_LOSS_S = 22.0

def _safe_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _is_finite(x: float) -> bool:
    return not (math.isnan(x) or math.isinf(x))

def _winsorize(arr: np.ndarray, p: float = 0.10) -> np.ndarray:
    if arr.size == 0:
        return arr
    lo = np.quantile(arr, p)
    hi = np.quantile(arr, 1.0 - p)
    return np.clip(arr, lo, hi)

def evaluate_candidates(
    live: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    horizon_laps: int = 15,
    mc_runs: int = 15
) -> List[Dict[str, Any]]:
    cur_lap = int(live["lap"])
    position0 = int(live["position"])

    lap_time_obs = _safe_float(live.get("lap_time_s", 95.0), 95.0)
    tyre_age0 = int(live.get("tyre_age_laps", 1))
    compound0 = str(live.get("tyre_compound", "MEDIUM")).upper()

    # categorical context (must match training)
    driver_id = str(live.get("driver", "UNK")).upper()
    race_id = str(live.get("race_id", "demo_race"))

    pace_roll_mean0 = _safe_float(live.get("pace_roll_mean", lap_time_obs), lap_time_obs)
    pace_roll_std0 = _safe_float(live.get("pace_roll_std", 0.8), 0.8)
    deg_roll_slope0 = _safe_float(live.get("deg_roll_slope", 0.0), 0.0)

    track_status = int(live.get("track_status", 1)) if str(live.get("track_status", "")).isdigit() else 1

    # tighter clamp
    clamp_lo = max(60.0, lap_time_obs - 8.0)
    clamp_hi = min(160.0, lap_time_obs + 12.0)

    def simulate_once(pit_lap: Optional[int], new_compound: Optional[str], rng: np.random.Generator) -> float:
        total = 0.0
        tyre_age = tyre_age0
        compound = compound0
        lap_time = lap_time_obs

        pace_roll_mean = pace_roll_mean0
        pace_roll_std = pace_roll_std0
        deg_roll_slope = deg_roll_slope0

        hist = [lap_time_obs]

        for lap in range(cur_lap + 1, cur_lap + horizon_laps + 1):
            pitted_flag = 0
            if pit_lap is not None and lap == pit_lap:
                total += PIT_LOSS_S
                tyre_age = 0
                if new_compound:
                    compound = new_compound
                pitted_flag = 1

            tail = hist[-5:]
            if len(tail) >= 2:
                pace_roll_mean = float(np.mean(tail))
                pace_roll_std = float(np.std(tail)) if len(tail) > 1 else 0.0

                y = np.array(tail, dtype=float)
                x = np.arange(len(y), dtype=float)
                x = x - x.mean()
                denom = (x**2).sum()
                deg_roll_slope = float(((x) * (y - y.mean())).sum() / denom) if denom != 0 else 0.0

            feats = {
                "lap": int(lap),
                "tyre_age": float(tyre_age),
                "lap_time": float(lap_time),
                "pace_roll_mean": float(pace_roll_mean),
                "pace_roll_std": float(pace_roll_std),
                "deg_roll_slope": float(deg_roll_slope),
                "position": float(position0),
                "track_status": int(track_status),
                "pitted_this_lap": int(pitted_flag),
                "compound": str(compound),
                "driver": driver_id,
                "race_id": race_id,
            }

            pred = float(predict_next_lap(feats))

            if not _is_finite(pred):
                pred = float(pace_roll_mean)

            noise_sigma = max(0.15, min(1.2, float(pace_roll_std)))
            pred = pred + float(rng.normal(0.0, noise_sigma))
            pred = _clamp(pred, clamp_lo, clamp_hi)

            total += pred
            lap_time = pred
            hist.append(pred)
            tyre_age += 1

        return total

    def simulate_mc(pit_lap: Optional[int], new_compound: Optional[str]) -> Tuple[float, float]:
        rng = np.random.default_rng(42)
        totals = np.array([simulate_once(pit_lap, new_compound, rng) for _ in range(mc_runs)], dtype=float)
        totals = _winsorize(totals, p=0.10)
        return float(totals.mean()), float(totals.std())

    base_mean, _ = simulate_mc(None, None)

    out = []
    for c in candidates:
        pit_lap = int(c["pit_lap"])
        new_comp = str(c["compound"]).upper()

        mean_total, std_total = simulate_mc(pit_lap, new_comp)
        delta = mean_total - base_mean

        pos_shift = int(round(delta / 8.0))
        expected_pos = max(1, position0 + pos_shift)

        risk = min(1.0, 0.10 + (std_total / 10.0) + abs(delta) / 80.0)

        out.append({
            "strategy": {"pit_lap": pit_lap, "compound": new_comp, "stops": 1},
            "expected_finish_pos": expected_pos,
            "expected_delta_s": round(delta, 2),
            "uncertainty_s": round(std_total, 2),
            "risk": round(float(risk), 2),
            "notes": f"Model+MC simulator stable (mc_runs={mc_runs})"
        })

    return out