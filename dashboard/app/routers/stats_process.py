from fastapi import APIRouter, Depends, Query
from datetime import date
from ..db import get_db
from ..schemas import ProgressResponse
from ..services.progress_service import fetch_progress, fetch_user_goal

router = APIRouter(prefix="/me/stats", tags=["stats"])

@router.get("/progress", response_model=ProgressResponse)
def progress(user_id: str,
             start_date: date | None = Query(None),
             end_date: date | None = Query(None),
             db = Depends(get_db)):
    goal = fetch_user_goal(db, user_id)
    data = fetch_progress(db, user_id, start_date, end_date, weekly_goal=goal)
    return {
        "user_id": user_id,
        "target_per_week": goal,
        "period_start": data["period_start"],
        "period_end": data["period_end"],
        "total_cooks": data["total"],
        "goal_attainment": data["goal_attainment"],
        "timeseries": data["timeseries"],
        "weekly": data["weekly"],
    }
