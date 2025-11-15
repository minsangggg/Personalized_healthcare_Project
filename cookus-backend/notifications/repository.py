# cookus-backend/notifications/repository.py
from typing import Any, Dict, List, Optional
from datetime import datetime
from core.database import get_conn

def insert_notification(
    user_id: str,
    title: str,
    body: str,
    link_url: Optional[str] = None,
    type: str = "generic",
    related_id: Optional[int] = None,
) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO notifications (id, type, related_id, title, body, link_url, created_at, is_read)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), 0)
            """,
            (user_id, type, related_id, title, body, link_url),
        )
        cur.execute("SELECT LAST_INSERT_ID() AS id")
        row = cur.fetchone()
        return int(row["id"])

def list_notifications(user_id: str, since: Optional[datetime]) -> List[Dict[str, Any]]:
    sql = """
        SELECT notification_id, id, type, related_id, title, body, link_url, created_at, read_at, is_read
        FROM notifications
        WHERE id=%s
    """
    params: List[Any] = [user_id]
    if since:
        sql += " AND created_at >= %s"
        params.append(since)
    sql += " ORDER BY created_at DESC LIMIT 100"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return cur.fetchall()

def mark_read(user_id: str, notification_id: int) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE notifications
            SET is_read=1, read_at=NOW()
            WHERE notification_id=%s AND id=%s
            """,
            (notification_id, user_id),
        )

def exists_today_supplement_notice(user_id: str, plan_id: int) -> bool:
    """같은 plan_id(영양제 복용 계획)에 대해 오늘 이미 알림을 보냈는지 확인"""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM notifications
            WHERE id=%s
              AND type='supplement'
              AND related_id=%s
              AND DATE(created_at)=CURDATE()
            LIMIT 1
            """,
            (user_id, plan_id),
        )
        return cur.fetchone() is not None
