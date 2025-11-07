# main.py
from fastapi import FastAPI
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from scheduler import start_scheduler
from badge_core import get_conn

app = FastAPI(title="CookUs 자동 뱃지 시스템")

# ✅ 스케줄러 자동 시작
start_scheduler()

@app.get("/")
def root():
    return {"message": "CookUs Badge System running 🚀"}


# ============================================================
# Badge APIs for frontend
# ============================================================

class UserBadge(BaseModel):
    badge_id: int
    name: str
    category: str
    awarded_at: datetime
    target_value: int
    repeatable: int


class BadgeProgress(BaseModel):
    badge_id: int
    name: str
    category: str
    current: int
    target: int
    is_completed: int
    updated_at: datetime


@app.get(
    "/users/{user_id}/badges",
    response_model=List[UserBadge],
    tags=["badges"],
    summary="Get awarded badges for a user",
    description="Returns the list of badges already awarded to the given user.",
)
def get_user_badges(user_id: str) -> List[UserBadge]:
    """Return the list of badges awarded to the user with basic metadata."""
    db = get_conn()
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    ub.badge_id,
                    COALESCE(bi.name_ko, '') AS name,
                    COALESCE(bi.category, '-') AS category,
                    ub.awarded_at,
                    COALESCE(bi.target_value, 1) AS target_value,
                    COALESCE(bi.repeatable, 0) AS repeatable
                FROM user_badges ub
                LEFT JOIN badge_info bi ON bi.badge_id = ub.badge_id
                WHERE ub.user_id = %s
                ORDER BY ub.awarded_at DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            # Shape rows to the response model, ensuring required keys
            result: List[UserBadge] = []
            for r in rows:
                result.append(
                    {
                        "badge_id": r.get("badge_id"),
                        "name": r.get("name") or "",
                        "category": r.get("category") or "-",
                        "awarded_at": r.get("awarded_at"),
                        "target_value": r.get("target_value") or 1,
                        "repeatable": r.get("repeatable") or 0,
                    }
                )
            return result
    finally:
        db.close()


@app.get(
    "/users/{user_id}/badges/progress",
    response_model=List[BadgeProgress],
    tags=["badges"],
    summary="Get badge progress for a user",
    description="Returns progress for all badges (current, target, is_completed).",
)

def get_user_badge_progress(user_id: str) -> List[BadgeProgress]:
    """Return progress for all badges for the user."""
    db = get_conn()
    try:
        with db.cursor() as cur:
            cur.execute(
                """
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
                ORDER BY bp.badge_id ASC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            # Ensure required keys and correct types
            result: List[BadgeProgress] = []
            for r in rows:
                result.append(
                    {
                        "badge_id": r.get("badge_id"),
                        "name": r.get("name") or "Unknown",
                        "category": r.get("category") or "-",
                        "current": r.get("current") or 0,
                        "target": r.get("target") or 1,
                        "is_completed": r.get("is_completed") or 0,
                        "updated_at": r.get("updated_at"),
                    }
                )
            return result

    except Exception as e:
        print(f"❌ [ERROR] get_user_badge_progress failed: {e}")
        return []
    finally:
        db.close()
