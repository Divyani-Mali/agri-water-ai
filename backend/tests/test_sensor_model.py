import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "simulator"))

from sensor_model import (  # noqa: E402
    SOILS, crop_coefficient, generate_daily_weather, reference_et,
    step_soil_day, water_demand,
)


def test_kc_follows_growth_stages():
    assert crop_coefficient("wheat", 0) == 0.30
    assert crop_coefficient("wheat", 70) == 1.15
    assert crop_coefficient("wheat", 119) < 1.15


def test_et0_is_realistic_for_hot_dry_day():
    et0 = reference_et(36, 23, 40, 8, 130, 18.5)
    assert 4 < et0 < 9


def test_dry_soil_needs_more_water_than_wet_soil():
    dry = water_demand(5, 0, SOILS["loamy"]["wp"], "loamy")
    wet = water_demand(5, 0, SOILS["loamy"]["fc"], "loamy")
    assert dry > wet


def test_soil_moisture_stays_in_physical_bounds():
    rng = np.random.default_rng(1)
    s = SOILS["sandy"]
    m = s["fc"]
    for day in range(1, 366):
        w = generate_daily_weather(day, rng)
        et0 = reference_et(w["temp_max"], w["temp_min"], w["humidity"], w["wind_speed"], day)
        m, _ = step_soil_day(m, "sandy", 1.1 * et0, 0.8 * w["rainfall"])
        assert s["wp"] <= m <= s["fc"]