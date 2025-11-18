from pydantic import BaseModel


class BoardLikeRequest(BaseModel):
    user_id: str
    content_id: int

