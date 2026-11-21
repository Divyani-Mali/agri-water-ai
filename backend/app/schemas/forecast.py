from datetime import date

from pydantic import BaseModel


class ForecastDay(BaseModel):
    target_date: date
    growth_stage: str
    growth_stage_label: str = ""
    kc: float
    predicted_water_mm: float
    total_liters: float


class ForecastResponse(BaseModel):
    field_id: int
    crop_type: str
    crop_label: str = ""
    soil_type: str
    soil_label: str = ""
    model_name: str
    based_on_days: int
    current_soil_moisture: float
    assumptions: str
    forecast: list[ForecastDay]