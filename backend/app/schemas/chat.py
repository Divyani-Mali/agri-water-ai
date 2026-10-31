from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    lang: Optional[Literal["en", "hi", "mr"]] = None

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class ChatResponse(BaseModel):
    reply: str
    lang: str
    intent: str
    source: Optional[str] = None
    suggestions: list[str] = []


class IrrigationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: int
    minutes: float
    source: str
    created_at: datetime