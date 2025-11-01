from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SaveItem(BaseModel):
    name: str
    quantity: int = Field(1, ge=1)
    unit: Optional[str] = None


class SaveFridgeIn(BaseModel):
    items: List[SaveItem]
    mode: Literal["merge", "replace"] = "merge"
    purgeMissing: bool = False
