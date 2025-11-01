from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, Response

from auth.service import auth_service
from core import get_current_user

from .models import MeUpdateIn
from .service import user_service


router = APIRouter(prefix="/me", tags=["user"])


@router.get("")
def read_me(current_user: str = Depends(get_current_user)):
    return user_service.get_profile(current_user)


@router.put("")
def update_me(payload: MeUpdateIn, current_user: str = Depends(get_current_user)):
    fields: Dict[str, Any] = {}

    if payload.user_name is not None:
        fields["user_name"] = payload.user_name.strip()
    if payload.email is not None:
        fields["email"] = payload.email.strip()
    if payload.gender is not None:
        fields["gender"] = payload.gender
    if payload.date_of_birth is not None:
        fields["date_of_birth"] = payload.date_of_birth or None
    if payload.goal is not None:
        fields["goal"] = int(payload.goal)
    if payload.cooking_level is not None:
        fields["cooking_level"] = payload.cooking_level

    return user_service.update_profile(current_user, fields)


@router.delete("/delete")
def delete_me(
    response: Response,
    current_user: str = Depends(get_current_user),
    payload: Dict[str, Any] = Body(...),
):
    result = user_service.delete_account(
        current_user,
        password=str(payload.get("password", "")),
        password_confirm=str(payload.get("password_confirm", "")),
    )
    auth_service.clear_refresh_cookie(response)
    return result
