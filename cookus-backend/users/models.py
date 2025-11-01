from typing import Literal, Optional

from pydantic import BaseModel, Field


class MeUpdateIn(BaseModel):
    user_name: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    date_of_birth: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    goal: Optional[int] = Field(None, ge=0, le=21)
    cooking_level: Optional[Literal["상", "하"]] = None
