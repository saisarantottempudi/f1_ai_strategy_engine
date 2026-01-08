import os
import joblib
import argparse
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.ensemble import GradientBoostingRegressor

MODEL_DIR = "backend/app/ml/models"

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def main():
    p = argparse.ArgumentParser(description="Train lap time prediction model")
    p.add_argument("--data", type=str, default="data/gold/lap_features_gold.csv")
    p.add_argument("--model_out", type=str, default=os.path.join(MODEL_DIR, "pace_model.joblib"))
    args = p.parse_args()

    ensure_dir(MODEL_DIR)

    df = pd.read_csv(args.data)

    target = "lap_time_next"

    features_num = [
        "lap",
        "tyre_age",
        "lap_time",
        "pace_roll_mean",
        "pace_roll_std",
        "deg_roll_slope",
        "position",
        "track_status",
        "pitted_this_lap",
    ]
    features_cat = ["compound"]

    X = df[features_num + features_cat].copy()
    y = df[target].copy()

    # Fill missing numeric values safely (no SettingWithCopyWarning)
    medians = X[features_num].median(numeric_only=True)
    X.loc[:, features_num] = X[features_num].fillna(medians)

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), features_cat),
            ("num", "passthrough", features_num),
        ]
    )

    model = GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=3,
        random_state=42,
    )

    pipe = Pipeline(steps=[
        ("prep", preprocessor),
        ("model", model),
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    pipe.fit(X_train, y_train)

    preds = pipe.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    mse = mean_squared_error(y_test, preds)   # no 'squared' arg for compatibility
    rmse = float(np.sqrt(mse))

    joblib.dump(pipe, args.model_out)

    print("[OK] Pace model trained & saved")
    print(f" - model: {args.model_out}")
    print(f" - MAE : {mae:.3f} sec")
    print(f" - RMSE: {rmse:.3f} sec")
    print(f" - train rows: {len(X_train)}  test rows: {len(X_test)}")

if __name__ == "__main__":
    main()
