from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import SensorReading, User
from app.models.models import Field as FieldModel
from app.routers.farms import get_field_or_404
from app.schemas.farm import ReadingCreate, ReadingOut

router = APIRouter(prefix="/api/fields", tags=["Sensor Readings"])


def verify_sensor_key(x_api_key: str = Header(...)):
    if x_api_key != settings.SENSOR_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid sensor API key")


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post(
    "/{field_id}/readings",
    response_model=ReadingOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_sensor_key)],
)
def add_reading(field_id: int, data: ReadingCreate, db: Session = Depends(get_db)):
    """Called by the sensor simulator (needs X-API-Key header)."""
    field = db.query(FieldModel).filter(FieldModel.id == field_id).first()
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")

    ts = data.timestamp
    if ts is not None:
        if ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
        if ts > utc_now() + timedelta(minutes=5):
            raise HTTPException(status_code=422, detail="Timestamp cannot be in the future")
    else:
        ts = utc_now()

    reading = SensorReading(
        field_id=field.id,
        timestamp=ts,
        soil_moisture=data.soil_moisture,
        temperature=data.temperature,
        humidity=data.humidity,
        rainfall=data.rainfall,
        wind_speed=data.wind_speed,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("/{field_id}/readings", response_model=list[ReadingOut])
def list_readings(
    field_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    field = get_field_or_404(db, field_id, user)
    return (
        db.query(SensorReading)
        .filter(SensorReading.field_id == field.id)
        .order_by(SensorReading.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.get("/{field_id}/readings/latest", response_model=ReadingOut)
def latest_reading(
    field_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    field = get_field_or_404(db, field_id, user)
    reading = (
        db.query(SensorReading)
        .filter(SensorReading.field_id == field.id)
        .order_by(SensorReading.timestamp.desc())
        .first()
    )
    if reading is None:
        raise HTTPException(status_code=404, detail="No readings yet for this field")
    return reading