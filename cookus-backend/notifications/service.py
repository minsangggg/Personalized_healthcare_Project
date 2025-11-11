# cookus-backend/notifications/service.py
from notifications.repository import insert_notification

def notify(
    user_id: str,
    title: str,
    body: str,
    link_url: str | None = None,
    type: str = "generic",
    related_id: int | None = None,
) -> int:
    return insert_notification(user_id, title, body, link_url, type, related_id)
