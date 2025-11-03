from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from core import get_current_user

from .service import stats_service


router = APIRouter(prefix="/me", tags=["stats"])


@router.get("/stats/progress")
def me_stats_progress(
    selected_date: Optional[date] = Query(default=None),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    p = stats_service.get_progress(current_user, selected_date)
    return {
        "weeklyRate": p.weeklyRate,
        "cookedCount": p.cookedCount,
        "avgDifficulty": p.avgDifficulty,
        "avgMinutes": p.avgMinutes,
    }


@router.get("/stats/recipe-logs-level")
def me_stats_level(
    selected_date: Optional[date] = Query(default=None),
    current_user: str = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return stats_service.get_level_distribution(current_user, selected_date)


@router.get("/stats/recipe-logs-category")
def me_stats_category(
    selected_date: Optional[date] = Query(default=None),
    current_user: str = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return stats_service.get_category_distribution(current_user, selected_date)

