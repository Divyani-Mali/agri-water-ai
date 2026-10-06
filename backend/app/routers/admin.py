from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.db.database import get_db
from app.models.models import Alert, Farm, SensorReading, User
from app.models.models import Field as FieldModel
from app.schemas.admin import AdminUserUpdate
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(User).order_by(User.id).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if data.is_active is None and data.role is None:
        raise HTTPException(status_code=400, detail="Nothing to update")
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot change your own account")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if data.is_active is not None:
        user.is_active = data.is_active
    if data.role is not None:
        user.role = data.role
    db.commit()
    db.refresh(user)
    return user


@router.get("/stats")
def stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return {
        "users": db.query(User).count(),
        "farms": db.query(Farm).count(),
        "fields": db.query(FieldModel).count(),
        "readings": db.query(SensorReading).count(),
        "unread_alerts": db.query(Alert).filter(Alert.is_read.is_(False)).count(),
    }