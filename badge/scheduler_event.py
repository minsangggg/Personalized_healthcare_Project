# ============================================================
# scheduler_event.py — 대회 종료 감시 + 순위 자동 집계 + ranks 배지 자동 지급 (event_id 기록 포함)
# ============================================================

import pymysql
import os
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler


# ------------------------------------------------------------
# 환경 변수 로드 (.env)
# ------------------------------------------------------------
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")


# ------------------------------------------------------------
# DB 연결
# ------------------------------------------------------------
def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset=DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


# ------------------------------------------------------------
# ranks 배지 자동 지급 로직
# ------------------------------------------------------------
def award_rank_badges(conn, winners, event_id):
    """
    winners: [{'user_id': 'userA', 'rank': 1}, ...]
    badge_info.category='ranks' 인 배지의 target_value 기준으로 자동 지급
    """
    with conn.cursor() as cur:
        # 1. ranks 관련 뱃지 조회
        cur.execute("""
            SELECT badge_id, name_ko, target_value
            FROM badge_info
            WHERE category = 'ranks';
        """)
        badges = cur.fetchall()

        if not badges:
            print("⚠️ No ranks badges found in badge_info.")
            return

        # 2. 순위별 지급 로직
        for w in winners:
            user_id, rank = w["user_id"], w["rank"]

            for b in badges:
                badge_id = b["badge_id"]
                target = b["target_value"]

                # target_value=1 → 1등만 / target_value=5 → 1~5등 지급
                if rank <= target:
                    # 중복 방지: 같은 이벤트 + 같은 뱃지 중복 지급 방지
                    cur.execute("""
                        SELECT 1 FROM user_badges
                        WHERE user_id = %s AND badge_id = %s AND event_id = %s;
                    """, (user_id, badge_id, event_id))
                    exists = cur.fetchone()
                    if exists:
                        print(f"🎖️ User {user_id} already has badge_id={badge_id} for event {event_id}. Skipping.")
                        continue

                    # 지급 실행
                    cur.execute("""
                        INSERT INTO user_badges (user_id, badge_id, awarded_at, is_active, event_id)
                        VALUES (%s, %s, NOW(), 1, %s);
                    """, (user_id, badge_id, event_id))
                    print(f"🏅 Badge {badge_id} awarded to {user_id} (rank {rank} ≤ target {target}, event {event_id})")


# ------------------------------------------------------------
#  대회 순위 집계 + 배지 지급
# ------------------------------------------------------------
def aggregate_event_results():
    conn = get_conn()
    cur = conn.cursor()

    print(f"\n📅 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Event result aggregation started...")

    # 종료된 이벤트 중 아직 결과 없는 이벤트
    cur.execute("""
        SELECT e.event_id
        FROM event e
        WHERE e.end_date < NOW()
          AND e.event_id NOT IN (SELECT DISTINCT event_id FROM event_result);
    """)
    finished_events = cur.fetchall()

    if not finished_events:
        print("⚠️ No finished events pending for result aggregation.")
        cur.close()
        conn.close()
        return

    for ev in finished_events:
        event_id = ev["event_id"]
        print(f"🏁 Aggregating results for event_id={event_id}...")

        # 상위 5등 게시글 집계
        cur.execute(f"""
            INSERT INTO event_result (event_id, content_id, user_id, rank, like_count)
            SELECT 
                ranked.event_id,
                ranked.content_id,
                ranked.user_id,
                ranked.rank,
                ranked.like_count
            FROM (
                SELECT 
                    event_id,
                    content_id,
                    user_id,
                    like_count,
                    ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY like_count DESC, created_at ASC) AS rank
                FROM board
                WHERE event_id = {event_id}
            ) AS ranked
            WHERE ranked.rank <= 5;
        """)
        print(f"event_id={event_id} results saved successfully.")

        # 상위 5명 조회
        cur.execute("""
            SELECT user_id, rank
            FROM event_result
            WHERE event_id = %s;
        """, (event_id,))
        winners = cur.fetchall()

        # ranks 배지 지급 (이벤트별)
        award_rank_badges(conn, winners, event_id)

    cur.close()
    conn.close()
    print("All event results aggregated and ranks badges awarded successfully.\n")


# ------------------------------------------------------------
# 자동 스케줄러 (1분마다 실행)
# ------------------------------------------------------------
def start_event_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(aggregate_event_results, "interval", hours=12)
    scheduler.start()
    print("[Scheduler] Event ranking auto-aggregation started (every 12 hours).")
