from __future__ import annotations

from typing import List

from fastapi import HTTPException

from app.db.connection import connection_scope


def fetch_visible_faqs() -> List[dict]:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        faq_id,
                        question,
                        answer,
                        category,
                        created_at
                    FROM faq
                    WHERE is_visible = 1
                    ORDER BY COALESCE(updated_at, created_at) DESC, faq_id DESC
                    """
                )
                rows = cur.fetchall()
                return rows or []
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail="FAQ 정보를 불러오지 못했습니다.") from exc


__all__ = ["fetch_visible_faqs"]
