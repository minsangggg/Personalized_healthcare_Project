from fastapi import APIRouter, Query

from app.services.youtube_service import fetch_top_short_video

router = APIRouter(tags=["youtube"])


@router.get("/youtube_shorts")
def youtube_shorts_endpoint(
    q: str = Query(..., description="검색할 키워드"),
    syllables: str | None = Query(default=None, description="제목에 포함되어야 할 음절 목록(콤마 구분)"),
    allowed: str | None = Query(default=None, description="허용되는 주요 재료 키워드 목록(콤마 구분)"),
) -> dict:
    """YouTube Shorts 영상을 검색해 가장 인기 있는 영상을 반환합니다."""
    syllable_list = [item.strip() for item in syllables.split(",") if item.strip()] if syllables else None
    allowed_list = [item.strip() for item in allowed.split(",") if item.strip()] if allowed else None
    return fetch_top_short_video(q, syllable_list, allowed_list)
