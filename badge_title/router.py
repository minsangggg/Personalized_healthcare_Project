from fastapi import APIRouter
from pydantic import BaseModel
from service import select_user_title  # ✅ 같은 폴더니까 이렇게

router = APIRouter(tags=["badges"])

class SelectTitleRequest(BaseModel):
    user_id: str
    badge_id: int

@router.post("/me/badges/select-title", summary="대표 칭호 선택/변경")
def select_title(req: SelectTitleRequest):
    """대표 칭호 선택 API"""
    return select_user_title(req.user_id, req.badge_id)
