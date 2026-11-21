"""Government Schemes API — fully isolated from existing irrigation features."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.database import get_db
from app.models.models import GovernmentScheme, SchemeNotification, User
from app.schemas.scheme import (
    SchemeCreate, SchemeNotificationOut, SchemeOut, SchemeUpdate,
)
from app.services.scheme_service import (
    create_notifications_for_user, get_recommendations, notify_all_users_new_scheme,
)

router = APIRouter(prefix="/api/schemes", tags=["Schemes"])


# ------------------------------------------------------------------ farmer endpoints

@router.get("", response_model=list[SchemeOut])
def list_schemes(
    search: Optional[str] = Query(None, description="Search scheme name or description"),
    level: Optional[str] = Query(None, description="Filter by level: central or maharashtra"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all active government schemes with optional search and filters."""
    q = db.query(GovernmentScheme).filter(GovernmentScheme.is_active.is_(True))
    if search:
        term = f"%{search.lower()}%"
        q = q.filter(
            (GovernmentScheme.name.ilike(term))
            | (GovernmentScheme.description.ilike(term))
            | (GovernmentScheme.benefits.ilike(term))
        )
    if level:
        q = q.filter(GovernmentScheme.level == level)
    if category:
        q = q.filter(GovernmentScheme.category == category)
    return q.order_by(GovernmentScheme.level, GovernmentScheme.name).all()


@router.get("/recommended", response_model=list[SchemeOut])
def recommended_schemes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get scheme recommendations based on the user's farm and field data.

    Recommendations use farm location and crop types but do not guarantee
    eligibility. Farmers must verify on the official portal.
    """
    return get_recommendations(db, user)


@router.get("/notifications", response_model=list[SchemeNotificationOut])
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List the user's scheme notifications."""
    q = db.query(SchemeNotification, GovernmentScheme.name).join(
        GovernmentScheme, SchemeNotification.scheme_id == GovernmentScheme.id
    ).filter(SchemeNotification.user_id == user.id)
    if unread_only:
        q = q.filter(SchemeNotification.is_read.is_(False))
    rows = q.order_by(
        SchemeNotification.created_at.desc(), SchemeNotification.id.desc()
    ).limit(limit).all()
    return [
        SchemeNotificationOut(
            id=n.id, scheme_id=n.scheme_id, scheme_name=name,
            notification_type=n.notification_type, message=n.message,
            is_read=n.is_read, created_at=n.created_at,
        )
        for n, name in rows
    ]


@router.get("/notifications/unread-count")
def unread_notification_count(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = (
        db.query(SchemeNotification)
        .filter(SchemeNotification.user_id == user.id, SchemeNotification.is_read.is_(False))
        .count()
    )
    return {"count": count}


@router.post("/notifications/{notification_id}/read", response_model=SchemeNotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark a scheme notification as read."""
    row = (
        db.query(SchemeNotification, GovernmentScheme.name)
        .join(GovernmentScheme, SchemeNotification.scheme_id == GovernmentScheme.id)
        .filter(
            SchemeNotification.id == notification_id,
            SchemeNotification.user_id == user.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif, name = row
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return SchemeNotificationOut(
        id=notif.id, scheme_id=notif.scheme_id, scheme_name=name,
        notification_type=notif.notification_type, message=notif.message,
        is_read=notif.is_read, created_at=notif.created_at,
    )


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ids = [
        n.id for n in
        db.query(SchemeNotification)
        .filter(SchemeNotification.user_id == user.id, SchemeNotification.is_read.is_(False))
        .all()
    ]
    if ids:
        db.query(SchemeNotification).filter(
            SchemeNotification.id.in_(ids)
        ).update({"is_read": True}, synchronize_session=False)
        db.commit()
    return {"marked": len(ids)}


@router.get("/{scheme_id}", response_model=SchemeOut)
def get_scheme(
    scheme_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get details of a specific scheme."""
    scheme = db.query(GovernmentScheme).filter(GovernmentScheme.id == scheme_id).first()
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme


# ------------------------------------------------------------------ admin endpoints

@router.post("", response_model=SchemeOut, status_code=status.HTTP_201_CREATED)
def create_scheme(
    data: SchemeCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Create a new government scheme (admin only)."""
    scheme = GovernmentScheme(**data.model_dump())
    scheme.updated_at = scheme.created_at = datetime.utcnow()
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    # Notify all users about the new scheme
    notify_all_users_new_scheme(db, scheme)
    return scheme


@router.put("/{scheme_id}", response_model=SchemeOut)
def update_scheme(
    scheme_id: int,
    data: SchemeUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update a government scheme (admin only)."""
    scheme = db.query(GovernmentScheme).filter(GovernmentScheme.id == scheme_id).first()
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(scheme, key, value)
    scheme.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(scheme)
    return scheme


@router.delete("/{scheme_id}")
def delete_scheme(
    scheme_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Delete a government scheme (admin only)."""
    scheme = db.query(GovernmentScheme).filter(GovernmentScheme.id == scheme_id).first()
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    db.delete(scheme)
    db.commit()
    return {"deleted": scheme_id}
