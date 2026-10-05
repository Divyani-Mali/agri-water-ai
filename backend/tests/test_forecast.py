from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from app.core.config import settings
from app.services.forecast_service import MODEL_PATH
from ml.features import FEATURES, build_features

SENSOR = {"X-API-Key": settings.SENSOR_API_KEY}


def auth_headers(client, email):
    client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Test User", "password": "Test1234"},
    )
    r = client.post("/api/auth/login", data={"username": email, "password": "Test1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_field(client, h):
    farm = client.post(
        "/api/farms", json={"name": "Green Farm", "location": "Pune"}, headers=h
    ).json()
    return client.post(
        f"/api/farms/{farm['id']}/fields",
        json={"name": "Plot 1", "crop_type": "wheat", "area_acres": 2.0},
        headers=h,
    ).json()


def seed_yesterday(client, field_id):
    yday = (datetime.now(timezone.utc) - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )
    for h in range(24):
        client.post(
            f"/api/fields/{field_id}/readings",
            json={
                "soil_moisture": 25,
                "temperature": 20 + h * 0.5,
                "humidity": 55,
                "rainfall": 0,
                "wind_speed": 8,
                "timestamp": (yday + timedelta(hours=h)).isoformat(),
            },
            headers=SENSOR,
        )


def test_features_have_no_missing_values():
    g = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=10),
            "crop_type": "wheat",
            "soil_type": "loamy",
            "day_in_season": range(10),
            "growth_stage": "initial",
            "kc": 0.3,
            "temp_max": 30.0,
            "temp_min": 18.0,
            "humidity": 50.0,
            "wind_speed": 7.0,
            "rainfall": 0.0,
            "soil_moisture": 25.0,
        }
    )
    out = build_features(g)
    assert not out[FEATURES].isna().any().any()


def test_forecast_requires_login(client):
    assert client.get("/api/fields/1/forecast").status_code == 401


def test_forecast_without_readings_is_rejected(client):
    auth_headers(client, "admin@test.com")
    a = auth_headers(client, "a@test.com")
    field = make_field(client, a)
    r = client.get(f"/api/fields/{field['id']}/forecast", headers=a)
    assert r.status_code == 400


def test_forecast_days_validation(client):
    auth_headers(client, "admin@test.com")
    a = auth_headers(client, "a@test.com")
    field = make_field(client, a)
    r = client.get(f"/api/fields/{field['id']}/forecast?days=0", headers=a)
    assert r.status_code == 422


def test_forecast_other_farmer_gets_404(client):
    auth_headers(client, "admin@test.com")
    a = auth_headers(client, "a@test.com")
    b = auth_headers(client, "b@test.com")
    field = make_field(client, a)
    r = client.get(f"/api/fields/{field['id']}/forecast", headers=b)
    assert r.status_code == 404


@pytest.mark.skipif(not MODEL_PATH.exists(), reason="model not trained yet")
def test_forecast_works_with_readings(client):
    auth_headers(client, "admin@test.com")
    a = auth_headers(client, "a@test.com")
    field = make_field(client, a)
    seed_yesterday(client, field["id"])

    r = client.get(f"/api/fields/{field['id']}/forecast?days=3", headers=a)
    assert r.status_code == 200
    body = r.json()
    assert len(body["forecast"]) == 3
    assert all(day["predicted_water_mm"] >= 0 for day in body["forecast"])
    assert body["forecast"][0]["total_liters"] >= 0