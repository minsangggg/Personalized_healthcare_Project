from typing import List, Optional

from pydantic import BaseModel


class IngredientForRecommendation(BaseModel):
    name: str
    amount: Optional[str] = None


class RecommendRequest(BaseModel):
    user_id: str
    ingredients: Optional[List[IngredientForRecommendation]] = None


class SelectedRecipe(BaseModel):
    user_id: str
    recommend_id: int
    recipe_id: int


class SelectedRecipeAction(BaseModel):
    user_id: str
    recommend_id: int
    recipe_id: int
    action: int
