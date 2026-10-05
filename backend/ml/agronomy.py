"""Crop and soil constants shared by training and the API.
Mirrors simulator/sensor_model.py."""
from datetime import date

CROPS = {
    "wheat":     {"kc_ini": 0.30, "kc_mid": 1.15, "kc_end": 0.25, "days": 120},
    "rice":      {"kc_ini": 1.05, "kc_mid": 1.20, "kc_end": 0.90, "days": 130},
    "cotton":    {"kc_ini": 0.35, "kc_mid": 1.15, "kc_end": 0.70, "days": 180},
    "sugarcane": {"kc_ini": 0.40, "kc_mid": 1.25, "kc_end": 0.75, "days": 270},
    "maize":     {"kc_ini": 0.30, "kc_mid": 1.20, "kc_end": 0.60, "days": 125},
    "soybean":   {"kc_ini": 0.40, "kc_mid": 1.15, "kc_end": 0.50, "days": 120},
    "tomato":    {"kc_ini": 0.60, "kc_mid": 1.15, "kc_end": 0.80, "days": 135},
    "onion":     {"kc_ini": 0.70, "kc_mid": 1.05, "kc_end": 0.75, "days": 150},
}

SOILS = {
    "sandy": {"fc": 20.0, "wp": 8.0},
    "loamy": {"fc": 32.0, "wp": 14.0},
    "clay":  {"fc": 42.0, "wp": 24.0},
}


def day_in_season(planting_date: date, on_date: date, crop: str) -> int:
    return (on_date - planting_date).days % CROPS[crop]["days"]


def growth_stage(crop: str, day: int) -> str:
    f = (day % CROPS[crop]["days"]) / CROPS[crop]["days"]
    if f < 0.20:
        return "initial"
    if f < 0.45:
        return "development"
    if f < 0.75:
        return "mid"
    return "late"


def crop_coefficient(crop: str, day: int) -> float:
    p = CROPS[crop]
    f = (day % p["days"]) / p["days"]
    if f < 0.20:
        return p["kc_ini"]
    if f < 0.45:
        return p["kc_ini"] + (p["kc_mid"] - p["kc_ini"]) * (f - 0.20) / 0.25
    if f < 0.75:
        return p["kc_mid"]
    return p["kc_mid"] + (p["kc_end"] - p["kc_mid"]) * (f - 0.75) / 0.25