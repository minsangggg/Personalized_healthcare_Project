import logging
import os

from core.database import get_conn
from .engine import handle_user_event, award_badge, update_badge_process

_base_logger = logging.getLogger("uvicorn.error")
log = _base_logger.getChild("badges.automation.jobs")

CHECK_INTERVAL = int(os.getenv("BADGE_CHECK_INTERVAL", "10"))
POPULAR_LIKE_THRESHOLD = int(os.getenv("LIKE_THRESHOLD", "50"))
RANK_AGGREGATION_INTERVAL_HOURS = int(os.getenv("BADGE_RANK_INTERVAL_HOURS", "12"))


def _run_job(name, worker):
  log.debug("Running badge job '%s'", name)
  try:
    worker()
  except Exception:
    log.exception("Badge automation job '%s' failed", name)
  else:
    log.debug("Finished badge job '%s'", name)


def check_new_boards():
  def worker():
    with get_conn() as conn, conn.cursor() as cur:
      cur.execute(
        """
        SELECT DISTINCT user_id
        FROM board
        WHERE created_at >= NOW() - INTERVAL %s SECOND
        """,
        (CHECK_INTERVAL,),
      )
      rows = cur.fetchall()
      if rows:
        log.info("check_new_boards: detected %d new posts", len(rows))
      for row in rows:
        handle_user_event(row["user_id"], "contest", conn)
  _run_job("check_new_boards", worker)


def check_recipe_recommendations():
  def worker():
    with get_conn() as conn, conn.cursor() as cur:
      cur.execute(
        """
        SELECT DISTINCT id AS user_id
        FROM recommend_recipe
        WHERE recommend_date >= NOW() - INTERVAL %s SECOND
        """,
        (CHECK_INTERVAL,),
      )
      rows = cur.fetchall()
      if rows:
        log.info("check_recipe_recommendations: detected %d recommendations", len(rows))
      for row in rows:
        handle_user_event(row["user_id"], "recipe", conn)
  _run_job("check_recipe_recommendations", worker)


def check_cooked_recipes():
  def worker():
    with get_conn() as conn, conn.cursor() as cur:
      cur.execute(
        """
        SELECT id AS user_id, COUNT(*) AS cooked_total
        FROM selected_recipe
        WHERE action = 1
        GROUP BY id
        """,
      )
      rows = cur.fetchall()
      if not rows:
        return
      log.info("check_cooked_recipes: evaluated cooked progress for %d users", len(rows))

      cur.execute("SELECT badge_id FROM badge_info WHERE category='cooked'")
      cooked_badges = cur.fetchall()
      if not cooked_badges:
        log.debug("No cooked badges configured; skipping")
        return

      for row in rows:
        user_id = row["user_id"]
        total_cooked = row["cooked_total"]
        for badge in cooked_badges:
          cur.execute(
            """
            SELECT current_value
            FROM badge_process
            WHERE user_id=%s AND badge_id=%s
            ORDER BY process_id DESC
            LIMIT 1
            """,
            (user_id, badge["badge_id"]),
          )
          process = cur.fetchone()
          previous_value = process["current_value"] if process else 0
          increment = total_cooked - previous_value
          if increment <= 0:
            continue
          progress = update_badge_process(user_id, badge["badge_id"], increment, conn)
          if progress["completed"]:
            award_badge(user_id, badge["badge_id"], conn)
  _run_job("check_cooked_recipes", worker)


def check_new_fridge_items():
  def worker():
    with get_conn() as conn, conn.cursor() as cur:
      cur.execute(
        """
        SELECT id AS user_id, COUNT(*) AS new_items
        FROM fridge_item
        WHERE stored_at >= NOW() - INTERVAL %s SECOND
        GROUP BY id
        """,
        (CHECK_INTERVAL,),
      )
      rows = cur.fetchall()
      if rows:
        log.info("check_new_fridge_items: detected %d new fridge items", len(rows))
      if not rows:
        return

      cur.execute("SELECT badge_id FROM badge_info WHERE category='fridge'")
      fridge_badges = cur.fetchall()
      if not fridge_badges:
        log.debug("No fridge badges configured; skipping")
        return

      for row in rows:
        user_id = row["user_id"]
        increment = row["new_items"]
        for badge in fridge_badges:
          progress = update_badge_process(user_id, badge["badge_id"], increment, conn)
          if progress["completed"]:
            award_badge(user_id, badge["badge_id"], conn)
  _run_job("check_new_fridge_items", worker)


