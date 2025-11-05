from fastapi import APIRouter

from app.schemas.auth import LoginRequest, ResetPasswordRequest, SignupRequest
from app.services.auth_service import login, reset_password, signup

router = APIRouter(tags=["auth"])


@router.post("/signup")
def signup_endpoint(payload: SignupRequest) -> dict:
    """회원가입"""
    return signup(payload)


@router.post("/login")
def login_endpoint(payload: LoginRequest) -> dict:
    """로그인"""
    return login(payload)


@router.post("/reset_password")
def reset_password_endpoint(payload: ResetPasswordRequest) -> dict:
    """이메일로 임시 비밀번호 전송"""
    return reset_password(payload)
