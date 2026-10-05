"""Train, compare and save the water demand model.
Run from the backend folder:  python -m ml.train"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder  # noqa: E402
from xgboost import XGBRegressor  # noqa: E402

from ml.features import (  # noqa: E402
    CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES, build_features,
)

BASE = Path(__file__).resolve().parent
DATA_FILE = BASE / "data" / "water_demand.csv"
MODEL_DIR = BASE / "models"
DOCS_DIR = BASE.parent.parent / "docs"
TARGET = "water_demand_mm"
SENSOR_COLS = ["temp_max", "temp_min", "humidity", "wind_speed", "soil_moisture"]
TEST_DAYS = 180


def load_and_clean() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE, parse_dates=["date"])
    print(f"Loaded {len(df):,} rows. Missing sensor values: {int(df[SENSOR_COLS].isna().sum().sum())}")

    parts = []
    for _, g in df.groupby(["crop_type", "soil_type"]):
        g = g.sort_values("date").copy()
        # fix broken sensors: fill gaps by interpolating between neighbouring days
        g[SENSOR_COLS] = g[SENSOR_COLS].interpolate(limit_direction="both")
        parts.append(build_features(g))

    out = pd.concat(parts).sort_values("date").reset_index(drop=True)
    print(f"Missing values after cleaning: {int(out[FEATURES].isna().sum().sum())}")
    return out


def make_pipeline(estimator) -> Pipeline:
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ("num", "passthrough", NUMERIC_FEATURES),
    ])
    return Pipeline([("prep", prep), ("model", estimator)])


def make_estimators() -> dict:
    return {
        "random_forest": RandomForestRegressor(
            n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=42
        ),
        "xgboost": XGBRegressor(
            n_estimators=600, learning_rate=0.05, max_depth=6, subsample=0.8,
            colsample_bytree=0.8, random_state=42, n_jobs=-1,
        ),
    }


def evaluate(y_true, y_pred) -> dict:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
    }


def main():
    df = load_and_clean()

    cutoff = df["date"].max() - pd.Timedelta(days=TEST_DAYS)
    train, test = df[df["date"] <= cutoff], df[df["date"] > cutoff]
    print(f"Train: {len(train):,} rows (up to {cutoff.date()})  |  Test: {len(test):,} rows (last {TEST_DAYS} days)\n")

    results = {}

    # baseline: just the average demand of each crop
    base = train.groupby("crop_type")[TARGET].mean()
    results["baseline_crop_average"] = evaluate(test[TARGET], test["crop_type"].map(base))

    fitted = {}
    for name, est in make_estimators().items():
        pipe = make_pipeline(est)
        pipe.fit(train[FEATURES], train[TARGET])
        results[name] = evaluate(test[TARGET], pipe.predict(test[FEATURES]))
        fitted[name] = pipe

    table = pd.DataFrame(results).T.round(3)
    print("Test results (lower MAE/RMSE is better, R2 closer to 1 is better):")
    print(table, "\n")

    best_name = min(fitted, key=lambda n: results[n]["rmse"])
    print(f"Best model: {best_name}")

    # ---- charts for the report ----
    DOCS_DIR.mkdir(exist_ok=True)
    best_pipe = fitted[best_name]

    names = [n.split("__", 1)[1] for n in best_pipe.named_steps["prep"].get_feature_names_out()]
    imp = pd.Series(best_pipe.named_steps["model"].feature_importances_, index=names)
    imp = imp.sort_values().tail(12)
    plt.figure(figsize=(8, 5))
    imp.plot(kind="barh", color="#2e7d32")
    plt.title(f"Top features driving water demand ({best_name})")
    plt.xlabel("Importance")
    plt.tight_layout()
    plt.savefig(DOCS_DIR / "feature_importance.png", dpi=120)
    plt.close()

    sub = test[(test["crop_type"] == "wheat") & (test["soil_type"] == "loamy")].sort_values("date")
    plt.figure(figsize=(10, 4))
    plt.plot(sub["date"], sub[TARGET], label="Actual", color="#1565c0")
    plt.plot(sub["date"], best_pipe.predict(sub[FEATURES]), label="Predicted", color="#ef6c00", linestyle="--")
    plt.title("Daily water demand: wheat on loamy soil (test period)")
    plt.ylabel("mm per day")
    plt.legend()
    plt.tight_layout()
    plt.savefig(DOCS_DIR / "actual_vs_predicted.png", dpi=120)
    plt.close()

    # ---- final model: refit on ALL data, then save ----
    final = make_pipeline(make_estimators()[best_name])
    final.fit(df[FEATURES], df[TARGET])

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(
        {
            "pipeline": final,
            "model_name": best_name,
            "features": FEATURES,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        },
        MODEL_DIR / "water_demand_model.joblib",
    )
    with open(MODEL_DIR / "metrics.json", "w") as f:
        json.dump(
            {
                "best_model": best_name,
                "test_days": TEST_DAYS,
                "train_rows": int(len(train)),
                "test_rows": int(len(test)),
                "results": results,
            },
            f,
            indent=2,
        )
    print("\nSaved: backend/ml/models/water_demand_model.joblib, metrics.json")
    print("Charts saved in docs/")


if __name__ == "__main__":
    main()