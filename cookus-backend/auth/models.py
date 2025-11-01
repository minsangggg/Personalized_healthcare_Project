from typing import Literal, Optional

from pydantic import BaseModel, Field


class AuthLoginIn(BaseModel):
    id: str
    password: str


class AuthSignupIn(BaseModel):
    id: str
    user_name: str
    email: str
    password: str
    gender: Literal["male", "female"]
    date_of_birth: Optional[str] = None
    cooking_level: Literal["상", "하"]
    goal: int = Field(0, ge=0, le=21)
