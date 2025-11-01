from fastapi import APIRouter, Depends

from core import get_current_user

from .models import SaveFridgeIn
from .service import fridge_service


router = APIRouter(prefix="/me", tags=["fridge"])


@router.get("/ingredients")
def me_ingredients_get(current_user: str = Depends(get_current_user)):
    return fridge_service.list_items(current_user)


@router.post("/ingredients")
def me_ingredients_post(payload: SaveFridgeIn, current_user: str = Depends(get_current_user)):
    return fridge_service.save_items(current_user, payload)
