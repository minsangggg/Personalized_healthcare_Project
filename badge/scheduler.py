from apscheduler.schedulers.background import BackgroundScheduler
from .service import handle_user_event, get_conn
import time
import os

CHECK_INTERVAL = 10  # 초 단위 (10초마다 감시)
LIKE_THRESHOLD = int(os.getenv("LIKE_THRESHOLD", "50"))

# ============================================================
# 게시글 작성 감지
# ============================================================
def check_new_boards():
    db = get_conn()
    with db.cursor() as cur:
        cur.execute("""
            SELECT user_id FROM board
            WHERE created_at >= NOW() - INTERVAL %s SECOND
        """, (CHECK_INTERVAL,))
        new_posts = cur.fetchall()

        if new_posts:
            print(f"📝 [Detect] New boards found: {len(new_posts)}")
        for post in new_posts:
            handle_user_event(user_id=post["user_id"], event_type="contest", db=db)
    db.close()

# ============================================================
# 레시피 추천 감지
# ============================================================
def check_recipe_recommendations():
    db = get_conn()
    with db.cursor() as cur:
        # 1. 최근 CHECK_INTERVAL 내 새 추천 레코드 확인
        cur.execute("""
            SELECT id, recommend_date
            FROM recommend_recipe
            WHERE recommend_date >= NOW() - INTERVAL %s SECOND
        """, (CHECK_INTERVAL,))
        logs = cur.fetchall()

        if logs:
            print(f"🍽️ [Detect] New recipe recommendations: {len(logs)}")

        # 2. 같은 시간대의 중복 추천(같은 id + recommend_date)은 1회만 처리
        unique_users = {}
        for log in logs:
            key = (log["id"], log["recommend_date"])
            if key not in unique_users:
                unique_users[key] = True

        # 3. 유저별로 handle_user_event 호출
        for user_id, _ in unique_users.keys():
            # ✅ 핵심 수정: user_id=id (내장함수) ❌ → user_id=user_id (정상 값) ✅
            handle_user_event(user_id=user_id, event_type="recipe", db=db)

    db.close()



# ============================================================
# 레시피 조리 완료 감지
# ============================================================
def check_cooked_recipes():
    db = get_conn()
    with db.cursor() as cur:
        cur.execute("""
            SELECT id, id AS recipe_id
            FROM selected_recipe
            WHERE updated_at >= NOW() - INTERVAL %s SECOND
              AND action = 1
        """, (CHECK_INTERVAL,))
        cooked = cur.fetchall()

        if cooked:
            print(f"🍽️ [Detect] Cooked recipes found: {len(cooked)}")
        else:
            print("⚠️ No cooked recipes detected this tick")

        for r in cooked:
            handle_user_event(user_id=r["id"], event_type="cooked", db=db)
    db.close()

# ============================================================
# 냉장고 재료 추가 감지
# ============================================================
def check_new_fridge_items():
    db = get_conn()
    with db.cursor() as cur:
        cur.execute("""
            SELECT id FROM fridge_item
            WHERE stored_at >= NOW() - INTERVAL %s SECOND
        """, (CHECK_INTERVAL,))
        items = cur.fetchall()

        if items:
            print(f"🥬 [Detect] New fridge items: {len(items)}")

        for i in items:
            handle_user_event(user_id=i["id"], event_type="fridge", db=db)
    db.close()

def check_goal_progress():
    db = get_conn()
    with db.cursor() as cur:
        # 1. 각 유저별로 완료한 요리 수(action=1) 집계
        cur.execute("""
            SELECT id AS user_id, COUNT(*) AS cooked_count
            FROM selected_recipe
            WHERE action = 1
            GROUP BY id
        """)
        users = cur.fetchall()

        if not users:
            print("⚠️ No cooked recipes detected this tick")
            return

        for u in users:
            user_id = u["user_id"]
            cooked_count = u["cooked_count"]

            # 2. goal_state_cache 조회
            cur.execute("SELECT last_goal FROM goal_state_cache WHERE user_id=%s", (user_id,))
            cached = cur.fetchone()

            # 3. 최초 등록 시 캐시 초기화
            if not cached:
                print(f"🆕 [GoalInit] user={user_id}, cooked={cooked_count} 기록됨")
                cur.execute("""
                    INSERT INTO goal_state_cache (user_id, last_goal, updated_at)
                    VALUES (%s, %s, NOW())
                """, (user_id, cooked_count))
                db.commit()
                continue

            last_goal = cached["last_goal"]

            # 4. 요리 완료 수가 증가한 경우만 이벤트 발생
            if cooked_count > last_goal:
                print(f"🎯 [GoalDetect] user={user_id} → cooked increased {last_goal} → {cooked_count}")
                handle_user_event(user_id=user_id, event_type="goal", db=db)
                cur.execute("""
                    UPDATE goal_state_cache
                    SET last_goal=%s, updated_at=NOW()
                    WHERE user_id=%s
                """, (cooked_count, user_id))
                db.commit()
    db.close()



