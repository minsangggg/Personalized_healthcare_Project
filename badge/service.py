# ======================================================
# service.py — 배지 진행도, 지급, 이벤트 처리 로직
# ======================================================
import pymysql
import os
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
import traceback

# ------------------------------------------------------
# ✅ .env 로드
# ------------------------------------------------------
ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

# ------------------------------------------------------
# ✅ DB 연결 함수
# ------------------------------------------------------
def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset=DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

# ------------------------------------------------------
# ✅ 진행도 갱신
# ------------------------------------------------------
def update_badge_process(user_id: str, badge_id: int, increment: int, db, event_id=None):
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT process_id, current_value, target_value, is_completed
                FROM badge_process
                WHERE user_id = %s AND badge_id = %s
                ORDER BY badge_id DESC LIMIT 1
            """, (user_id, badge_id))
            process = cur.fetchone()

            cur.execute("SELECT target_value FROM badge_info WHERE badge_id = %s", (badge_id,))
            badge = cur.fetchone()
            latest_target = badge["target_value"] if badge else 1

            if not process:
                is_completed_init = 1 if increment >= latest_target else 0
                cur.execute("""
                    INSERT INTO badge_process (user_id, badge_id, current_value, target_value, is_completed, event_id, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (user_id, badge_id, increment, latest_target, is_completed_init, event_id))
                return {"current": increment, "target": latest_target, "completed": bool(is_completed_init)}

            if process["is_completed"] == 1:
                return {"current": process["current_value"], "target": latest_target, "completed": True}

            new_value = process["current_value"] + increment
            completed = 1 if new_value >= latest_target else 0

            cur.execute("""
                UPDATE badge_process
                SET current_value=%s, target_value=%s, is_completed=%s, updated_at=NOW()
                WHERE process_id=%s
            """, (new_value, latest_target, completed, process["process_id"]))

            return {"current": new_value, "target": latest_target, "completed": bool(completed)}

    except Exception:
        traceback.print_exc()
        return {"current": 0, "target": 0, "completed": False}

# ------------------------------------------------------
# ✅ 배지 지급
# ------------------------------------------------------
def award_badge(user_id: str, badge_id: int, db, event_id=None, board_id=None, recipe_id=None):
    """
    user_badges 테이블에 배지 지급 기록을 남김.
    현재 테이블 구조: user_id, badge_id, awarded_at, is_active, event_id, is_displayed
    """
    try:
        with db.cursor() as cur:
            # 반복 가능 여부 확인
            cur.execute("SELECT repeatable FROM badge_info WHERE badge_id = %s", (badge_id,))
            badge = cur.fetchone()
            repeatable = badge["repeatable"] if badge else 0

            # 반복 불가 배지는 중복 방지
            if not repeatable:
                cur.execute("""
                    SELECT 1 FROM user_badges 
                    WHERE user_id = %s AND badge_id = %s
                """, (user_id, badge_id))
                if cur.fetchone():
                    print(f"⏭️ [Skip] user={user_id} already has badge={badge_id}")
                    return

            # ✅ 현재 스키마에 맞춘 INSERT
            cur.execute("""
                INSERT INTO user_badges (user_id, badge_id, awarded_at, is_active, event_id, is_displayed)
                VALUES (%s, %s, NOW(), 1, %s, 1)
            """, (user_id, badge_id, event_id))

            print(f"🏅 Badge awarded → user={user_id}, badge={badge_id}, event={event_id}")

    except Exception as e:
        print(f"[ERROR] award_badge failed for user={user_id}, badge={badge_id}")
        import traceback; traceback.print_exc()


# ------------------------------------------------------
# ✅ 유저 이벤트 처리
# ------------------------------------------------------
def handle_user_event(user_id: str, event_type: str, db, event_id=None):
    try:
        with db.cursor() as cur:
            cur.execute("SELECT 1 FROM user_info WHERE id=%s", (user_id,))
            if not cur.fetchone():
                return

            cur.execute("SELECT badge_id, target_value FROM badge_info WHERE category=%s", (event_type,))
            badges = cur.fetchall()
            if not badges:
                return

            for badge in badges:
                progress = update_badge_process(user_id, badge["badge_id"], 1, db, event_id)
                if progress["completed"]:
                    award_badge(user_id, badge["badge_id"], db, event_id)
    except Exception:
        traceback.print_exc()

