# ============================================================
# router.py — Badge API endpoints
# ============================================================

from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
from datetime import datetime
from .service import get_conn # badge_core → service 로 변경

router = APIRouter(prefix="/me/badges", tags=["badges"])

# ------------------------------------------------------------
# ✅ Pydantic Models
# ------------------------------------------------------------
class UserBadge(BaseModel):
    badge_id: int
    name: str
    description: str | None = None
    category: str
    awarded_at: datetime

class BadgeProgress(BaseModel):
    badge_id: int
    name: str
    category: str
    current: int
    target: int
    is_completed: int
    updated_at: datetime

# ------------------------------------------------------------
# ✅ Endpoints
# ------------------------------------------------------------

@router.get(
    "/overview",
    response_model=List[UserBadge],
    summary="Get awarded badges for a user"
)
def get_user_badges(user_id: str) -> List[UserBadge]:
    db = get_conn()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT 
                    ub.badge_id,
                    COALESCE(bi.name_ko, '') AS name,
                    COALESCE(bi.description, '') AS description,
                    COALESCE(bi.category, '-') AS category,
                    ub.awarded_at
                FROM user_badges ub
                LEFT JOIN badge_info bi ON bi.badge_id = ub.badge_id
                WHERE ub.user_id = %s
                ORDER BY ub.awarded_at DESC
            """, (user_id,))
            rows = cur.fetchall()
            return [
                {
                    "badge_id": r["badge_id"],
                    "name": r["name"],
                    "description": r["description"],
                    "category": r["category"],
                    "awarded_at": r["awarded_at"],
                }
                for r in rows
            ]
    finally:
        db.close()


@router.get(
    "/overview/progress",
    response_model=List[BadgeProgress],
    summary="Get badge progress for a user"
)
def get_user_badge_progress(user_id: str) -> List[BadgeProgress]:
    db = get_conn()
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT 
                    bp.badge_id,
                    COALESCE(bi.name_ko, 'Unknown') AS name,
                    COALESCE(bi.category, '-') AS category,
                    bp.current_value AS current,
                    bp.target_value  AS target,
                    bp.is_completed  AS is_completed,
                    bp.updated_at
                FROM badge_process bp
                LEFT JOIN badge_info bi ON bi.badge_id = bp.badge_id
                WHERE bp.user_id = %s
                    AND bp.is_completed = 0
                ORDER BY bp.badge_id ASC
            """, (user_id,))
            rows = cur.fetchall()
            return [
                {
                    "badge_id": r["badge_id"],
                    "name": r["name"],
                    "category": r["category"],
                    "current": r["current"],
                    "target": r["target"],
                    "is_completed": r["is_completed"],
                    "updated_at": r["updated_at"],
                }
                for r in rows
            ]
    finally:
        db.close()
