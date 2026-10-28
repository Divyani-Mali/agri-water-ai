"""Rule-based alert engine: dry soil, heat stress, heavy rain, offline sensors.
Each alert stores its numbers (params) so it can be shown in the user's language."""
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.i18n import render_alert
from app.models.models import Alert, SensorReading
from app.models.models import Field as FieldModel
from ml.agronomy import SOILS

FRESH_MINUTES = 30      # only react to readings newer than this
OFFLINE_MINUTES = 30    # no data for this long = sensor offline
HEAT_WARNING = 38.0     # deg C
HEAT_CRITICAL = 42.0
HEAVY_RAIN_MM = 10.0    # mm in one reading

COOLDOWN_HOURS = {"dry_soil": 6, "heat_stress": 6, "heavy_rain": 3, "sensor_offline": 6}
RANK = {"info": 0, "warning": 1, "critical": 2}


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _create(db: Session, field_id: int, alert_type: str, severity: str, params: dict):
    """Create an alert unless an equal or more severe one was raised recently."""
    since = utc_now() - timedelta(hours=COOLDOWN_HOURS[alert_type])
    recent = (
        db.query(Alert.severity)
        .filter(
            Alert.field_id == field_id,
            Alert.alert_type == alert_type,
            Alert.created_at >= since,
        )
        .all()
    )
    if any(RANK.get(s, 0) >= RANK[severity] for (s,) in recent):
        return None

    message = render_alert(alert_type, severity, params, "en") or alert_type
    alert = Alert(
        field_id=field_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        params=json.dumps(params),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def evaluate_reading(db: Session, field: FieldModel, reading: SensorReading) -> list:
    """Check one new sensor reading against the rules."""
    if reading.timestamp < utc_now() - timedelta(minutes=FRESH_MINUTES):
        return []  # old/backfilled data must not trigger alerts

    created = []
    soil = SOILS.get(field.soil_type, SOILS["loamy"])
    span = soil["fc"] - soil["wp"]
    pct = (reading.soil_moisture - soil["wp"]) / span

    if pct < 0.5:
        created.append(_create(
            db, field.id, "dry_soil", "critical",
            {"field": field.name, "moisture": reading.soil_moisture},
        ))
    elif pct < 0.7:
        created.append(_create(
            db, field.id, "dry_soil", "warning",
            {"field": field.name, "moisture": reading.soil_moisture},
        ))

    if reading.temperature >= HEAT_CRITICAL:
        created.append(_create(
            db, field.id, "heat_stress", "critical",
            {"field": field.name, "temperature": reading.temperature},
        ))
    elif reading.temperature >= HEAT_WARNING:
        created.append(_create(
            db, field.id, "heat_stress", "warning",
            {"field": field.name, "temperature": reading.temperature},
        ))

    if reading.rainfall >= HEAVY_RAIN_MM:
        created.append(_create(
            db, field.id, "heavy_rain", "warning",
            {"field": field.name, "rain": reading.rainfall},
        ))

    return [a for a in created if a is not None]


def check_offline(db: Session) -> int:
    """Raise an alert for every field whose sensors went silent. Returns alerts created."""
    now = utc_now()
    cutoff = now - timedelta(minutes=OFFLINE_MINUTES)
    count = 0
    for field in db.query(FieldModel).all():
        last = (
            db.query(func.max(SensorReading.timestamp))
            .filter(SensorReading.field_id == field.id)
            .scalar()
        )
        if last is None or last >= cutoff:
            continue
        minutes = int((now - last).total_seconds() // 60)
        alert = _create(
            db, field.id, "sensor_offline", "warning",
            {"field": field.name, "minutes": minutes},
        )
        if alert:
            count += 1
    return count


def run_offline_check() -> int:
    """Used by the background job (opens its own database session)."""
    with SessionLocal() as db:
        return check_offline(db)