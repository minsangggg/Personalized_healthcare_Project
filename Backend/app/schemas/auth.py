from typing import Literal, Optional

from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    id: str
    user_name: str
    password: str
    email: EmailStr
    date_of_birth: Optional[str] = None
    gender: Literal["male", "female"]
    cooking_level: Literal["상", "하"]
    goal: int


class LoginRequest(BaseModel):
    ID: str
    PASSWORD: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
