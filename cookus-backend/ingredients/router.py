from fastapi import APIRouter, Query

from .service import ingredient_service


router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("/search")
def ingredients_search(q: str = Query(..., description="검색어")):
    return ingredient_service.search(q)
