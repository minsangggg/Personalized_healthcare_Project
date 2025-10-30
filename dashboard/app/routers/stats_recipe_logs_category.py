from fastapi import APIRouter, Depends, Query
from datetime import date
from ..db import get_db
from ..services.recipe_logs_category_service import fetch_recipe_category_ratio

router = APIRouter(prefix="/me/stats", tags=["stats"])

@router.get("/recipe-logs-category", summary="선택한 레시피의 요리 분류 비율")
def recipe_logs_category(user_id: str,
                         start_date: date | None = Query(None),
                         end_date: date | None = Query(None),
                         db = Depends(get_db)):
    return fetch_recipe_category_ratio(db, user_id, start_date, end_date)
