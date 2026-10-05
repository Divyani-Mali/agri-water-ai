"""Turns the field's real sensor readings into a water demand forecast."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import Forecast, SensorReading
from app.models.models import Field as FieldModel
from ml.agronomy import crop_coefficient, day_in_season, growth_stage
from ml.features import FEATURES, build_features

MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "models" / "water_demand_model.joblib"
METRICS_PATH = MODEL_PATH.with_name("metrics.json")
ACRE_M2 = 4046.856
MIN_READINGS_PER_DAY = 12


class ModelNotReady(Exception):
    pass


class NotEnoughData(Exception):
    pass


_bundle = None


def load_model():
    global _bundle
    if _bundle is None:
        if not MODEL_PATH.exists():
            raise ModelNotReady("Model not trained yet. Run: python -m ml.train")
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def _crop_info(field: FieldModel, d: date) -> dict:
    n = day_in_season(field.planting_date, d, field.crop_type)
    return {
        "crop_type": field.crop_type,
        "soil_type": field.soil_type,
        "day_in_season": n,
        "growth_stage": growth_stage(field.crop_type, n),
        "kc": crop_coefficient(field.crop_type, n),
    }


def _daily_history(db: Session, field_id: int, today: date) -> pd.DataFrame:
    """Hourly readings -> one row per COMPLETE past day (today is excluded)."""
    end = datetime.combine(today, datetime.min.time())
    start = end - timedelta(days=10)
    rows = (
        db.query(SensorReading)
        .filter(
            SensorReading.field_id == field_id,
            SensorReading.timestamp >= start,
            SensorReading.timestamp < end,
        )
        .order_by(SensorReading.timestamp)
        .all()
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        [
            {
                "timestamp": r.timestamp,
                "temperature": r.temperature,
                "humidity": r.humidity,
                "rainfall": r.rainfall,
                "wind_speed": r.wind_speed,
                "soil_moisture": r.soil_moisture,
            }
            for r in rows
        ]
    )
    df["date"] = pd.to_datetime(df["timestamp"]).dt.normalize()
    daily = (
        df.groupby("date")
        .agg(
            n=("temperature", "size"),
            temp_max=("temperature", "max"),
            temp_min=("temperature", "min"),
            humidity=("humidity", "mean"),
            wind_speed=("wind_speed", "mean"),
            rainfall=("rainfall", "sum"),
            soil_moisture=("soil_moisture", "first"),  # morning reading
        )
        .reset_index()
    )
    return daily[daily["n"] >= MIN_READINGS_PER_DAY].drop(columns="n")


def forecast_field(db: Session, field: FieldModel, days: int) -> dict:
    today = _utc_today()

    history = _daily_history(db, field.id, today)
    if history.empty:
        raise NotEnoughData(
            f"Need at least one complete past day ({MIN_READINGS_PER_DAY}+ readings) "
            "of sensor data before forecasting."
        )

    latest = (
        db.query(SensorReading)
        .filter(SensorReading.field_id == field.id)
        .order_by(SensorReading.timestamp.desc())
        .first()
    )
    current_moisture = float(latest.soil_moisture)

    bundle = load_model()
    pipe = bundle["pipeline"]

    history = history.tail(7)
    rows = []
    for _, r in history.iterrows():
        rows.append({**r.to_dict(), **_crop_info(field, r["date"].date())})

    recent = history.tail(3)
    assumed = {
        "temp_max": float(recent["temp_max"].mean()),
        "temp_min": float(recent["temp_min"].mean()),
        "humidity": float(recent["humidity"].mean()),
        "wind_speed": float(recent["wind_speed"].mean()),
        "rainfall": 0.0,
        "soil_moisture": current_moisture,
    }

    out_days = []
    for i in range(days):
        d = today + timedelta(days=i)
        info = _crop_info(field, d)
        rows.append({"date": pd.Timestamp(d), **assumed, **info})

        feats = build_features(pd.DataFrame(rows))
        pred = max(0.0, float(pipe.predict(feats.iloc[[-1]][FEATURES])[0]))

        out_days.append(
            {
                "target_date": d,
                "growth_stage": info["growth_stage"],
                "kc": round(info["kc"], 3),
                "predicted_water_mm": round(pred, 2),
                "total_liters": round(pred * field.area_acres * ACRE_M2, 0),
            }
        )

    # store forecasts in the database (replace old ones for the same day/model)
    for item in out_days:
        db.query(Forecast).filter(
            Forecast.field_id == field.id,
            Forecast.target_date == item["target_date"],
            Forecast.model_name == bundle["model_name"],
        ).delete()
        db.add(
            Forecast(
                field_id=field.id,
                target_date=item["target_date"],
                predicted_water_mm=item["predicted_water_mm"],
                model_name=bundle["model_name"],
            )
        )
    db.commit()

    return {
        "field_id": field.id,
        "crop_type": field.crop_type,
        "soil_type": field.soil_type,
        "model_name": bundle["model_name"],
        "based_on_days": int(len(history)),
        "current_soil_moisture": round(current_moisture, 2),
        "assumptions": (
            "Future weather is assumed equal to the average of the last 3 complete days, "
            "with no rain. Soil moisture is held at the latest reading. "
            "Connect a weather-forecast API for better accuracy."
        ),
        "forecast": out_days,
    }