from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Cookie, HTTPException, Request, Response

from .models import AuthLoginIn, AuthSignupIn
from .service import auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def auth_login(payload: AuthLoginIn, request: Request, response: Response):
    user, tokens = auth_service.login(payload.id, payload.password, request.headers.get("user-agent"))
    auth_service.set_refresh_cookie(response, tokens.refresh_token)
    return {"accessToken": tokens.access_token, "user": user}


@router.post("/signup")
def auth_signup(payload: AuthSignupIn, request: Request, response: Response):
    # 필수값은 Pydantic 모델에서 검증
    user, tokens = auth_service.signup(payload.dict(), request.headers.get("user-agent"))
    auth_service.set_refresh_cookie(response, tokens.refresh_token)
    return {"accessToken": tokens.access_token, "user": user}


@router.post("/refresh")
def auth_refresh(request: Request, response: Response, refresh: Optional[str] = Cookie(default=None)):
    if not refresh:
        raise HTTPException(401, "No refresh cookie")
    access, new_refresh = auth_service.refresh(refresh, user_agent=request.headers.get("user-agent"))
    auth_service.set_refresh_cookie(response, new_refresh)
    return {"accessToken": access}


@router.post("/logout")
def auth_logout(response: Response, refresh: Optional[str] = Cookie(default=None)):
    auth_service.logout(refresh)
    auth_service.clear_refresh_cookie(response)
    return {"ok": True}


@router.post("/find-id")
async def find_id_send_code(payload: Dict[str, Any] = Body(...)):
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip()
    return await auth_service.send_find_id_code(email=email, username=username)


@router.post("/find-id/verify")
def find_id_verify(payload: Dict[str, Any] = Body(...)):
    email = (payload.get("email") or "").strip()
    code = (payload.get("code") or "").strip()
    return auth_service.verify_find_id_code(email, code)


@router.post("/find-password")
async def find_pw_send_code(payload: Dict[str, Any] = Body(...)):
    user_id = (payload.get("id") or "").strip()
    email = (payload.get("email") or "").strip()
    return await auth_service.send_password_code(user_id, email)


@router.put("/password-set")
def password_set(payload: Dict[str, Any] = Body(...)):
    user_id = (payload.get("id") or "").strip()
    email = (payload.get("email") or "").strip()
    code = (payload.get("code") or "").strip()
    new_pw = (payload.get("new_password") or "").strip()
    return auth_service.reset_password(user_id, email, code, new_pw)
