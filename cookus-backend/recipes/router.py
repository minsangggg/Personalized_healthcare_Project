from fastapi import APIRouter, Depends

from core import get_current_user

from .service import recipe_service


router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("/{recipe_id}")
def get_recipe(recipe_id: int, current_user: str = Depends(get_current_user)):
    return recipe_service.get_recipe(recipe_id)
