from fastapi import APIRouter, Query

from app.schemas.ingredient import IngredientItem
from app.services.ingredient_service import add_ingredient, search_ingredient_names

router = APIRouter(tags=["ingredients"])


@router.get("/search_ingredient")
def search_ingredient_endpoint(
    keyword: str = Query("", description="Keyword for ingredient search"),
    limit: int = Query(15, ge=1, le=50, description="Maximum number of ingredients to return"),
) -> dict:
    """Return ingredient names from the master table that match the keyword."""
    return {"results": search_ingredient_names(keyword, limit)}


@router.post("/add_ingredient")
def add_ingredient_endpoint(item: IngredientItem) -> dict:
    """Add a new ingredient record for the user's fridge."""
    return add_ingredient(item)
