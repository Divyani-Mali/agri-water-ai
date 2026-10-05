"""Feature engineering, used for BOTH training and live forecasting."""
import numpy as np
import pandas as pd

from ml.agronomy import SOILS

NUMERIC_FEATURES = [
    "day_in_season", "kc", "temp_max", "temp_min", "temp_mean", "temp_range",
    "humidity", "wind_speed", "rainfall", "soil_moisture", "soil_dryness",
    "rain_prev3", "rain_prev7", "temp_max_prev1", "doy_sin", "doy_cos",
]
CATEGORICAL_FEATURES = ["crop_type", "soil_type", "growth_stage"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def build_features(g: pd.DataFrame) -> pd.DataFrame:
    """g = daily rows of ONE field/combination."""
    g = g.copy()
    g["date"] = pd.to_datetime(g["date"])
    g = g.sort_values("date")

    g["temp_mean"] = (g["temp_max"] + g["temp_min"]) / 2
    g["temp_range"] = g["temp_max"] - g["temp_min"]

    doy = g["date"].dt.dayofyear
    g["doy_sin"] = np.sin(2 * np.pi * doy / 365)
    g["doy_cos"] = np.cos(2 * np.pi * doy / 365)

    past_rain = g["rainfall"].shift(1)
    g["rain_prev3"] = past_rain.rolling(3, min_periods=1).sum().fillna(0)
    g["rain_prev7"] = past_rain.rolling(7, min_periods=1).sum().fillna(0)
    g["temp_max_prev1"] = g["temp_max"].shift(1).fillna(g["temp_max"])

    wp = g["soil_type"].map(lambda s: SOILS[s]["wp"])
    fc = g["soil_type"].map(lambda s: SOILS[s]["fc"])
    g["soil_dryness"] = (1 - (g["soil_moisture"] - wp) / (fc - wp)).clip(0, 1)
    return g