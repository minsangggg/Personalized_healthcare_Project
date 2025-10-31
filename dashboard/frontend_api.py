"""
Frontend API entrypoint consolidated into a single file.
Includes config, DB helpers, services, and endpoints — no app.* imports.

How to run:
  - python frontend_api.py
  - or: uvicorn frontend_api:app --reload

Available endpoints (query via params):
  - GET /              (health)
  - GET /test-db       (DB health)
  - GET /me/stats/progress?user_id=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  - GET /me/stats/recipe-logs-level?user_id=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  - GET /me/stats/recipe-logs-category?user_id=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  - GET /me/recommendations?user_id=...&limit=3
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Tuple, Dict, List

import os
from dotenv import load_dotenv
import pymysql

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# =========================
# Config (inline of app/config.py)
# =========================
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

# =========================
# DB (inline of app/db.py)
# =========================
def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset=DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def get_db():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()

# =========================
# Services (inline of app/services/*.py)
# =========================
def _parse_dates(start_date: Optional[date], end_date: Optional[date]) -> Tuple[datetime, datetime]:
    if not start_date and not end_date:
        end_dt = datetime.combine(date.today(), datetime.min.time())
        start_dt = end_dt - timedelta(days=27)
    elif start_date and not end_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(date.today(), datetime.min.time())
    elif not start_date and end_date:
        end_dt = datetime.combine(end_date, datetime.min.time())
        start_dt = end_dt - timedelta(days=27)
    else:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())
    return start_dt, end_dt + timedelta(days=1)


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def fetch_user_goal(db, user_id: str) -> int:
    with db.cursor() as cur:
        cur.execute("SELECT goal FROM user_info WHERE id=%s", (user_id,))
        row = cur.fetchone()
    return (row and row.get("goal")) or 3


def fetch_progress(db, user_id: str, start_date: Optional[date], end_date: Optional[date], weekly_goal: int):
    start_dt, end_dt_inc = _parse_dates(start_date, end_date)

    sql = """
      SELECT DATE(selected_date) AS d, COUNT(*) AS c
      FROM selected_recipe
      WHERE id = %s AND selected_date >= %s AND selected_date < %s
      GROUP BY DATE(selected_date) ORDER BY d
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, start_dt, end_dt_inc))
        rows = cur.fetchall()

    day_counts = {r["d"]: int(r["c"]) for r in rows}
    total = sum(day_counts.values())

    ts: List[dict] = []
    day = start_dt.date()
    end_excl = (end_dt_inc - timedelta(days=1)).date()
    while day <= end_excl:
        ts.append({"date": day, "count": day_counts.get(day, 0)})
        day += timedelta(days=1)

    weekly_map: Dict[date, int] = {}
    for t in ts:
        w = _week_start(t["date"])
        weekly_map[w] = weekly_map.get(w, 0) + t["count"]

    weekly = [{"week_start": w, "count": c, "attainment": min(c/max(weekly_goal,1), 1.0)}
              for w, c in sorted(weekly_map.items())]
    goal_attainment = (sum(w["attainment"] for w in weekly)/len(weekly)) if weekly else 0.0

    return {
        "period_start": start_dt.date(),
        "period_end": end_excl,
        "total": total,
        "timeseries": ts,
        "weekly": weekly,
        "goal_attainment": goal_attainment
    }


def fetch_recipe_level_ratio(db, user_id: str, start_date: Optional[date], end_date: Optional[date]):
    start_dt, end_dt_inc = _parse_dates(start_date, end_date)
    sql = """
      SELECT r.level_nm AS level, COUNT(*) AS cnt
      FROM selected_recipe s
      JOIN recipe r ON s.recipe_id = r.recipe_id
      WHERE s.id = %s AND s.selected_date >= %s AND s.selected_date < %s
      GROUP BY r.level_nm
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, start_dt, end_dt_inc))
        rows = cur.fetchall()

    total = sum([r["cnt"] for r in rows]) or 1
    data = [
        {"label": r["level"] or "미정", "count": int(r["cnt"]), "ratio": round(r["cnt"]/total, 3)}
        for r in rows
    ]
    return {"user_id": user_id, "total": total, "levels": data}


def fetch_recipe_category_ratio(db, user_id: str, start_date: Optional[date], end_date: Optional[date]):
    start_dt, end_dt_inc = _parse_dates(start_date, end_date)
    sql = """
      SELECT r.ty_nm AS category, COUNT(*) AS cnt
      FROM selected_recipe s
      JOIN recipe r ON s.recipe_id = r.recipe_id
      WHERE s.id = %s AND s.selected_date >= %s AND s.selected_date < %s
      GROUP BY r.ty_nm
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, start_dt, end_dt_inc))
        rows = cur.fetchall()

    total = sum([r["cnt"] for r in rows]) or 1
    data = [
        {"label": r["category"] or "기타", "count": int(r["cnt"]), "ratio": round(r["cnt"]/total, 3)}
        for r in rows
    ]
    return {"user_id": user_id, "total": total, "categories": data}


app = FastAPI(title="Recipe Dashboard API (Single File)", version="1.0.0")

# CORS for frontend integration (tighten origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/me/stats/progress")
def progress(
    user_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db = Depends(get_db),
):
    goal = fetch_user_goal(db, user_id)
    data = fetch_progress(db, user_id, start_date, end_date, weekly_goal=goal)
    return {
        "user_id": user_id,
        "target_per_week": goal,
        "period_start": data["period_start"],
        "period_end": data["period_end"],
        "total_cooks": data["total"],
        "goal_attainment": data["goal_attainment"],
        "timeseries": data["timeseries"],
        "weekly": data["weekly"],
    }


@app.get("/me/stats/recipe-logs-level", summary="선택한 레시피의 난이도 비율")
def recipe_logs_level(
    user_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db = Depends(get_db),
):
    return fetch_recipe_level_ratio(db, user_id, start_date, end_date)


@app.get("/me/stats/recipe-logs-category", summary="선택한 레시피의 요리 분류 비율")
def recipe_logs_category(
    user_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db = Depends(get_db),
):
    return fetch_recipe_category_ratio(db, user_id, start_date, end_date)


@app.get("/me/recommendations")
def get_recommendations(
    user_id: Optional[str] = Query(
        None, description="사용자 ID (로그인 안된 경우 비워둘 수 있음)",
    ),
    limit: int = Query(
        3, ge=1, le=5, description="추천 레시피 개수 (기본 3개)",
    ),
):
    """
    검색해온 레시피를 기반으로 LLM이 최대 limit개 레시피를 정리/추천 (JSON 응답)
    recommend_core4.recommend_json() 결과를 그대로 내려주도록 시도합니다.
    모듈이 없으면 501을 반환합니다.
    """
    try:
        # Lazy import so app can start even if module is optional
        from recommend_core4 import recommend_json  # type: ignore
    except Exception as e:  # Module not available
        raise HTTPException(status_code=501, detail="recommend_core4 모듈을 찾을 수 없습니다")

    try:
        result = recommend_json(user_id=user_id, limit=limit)
        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



