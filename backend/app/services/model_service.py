from typing import Dict, Any
import os
import joblib
import pandas as pd

MODEL_PATH = "backend/app/ml/models/pace_model.joblib"

_model = None

def load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Train it first.")
        _model = joblib.load(MODEL_PATH)
    return _model

def predict_next_lap(features: Dict[str, Any]) -> float:
    """
    Predict next lap time (seconds) using trained pipeline.
    Expected features include:
      lap, tyre_age, lap_time, pace_roll_mean, pace_roll_std, deg_roll_slope,
      position, track_status, pitted_this_lap, compound
    """
    model = load_model()
    X = pd.DataFrame([features])
    pred = float(model.predict(X)[0])
    return pred
