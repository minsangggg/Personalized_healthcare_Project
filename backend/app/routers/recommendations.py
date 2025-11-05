from fastapi import APIRouter

from fastapi import Query

from app.schemas.recommendation import RecommendRequest, SelectedRecipe
from app.services.recommendation_service import (
    list_selected_recipes,
    recommend_recipes,
    save_selected_recipe,
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
