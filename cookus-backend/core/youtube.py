import os
import time
import requests
from typing import Optional, Dict, Tuple, List

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# 간단 캐시: 동일 쿼리는 3시간 재사용 (쿼터 절약)
_cache: Dict[str, Tuple[str, float]] = {}
_TTL = 60 * 60 * 3

def _now() -> float:
    return time.time()

def _iso8601_to_seconds(iso: str) -> Optional[int]:
    try:
        if not iso.startswith("PT"):
            return None
        total = 0
        tmp = iso[2:]
        if "M" in tmp:
            m = tmp.split("M")[0]
            total += int(m) * 60
            tmp = tmp.split("M")[1]
        if "S" in tmp:
            s = tmp.replace("S", "")
            if s:
                total += int(s)
        return total
    except:
        return None

def _pick_first_shorts(video_ids: List[str]) -> Optional[str]:
    if not video_ids:
        return None
    params = {"part": "contentDetails", "id": ",".join(video_ids), "key": YOUTUBE_API_KEY}
    r = requests.get(VIDEOS_URL, params=params, timeout=8)
    r.raise_for_status()
    for it in r.json().get("items", []):
        vid = it["id"]
        dur = it["contentDetails"]["duration"]
        secs = _iso8601_to_seconds(dur)
        if secs is not None and secs <= 60:
            return f"https://www.youtube.com/shorts/{vid}"
    return None

def get_top_shorts_link(query: str) -> Optional[str]:
    if not YOUTUBE_API_KEY:
        return None
    if query in _cache and _now() < _cache[query][1]:
        return _cache[query][0]

    params = {
        "key": YOUTUBE_API_KEY,
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "relevance",
        "maxResults": 5,
        "regionCode": "KR",
        "relevanceLanguage": "ko",
        "videoDuration": "short",
        "videoEmbeddable": "true",
        "safeSearch": "moderate",
    }
    r = requests.get(SEARCH_URL, params=params, timeout=8)
    r.raise_for_status()
    video_ids = [it["id"]["videoId"] for it in r.json().get("items", []) if it.get("id", {}).get("videoId")]
    link = _pick_first_shorts(video_ids)
    if not link and video_ids:
        link = f"https://www.youtube.com/watch?v={video_ids[0]}"  # 폴백
    if link:
        _cache[query] = (link, _now() + _TTL)
    return link

