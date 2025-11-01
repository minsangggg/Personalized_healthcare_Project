from fastapi import APIRouter, Depends, Query, Response

from core import get_current_user

from .models import SelectIn, SelectedActionIn
from .service import recommendation_service


router = APIRouter(tags=["recommendations"])


@router.get("/me/recommendations")
def get_recommendations(
    current_user: str = Depends(get_current_user),
    limit: int = Query(3, ge=1, le=5, description="추천 레시피 개수 (기본 3개)"),
):
    return recommendation_service.get_recommendations(current_user, limit)


@router.post("/me/selected-recipe")
def save_selected_recipe(payload: SelectIn, current_user: str = Depends(get_current_user)):
    return recommendation_service.save_selected_recipe(current_user, payload.recipe_id)


@router.get("/recipes/selected")
def get_selected_recipes(current_user: str = Depends(get_current_user)):
    return recommendation_service.list_selected_recipes(current_user)


@router.delete("/me/selected-recipe/{selected_id}")
def delete_selected_recipe(selected_id: int, current_user: str = Depends(get_current_user)):
    recommendation_service.delete_selected_recipe(current_user, selected_id)
    return Response(status_code=204)


@router.patch("/me/selected-recipe/{selected_id}/action")
def update_selected_action(selected_id: int, payload: SelectedActionIn, current_user: str = Depends(get_current_user)):
    return recommendation_service.update_selected_action(current_user, selected_id, payload.action)


@router.get("/me/selected-recipe/status")
def selected_status(recipe_id: int, current_user: str = Depends(get_current_user)):
    return recommendation_service.selected_status(current_user, recipe_id)


@router.get("/recommendations/{recommend_id}")
def get_recommendation_detail(recommend_id: int, current_user: str = Depends(get_current_user)):
    return recommendation_service.get_recommendation_detail(current_user, recommend_id)
