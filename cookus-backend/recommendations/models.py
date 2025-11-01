from pydantic import BaseModel, Field


class SelectIn(BaseModel):
    recipe_id: int


class SelectedActionIn(BaseModel):
    action: int = Field(..., ge=0, le=1)
