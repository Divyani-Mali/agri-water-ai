from app.core.config import settings

SENSOR = {"X-API-Key": settings.SENSOR_API_KEY}
READING = {
    "soil_moisture": 35.5,
    "temperature": 28,
    "humidity": 60,
    "rainfall": 0,
    "wind_speed": 8,
}


def auth_headers(client, email):
    client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Test User", "password": "Test1234"},
    )
    r = client.post(
        "/api/auth/login", data={"username": email, "password": "Test1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def setup_users(client):
    # first registered user is admin, so create an admin first
    auth_headers(client, "admin@test.com")
    return auth_headers(client, "a@test.com"), auth_headers(client, "b@test.com")


def make_field(client, h):
    farm = client.post(
        "/api/farms", json={"name": "Green Farm", "location": "Pune"}, headers=h
    ).json()
    field = client.post(
        f"/api/farms/{farm['id']}/fields",
        json={"name": "Plot 1", "crop_type": "wheat", "area_acres": 2.5},
        headers=h,
    ).json()
    return farm, field


def test_create_farm_and_field(client):
    a, _ = setup_users(client)
    farm, field = make_field(client, a)
    assert farm["name"] == "Green Farm"
    assert field["crop_type"] == "wheat"


def test_duplicate_farm_name_rejected(client):
    a, _ = setup_users(client)
    make_field(client, a)
    r = client.post(
        "/api/farms", json={"name": "Green Farm", "location": "Pune"}, headers=a
    )
    assert r.status_code == 400


def test_other_farmer_cannot_see_farm(client):
    a, b = setup_users(client)
    farm, field = make_field(client, a)
    assert client.get(f"/api/farms/{farm['id']}", headers=b).status_code == 404
    assert client.get(f"/api/fields/{field['id']}", headers=b).status_code == 404


def test_invalid_crop_rejected(client):
    a, _ = setup_users(client)
    farm, _ = make_field(client, a)
    r = client.post(
        f"/api/farms/{farm['id']}/fields",
        json={"name": "Plot 2", "crop_type": "banana", "area_acres": 1},
        headers=a,
    )
    assert r.status_code == 422


def test_future_planting_date_rejected(client):
    a, _ = setup_users(client)
    farm, _ = make_field(client, a)
    r = client.post(
        f"/api/farms/{farm['id']}/fields",
        json={
            "name": "Plot 3",
            "crop_type": "rice",
            "area_acres": 1,
            "planting_date": "2999-01-01",
        },
        headers=a,
    )
    assert r.status_code == 422


def test_reading_requires_api_key(client):
    a, _ = setup_users(client)
    _, field = make_field(client, a)
    url = f"/api/fields/{field['id']}/readings"
    assert client.post(url, json=READING).status_code == 422  # header missing
    assert client.post(url, json=READING, headers={"X-API-Key": "wrong"}).status_code == 401


def test_reading_out_of_range_rejected(client):
    a, _ = setup_users(client)
    _, field = make_field(client, a)
    bad = {**READING, "soil_moisture": 150}
    r = client.post(f"/api/fields/{field['id']}/readings", json=bad, headers=SENSOR)
    assert r.status_code == 422


def test_add_and_fetch_readings(client):
    a, _ = setup_users(client)
    _, field = make_field(client, a)
    url = f"/api/fields/{field['id']}/readings"

    assert client.get(url + "/latest", headers=a).status_code == 404  # none yet

    r = client.post(url, json=READING, headers=SENSOR)
    assert r.status_code == 201

    latest = client.get(url + "/latest", headers=a)
    assert latest.status_code == 200
    assert latest.json()["soil_moisture"] == 35.5
    assert len(client.get(url, headers=a).json()) == 1


def test_reading_unknown_field(client):
    r = client.post("/api/fields/999/readings", json=READING, headers=SENSOR)
    assert r.status_code == 404