# cookus-backend/core/tasks.py
import asyncio
from datetime import datetime, time
from core.database import get_conn
from notifications.service import notify
from notifications.repository import exists_today_supplement_notice

SLOTS = {
    # Morning
    "아침_공복": (time(6, 0),  time(9, 59)),
    "아침_식후": (time(7, 0),  time(10, 59)),
    # Lunch
    "점심_공복": (time(11, 0), time(12, 29)),
    "점심_식후": (time(12, 0), time(13, 59)),
    # Dinner
    "저녁_공복": (time(17, 0), time(18, 29)),
    "저녁_식후": (time(18, 0), time(20, 59)),
}

def _in_slot(now_t: time, window: tuple[time, time]) -> bool:
    return window[0] <= now_t <= window[1]

async def supplement_reminder_worker(poll_seconds: int = 60):
    while True:
        try:
            now_t = datetime.now().time()
            active_slots = [slot for slot, win in SLOTS.items() if _in_slot(now_t, win)]
            if active_slots:
                placeholders = ",".join(["%s"] * len(active_slots))
                sql = f"""
                    SELECT plan_id, user_id, supplement_name, time_slot
                    FROM supplement_plans
                    WHERE deleted_at IS NULL
                      AND time_slot IN ({placeholders})
                """
                with get_conn() as conn, conn.cursor() as cur:
                    cur.execute(sql, tuple(active_slots))
                    rows = cur.fetchall()

                for r in rows:
                    plan_id = int(r["plan_id"])
                    uid = r["user_id"]
                    supplement_name = r["supplement_name"]
                    time_slot = r["time_slot"]

                    if not exists_today_supplement_notice(uid, plan_id):
                        notify(
                            user_id=uid,
                            title="영양제 알림",
                            body=f"{time_slot}에 복용할 '{supplement_name}' 먹을 시간이에요!",
                            link_url="/my/supplements",
                            type="supplement",
                            related_id=plan_id,
                        )
        except Exception as e:
            print("[supplement_reminder_worker] error:", e)

        await asyncio.sleep(poll_seconds)
