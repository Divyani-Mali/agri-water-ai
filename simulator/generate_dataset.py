"""Generates a ~3 year daily dataset for every crop x soil combination."""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from sensor_model import (
    CROPS, SOILS, crop_coefficient, generate_daily_weather, growth_stage,
    reference_et, step_soil_day, water_demand,
)

START_DATE = date(2023, 10, 5)
N_DAYS = 1096
LATITUDE = 18.5
OUT_FILE = Path(__file__).resolve().parent.parent / "backend" / "ml" / "data" / "water_demand.csv"


def simulate_combo(crop: str, soil: str, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    season_offset = int(rng.integers(0, CROPS[crop]["days"]))
    moisture = SOILS[soil]["fc"]
    rows = []

    for i in range(N_DAYS):
        d = START_DATE + timedelta(days=i)
        doy = d.timetuple().tm_yday
        w = generate_daily_weather(doy, rng)
        et0 = reference_et(
            w["temp_max"], w["temp_min"], w["humidity"], w["wind_speed"], doy, LATITUDE
        )
        day_in_season = (i + season_offset) % CROPS[crop]["days"]
        kc = crop_coefficient(crop, day_in_season)
        etc = kc * et0
        eff_rain = 0.8 * w["rainfall"]
        demand = water_demand(etc, eff_rain, moisture, soil)
        new_moisture, irrigation = step_soil_day(moisture, soil, etc, eff_rain)

        rows.append({
            "date": d.isoformat(),
            "crop_type": crop,
            "soil_type": soil,
            "day_in_season": day_in_season,
            "growth_stage": growth_stage(crop, day_in_season),
            "kc": round(kc, 3),
            "temp_max": round(w["temp_max"], 2),
            "temp_min": round(w["temp_min"], 2),
            "humidity": round(w["humidity"], 2),
            "wind_speed": round(w["wind_speed"], 2),
            "rainfall": round(w["rainfall"], 2),
            "soil_moisture": round(moisture, 2),   # morning reading
            "et0": round(et0, 3),
            "etc": round(etc, 3),
            "irrigation_applied_mm": round(irrigation, 2),
            "water_demand_mm": round(demand, 3),   # <- target for ML
        })
        moisture = new_moisture
    return rows


def main():
    all_rows = []
    seed = 42
    for crop in CROPS:
        for soil in SOILS:
            all_rows.extend(simulate_combo(crop, soil, seed))
            seed += 1

    df = pd.DataFrame(all_rows)

    # Real sensors fail sometimes: knock out ~1.5% of sensor values
    rng = np.random.default_rng(7)
    for col in ["temp_max", "temp_min", "humidity", "wind_speed", "soil_moisture"]:
        df.loc[rng.random(len(df)) < 0.015, col] = np.nan

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False)

    print(f"Saved {len(df):,} rows to {OUT_FILE}")
    print(f"Missing sensor values: {int(df.isna().sum().sum())}")
    print("\nAverage daily water demand (mm) by crop:")
    print(df.groupby("crop_type")["water_demand_mm"].mean().round(2))


if __name__ == "__main__":
    main()