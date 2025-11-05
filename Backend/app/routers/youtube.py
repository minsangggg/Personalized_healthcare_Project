from fastapi import APIRouter, Query

from app.services.youtube_service import fetch_top_short_video

router = APIRouter(tags=["youtube"])


@router.get("/youtube_shorts")
def youtube_shorts_endpoint(q: str = Query(..., description="검색할 키워드")) -> dict:
    """YouTube Shorts 영상 중 조회수가 높은 영상을 반환합니다."""
    return fetch_top_short_video(q)
