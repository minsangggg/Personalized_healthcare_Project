# SQL만 모아두는 얇은 레이어
from typing import Any, Dict, List, Tuple
from core.database import get_conn  # <= 네 프로젝트의 DB 헬퍼

EARNED_SQL = """
SELECT b.badge_id, b.name_ko AS name, b.category,
       ub.earned_at, (ub.is_active = 1) AS is_active
FROM user_badge ub
JOIN badge_info b ON b.badge_id = ub.badge_id
WHERE ub.user_id = %s
ORDER BY ub.earned_at DESC;
"""

LOCKED_SQL = """
SELECT b.badge_id, b.name_ko AS name, b.category,
       COALESCE(bp.current_value, 0) AS current_value,
       b.target_value
FROM badge_info b
LEFT JOIN user_badge ub
  ON ub.user_id = %s AND ub.badge_id = b.badge_id
LEFT JOIN badge_process bp
  ON bp.user_id = %s AND bp.badge_id = b.badge_id
WHERE ub.user_badge_id IS NULL
ORDER BY b.badge_id ASC;
"""

def fetch_overview(user_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(EARNED_SQL, (user_id,))
        earned = cur.fetchall()
        cur.execute(LOCKED_SQL, (user_id, user_id))
        locked = cur.fetchall()
    return earned, locked

def own_badge(user_id: str, badge_id: int) -> bool:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM user_badge WHERE user_id=%s AND badge_id=%s",
                    (user_id, badge_id))
        return cur.fetchone() is not None

def deactivate_all(user_id: str) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE user_badge SET is_active=0 WHERE user_id=%s", (user_id,))

def activate_one(user_id: str, badge_id: int) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE user_badge SET is_active=1 WHERE user_id=%s AND badge_id=%s",
                    (user_id, badge_id))
