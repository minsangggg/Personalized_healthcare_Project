import logging
from typing import Optional

from core.database import get_conn
from notifications.service import notify

log = logging.getLogger(__name__)

EVENT_CATEGORY_MAP = {
  "contest": "contest",
  "likes": "likes",
  "recipe": "recipe",
  "cooked": "cooked",
  "fridge": "fridge",
  "goal": "goal",
  "ranks": "ranks",
}


def _ensure_conn(conn):
  if conn:
    return conn, False
  return get_conn(), True


def _close_conn(conn, owns_conn):
  if owns_conn:
    try:
      conn.close()
    except Exception:
      log.exception("Failed to close badge automation connection")


def update_badge_process(user_id: str, badge_id: int, increment: int, conn=None, event_id: Optional[int] = None):
  conn, owns_conn = _ensure_conn(conn)
  try:
    with conn.cursor() as cur:
      cur.execute(
        """
        SELECT process_id, current_value, target_value, is_completed
        FROM badge_process
        WHERE user_id=%s AND badge_id=%s
        ORDER BY badge_id DESC
        LIMIT 1
        """,
        (user_id, badge_id),
      )
      process = cur.fetchone()

      cur.execute("SELECT target_value FROM badge_info WHERE badge_id=%s", (badge_id,))
      badge = cur.fetchone()
      latest_target = badge["target_value"] if badge else 1

      if not process:
        initial_completed = 1 if increment >= latest_target else 0
        cur.execute(
          """
          INSERT INTO badge_process (user_id, badge_id, current_value, target_value, is_completed, updated_at)
          VALUES (%s, %s, %s, %s, %s, NOW())
          """,
          (user_id, badge_id, increment, latest_target, initial_completed),
        )
        return {"current": increment, "target": latest_target, "completed": bool(initial_completed)}

      if process["is_completed"] == 1:
        return {"current": process["current_value"], "target": latest_target, "completed": True}

      new_value = process["current_value"] + increment
      completed = 1 if new_value >= latest_target else 0
      cur.execute(
        """
        UPDATE badge_process
        SET current_value=%s, target_value=%s, is_completed=%s, updated_at=NOW()
        WHERE process_id=%s
        """,
        (new_value, latest_target, completed, process["process_id"]),
      )
      return {"current": new_value, "target": latest_target, "completed": bool(completed)}
  finally:
    _close_conn(conn, owns_conn)


def award_badge(user_id: str, badge_id: int, conn=None, event_id: Optional[int] = None):
  conn, owns_conn = _ensure_conn(conn)
  try:
    with conn.cursor() as cur:
      cur.execute(
        "SELECT repeatable, name_ko FROM badge_info WHERE badge_id=%s",
        (badge_id,),
      )
      badge = cur.fetchone()
      if not badge:
        log.warning("Badge %s not found when awarding to %s", badge_id, user_id)
        return False

      repeatable = badge.get("repeatable", 0)
      badge_name = badge.get("name_ko") or "배지"

      if not repeatable:
        cur.execute(
          "SELECT 1 FROM user_badges WHERE user_id=%s AND badge_id=%s",
          (user_id, badge_id),
        )
        if cur.fetchone():
          return False

      cur.execute(
        """
        INSERT INTO user_badges (user_id, badge_id, awarded_at, is_active, event_id, is_displayed)
        VALUES (%s, %s, NOW(), 0, %s, 0)
        """,
        (user_id, badge_id, event_id),
      )

      notify(
        user_id=user_id,
        title="새 배지를 획득했어요!",
        body=f"'{badge_name}' 배지를 획득했습니다.",
        link_url="/me/badges",
        type="badge",
        related_id=badge_id,
      )
      return True
  finally:
    _close_conn(conn, owns_conn)


def handle_user_event(user_id: str, event_type: str, conn=None, event_id: Optional[int] = None):
  conn, owns_conn = _ensure_conn(conn)
  try:
    if not user_id:
      log.warning("handle_user_event called with empty user_id for event %s (event_id=%s)", event_type, event_id)
      return
    db_category = EVENT_CATEGORY_MAP.get(event_type, event_type)
    with conn.cursor() as cur:
      cur.execute("SELECT badge_id FROM badge_info WHERE category=%s", (db_category,))
      badges = cur.fetchall()
      if not badges:
        log.debug("No badges configured for category '%s' (event_type=%s)", db_category, event_type)
        return

    log.debug("User %s triggered event %s mapped to %s (%d badges)", user_id, event_type, db_category, len(badges))
    for badge in badges:
      progress = update_badge_process(user_id, badge["badge_id"], 1, conn, event_id)
      log.debug(
        "Badge %s progress for user %s: current=%s target=%s completed=%s",
        badge["badge_id"],
        user_id,
        progress["current"],
        progress["target"],
        progress["completed"],
      )
      if progress["completed"]:
        awarded = award_badge(user_id, badge["badge_id"], conn, event_id)
        log.info(
          "Awarded badge %s to user %s from event %s (event_id=%s, awarded=%s)",
          badge["badge_id"],
          user_id,
          event_type,
          event_id,
          awarded,
        )
  finally:
    _close_conn(conn, owns_conn)
