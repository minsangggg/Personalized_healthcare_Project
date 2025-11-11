from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FaqItem(BaseModel):
    faq_id: int
    question: str
    answer: str
    category: Optional[str] = None
    created_at: Optional[datetime] = None


__all__ = ["FaqItem"]
