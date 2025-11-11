from fastapi import HTTPException

from core.database import get_conn


def select_user_title(user_id: str, badge_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE user_badges SET is_displayed = 0 WHERE user_id = %s",
            (user_id,),
        )
        cur.execute(
            """
            UPDATE user_badges
            SET is_displayed = 1
            WHERE user_id = %s AND badge_id = %s
            """,
            (user_id, badge_id),
        )
        cur.execute(
            """
            SELECT badge_id
            FROM user_badges
            WHERE user_id = %s AND badge_id = %s AND is_displayed = 1
            """,
            (user_id, badge_id),
        )
        selected = cur.fetchone()
        if not selected:
            raise HTTPException(status_code=400, detail="해당 뱃지를 보유하고 있지 않습니다.")
        return {
            "message": "대표 배지가 갱신되었습니다.",
            "user_id": user_id,
            "badge_id": selected["badge_id"],
        }


def clear_user_title(user_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE user_badges SET is_displayed = 0 WHERE user_id = %s", (user_id,))
    return {"message": "대표 배지 설정을 초기화했습니다.", "user_id": user_id}
