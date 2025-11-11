from pydantic import BaseModel
from typing import Literal, Optional, List

class EarnedBadge(BaseModel):
    badge_id: int
    name: str
    category: str
    earned_at: str
    is_active: bool
    is_displayed: bool

class Progress(BaseModel):
    current: int
    target: int
    remaining: int

class LockedBadge(BaseModel):
    badge_id: int
    name: str
    category: str
    progress: Optional[Progress] = None

class BadgeOverview(BaseModel):
    earned: List[EarnedBadge]
    locked: List[LockedBadge]
