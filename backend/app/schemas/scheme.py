from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class SchemeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    benefits: str
    eligibility: str
    documents_required: str
    application_process: str
    application_url: Optional[str] = None
    source_url: str
    last_verified: date
    deadline: Optional[date] = None
    level: str
    category: Optional[str] = None
    applicable_crops: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SchemeCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10)
    benefits: str = Field(min_length=5)
    eligibility: str = Field(min_length=5)
    documents_required: str = Field(min_length=5)
    application_process: str = Field(min_length=5)
    application_url: Optional[str] = None
    source_url: str = Field(min_length=5)
    last_verified: date
    deadline: Optional[date] = None
    level: Literal["central", "maharashtra"]
    category: Optional[str] = None
    applicable_crops: Optional[str] = None
    is_active: bool = True


class SchemeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10)
    benefits: Optional[str] = Field(default=None, min_length=5)
    eligibility: Optional[str] = Field(default=None, min_length=5)
    documents_required: Optional[str] = Field(default=None, min_length=5)
    application_process: Optional[str] = Field(default=None, min_length=5)
    application_url: Optional[str] = None
    source_url: Optional[str] = Field(default=None, min_length=5)
    last_verified: Optional[date] = None
    deadline: Optional[date] = None
    level: Optional[Literal["central", "maharashtra"]] = None
    category: Optional[str] = None
    applicable_crops: Optional[str] = None
    is_active: Optional[bool] = None


class SchemeNotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheme_id: int
    scheme_name: str
    notification_type: str
    message: str
    is_read: bool
    created_at: datetime
