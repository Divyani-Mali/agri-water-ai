"""Shared virtual-farm model: weather, crop water use, soil moisture."""
import math

import numpy as np

# Crop coefficients (Kc) at initial / mid / end stage, season length in days
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

# Soil moisture (%): field capacity (full) and wilting point (empty)
SOILS = {
    "sandy": {"fc": 20.0, "wp": 8.0},
    "loamy": {"fc": 32.0, "wp": 14.0},
    "clay":  {"fc": 42.0, "wp": 24.0},
}

ROOT_ZONE_MM = 400.0
MM_TO_PCT = 100.0 / ROOT_ZONE_MM  # 1 mm of water = 0.25 % soil moisture

# Share of the daily crop water use that happens in each hour (daytime only)
HOUR_WEIGHTS = [max(0.0, math.sin(math.pi * (h - 6) / 12)) for h in range(24)]
HOUR_WEIGHT_SUM = sum(HOUR_WEIGHTS)


# ---------------- crop ----------------
def growth_stage(crop: str, day_in_season: int) -> str:
    f = (day_in_season % CROPS[crop]["days"]) / CROPS[crop]["days"]
    if f < 0.20:
        return "initial"
    if f < 0.45:
        return "development"
    if f < 0.75:
        return "mid"
    return "late"


def crop_coefficient(crop: str, day_in_season: int) -> float:
    p = CROPS[crop]
    f = (day_in_season % p["days"]) / p["days"]
    if f < 0.20:
        return p["kc_ini"]
    if f < 0.45:
        return p["kc_ini"] + (p["kc_mid"] - p["kc_ini"]) * (f - 0.20) / 0.25
    if f < 0.75:
        return p["kc_mid"]
    return p["kc_mid"] + (p["kc_end"] - p["kc_mid"]) * (f - 0.75) / 0.25


# ---------------- weather ----------------
def generate_daily_weather(day_of_year: int, rng: np.random.Generator) -> dict:
    """One day of Pune-like weather."""
    season = math.sin(2 * math.pi * (day_of_year - 34) / 365)
    monsoon = 152 <= day_of_year <= 273   # June - September
    post_monsoon = 274 <= day_of_year <= 304  # October

    tmean = 25.5 + 4.5 * season + rng.normal(0, 1.2)
    if monsoon:
        tmean -= 2.5
    half_range = 4.0 if monsoon else 6.5
    tmax = tmean + half_range + rng.normal(0, 0.8)
    tmin = tmean - half_range + rng.normal(0, 0.8)

    if monsoon:
        p_rain, mean_rain = 0.55, 16.0
    elif post_monsoon:
        p_rain, mean_rain = 0.15, 10.0
    else:
        p_rain, mean_rain = 0.03, 6.0
    rain = float(min(rng.exponential(mean_rain), 150.0)) if rng.random() < p_rain else 0.0

    base_hum = 80.0 if monsoon else (62.0 if post_monsoon else 50.0)
    humidity = base_hum + (28.0 - tmax) + (8.0 if rain > 0 else 0.0) + rng.normal(0, 6)
    humidity = float(min(max(humidity, 20.0), 100.0))

    wind = float(min(max(rng.normal(12.0 if monsoon else 7.0, 3.0), 0.0), 40.0))

    return {
        "temp_max": float(tmax),
        "temp_min": float(tmin),
        "humidity": humidity,
        "wind_speed": wind,
        "rainfall": rain,
    }


# ---------------- water physics ----------------
def extraterrestrial_radiation(day_of_year: int, lat_deg: float) -> float:
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    delta = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
    ws = math.acos(-math.tan(phi) * math.tan(delta))
    return (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(delta)
        + math.cos(phi) * math.cos(delta) * math.sin(ws)
    )


def reference_et(tmax, tmin, humidity, wind, day_of_year, lat_deg=18.5) -> float:
    """Simplified Hargreaves ET0 (mm/day) with small humidity/wind corrections."""
    tmean = (tmax + tmin) / 2
    ra = extraterrestrial_radiation(day_of_year, lat_deg)
    et0 = 0.0023 * (tmean + 17.8) * math.sqrt(max(tmax - tmin, 0.1)) * 0.408 * ra
    et0 *= (1 + 0.004 * (50 - humidity)) * (1 + 0.01 * (wind - 8))
    return max(et0, 0.3)


def irrigation_trigger(soil: str) -> float:
    s = SOILS[soil]
    return s["wp"] + 0.5 * (s["fc"] - s["wp"])


def water_demand(etc_mm: float, eff_rain_mm: float, soil_moisture: float, soil: str) -> float:
    """Irrigation requirement (mm): crop need minus rain, adjusted by soil dryness."""
    s = SOILS[soil]
    rel = (soil_moisture - s["wp"]) / (s["fc"] - s["wp"])
    rel = min(max(rel, 0.0), 1.0)
    adj = min(max(1.3 - 0.8 * rel, 0.6), 1.3)
    return max(0.0, etc_mm - eff_rain_mm) * adj


def step_soil_day(moisture: float, soil: str, etc_mm: float, eff_rain_mm: float):
    """Advance soil moisture by one day. Returns (new_moisture, irrigation_mm)."""
    s = SOILS[soil]
    m = moisture + (eff_rain_mm - etc_mm) * MM_TO_PCT
    m = min(max(m, s["wp"]), s["fc"])
    irrigation_mm = 0.0
    if m < irrigation_trigger(soil):
        irrigation_mm = (s["fc"] - m) / MM_TO_PCT
        m = s["fc"]
    return m, irrigation_mm