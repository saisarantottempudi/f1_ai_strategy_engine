from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.services.live_state import LiveStateStore
from app.services.strategy_service import recommend_strategy

router = APIRouter(prefix="/api", tags=["api"])
store = LiveStateStore()

class TelemetryUpdate(BaseModel):
    race_id: str
    driver: str
    lap: int
    lap_time_s: float
    position: int
    gap_ahead_s: float = 0.0
    gap_behind_s: float = 0.0
    tyre_compound: str = Field(..., description="SOFT/MEDIUM/HARD/INTER/WET")
    tyre_age_laps: int
    sc_status: str = "GREEN"  # GREEN/SC/VSC

class StrategyRequest(BaseModel):
    race_id: str
    driver: str
    horizon_laps: int = 15
    candidates: int = 30

@router.get("/health")
def health():
    return {"ok": True}

@router.post("/telemetry")
def post_telemetry(update: TelemetryUpdate):
    store.update(update.model_dump())
    return {"ok": True}

@router.post("/recommend")
def post_recommend(req: StrategyRequest):
    live = store.get(req.race_id, req.driver)
    if not live:
        return {"ok": False, "error": "No telemetry found. Call POST /api/telemetry first."}
    rec = recommend_strategy(live, horizon_laps=req.horizon_laps, candidates=req.candidates)
    return {"ok": True, "recommendation": rec}