def check_goal_progress():
  def worker():
    with get_conn() as conn, conn.cursor() as cur:
      cur.execute(
        """
        SELECT id AS user_id, COUNT(*) AS cooked_count
        FROM selected_recipe
        WHERE action = 1
        GROUP BY id
        """,
      )
      rows = cur.fetchall()
      if not rows:
        return

      for row in rows:
        user_id = row["user_id"]
        cooked_count = row["cooked_count"]

        cur.execute("SELECT last_goal FROM goal_state_cache WHERE user_id=%s", (user_id,))
        cached = cur.fetchone()

        if not cached:
          cur.execute(
            """
            INSERT INTO goal_state_cache (user_id, last_goal, updated_at)
            VALUES (%s, %s, NOW())
            """,
            (user_id, cooked_count),
          )
          continue

        last_goal = cached["last_goal"]
        if cooked_count > last_goal:
          handle_user_event(user_id, "goal", conn)
          cur.execute(
            """
            UPDATE goal_state_cache
            SET last_goal=%s, updated_at=NOW()
            WHERE user_id=%s
            """,
            (cooked_count, user_id),
          )
  _run_job("check_goal_progress", worker)


def check_popular_boards():
  def worker():
    with get_conn() as conn, conn.cursor() as cur:
      cur.execute(
        """
        SELECT DISTINCT content_id
        FROM board_likes
        WHERE created_at >= NOW() - INTERVAL %s SECOND
        """,
        (CHECK_INTERVAL,),
      )
      liked_rows = cur.fetchall()
      if not liked_rows:
        return
      log.info("check_popular_boards: evaluating %d liked posts", len(liked_rows))

      for row in liked_rows:
        content_id = row["content_id"]
        cur.execute(
          """
          SELECT user_id, like_count, is_popular
          FROM board
          WHERE content_id=%s
          """,
          (content_id,),
        )
        board = cur.fetchone()
        if not board:
          continue
        if board.get("is_popular"):
          continue
        if board["like_count"] >= POPULAR_LIKE_THRESHOLD:
          handle_user_event(board["user_id"], "likes", conn)
          cur.execute(
            "UPDATE board SET is_popular=1 WHERE content_id=%s",
            (content_id,),
          )
  _run_job("check_popular_boards", worker)


def aggregate_event_results():
  def worker():
    with get_conn() as conn, conn.cursor() as cur:
      cur.execute(
        """
        SELECT e.event_id
        FROM event e
        WHERE e.end_date < NOW()
          AND e.event_id NOT IN (SELECT DISTINCT event_id FROM event_result)
        """,
      )
      events = cur.fetchall()
      if not events:
        return
      log.info("aggregate_event_results: %d finished events to aggregate", len(events))

      cur.execute(
        """
        SELECT badge_id, target_value
        FROM badge_info
        WHERE category='ranks'
        """,
      )
      rank_badges = cur.fetchall()

      for event in events:
        event_id = event["event_id"]
        cur.execute(
          """
          INSERT INTO event_result (event_id, content_id, user_id, rank, like_count)
          SELECT *
          FROM (
            SELECT
              board.event_id,
              board.content_id,
              board.user_id,
              ROW_NUMBER() OVER (PARTITION BY board.event_id ORDER BY board.like_count DESC, board.created_at ASC) AS rank,
              board.like_count
            FROM board
            WHERE board.event_id=%s
          ) ranked
          WHERE ranked.rank <= 5
          """,
          (event_id,),
        )

        cur.execute(
          """
          SELECT user_id, rank
          FROM event_result
          WHERE event_id=%s
          """,
          (event_id,),
        )
        winners = cur.fetchall()
        for winner in winners:
          user_id = winner["user_id"]
          rank = winner["rank"]
          for badge in rank_badges:
            if rank <= badge["target_value"]:
              award_badge(user_id, badge["badge_id"], conn, event_id=event_id)
  _run_job("aggregate_event_results", worker)


JOB_DEFINITIONS = [
  ("check_new_boards", check_new_boards, CHECK_INTERVAL),
  ("check_cooked_recipes", check_cooked_recipes, CHECK_INTERVAL),
  ("check_new_fridge_items", check_new_fridge_items, CHECK_INTERVAL),
  ("check_goal_progress", check_goal_progress, 15),
  ("check_popular_boards", check_popular_boards, 20),
  ("check_recipe_recommendations", check_recipe_recommendations, CHECK_INTERVAL),
]
