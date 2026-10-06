from typing import Literal, Optional

from pydantic import BaseModel


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[Literal["farmer", "admin"]] = None