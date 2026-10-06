"""Rule-based alert engine: dry soil, heat stress, heavy rain, offline sensors."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
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


def _ago(minutes: int) -> str:
    if minutes < 120:
        return f"{minutes} minutes"
    if minutes < 2880:
        return f"{minutes // 60} hours"
    return f"{minutes // 1440} days"


def _create(db: Session, field_id: int, alert_type: str, severity: str, message: str):
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

    alert = Alert(
        field_id=field_id, alert_type=alert_type, severity=severity, message=message
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
            f"Irrigation overdue in '{field.name}': soil moisture is {reading.soil_moisture:.1f}%, "
            f"below the irrigation trigger.",
        ))
    elif pct < 0.7:
        created.append(_create(
            db, field.id, "dry_soil", "warning",
            f"Soil in '{field.name}' is getting dry ({reading.soil_moisture:.1f}%). "
            f"Irrigation will be needed soon.",
        ))

    if reading.temperature >= HEAT_CRITICAL:
        created.append(_create(
            db, field.id, "heat_stress", "critical",
            f"Extreme heat in '{field.name}': {reading.temperature:.1f} C. "
            f"High risk of crop heat stress.",
        ))
    elif reading.temperature >= HEAT_WARNING:
        created.append(_create(
            db, field.id, "heat_stress", "warning",
            f"High temperature in '{field.name}': {reading.temperature:.1f} C. "
            f"Crops may need extra water.",
        ))

    if reading.rainfall >= HEAVY_RAIN_MM:
        created.append(_create(
            db, field.id, "heavy_rain", "warning",
            f"Heavy rain in '{field.name}' ({reading.rainfall:.1f} mm). "
            f"Consider postponing irrigation.",
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
            f"No sensor data from '{field.name}' for {_ago(minutes)}. Please check the sensors.",
        )
        if alert:
            count += 1
    return count


def run_offline_check() -> int:
    """Used by the background job (opens its own database session)."""
    with SessionLocal() as db:
        return check_offline(db)