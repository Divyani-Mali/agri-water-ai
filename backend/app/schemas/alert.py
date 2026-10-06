from datetime import datetime

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: int
    field_id: int
    field_name: str
    alert_type: str = "general"
    severity: str
    message: str
    is_read: bool
    created_at: datetime