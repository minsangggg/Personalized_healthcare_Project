from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .service import ingredient_service


router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("/search")
def ingredients_search(q: str = Query(..., description="검색어")):
    return ingredient_service.search(q)


class IngredientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


@router.post("")
def ingredients_create(payload: IngredientCreate):
    try:
        return ingredient_service.add(payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
