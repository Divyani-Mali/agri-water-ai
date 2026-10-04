from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

CropType = Literal[
    "wheat", "rice", "cotton", "sugarcane", "maize", "soybean", "tomato", "onion"
]
SoilType = Literal["sandy", "loamy", "clay"]


# ---------- Farm ----------
class FarmCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=200)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class FarmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    latitude: Optional[float]
    longitude: Optional[float]
    owner_id: int
    created_at: datetime


# ---------- Field ----------
class FieldCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    crop_type: CropType
    soil_type: SoilType = "loamy"
    area_acres: float = Field(gt=0, le=10000)
    planting_date: date = Field(default_factory=date.today)

    @field_validator("planting_date")
    @classmethod
    def not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Planting date cannot be in the future")
        return v


class FieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    name: str
    crop_type: str
    soil_type: str
    area_acres: float
    planting_date: date
    created_at: datetime


# ---------- Sensor readings ----------
class ReadingCreate(BaseModel):
    soil_moisture: float = Field(ge=0, le=100)
    temperature: float = Field(ge=-10, le=60)
    humidity: float = Field(ge=0, le=100)
    rainfall: float = Field(default=0.0, ge=0, le=500)
    wind_speed: float = Field(default=0.0, ge=0, le=200)
    timestamp: Optional[datetime] = None


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    timestamp: datetime
    soil_moisture: float
    temperature: float
    humidity: float
    rainfall: float
    wind_speed: float