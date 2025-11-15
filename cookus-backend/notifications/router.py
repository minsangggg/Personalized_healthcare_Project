# cookus-backend/notifications/router.py
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse

from core import get_current_user
from core.security import token_service
from notifications.repository import list_notifications, mark_read
from notifications.poller import get_poller

router = APIRouter(prefix="/me", tags=["notifications"])

@router.get("/notifications", response_model=List[Dict[str, Any]])
def get_notifications_api(
    since: Optional[datetime] = Query(default=None),
    user_id: str = Depends(get_current_user),
):
    # 초기 진입 시 최근 알림 목록
    return list_notifications(user_id, since)

@router.post("/notifications/{notification_id}/read")
def set_read_api(notification_id: int, user_id: str = Depends(get_current_user)):
    # 단건 읽음 처리
    mark_read(user_id, notification_id)
    return {"ok": True}

# -------------------------
#     SSE 스트리밍
# -------------------------
@router.get("/notifications/stream")
async def stream_notifications(access_token: Optional[str] = Query(default=None)):
    """
    EventSource는 Authorization 헤더를 못 보낸다 → 쿼리로 토큰을 받는다.
    """
    if not access_token:
        raise HTTPException(status_code=401, detail="missing access_token")
    try:
        payload = token_service.decode(access_token)
        user_id = str(payload.get("sub") or "")
        if not user_id:
            raise ValueError("no sub")
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")

    queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
    poller = get_poller()

    # 폴러가 새 알림을 발견하면 여기로 한 건씩 들어온다
    def _subscriber(row: Dict[str, Any]) -> None:
        if str(row.get("id")) == user_id:  # 내 알림만
            try:
                queue.put_nowait(row)
            except Exception:
                pass

    poller.subscribe(_subscriber)  # 구독 시작

    async def event_generator():
        try:
            while True:
                row = await queue.get()  # 새 알림 대기
                yield "data: " + json.dumps(row, default=str, ensure_ascii=False) + "\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            poller.unsubscribe(_subscriber)  # 끊길 때 정리

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # 리버스 프록시(Nginx) 앞이면 필요할 수 있음:
        # "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)
