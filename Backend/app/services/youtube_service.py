from __future__ import annotations

from typing import Dict, Optional

import httpx
from fastapi import HTTPException

from app.core.config import get_settings

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
MAX_DURATION_SECONDS = 180  # 3 minutes


def _parse_iso8601_duration(value: str) -> int:
    """
    Convert ISO8601 duration (e.g. PT2M30S) into seconds.
    """
    if not value or not value.startswith("P"):
        return 0

    seconds = 0
    num = ""
    for char in value:
        if char.isdigit():
            num += char
            continue
        if char in {"P", "T"}:
            num = ""
            continue
        if not num:
            continue

        if char == "H":
            seconds += int(num) * 3600
        elif char == "M":
            seconds += int(num) * 60
        elif char == "S":
            seconds += int(num)
        num = ""
    return seconds


def fetch_top_short_video(query: str) -> Dict[str, str]:
    """
    Find the most viewed YouTube Shorts video matching the query
    with duration less than or equal to MAX_DURATION_SECONDS.
    """
    trimmed = (query or "").strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="검색어가 필요합니다.")

    settings = get_settings()
    api_key = settings.youtube_api_key
    if not api_key:
        raise HTTPException(status_code=500, detail="YouTube API 키가 설정되지 않았습니다.")

    with httpx.Client(timeout=10.0) as client:
        search_params = {
            "part": "snippet",
            "q": trimmed,
            "type": "video",
            "maxResults": 10,
            "order": "viewCount",
            "videoDuration": "short",
            "key": api_key,
        }
        search_resp = client.get(f"{YOUTUBE_API_BASE}/search", params=search_params)
        if search_resp.status_code >= 400:
            raise HTTPException(status_code=502, detail="YouTube 검색에 실패했습니다.")
        search_data = search_resp.json()

        video_ids = [
            item["id"]["videoId"]
            for item in search_data.get("items", [])
            if item.get("id", {}).get("videoId")
        ]
        if not video_ids:
            raise HTTPException(status_code=404, detail="조건에 맞는 영상이 없습니다.")

        videos_params = {
            "part": "contentDetails,statistics",
            "id": ",".join(video_ids),
            "key": api_key,
        }
        videos_resp = client.get(f"{YOUTUBE_API_BASE}/videos", params=videos_params)
        if videos_resp.status_code >= 400:
            raise HTTPException(status_code=502, detail="YouTube 영상 정보를 가져오지 못했습니다.")
        videos_data = videos_resp.json()

        best_video: Optional[Dict[str, str]] = None
        best_views = -1

        for item in videos_data.get("items", []):
            video_id = item.get("id")
            if not video_id:
                continue

            duration = _parse_iso8601_duration(item.get("contentDetails", {}).get("duration", ""))
            if duration <= 0 or duration > MAX_DURATION_SECONDS:
                continue

            view_count = int(item.get("statistics", {}).get("viewCount", 0))
            if view_count > best_views:
                best_views = view_count
                best_video = {
                    "video_id": video_id,
                    "duration_seconds": str(duration),
                    "view_count": str(view_count),
                    "embed_url": f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&playsinline=1",
                }

        if not best_video:
            raise HTTPException(status_code=404, detail="조건에 맞는 영상이 없습니다.")

        return best_video