# ============================================================
# 게시글 좋아요 수 감지 (50개 이상일 때 작성자에게 배지 지급)
# ============================================================
LIKE_THRESHOLD = 50  # 임계치

def check_popular_boards():
    """
    최근 board_likes insert 발생 감지 → board.like_count 확인 → 배지 지급.
    """
    db = get_conn()
    with db.cursor() as cur:
        # 1. 최근 몇 초 내 새 좋아요 감지
        cur.execute("""
            SELECT DISTINCT content_id
            FROM board_likes
            WHERE created_at >= NOW() - INTERVAL %s SECOND
        """, (CHECK_INTERVAL,))
        new_likes = cur.fetchall()

        if not new_likes:
            print("⚠️ No new likes detected this tick.")
            return

        print(f"[Detect] New likes: {len(new_likes)} recent events")

        # 2. 각 게시글별로 board.like_count 확인
        for row in new_likes:
            content_id = row["content_id"]

            cur.execute("""
                SELECT user_id, like_count, is_popular
                FROM board
                WHERE content_id = %s
            """, (content_id,))
            board = cur.fetchone()

            # 게시글이 삭제되었거나 없음
            if not board:
                continue

            user_id = board["user_id"]
            like_count = board["like_count"]
            is_popular = board.get("is_popular", 0)

            # 3 이미 인기글이면 스킵
            if is_popular == 1:
                continue

            # 4. 좋아요 수 기준 달성 여부 확인
            if like_count >= LIKE_THRESHOLD:
                print(f"🏆 [PopularPost] content_id={content_id}, author={user_id}, likes={like_count}")

                # 배지 지급
                handle_user_event(user_id=user_id, event_type="likes", db=db)

                # 중복 방지 마킹
                cur.execute("""
                    UPDATE board
                    SET is_popular = 1
                    WHERE content_id = %s
                """, (content_id,))
                db.commit()

        print("[Done] Popular post check complete.")
    db.close()




# ============================================================
# 스케줄러 시작(라이브러리 호출용)
# ============================================================
_SCHEDULER = None


def start_scheduler():
    """Create and start a singleton BackgroundScheduler with all jobs.

    Safe to call multiple times (no duplicate schedulers under reload).
    """
    global _SCHEDULER
    if _SCHEDULER is not None:
        return _SCHEDULER

    scheduler = BackgroundScheduler()
    scheduler.add_job(check_new_boards, 'interval', seconds=CHECK_INTERVAL, max_instances=1)
    scheduler.add_job(check_cooked_recipes, 'interval', seconds=CHECK_INTERVAL, max_instances=1)
    scheduler.add_job(check_new_fridge_items, 'interval', seconds=CHECK_INTERVAL, max_instances=1)
    scheduler.add_job(check_goal_progress, 'interval', seconds=15, max_instances=1)
    scheduler.add_job(check_popular_boards, 'interval', seconds=20, max_instances=1)
    scheduler.add_job(check_recipe_recommendations, 'interval', seconds=CHECK_INTERVAL, max_instances=1)
    scheduler.start()
    _SCHEDULER = scheduler
    print(f"✅ Badge Scheduler started! (interval={CHECK_INTERVAL}s, DB 감시 중...)")
    return _SCHEDULER


if __name__ == "__main__":
    # Local run fallback
    start_scheduler()
    try:
        while True:
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        if _SCHEDULER:
            _SCHEDULER.shutdown()
        print("🛑 Scheduler stopped.")
