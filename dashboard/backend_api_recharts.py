"""
Recipe Dashboard API (Monthly Data Only)
프론트엔드(Recharts)에서 사용할 월간 요리 통계 JSON 데이터를 반환한다.

How to run:
  - python frontend_api_recharts.py
  - or: uvicorn frontend_api_recharts:app --reload

Endpoints:
   - GET /me/stats/progress           → 주별 요리 목표 달성률 데이터
   - GET /me/stats/recipe-logs-level  → 주별 난이도별 조리 비율 데이터
   - GET /me/stats/recipe-logs-category → 카테고리 비율 데이터
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Dict, List
import calendar
import os
import pymysql
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# ======================================================
# CONFIG
# ======================================================
load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

# ======================================================
# DB CONNECTION
# ======================================================
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

# ======================================================
# DATE UTILITIES
# ======================================================
def get_month_range(selected_date: datetime):
    year, month = selected_date.year, selected_date.month
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    return first_day, last_day

def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

# ======================================================
# SERVICES
# ======================================================
def fetch_user_goal(db, user_id: str) -> int:
    """사용자의 주간 목표 요리 횟수를 조회하고 기본값(3)을 보정한다."""
    with db.cursor() as cur:
        cur.execute("SELECT goal FROM user_info WHERE id=%s", (user_id,))
        row = cur.fetchone()
    return (row and row.get("goal")) or 3


def fetch_progress(db, user_id: str, start_date: date, end_date: date, weekly_goal: int):
    """월 단위로 요리 기록을 집계해 주차별 달성 횟수와 목표 대비 비율 반환."""
    sql = """
      SELECT DATE(selected_date) AS d, COUNT(*) AS c
      FROM selected_recipe
      WHERE id=%s AND selected_date >= %s AND selected_date < %s AND action=1
      GROUP BY DATE(selected_date)
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, start_date, end_date + timedelta(days=1)))
        rows = cur.fetchall()

    day_counts = {r["d"]: int(r["c"]) for r in rows}
    total = sum(day_counts.values())

    weekly_map: Dict[date, int] = {}
    day = start_date
    while day <= end_date:
        w = _week_start(day)
        weekly_map[w] = weekly_map.get(w, 0) + day_counts.get(day, 0)
        day += timedelta(days=1)

    weekly = [
        {"week_start": w, "count": c, "weekly_goal": round(c / max(weekly_goal, 1), 2)}
        for w, c in sorted(weekly_map.items())
    ]
    monthly_goal = round(total / (weekly_goal * len(weekly or [1])), 2)
    return {"weekly": weekly, "monthly_goal": monthly_goal}


def fetch_recipe_level_ratio(db, user_id: str, start_date: date, end_date: date):
    """월간 데이터를 주차별로 나눠 난이도별 조리 횟수와 비율을 계산."""
    weekly_data = []
    day = start_date
    week_idx = 1
    while day <= end_date:
        week_start, week_end = day, min(day + timedelta(days=6), end_date)
        sql = """
          SELECT r.level_nm AS level, COUNT(*) AS cnt
          FROM selected_recipe s
          JOIN recipe r ON s.recipe_id = r.recipe_id
          WHERE s.id=%s AND s.selected_date >= %s AND s.selected_date < %s AND s.action=1
          GROUP BY r.level_nm
        """
        with db.cursor() as cur:
            cur.execute(sql, (user_id, week_start, week_end + timedelta(days=1)))
            rows = cur.fetchall()

        total = sum(r["cnt"] for r in rows) or 0
        weekly_data.append({"week_idx": week_idx, "total": total, "levels": rows})
        day = week_end + timedelta(days=1)
        week_idx += 1
    return {"weeks": weekly_data}


def fetch_recipe_category_ratio(db, user_id: str, start_date: date, end_date: date):
    """월간 요리 기록을 카테고리로 그룹화."""
    sql = """
      SELECT r.ty_nm AS category, COUNT(*) AS cnt
      FROM selected_recipe s
      JOIN recipe r ON s.recipe_id = r.recipe_id
      WHERE s.id=%s AND s.selected_date >= %s AND s.selected_date < %s AND s.action=1
      GROUP BY r.ty_nm
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, start_date, end_date + timedelta(days=1)))
        rows = cur.fetchall()
    total = sum(r["cnt"] for r in rows) or 1
    return {"categories": [{"label": r["category"] or "기타", "count": r["cnt"], "ratio": round(r["cnt"]/total, 3)} for r in rows]}

# ======================================================
# FASTAPI APP
# ======================================================
app = FastAPI(title="Recipe Dashboard API (Monthly JSON)", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# JSON ENDPOINTS (Recharts용)
# ======================================================

@app.get("/me/stats/progress")
def get_progress(user_id: str, selected_date: date = Query(...), db=Depends(get_db)):
    """① 주별 요리 목표 달성률 (라인차트용)"""
    selected_dt = datetime.combine(selected_date, datetime.min.time())
    start_date, end_date = get_month_range(selected_dt)
    goal = fetch_user_goal(db, user_id)
    progress = fetch_progress(db, user_id, start_date, end_date, weekly_goal=goal)
    week_labels = ["첫째 주", "둘째 주", "셋째 주", "넷째 주", "다섯째 주"]

    data = []
    for i, w in enumerate(progress["weekly"]):
        data.append({
            "week": week_labels[i] if i < len(week_labels) else f"{i+1}주차",
            "rate": round(w["weekly_goal"] * 100, 1)
        })

    return {"month_goal": round(progress["monthly_goal"] * 100, 1), "weeks": data}


@app.get("/me/stats/recipe-logs-level")
def get_level_ratio(user_id: str, selected_date: date = Query(...), db=Depends(get_db)):
    """② 주별 난이도별 조리 비율 (스택바용)"""
    selected_dt = datetime.combine(selected_date, datetime.min.time())
    start_date, end_date = get_month_range(selected_dt)
    levels = fetch_recipe_level_ratio(db, user_id, start_date, end_date)
    week_labels = ["첫째 주", "둘째 주", "셋째 주", "넷째 주", "다섯째 주"]

    result = []
    for i, week in enumerate(levels["weeks"]):
        week_label = week_labels[i] if i < len(week_labels) else f"{i+1}주차"
        total = week.get("total", 0)
        high = low = 0
        for l in week.get("levels", []):
            if l["level"] == "상":
                high = l["cnt"]
            elif l["level"] == "하":
                low = l["cnt"]
        result.append({"week": week_label, "levelHigh": high, "levelLow": low, "total": total})

    return {"weeks": result}


@app.get("/me/stats/recipe-logs-category")
def get_category_ratio(user_id: str, selected_date: date = Query(...), db=Depends(get_db)):
    """③ 카테고리 비율 (파이차트용)"""
    selected_dt = datetime.combine(selected_date, datetime.min.time())
    start_date, end_date = get_month_range(selected_dt)
    categories = fetch_recipe_category_ratio(db, user_id, start_date, end_date)
    return categories


