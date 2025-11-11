from fastapi import APIRouter

from core.database import get_conn

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/displayed-badge")
def get_displayed_badge(user_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT badge_id
            FROM user_badges
            WHERE user_id = %s
              AND is_displayed = 1
            LIMIT 1
            """,
            (user_id,),
        )
        row = cur.fetchone()
    return {"badge_id": row["badge_id"] if row else None}
