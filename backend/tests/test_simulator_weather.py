from datetime import datetime
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "simulator"))

from run_simulator import FieldSim  # noqa: E402
from weather_client import OpenMeteoWeather, WeatherError  # noqa: E402


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params, timeout))
        response = next(self.responses)
        return response if isinstance(response, FakeResponse) else FakeResponse(response)


def forecast_data(times):
    return {
        "hourly": {
            "time": times,
            "temperature_2m": [25.0] * len(times),
            "relative_humidity_2m": [60.0] * len(times),
            "precipitation": [2.0] * len(times),
            "wind_speed_10m": [10.0] * len(times),
            "et0_fao_evapotranspiration": [0.1] * len(times),
        }
    }


def test_weather_geocodes_location_and_caches_hourly_forecast():
    session = FakeSession([
        {"results": [{"latitude": 18.52, "longitude": 73.85}]},
        forecast_data(["2026-01-01T10:00"]),
    ])
    weather = OpenMeteoWeather(session, past_days=3)
    farm = {"location": "Pune, Maharashtra"}

    weather.prepare(farm)
    reading = weather.hourly(farm, datetime(2026, 1, 1, 10, 30))

    assert reading["temperature_2m"] == 25.0
    assert session.calls[1][1]["latitude"] == 18.52
    assert session.calls[1][1]["past_days"] == 4
    assert len(session.calls) == 2


def test_saved_coordinates_skip_geocoding():
    session = FakeSession([forecast_data(["2026-01-01T10:00"])])
    weather = OpenMeteoWeather(session, past_days=0)

    weather.prepare({"latitude": 18.52, "longitude": 73.85, "location": "Pune"})

    assert len(session.calls) == 1
    assert session.calls[0][0].endswith("/forecast")


def test_missing_hourly_weather_fails_instead_of_fabricating_data():
    session = FakeSession([
        {"results": [{"latitude": 18.52, "longitude": 73.85}]},
        forecast_data(["2026-01-01T10:00"]),
        forecast_data(["2026-01-01T10:00"]),
    ])
    weather = OpenMeteoWeather(session, past_days=0)
    farm = {"location": "Pune"}
    weather.prepare(farm)

    with pytest.raises(WeatherError, match="no hourly data"):
        weather.hourly(farm, datetime(2026, 1, 1, 11))


class FixedWeather:
    def hourly(self, farm, timestamp):
        return {
            "temperature_2m": 25.0,
            "relative_humidity_2m": 60.0,
            "precipitation": 2.0,
            "wind_speed_10m": 10.0,
            "et0_fao_evapotranspiration": 0.1,
        }


def test_field_sim_applies_weather_over_real_elapsed_time():
    field = {
        "id": 2,
        "name": "North Plot",
        "crop_type": "wheat",
        "soil_type": "loamy",
        "planting_date": "2026-01-01",
        "farm": {"location": "Pune"},
    }
    sim = FieldSim(field, seed=1, weather=FixedWeather())
    sim.last_tick = datetime(2026, 1, 1, 9)

    reading = sim.tick(datetime(2026, 1, 1, 10))

    assert reading["rainfall"] == 2.0
    assert sim.moisture == pytest.approx(29.1925)

    next_reading = sim.tick(datetime(2026, 1, 1, 10, 30))
    assert next_reading["rainfall"] == 1.0
