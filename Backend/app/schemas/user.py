from pydantic import BaseModel


class UpdateLevelRequest(BaseModel):
    id: str
    new_level: str


class UpdateProfileRequest(BaseModel):
    id: str
    goal: str
    cooking_level: str
