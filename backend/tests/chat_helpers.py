import json
from datetime import datetime, timezone

from app.db.database import get_db
from app.main import app
from app.models.models import Alert, Farm, SensorReading, User
from app.models.models import Field as FieldModel


def register(client, email, lang=None):
    body = {"email": email, "full_name": "Test User", "password": "Test1234"}
    if lang:
        body["preferred_language"] = lang
    client.post("/api/auth/register", json=body)
    r = client.post("/api/auth/login", data={"username": email, "password": "Test1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def db_session():
    return next(app.dependency_overrides[get_db]())


def seed_field(email, name="North Plot", moisture=28.0, reading=True):
    """Create a farm, a field and (optionally) one fresh reading straight in the database."""
    db = db_session()
    try:
        user = db.query(User).filter(User.email == email).first()
        farm = Farm(name=f"Farm {name}", location="Pune", owner_id=user.id)
        db.add(farm)
        db.flush()
        field = FieldModel(
            farm_id=farm.id, name=name, crop_type="wheat",
            soil_type="loamy", area_acres=2.0,
        )
        db.add(field)
        db.flush()
        if reading:
            db.add(SensorReading(
                field_id=field.id,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                soil_moisture=moisture, temperature=28.0, humidity=55.0,
                rainfall=0.0, wind_speed=6.0,
            ))
        db.commit()
        return field.id
    finally:
        db.close()


def add_alert(field_id, alert_type="dry_soil", severity="critical", name="North Plot"):
    db = db_session()
    try:
        db.add(Alert(
            field_id=field_id, alert_type=alert_type, severity=severity,
            message="Irrigation overdue in 'North Plot': soil moisture is 12.0%, below the irrigation trigger.",
            params=json.dumps({"field": name, "moisture": 12.0}),
        ))
        db.commit()
    finally:
        db.close()