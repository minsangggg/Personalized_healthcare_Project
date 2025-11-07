# ======================================================
# ✅ badge_core.py (FINAL STABLE VERSION)
# ======================================================
import pymysql
from datetime import datetime
import os
from dotenv import load_dotenv
from pathlib import Path
import traceback

# ======================================================
# CONFIG & DB
# ======================================================
ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

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

# ======================================================
# 1️⃣ 진행도 갱신
# ======================================================
def update_badge_process(user_id: str, badge_id: int, increment: int, db, event_id=None):
    """배지 진행도를 갱신하고, 필요 시 새 row 생성"""
    try:
        with db.cursor() as cur:
            # 기존 진행도 조회
            cur.execute("""
                SELECT process_id, current_value, target_value, is_completed
                FROM badge_process
                WHERE user_id = %s AND badge_id = %s
                ORDER BY badge_id DESC
                LIMIT 1
            """, (user_id, badge_id))
            process = cur.fetchone()

            # 항상 최신 target_value로 덮어쓰기
            cur.execute("SELECT target_value FROM badge_info WHERE badge_id = %s", (badge_id,))
            badge = cur.fetchone()
            latest_target = badge["target_value"] if badge else 1

            # 1️⃣ 기존 진행도 없으면 새로 INSERT
            if not process:
                # 최초 삽입 시에도 목표 달성 여부 반영
                is_completed_init = 1 if increment >= latest_target else 0
                cur.execute("""
                    INSERT INTO badge_process (user_id, badge_id, current_value, target_value, is_completed, event_id, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (user_id, badge_id, increment, latest_target, is_completed_init, event_id))
                print(f"🆕 [badge_process] New row inserted for user={user_id}, badge={badge_id}, completed={bool(is_completed_init)}")
                return {"current": increment, "target": latest_target, "completed": bool(is_completed_init)}

            # ✅ 진행도와 목표치 갱신
            current_value = process["current_value"]
            is_completed = process["is_completed"]

            # 2️⃣ 이미 완료된 배지는 더 이상 증가 금지
            if is_completed == 1:
                print(f"⏸️ [badge_process] Already completed badge={badge_id}, skipping increment")
                return {"current": current_value, "target": latest_target, "completed": True}

            # 3️⃣ 진행도 누적
            new_value = current_value + increment

            # ✅ 목표 달성 여부 최신 기준으로 판정
            completed = 1 if new_value >= latest_target else 0

            # ✅ 최신 target_value 동기화 + 상태 갱신
            cur.execute("""
                UPDATE badge_process
                SET current_value = %s,
                    target_value = %s,
                    is_completed = %s,
                    updated_at = NOW()
                WHERE process_id = %s
            """, (new_value, latest_target, completed, process["process_id"]))

            if completed:
                print(f"🎯 [badge_process] Completed → user={user_id}, badge={badge_id}")
            else:
                print(f"🔄 [badge_process] Updated: user={user_id}, badge={badge_id}, progress={new_value}/{latest_target}")

            return {"current": new_value, "target": latest_target, "completed": bool(completed)}

    except Exception:
        print(f"❌ [ERROR] update_badge_process failed for user={user_id}, badge={badge_id}")
        traceback.print_exc()
        return {"current": 0, "target": 0, "completed": False}


# ======================================================
# 2️⃣ 배지 지급
# ======================================================
def award_badge(user_id: str, badge_id: int, db, event_id=None, board_id=None, recipe_id=None):
    """배지 지급 처리 (repeatable 뱃지는 중복 허용)"""
    try:
        with db.cursor() as cur:
            # 🔹 이 배지가 반복 가능한지 조회
            cur.execute("SELECT repeatable FROM badge_info WHERE badge_id = %s", (badge_id,))
            badge = cur.fetchone()
            repeatable = badge["repeatable"] if badge else 0

            # 🔹 반복 불가 배지라면 중복 지급 방지
            if not repeatable:
                cur.execute("""
                    SELECT 1 FROM user_badges
                    WHERE user_id = %s AND badge_id = %s
                """, (user_id, badge_id))
                if cur.fetchone():
                    print(f"⏭️ [Skip] user={user_id} already owns badge={badge_id}")
                    return  # 이미 보유 → 스킵

            # 🔹 반복 가능 배지거나, 처음 받는 경우 → 새 row 추가
            cur.execute("""
                INSERT INTO user_badges (user_id, badge_id, awarded_at, is_active, event_id, board_id, recipe_id)
                VALUES (%s, %s, NOW(), 1, %s, %s, %s)
            """, (user_id, badge_id, event_id, board_id, recipe_id))

            print(f"🏅 [user_badges] Badge awarded → user={user_id}, badge={badge_id}, repeatable={repeatable}")

    except Exception:
        print(f"❌ [ERROR] award_badge failed for user={user_id}, badge={badge_id}")
        traceback.print_exc()


# ======================================================
# 3️⃣ 이벤트 처리
# ======================================================
def handle_user_event(user_id: str, event_type: str, db, event_id=None):
    """
    유저 이벤트 발생 시 해당 카테고리의 배지 진행도 갱신 및 지급 처리
    event_type 예시: contest, cooked, recipe 등
    """
    try:
        with db.cursor() as cur:
            # ✅ 유효한 유저인지 검증 (FK 무결성 보호)
            cur.execute("SELECT 1 FROM user_info WHERE id=%s", (user_id,))
            if not cur.fetchone():
                print(f"⚠️ [Skip] user_id={user_id} not found in user_info → event ignored")
                return

            # ✅ 이벤트 타입에 연결된 배지 조회
            cur.execute("""
                SELECT badge_id, target_value
                FROM badge_info
                WHERE category = %s
            """, (event_type,))
            badges = cur.fetchall()

            if not badges:
                print(f"⚠️ No badge linked to category={event_type}")
                return

            awarded_list = []
            for badge in badges:
                badge_id = badge["badge_id"]
                progress = update_badge_process(user_id, badge_id, increment=1, db=db, event_id=event_id)
                if progress["completed"]:
                    award_badge(user_id, badge_id, db, event_id=event_id)
                    awarded_list.append(badge_id)

            print(f"[🏅 BadgeEvent] user={user_id} event={event_type} → awarded={awarded_list}")

    except Exception:
        print(f"❌ [ERROR] handle_user_event failed for user={user_id}, event={event_type}")
        traceback.print_exc()
