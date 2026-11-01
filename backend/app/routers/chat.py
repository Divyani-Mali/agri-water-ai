from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import IrrigationLog, User
from app.routers.farms import get_field_or_404
from app.schemas.chat import ChatRequest, ChatResponse, IrrigationLogOut
from app.services.chat_service import handle_message

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    data: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return handle_message(db, user, data.message, data.lang)


@router.get("/fields/{field_id}/irrigation-logs", response_model=list[IrrigationLogOut])
def list_irrigation_logs(
    field_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    field = get_field_or_404(db, field_id, user)
    return (
        db.query(IrrigationLog)
        .filter(IrrigationLog.field_id == field.id)
        .order_by(IrrigationLog.created_at.desc(), IrrigationLog.id.desc())
        .limit(limit)
        .all()
    )