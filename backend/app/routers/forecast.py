import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.i18n import LANGS, label, normalize_lang, translate_assumptions
from app.models.models import User
from app.routers.farms import get_field_or_404
from app.schemas.forecast import ForecastResponse
from app.services.forecast_service import (
    METRICS_PATH, ModelNotReady, NotEnoughData, forecast_field,
)

router = APIRouter(prefix="/api", tags=["Forecast"])


def localize_forecast(result: dict, lang: str) -> dict:
    """Add readable crop, soil and growth-stage names, and translate the assumptions note."""
    result = dict(result)
    result["crop_label"] = label("crop", result["crop_type"], lang)
    result["soil_label"] = label("soil", result["soil_type"], lang)
    result["assumptions"] = translate_assumptions(result["assumptions"], lang)
    result["forecast"] = [
        {**day, "growth_stage_label": label("stage", day["growth_stage"], lang)}
        for day in result["forecast"]
    ]
    return result


@router.get("/fields/{field_id}/forecast", response_model=ForecastResponse)
def get_forecast(
    field_id: int,
    days: int = Query(3, ge=1, le=7),
    lang: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    field = get_field_or_404(db, field_id, user)
    chosen = lang if lang in LANGS else normalize_lang(user.preferred_language)
    try:
        result = forecast_field(db, field, days)
    except NotEnoughData as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ModelNotReady as e:
        raise HTTPException(status_code=503, detail=str(e))
    return localize_forecast(result, chosen)


@router.get("/ml/model-info")
def model_info(user: User = Depends(get_current_user)):
    if not METRICS_PATH.exists():
        raise HTTPException(status_code=404, detail="Model not trained yet")
    with open(METRICS_PATH) as f:
        return json.load(f)