from fastapi import APIRouter
from app.schemas.user import UpdateLevelRequest, UpdateProfileRequest
from app.services.user_service import (
    delete_user,
    get_user_info,
    get_user_name,
    update_level,
    update_profile,
)
router = APIRouter(tags=["users"])


# ---------------- 기존 코드 ----------------
@router.get("/get_user_name/{user_id}")
def get_user_name_endpoint(user_id: str) -> dict:
    """사용자 이름 조회"""
    return get_user_name(user_id)


@router.get("/get_user_info/{user_id}")
def get_user_info_endpoint(user_id: str) -> dict:
    """사용자 정보 조회"""
    return get_user_info(user_id)


@router.put("/update_level")
def update_level_endpoint(payload: UpdateLevelRequest) -> dict:
    """요리 난이도 수정"""
    return update_level(payload)


@router.put("/update_profile")
def update_profile_endpoint(payload: UpdateProfileRequest) -> dict:
    """주간 목표 및 요리 레벨 수정"""
    return update_profile(payload)


@router.delete("/delete_user/{user_id}")
def delete_user_endpoint(user_id: str) -> dict:
    """회원 탈퇴"""
    return delete_user(user_id)
