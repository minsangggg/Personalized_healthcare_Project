from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse, JSONResponse

from core.youtube import get_top_shorts_link


router = APIRouter(prefix="/shorts", tags=["shorts"])


@router.get("/open")
def open_shorts(title: Optional[str] = Query(default=None)):
    if not title:
        return JSONResponse({"detail": "title is required"}, status_code=400)
    # 검색 쿼리 보강: 요리/레시피 키워드 추가
    link = get_top_shorts_link(f"{title} 레시피") or get_top_shorts_link(title)
    if not link:
        return JSONResponse({"detail": "no shorts found"}, status_code=404)
    return RedirectResponse(url=link, status_code=307)

