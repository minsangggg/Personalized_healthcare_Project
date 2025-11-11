from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core import get_current_user
from .service import clear_user_title, select_user_title

router = APIRouter(prefix="/me/badges/title", tags=["badges"])


class DisplayBadgeRequest(BaseModel):
    badge_id: int


@router.post("", summary="대표 뱃지 설정")
def post_display_badge(req: DisplayBadgeRequest, user_id: str = Depends(get_current_user)):
    return select_user_title(user_id, req.badge_id)


@router.delete("", summary="대표 뱃지 해제")
def delete_display_badge(user_id: str = Depends(get_current_user)):
    return clear_user_title(user_id)
