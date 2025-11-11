# notifications/poller.py
import asyncio
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any
from core.database import get_conn

Row = Dict[str, Any]
Subscriber = Callable[[Row], None]


class NotificationPoller:
    """
    DB의 notifications 테이블을 주기적으로 스캔해서
    새로 생긴 레코드를 구독자들에게 브로드캐스트하는 폴러.
    """
    def __init__(self, interval_sec: int = 5):
        self.interval = interval_sec
        self.task: Optional[asyncio.Task] = None
        self.last_ts: Optional[datetime] = None
        self.subscribers: List[Subscriber] = []

    # --- 구독/해지 ---
    def subscribe(self, fn: Subscriber) -> None:
        if fn not in self.subscribers:
            self.subscribers.append(fn)

    def unsubscribe(self, fn: Subscriber) -> None:
        try:
            self.subscribers.remove(fn)
        except ValueError:
            pass

    # --- 라이프사이클 ---
    async def start(self) -> None:
        if self.task:
            return
        self.task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

    # --- 내부 루프 ---
    async def _loop(self) -> None:
        while True:
            await asyncio.to_thread(self._check_once)
            await asyncio.sleep(self.interval)

    def _check_once(self) -> None:
        """
        last_ts 이후로 생성된 notifications를 가져와
        모든 구독자에게 순서대로 전달.
        """
        sql = """
            SELECT notification_id, user_id, type, related_id, title, body, link_url, created_at, is_read
            FROM notifications
            WHERE (%s IS NULL OR created_at > %s)
            ORDER BY created_at ASC
            LIMIT 500
        """
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (self.last_ts, self.last_ts))
            rows = cur.fetchall()

        # 새로 생긴 알림을 각 구독자에게 브로드캐스트
        for row in rows:
            for fn in list(self.subscribers):
                try:
                    fn(row)
                except Exception:
                    # 개별 구독자 에러는 전체 브로드캐스트에 영향 주지 않음
                    pass
            self.last_ts = row["created_at"]


# 전역 싱글톤 폴러 인스턴스
_poller = NotificationPoller()

async def start_poller() -> None:
    await _poller.start()

async def stop_poller() -> None:
    await _poller.stop()

def get_poller() -> NotificationPoller:
    return _poller
