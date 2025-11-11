from pydantic import BaseModel


class IngredientItem(BaseModel):
    user_id: str
    name: str
    amount: str
