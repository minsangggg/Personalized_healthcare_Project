# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from badge_core import handle_user_event, get_conn

CHECK_INTERVAL = 10  # 초 단위 (10초마다 감시)

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

        for post in new_posts:
            handle_user_event(user_id=post["user_id"], event_type="post_write", db=db)
    db.close()

# ============================================================
# 레시피 조리 완료 감지
# ============================================================
def check_cooked_recipes():
    db = get_conn()
    with db.cursor() as cur:
        cur.execute("""
            SELECT id FROM selected_recipe
            WHERE selected_date >= NOW() - INTERVAL %s SECOND
              AND action = 1
        """, (CHECK_INTERVAL,))
        cooked = cur.fetchall()

        for r in cooked:
            handle_user_event(user_id=r["id"], event_type="recipe_cooked", db=db)
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

        for i in items:
            handle_user_event(user_id=i["id"], event_type="fridge_item_added", db=db)
    db.close()

# ============================================================
# 목표 달성 감지 (goal_state_cache 기반)
# ============================================================
def check_goal_progress():
    db = get_conn()
    with db.cursor() as cur:
        # 1️⃣ 현재 모든 유저의 goal 값 가져오기
        cur.execute("SELECT id, goal FROM user_info")
        users = cur.fetchall()

        for u in users:
            user_id = u["id"]
            current_goal = u["goal"]

            # 2️⃣ goal_state_cache에서 이전 goal 값 조회
            cur.execute("""
                SELECT last_goal FROM goal_state_cache
                WHERE user_id = %s
            """, (user_id,))
            cached = cur.fetchone()

            if not cached:
                # 캐시가 없으면 새로 추가
                cur.execute("""
                    INSERT INTO goal_state_cache (user_id, last_goal, updated_at)
                    VALUES (%s, %s, NOW())
                """, (user_id, current_goal))
                db.commit()
                continue  # 처음 등록이므로 비교 생략

            last_goal = cached["last_goal"]

            # 3️⃣ goal이 증가한 경우만 감지
            if current_goal > last_goal:
                print(f"[🎯 GoalDetect] user={user_id} → goal_achieved ({last_goal} → {current_goal})")

                # 뱃지 시스템 호출
                handle_user_event(user_id=user_id, event_type="goal_achieved", db=db)

                # 캐시 업데이트
                cur.execute("""
                    UPDATE goal_state_cache
                    SET last_goal = %s, updated_at = NOW()
                    WHERE user_id = %s
                """, (current_goal, user_id))
                db.commit()

    db.close()


# ============================================================
# 스케줄러 시작
# ============================================================
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_new_boards, 'interval', seconds=CHECK_INTERVAL)
    scheduler.add_job(check_cooked_recipes, 'interval', seconds=CHECK_INTERVAL)
    scheduler.add_job(check_new_fridge_items, 'interval', seconds=CHECK_INTERVAL)
    scheduler.add_job(check_goal_progress, 'interval', seconds=CHECK_INTERVAL)
    scheduler.start()
    print(f"🛰️ Scheduler started! (interval={CHECK_INTERVAL}s)")

if __name__ == "__main__":
    from apscheduler.schedulers.background import BackgroundScheduler
    import time

    scheduler = BackgroundScheduler()

    # 감시할 작업 등록 (5초마다)
    scheduler.add_job(check_new_boards, 'interval', seconds=10, max_instances=1)
    scheduler.add_job(check_cooked_recipes, 'interval', seconds=10, max_instances=1)
    scheduler.add_job(check_new_fridge_items, 'interval', seconds=10, max_instances=1)
    scheduler.add_job(check_goal_progress, 'interval', seconds=15, max_instances=1)

    scheduler.start()
    print("✅ Badge Scheduler started! (DB 감시 중...)")

    try:
        while True:
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("🛑 Scheduler stopped.")