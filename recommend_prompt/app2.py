# app2.py
import os
from typing import Optional

from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from dotenv import load_dotenv
from recommend_core2 import recommend_json

load_dotenv()

app = FastAPI(title="CookUS API v2", version="0.2.0")

# index2.html 이 같은 폴더에 있다고 가정
templates = Jinja2Templates(directory=".")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # 개발 중 전체 허용
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

# 프론트에서 호출하는 추천 API
@app.get("/me/recommendations")
def get_recommendations(
    request: Request,
    response: Response,
    userId: Optional[str] = None,
    limit: int = 3,
    excludeIds: Optional[str] = Query(None, description="콤마구분: 6812345,6900011"),
):
    """
    동작 규칙
    - userId 파라미터가 있으면 그 사용자로 추천
    - userId 가 없고 쿠키(last_user_id)가 있으면 그 사용자로 추천
    - 둘 다 없으면 랜덤 사용자로 추천하고, 그 userId를 쿠키에 저장
    - excludeIds가 있으면 해당 recipe_id는 제외하고 다시 추천
    """
    exclude = None
    if excludeIds:
        exclude = [int(x) for x in excludeIds.split(",") if x.strip().isdigit()]
    # return recommend_json(userId, limit=limit, exclude_ids=exclude)
    
    # 2) userId 결정: 쿼리스트링 > 쿠키 > None(랜덤)
    uid_from_cookie = request.cookies.get("last_user_id")
    uid = userId or uid_from_cookie or None
    
    # 3) 추천 실행
    data = recommend_json(uid, limit=limit, exclude_ids=exclude)
    
    # 4) 응답의 userId를 쿠키로 저장(다음 호출에서 같은 사용자 유지)
    if isinstance(data, dict) and data.get("userId"):
        response.set_cookie(
            key="last_user_id",
            value=str(data["userId"]),
            max_age=7 * 24 * 3600,   # 7일
            httponly=False,          # JS에서 읽을 필요 없으면 True 가능
            samesite="lax",
            path="/",
        )

    return data


# (옵션) 다른 사용자로 새로 시작하고 싶을 때 호출
@app.post("/me/recommendations/new-user")
def new_user_recommendations(response: Response, limit: int = 3):
    """
    강제로 랜덤 사용자로 새 추천 시작(쿠키 갱신).
    프론트에서 '다른 사람으로 추천받기' 버튼 등에 연결 가능.
    """
    data = recommend_json(None, limit=limit, exclude_ids=None)
    if isinstance(data, dict) and data.get("userId"):
        response.set_cookie(
            key="last_user_id",
            value=str(data["userId"]),
            max_age=7 * 24 * 3600,
            httponly=False,
            samesite="lax",
            path="/",
        )
    return data


# 루트로 접속 시 index2.html 렌더
@app.get("/", response_class=HTMLResponse)
async def serve_test_html(request: Request):
    return templates.TemplateResponse("index2.html", {"request": request})
