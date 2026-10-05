from datetime import date

from pydantic import BaseModel


class ForecastDay(BaseModel):
    target_date: date
    growth_stage: str
    kc: float
    predicted_water_mm: float
    total_liters: float


class ForecastResponse(BaseModel):
    field_id: int
    crop_type: str
    soil_type: str
    model_name: str
    based_on_days: int
    current_soil_moisture: float
    assumptions: str
    forecast: list[ForecastDay]