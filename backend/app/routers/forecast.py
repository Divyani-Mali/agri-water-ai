import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.routers.farms import get_field_or_404
from app.schemas.forecast import ForecastResponse
from app.services.forecast_service import (
    METRICS_PATH, ModelNotReady, NotEnoughData, forecast_field,
)

router = APIRouter(prefix="/api", tags=["Forecast"])


@router.get("/fields/{field_id}/forecast", response_model=ForecastResponse)
def get_forecast(
    field_id: int,
    days: int = Query(3, ge=1, le=7),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    field = get_field_or_404(db, field_id, user)
    try:
        return forecast_field(db, field, days)
    except NotEnoughData as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ModelNotReady as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/ml/model-info")
def model_info(user: User = Depends(get_current_user)):
    if not METRICS_PATH.exists():
        raise HTTPException(status_code=404, detail="Model not trained yet")
    with open(METRICS_PATH) as f:
        return json.load(f)