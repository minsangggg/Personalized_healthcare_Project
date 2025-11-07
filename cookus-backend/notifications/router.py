from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from core import get_current_user
from .repository import list_notifications, mark_read

router = APIRouter(prefix="/me/notifications", tags=["notifications"])

@router.get("", response_model=List[Dict[str, Any]])
def get_notifications(
    since: Optional[datetime] = Query(default=None),
    user_id: str = Depends(get_current_user),
):
    rows = list_notifications(user_id, since)
    return rows

@router.post("/{notification_id}/read")
def set_read(notification_id: int, user_id: str = Depends(get_current_user)):
    mark_read(user_id, notification_id)
    return {"ok": True}
