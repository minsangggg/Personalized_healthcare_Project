# badge_core.py
import pymysql
from datetime import datetime
import os
from dotenv import load_dotenv
from pathlib import Path

# ======================================================
# CONFIG & DB
# ======================================================
ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)
# ============================================================
# ✅ DB 연결 설정
# ============================================================
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

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

# ============================================================
# 1️⃣ 진행도 갱신
# ============================================================
def update_badge_process(user_id: str, badge_id: int, increment: int, db):
    with db.cursor() as cur:
        cur.execute("""
            SELECT process_id, current_value, target_value, is_completed
            FROM badge_process
            WHERE user_id = %s AND badge_id = %s
            ORDER BY updated_at DESC
            LIMIT 1
        """, (user_id, badge_id))
        process = cur.fetchone()

        cur.execute("SELECT target_value FROM badge_info WHERE badge_id = %s", (badge_id,))
        badge = cur.fetchone()
        target_value = badge["target_value"] if badge else 1

        if not process:
            cur.execute("""
                INSERT INTO badge_process (user_id, badge_id, current_value, target_value, is_completed, updated_at)
                VALUES (%s, %s, %s, %s, 0, NOW())
            """, (user_id, badge_id, increment, target_value))
            db.commit()
            return {"current": increment, "target": target_value, "completed": False}

        if process["is_completed"] == 1:
            return {"current": process["current_value"], "target": target_value, "completed": True}

        new_value = process["current_value"] + increment
        is_completed = 1 if new_value >= target_value else 0

        cur.execute("""
            UPDATE badge_process
            SET current_value = %s, is_completed = %s, updated_at = NOW()
            WHERE process_id = %s
        """, (new_value, is_completed, process["process_id"]))
        db.commit()

        return {"current": new_value, "target": target_value, "completed": bool(is_completed)}

# ============================================================
# 2️⃣ 뱃지 지급
# ============================================================
def award_badge(user_id: str, badge_id: int, db, event_id=None, board_id=None, recipe_id=None):
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO user_badges (user_id, badge_id, awarded_at, is_active, event_id, board_id, recipe_id)
            VALUES (%s, %s, NOW(), 1, %s, %s, %s)
            ON DUPLICATE KEY UPDATE is_active = 1
        """, (user_id, badge_id, event_id, board_id, recipe_id))
        db.commit()

# ============================================================
# 3️⃣ 이벤트 처리
# ============================================================
def handle_user_event(user_id: str, event_type: str, db):
    with db.cursor() as cur:
        cur.execute("""
            SELECT badge_id, target_value
            FROM badge_info
            WHERE event_type = %s
        """, (event_type,))
        badges = cur.fetchall()

        if not badges:
            print(f"⚠️ No badge linked to event_type={event_type}")
            return

        awarded_list = []
        for badge in badges:
            badge_id = badge["badge_id"]
            progress = update_badge_process(user_id, badge_id, increment=1, db=db)
            if progress["completed"]:
                award_badge(user_id, badge_id, db)
                awarded_list.append(badge_id)

        print(f"[🏅 BadgeEvent] user={user_id} event={event_type} → awarded={awarded_list}")
