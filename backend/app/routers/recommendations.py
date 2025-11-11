from fastapi import APIRouter

from fastapi import Query

from app.schemas.recommendation import RecommendRequest, SelectedRecipe, SelectedRecipeAction
from app.services.recommendation_service import (
    list_selected_recipes,
    recommend_recipes,
    save_selected_recipe,
    update_selected_recipe_action,
    delete_selected_recipe,
    count_monthly_completed_recipes,
    estimate_monthly_savings,
)

router = APIRouter(tags=["recommendations"])


@router.post("/recommend")
def recommend_endpoint(payload: RecommendRequest) -> dict:
    """냉장고 재료 기반 레시피 추천"""
    return recommend_recipes(payload)


@router.post("/save_selected_recipe")
def save_selected_recipe_endpoint(payload: SelectedRecipe) -> dict:
    """추천 중 선택한 레시피 저장"""
    return save_selected_recipe(payload)


@router.get("/get_selected_recipes")
def get_selected_recipes_endpoint(user_id: str = Query(..., description="사용자 ID")) -> dict:
    """선택한 레시피 목록 조회"""
    return list_selected_recipes(user_id)


@router.patch("/selected_recipe/action")
def update_selected_recipe_action_endpoint(payload: SelectedRecipeAction) -> dict:
    """선택한 레시피 상태 변경"""
    return update_selected_recipe_action(payload)


@router.delete("/selected_recipe")
def delete_selected_recipe_endpoint(payload: SelectedRecipe) -> dict:
    """선택한 레시피 삭제"""
    return delete_selected_recipe(payload)


@router.get("/selected_recipe/monthly_completed")
def get_monthly_completed_recipes(user_id: str = Query(..., description="사용자 ID")) -> dict:
    """이번 달 완료된 레시피 수"""
    return count_monthly_completed_recipes(user_id)


@router.get("/dashboard/monthly_savings")
def get_monthly_savings(user_id: str = Query(..., description="사용자 ID")) -> dict:
    """이번 달 예상 절약 비용"""
    return estimate_monthly_savings(user_id)
