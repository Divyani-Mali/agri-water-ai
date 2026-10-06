from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import Alert, Farm, User
from app.models.models import Field as FieldModel
from app.schemas.alert import AlertOut

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


def visible_alerts(db: Session, user: User):
    """Alerts the user is allowed to see: own farms only (admin sees all)."""
    q = (
        db.query(Alert, FieldModel.name)
        .join(FieldModel, Alert.field_id == FieldModel.id)
        .join(Farm, FieldModel.farm_id == Farm.id)
    )
    if user.role != "admin":
        q = q.filter(Farm.owner_id == user.id)
    return q


def to_out(alert: Alert, field_name: str) -> AlertOut:
    return AlertOut(
        id=alert.id,
        field_id=alert.field_id,
        field_name=field_name,
        alert_type=alert.alert_type or "general",
        severity=alert.severity,
        message=alert.message,
        is_read=alert.is_read,
        created_at=alert.created_at,
    )


@router.get("", response_model=list[AlertOut])
def list_alerts(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = visible_alerts(db, user)
    if unread_only:
        q = q.filter(Alert.is_read.is_(False))
    rows = q.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit).all()
    return [to_out(a, name) for a, name in rows]


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count = visible_alerts(db, user).filter(Alert.is_read.is_(False)).count()
    return {"count": count}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ids = [a.id for a, _ in visible_alerts(db, user).filter(Alert.is_read.is_(False)).all()]
    if ids:
        db.query(Alert).filter(Alert.id.in_(ids)).update(
            {"is_read": True}, synchronize_session=False
        )
        db.commit()
    return {"marked": len(ids)}


@router.post("/{alert_id}/read", response_model=AlertOut)
def mark_read(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = visible_alerts(db, user).filter(Alert.id == alert_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert, name = row
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return to_out(alert, name)