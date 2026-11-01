import json
from datetime import date, datetime, timezone

from app.i18n import ASSUMPTIONS
from app.models.models import Field as FieldModel
from app.models.models import SensorReading
from app.services.alert_service import evaluate_reading

from chat_helpers import add_alert, db_session, register, seed_field


def me(client, headers):
    return client.get("/api/auth/me", headers=headers).json()


def test_default_language_is_english(client):
    h = register(client, "admin@test.com")
    assert me(client, h)["preferred_language"] == "en"


def test_register_with_hindi_and_change_it(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "hi")
    assert me(client, h)["preferred_language"] == "hi"
    r = client.patch("/api/auth/me", json={"preferred_language": "mr"}, headers=h)
    assert r.status_code == 200 and r.json()["preferred_language"] == "mr"
    assert me(client, h)["preferred_language"] == "mr"


def test_invalid_language_is_rejected(client):
    h = register(client, "admin@test.com")
    r = client.patch("/api/auth/me", json={"preferred_language": "fr"}, headers=h)
    assert r.status_code == 422
    assert client.patch("/api/auth/me", json={"preferred_language": "hi"}).status_code == 401


def test_alerts_follow_the_users_language_and_the_override(client):
    register(client, "admin@test.com")
    h = register(client, "a@test.com", "hi")
    add_alert(seed_field("a@test.com"))

    hindi = client.get("/api/alerts", headers=h).json()[0]["message"]
    assert "सिंचाई" in hindi
    marathi = client.get("/api/alerts?lang=mr", headers=h).json()[0]["message"]
    assert "सिंचनाची" in marathi
    english = client.get("/api/alerts?lang=en", headers=h).json()[0]["message"]
    assert english.startswith("Irrigation overdue")
    assert client.get("/api/alerts?lang=xx", headers=h).json()[0]["message"] == hindi


def test_old_alerts_without_numbers_stay_in_english(client):
    from app.models.models import Alert

    register(client, "admin@test.com")
    h = register(client, "a@test.com", "hi")
    fid = seed_field("a@test.com")
    db = db_session()
    db.add(Alert(field_id=fid, alert_type="dry_soil", severity="critical", message="Old English text"))
    db.commit()
    db.close()
    assert client.get("/api/alerts", headers=h).json()[0]["message"] == "Old English text"


def test_new_alerts_store_their_numbers(client):
    register(client, "admin@test.com")
    register(client, "a@test.com")
    fid = seed_field("a@test.com", reading=False)

    db = db_session()
    try:
        field = db.query(FieldModel).filter(FieldModel.id == fid).first()
        reading = SensorReading(
            field_id=fid,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            soil_moisture=12.0, temperature=43.0, humidity=30.0,
            rainfall=15.0, wind_speed=5.0,
        )
        db.add(reading)
        db.commit()
        created = evaluate_reading(db, field, reading)
        assert len(created) == 3
        params = json.loads(created[0].params)
        assert params["field"] == "North Plot" and params["moisture"] == 12.0
        assert created[0].message.startswith("Irrigation overdue")
    finally:
        db.close()


def test_forecast_labels_are_translated(client, monkeypatch):
    def fake(db, field, days):
        return {
            "field_id": field.id,
            "crop_type": field.crop_type,
            "soil_type": field.soil_type,
            "model_name": "xgboost",
            "based_on_days": 7,
            "current_soil_moisture": 28.0,
            "assumptions": ASSUMPTIONS[0]["en"],
            "forecast": [
                {
                    "target_date": date.today(),
                    "growth_stage": "initial",
                    "kc": 0.3,
                    "predicted_water_mm": 0.8,
                    "total_liters": 8000.0,
                }
            ],
        }

    monkeypatch.setattr("app.routers.forecast.forecast_field", fake)
    register(client, "admin@test.com")
    h = register(client, "a@test.com")
    other = register(client, "b@test.com")
    fid = seed_field("a@test.com")

    hindi = client.get(f"/api/fields/{fid}/forecast?days=1&lang=hi", headers=h).json()
    assert hindi["crop_label"] == "गेहूँ"
    assert hindi["forecast"][0]["growth_stage_label"] == "शुरुआती"
    assert hindi["assumptions"] == ASSUMPTIONS[0]["hi"]

    english = client.get(f"/api/fields/{fid}/forecast?days=1", headers=h).json()
    assert english["crop_label"] == "Wheat"
    assert english["assumptions"] == ASSUMPTIONS[0]["en"]

    assert client.get(f"/api/fields/{fid}/forecast?days=1", headers=other).status_code == 404