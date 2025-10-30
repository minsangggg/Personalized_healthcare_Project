from fastapi import APIRouter, Depends, Query
from datetime import date
from ..db import get_db
from ..services.recipe_logs_level_service import fetch_recipe_level_ratio

router = APIRouter(prefix="/me/stats", tags=["stats"])

@router.get("/recipe-logs-level", summary="선택한 레시피의 난이도 비율")
def recipe_logs_level(user_id: str,
                      start_date: date | None = Query(None),
                      end_date: date | None = Query(None),
                      db = Depends(get_db)):
    return fetch_recipe_level_ratio(db, user_id, start_date, end_date)
