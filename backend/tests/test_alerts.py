from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.database import get_db
from app.main import app
from app.services.alert_service import check_offline

SENSOR = {"X-API-Key": settings.SENSOR_API_KEY}


def auth_headers(client, email):
    client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Test User", "password": "Test1234"},
    )
    r = client.post("/api/auth/login", data={"username": email, "password": "Test1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def setup(client):
    auth_headers(client, "admin@test.com")  # first user = admin
    a = auth_headers(client, "a@test.com")
    b = auth_headers(client, "b@test.com")
    farm = client.post(
        "/api/farms", json={"name": "Green Farm", "location": "Pune"}, headers=a
    ).json()
    field = client.post(
        f"/api/farms/{farm['id']}/fields",
        json={"name": "Plot 1", "crop_type": "wheat", "soil_type": "loamy", "area_acres": 2.0},
        headers=a,
    ).json()
    return a, b, field["id"]


def reading(client, field_id, **over):
    data = {"soil_moisture": 28, "temperature": 25, "humidity": 55, "rainfall": 0, "wind_speed": 5}
    data.update(over)
    r = client.post(f"/api/fields/{field_id}/readings", json=data, headers=SENSOR)
    assert r.status_code == 201
    return r


def alerts(client, h, **params):
    return client.get("/api/alerts", headers=h, params=params).json()


def test_normal_reading_creates_no_alert(client):
    a, _, fid = setup(client)
    reading(client, fid)
    assert alerts(client, a) == []


def test_dry_soil_warning(client):
    a, _, fid = setup(client)
    reading(client, fid, soil_moisture=25)
    got = alerts(client, a)
    assert len(got) == 1
    assert got[0]["alert_type"] == "dry_soil"
    assert got[0]["severity"] == "warning"


def test_dry_soil_critical(client):
    a, _, fid = setup(client)
    reading(client, fid, soil_moisture=12)
    got = alerts(client, a)
    assert got[0]["severity"] == "critical"
    assert got[0]["field_name"] == "Plot 1"


def test_cooldown_prevents_duplicates(client):
    a, _, fid = setup(client)
    reading(client, fid, soil_moisture=12)
    reading(client, fid, soil_moisture=12)
    reading(client, fid, soil_moisture=25)  # less severe than the existing critical one
    assert len(alerts(client, a)) == 1


def test_warning_escalates_to_critical(client):
    a, _, fid = setup(client)
    reading(client, fid, soil_moisture=25)
    reading(client, fid, soil_moisture=12)
    severities = sorted(x["severity"] for x in alerts(client, a))
    assert severities == ["critical", "warning"]


def test_heat_alert(client):
    a, _, fid = setup(client)
    reading(client, fid, temperature=43)
    got = alerts(client, a)
    assert got[0]["alert_type"] == "heat_stress"
    assert got[0]["severity"] == "critical"


def test_heavy_rain_alert(client):
    a, _, fid = setup(client)
    reading(client, fid, rainfall=15)
    assert alerts(client, a)[0]["alert_type"] == "heavy_rain"


def test_old_reading_does_not_alert(client):
    a, _, fid = setup(client)
    old = (datetime.now(timezone.utc) - timedelta(days=2)).replace(tzinfo=None).isoformat()
    reading(client, fid, soil_moisture=12, timestamp=old)
    assert alerts(client, a) == []


def test_other_farmer_cannot_see_or_read_alert(client):
    a, b, fid = setup(client)
    reading(client, fid, soil_moisture=12)
    alert_id = alerts(client, a)[0]["id"]
    assert alerts(client, b) == []
    assert client.post(f"/api/alerts/{alert_id}/read", headers=b).status_code == 404


def test_mark_read_and_unread_count(client):
    a, _, fid = setup(client)
    reading(client, fid, soil_moisture=12)
    assert client.get("/api/alerts/unread-count", headers=a).json()["count"] == 1

    alert_id = alerts(client, a)[0]["id"]
    r = client.post(f"/api/alerts/{alert_id}/read", headers=a)
    assert r.status_code == 200 and r.json()["is_read"] is True
    assert client.get("/api/alerts/unread-count", headers=a).json()["count"] == 0
    assert alerts(client, a, unread_only=True) == []


def test_mark_all_read(client):
    a, _, fid = setup(client)
    reading(client, fid, soil_moisture=12, temperature=43)  # two alerts at once
    assert len(alerts(client, a)) == 2
    assert client.post("/api/alerts/read-all", headers=a).json()["marked"] == 2
    assert client.get("/api/alerts/unread-count", headers=a).json()["count"] == 0


def test_alerts_require_login(client):
    assert client.get("/api/alerts").status_code == 401
    assert client.get("/api/alerts/unread-count").status_code == 401


def test_offline_sensor_alert(client):
    a, _, fid = setup(client)
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(tzinfo=None).isoformat()
    reading(client, fid, timestamp=old)

    db = next(app.dependency_overrides[get_db]())
    try:
        assert check_offline(db) == 1
        assert check_offline(db) == 0  # cooldown: no duplicate
    finally:
        db.close()

    got = alerts(client, a)
    assert got[0]["alert_type"] == "sensor_offline"