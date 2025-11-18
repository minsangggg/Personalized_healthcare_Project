from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.schemas.faq import FaqItem
from app.services.faq_service import fetch_visible_faqs


router = APIRouter(prefix="/faq", tags=["faq"])


@router.get("", response_model=List[FaqItem])
def list_faq() -> List[FaqItem]:
    return fetch_visible_faqs()


__all__ = ["router"]
