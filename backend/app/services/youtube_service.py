from __future__ import annotations

import re
from typing import Dict, List, Optional

import httpx
from fastapi import HTTPException

from app.core.config import get_settings

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
MAX_DURATION_SECONDS = 90  # 1 minute 30 seconds
MIN_DURATION_SECONDS = 20
MAX_SEARCH_PAGES = 3
RESULTS_PER_PAGE = 50
_normalize_pattern = re.compile(r"\s+")
_hangul_word_pattern = re.compile(r"[가-힣]+")
COMMON_DESCRIPTOR_KEYWORDS = {
  "간단",
  "초간단",
  "맛있",
  "맛있는",
  "레시피",
  "요리",
  "집밥",
  "반찬",
  "메뉴",
  "한끼",
  "간식",
  "초보",
  "자취",
  "비법",
  "꿀팁",
  "초간편",
  "초스피드",
  "특급",
  "최고",
  "오늘",
  "저녁",
  "아침",
  "점심",
  "만드는",
  "방법",
  "영상",
  "필수",
  "레전드",
  "대박",
  "초간",
  "캠핑",
  "든든",
  "자취생",
  "항상",
  "쉽게",
  "쉬운",
  "환상",
  "요즘",
  "핫",
  "새로운",
  "초간단요리",
  "초간단레시피",
  "초간단반찬",
  "가성비",
  "아이",
  "어른",
  "엄마",
  "아빠",
  "국민",
}


def _normalize_text(value: str) -> str:
  """
  Remove whitespace and lowercase for comparison.
  """
  return _normalize_pattern.sub("", value or "").lower()


def _title_matches(title: str, query: str, syllables: Optional[List[str]]) -> bool:
  normalized_title = _normalize_text(title)
  if syllables:
    return all(syllable in normalized_title for syllable in syllables)
  normalized_query = _normalize_text(query)
  return bool(normalized_query) and normalized_query in normalized_title


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


def _normalize_syllables(syllables: Optional[List[str]]) -> List[str]:
  if not syllables:
    return []
  normalized = []
  for syllable in syllables:
    cleaned = syllable.strip()
    if cleaned:
      normalized.append(_normalize_text(cleaned))
  return [item for item in normalized if item]


def _normalize_allowed_words(words: Optional[List[str]]) -> List[str]:
  if not words:
    return []
  normalized = []
  for word in words:
    cleaned = word.strip()
    if cleaned:
      normalized.append(_normalize_text(cleaned))
  return [item for item in normalized if item]


def _extract_hangul_words(value: str) -> List[str]:
  return _hangul_word_pattern.findall(value)


def _has_allowed_word(title: str, allowed_words: List[str]) -> bool:
  if not allowed_words:
    return True
  normalized_title = _normalize_text(title)
  return any(word and word in normalized_title for word in allowed_words)


def fetch_top_short_video(query: str, syllables: Optional[List[str]] = None, allowed_words: Optional[List[str]] = None) -> Dict[str, str]:
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

  normalized_syllables = _normalize_syllables(syllables)
  normalized_allowed_words = _normalize_allowed_words(allowed_words)

  best_video: Optional[Dict[str, str]] = None
  best_views = -1

  with httpx.Client(timeout=10.0) as client:
    page_token: Optional[str] = None
    pages_checked = 0

    while pages_checked < MAX_SEARCH_PAGES:
      search_params = {
        "part": "snippet",
        "q": trimmed,
        "type": "video",
        "maxResults": RESULTS_PER_PAGE,
        "order": "viewCount",
        "videoDuration": "short",
        "key": api_key,
      }
      if page_token:
        search_params["pageToken"] = page_token

      search_resp = client.get(f"{YOUTUBE_API_BASE}/search", params=search_params)
      if search_resp.status_code >= 400:
        raise HTTPException(status_code=502, detail="YouTube 검색에 실패했습니다.")
      search_data = search_resp.json()

      id_title_map: Dict[str, str] = {}
      for item in search_data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        title = item.get("snippet", {}).get("title", "")
        if not video_id or not title:
          continue
        if not _title_matches(title, trimmed, normalized_syllables):
          continue
        if normalized_allowed_words and not _has_allowed_word(title, normalized_allowed_words):
          continue
        id_title_map[video_id] = title

      if id_title_map:
        videos_params = {
          "part": "contentDetails,statistics",
          "id": ",".join(id_title_map.keys()),
          "key": api_key,
        }
        videos_resp = client.get(f"{YOUTUBE_API_BASE}/videos", params=videos_params)
        if videos_resp.status_code >= 400:
          raise HTTPException(status_code=502, detail="YouTube 영상을 불러오지 못했습니다.")
        videos_data = videos_resp.json()

        for item in videos_data.get("items", []):
          video_id = item.get("id")
          if not video_id:
            continue

          duration = _parse_iso8601_duration(item.get("contentDetails", {}).get("duration", ""))
          if duration < MIN_DURATION_SECONDS or duration > MAX_DURATION_SECONDS:
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

      page_token = search_data.get("nextPageToken")
      pages_checked += 1
      if not page_token:
        break

  if not best_video:
    raise HTTPException(status_code=404, detail="조건에 맞는 영상이 없습니다.")

  return best_video
