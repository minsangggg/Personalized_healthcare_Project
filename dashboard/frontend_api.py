"""
Recipe Dashboard API (Monthly Only)
Frontend에서 사용자별 월간 요리 통계(진행률, 난이도 비율, 카테고리 비율)를 조회하기 위한 단일 엔드포인트 서버.

How to run:
  - python frontend_api.py
  - or: uvicorn frontend_api:app --reload

Endpoints:
   - GET /
      → 서버 상태 확인
   - GET /test-db
      → DB 연결 테스트
   - GET /me/stats/progress?user_id=...&selected_date=YYYY-MM-DD
      → 사용자의 월간 요리 진행 현황
   - GET /me/stats/recipe-logs-level?user_id=...&selected_date=YYYY-MM-DD
      → 해당 달의 레시피 난이도 비율 (주차별)
   - GET /me/stats/recipe-logs-category?user_id=...&selected_date=YYYY-MM-DD
      → 해당 달의 레시피 카테고리 비율
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Dict, List
import calendar
import os
import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import pandas as pd
import base64
import io

# ======================================================
# CONFIGURATION
# ======================================================
load_dotenv()
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

# ======================================================
# 🧩 DATABASE CONNECTION
# ======================================================
def get_conn():
    """MariaDB / MySQL 연결 객체 생성"""
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
    """FastAPI Dependency로 DB Connection을 관리"""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()

# ======================================================
# 🗓 DATE UTILITIES (날짜 계산 함수)
# ======================================================
def get_month_range(selected_date: datetime):
    """해당 달의 1일 ~ 말일"""
    year = selected_date.year
    month = selected_date.month
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    return first_day, last_day

def _week_start(d: date) -> date:
    """내부용: 날짜가 속한 주의 월요일 반환"""
    return d - timedelta(days=d.weekday())

# ======================================================
# SERVICES (데이터 조회 / 집계)
# ======================================================
def fetch_user_goal(db, user_id: str) -> int:
    """사용자의 주간 목표 요리 횟수 조회"""
    with db.cursor() as cur:
        cur.execute("SELECT goal FROM user_info WHERE id=%s", (user_id,))
        row = cur.fetchone()
    return (row and row.get("goal")) or 3


def fetch_progress(db, user_id: str, start_date: date, end_date: date, weekly_goal: int):
    """
    월간 요리 진행 통계
    - selected_recipe.action = 1 만 집계
    - 주차별 합계 및 달성률(상한 없음) 포함
    """
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt_inc = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

    sql = """
      SELECT DATE(selected_date) AS d, COUNT(*) AS c
      FROM selected_recipe
      WHERE id = %s 
        AND selected_date >= %s 
        AND selected_date < %s
        AND action = 1
      GROUP BY DATE(selected_date)
      ORDER BY d
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, start_dt, end_dt_inc))
        rows = cur.fetchall()

    # 일자별 요리 횟수
    day_counts = {r["d"]: int(r["c"]) for r in rows}
    total = sum(day_counts.values())

    # 주별 합산
    weekly_map: Dict[date, int] = {}
    day = start_date
    while day <= end_date:
        w = _week_start(day)
        weekly_map[w] = weekly_map.get(w, 0) + day_counts.get(day, 0)
        day += timedelta(days=1)

    # 주별 달성률 계산
    weekly = [
        {"week_start": w, "count": c, "weekly_goal": round(c / max(weekly_goal, 1), 2)}
        for w, c in sorted(weekly_map.items())
    ]

    # 월간 달성률 계산
    num_weeks = len(weekly) or 1
    monthly_goal = round(total / (weekly_goal * num_weeks), 2)

    return {
        "period_start": start_date,
        "period_end": end_date,
        "total": total,
        "weekly": weekly,
        "monthly_goal": monthly_goal,
    }


def fetch_recipe_level_ratio(db, user_id: str, start_date: date, end_date: date):
    """
    📅 월간 레시피 난이도 비율 조회 (주차별 버전)
    - 입력된 달을 주차 단위로 분할하여 각 주차별 난이도 비율 계산
    - week_label: "10-1", "10-2" 형식으로 표시
    """
    weekly_data = []
    day = start_date
    week_idx = 1

    while day <= end_date:
        week_start = day
        week_end = min(week_start + timedelta(days=6), end_date)

        start_dt = datetime.combine(week_start, datetime.min.time())
        end_dt_inc = datetime.combine(week_end, datetime.min.time()) + timedelta(days=1)

        sql = """
          SELECT r.level_nm AS level, COUNT(*) AS cnt
          FROM selected_recipe s
          JOIN recipe r ON s.recipe_id = r.recipe_id
          WHERE s.id = %s 
            AND s.selected_date >= %s 
            AND s.selected_date < %s
            AND s.action = 1
          GROUP BY r.level_nm
        """
        with db.cursor() as cur:
            cur.execute(sql, (user_id, start_dt, end_dt_inc))
            rows = cur.fetchall()

        total = sum([r["cnt"] for r in rows]) or 0
        levels = []
        if total > 0:
            levels = [
                {"label": r["level"] or "미정", "count": int(r["cnt"]), "ratio": round(r["cnt"] / total, 2)}
                for r in rows
            ]

        weekly_data.append({
            "week_label": f"{start_date.month}-{week_idx}",
            "total": total,
            "levels": levels,
        })

        day = week_end + timedelta(days=1)
        week_idx += 1

    return {
        "user_id": user_id,
        "period_start": start_date,
        "period_end": end_date,
        "weeks": weekly_data,
    }


def fetch_recipe_category_ratio(db, user_id: str, start_date: date, end_date: date):
    """🍳 월간 요리 카테고리 비율 조회"""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt_inc = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

    sql = """
      SELECT r.ty_nm AS category, COUNT(*) AS cnt
      FROM selected_recipe s
      JOIN recipe r ON s.recipe_id = r.recipe_id
      WHERE s.id = %s 
        AND s.selected_date >= %s 
        AND s.selected_date < %s
        AND s.action = 1
      GROUP BY r.ty_nm
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, start_dt, end_dt_inc))
        rows = cur.fetchall()

    total = sum([r["cnt"] for r in rows]) or 1
    return {
        "user_id": user_id,
        "period_start": start_date,
        "period_end": end_date,
        "categories": [
            {"label": r["category"] or "기타", "count": int(r["cnt"]), "ratio": round(r["cnt"]/total, 3)}
            for r in rows
        ],
    }

# ======================================================
# FASTAPI APPLICATION
# ======================================================
app = FastAPI(title="Recipe Dashboard API (Monthly Only)", version="3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 운영 시 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🌐 ENDPOINTS
# ======================================================
@app.get("/")
def health():
    """서버 상태 확인용"""
    return {"status": "ok"}


@app.get("/test-db")
def test_db(db = Depends(get_db)):
    """DB 연결 테스트용"""
    with db.cursor() as cur:
        cur.execute("SELECT 1 AS ok")
        return cur.fetchone()


@app.get("/me/stats/progress")
def progress(
    user_id: str,
    selected_date: date = Query(..., description="기준 날짜 (YYYY-MM-DD)"),
    db = Depends(get_db),
):
    """사용자 월간 요리 진행률 조회"""
    selected_dt = datetime.combine(selected_date, datetime.min.time())
    start_date, end_date = get_month_range(selected_dt)
    goal = fetch_user_goal(db, user_id)
    data = fetch_progress(db, user_id, start_date, end_date, weekly_goal=goal)
    return {
        "user_id": user_id,
        "mode": "month",
        "target_per_week": goal,
        **data,
    }


@app.get("/me/stats/recipe-logs-level")
def recipe_logs_level(
    user_id: str,
    selected_date: date = Query(..., description="기준 날짜 (YYYY-MM-DD)"),
    db = Depends(get_db),
):
    """해당 달의 레시피 난이도 비율 (주차별)"""
    selected_dt = datetime.combine(selected_date, datetime.min.time())
    start_date, end_date = get_month_range(selected_dt)
    return fetch_recipe_level_ratio(db, user_id, start_date, end_date)


@app.get("/me/stats/recipe-logs-category")
def recipe_logs_category(
    user_id: str,
    selected_date: date = Query(..., description="기준 날짜 (YYYY-MM-DD)"),
    db = Depends(get_db),
):
    """해당 달의 요리 카테고리 비율"""
    selected_dt = datetime.combine(selected_date, datetime.min.time())
    start_date, end_date = get_month_range(selected_dt)
    return fetch_recipe_category_ratio(db, user_id, start_date, end_date)



import matplotlib
matplotlib.use("Agg")  # ✅ GUI 백엔드 비활성화

import io
import base64
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import matplotlib.font_manager as fm
from datetime import date, datetime
from fastapi import Query, Depends
from fastapi.testclient import TestClient

# ✅ 한글 폰트 설정
font_path = "C:/Windows/Fonts/malgun.ttf"
font_name = fm.FontProperties(fname=font_path).get_name()
plt.rcParams["font.family"] = font_name
plt.rcParams["axes.unicode_minus"] = False  # 마이너스 깨짐 방지

# ✅ 색상 테마 정의
COLORS = {
    "cream": "#FFE7B8",   # 밝은 크림색 (상단 바/하이라이트)
    "orange": "#F5B14C",  # 포인트 컬러 (라인, 주요 텍스트)
    "brown": "#A5672B",   # 메인 텍스트 / 구분선
    "beige": "#FFF6E5",   # 배경
}

# ✅ Seaborn 전역 테마 적용
sns.set_theme(
    style="whitegrid",
    rc={
        "axes.facecolor": COLORS["beige"],
        "figure.facecolor": COLORS["beige"],
        "axes.edgecolor": COLORS["brown"],
        "grid.color": "#f2e0ba",
        "font.family": font_name,
        "font.weight": "bold"
    }
)


@app.get("/me/stats/visualize")
def visualize_dashboard(user_id: str, selected_date: date = Query(...), db=Depends(get_db)):
    """CookUS 월간 시각화"""
    selected_dt = datetime.combine(selected_date, datetime.min.time())
    start_date, end_date = get_month_range(selected_dt)
    goal = fetch_user_goal(db, user_id)
    month_label = f"{selected_date.month}월"

    # 데이터 조회
    progress = fetch_progress(db, user_id, start_date, end_date, weekly_goal=goal)
    levels = fetch_recipe_level_ratio(db, user_id, start_date, end_date)
    categories = fetch_recipe_category_ratio(db, user_id, start_date, end_date)

    # igure 생성
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    fig.suptitle(
        f"CookUS {month_label} 월간 대시보드",
        fontsize=20,
        color=COLORS["brown"],
        fontweight="bold"
    )

    week_labels = ["첫째 주", "둘째 주", "셋째 주", "넷째 주", "다섯째 주"]

    # --------------------------------------------------
    # ① 주별 요리 목표 달성률 (Line Chart)
    # --------------------------------------------------
    df_progress = pd.DataFrame(progress["weekly"])
    df_progress["week_label"] = week_labels[:len(df_progress)]
    df_progress["weekly_goal_percent"] = df_progress["weekly_goal"] * 100
    df_progress["plot_value"] = df_progress["weekly_goal_percent"].apply(lambda v: v if v > 0 else 0.2)

    sns.lineplot(
        data=df_progress,
        x="week_label",
        y="plot_value",
        marker="o",
        linewidth=3.5,
        color=COLORS["orange"],
        ax=axes[0]
    )

    axes[0].set_title(f"{month_label} 요리 목표 달성률 (%)", fontsize=14, color=COLORS["brown"], fontweight="bold")
    axes[0].set_ylabel("달성률 (%)", fontsize=11, color=COLORS["brown"], fontweight="bold")
    axes[0].set_xlabel("")        # ✅ 축 제목도 제거
    ymax = max(df_progress["weekly_goal_percent"].max() * 1.1, 10)
    axes[0].set_ylim(0, ymax)
    axes[0].set_xticks(range(len(df_progress)))
    axes[0].set_xticklabels(df_progress["week_label"], fontweight="bold", color=COLORS["brown"])

    # 🎯 점 위의 퍼센트 (0%는 표시하지 않음)
    for i, val in enumerate(df_progress["weekly_goal_percent"]):
        if val > 0:
            axes[0].text(
                i,
                df_progress.loc[i, "plot_value"] + ymax * 0.02,
                f"{val:.0f}%",
                ha="center",
                color=COLORS["brown"],
                fontsize=10,
                fontweight="bold"
            )

    axes[0].text(
        0.9,
        0.93,
        f"Monthly Goal: {progress['monthly_goal']*100:.1f}%",
        transform=axes[0].transAxes,
        fontsize=11,
        color=COLORS["orange"],
        ha="right",
        fontweight="bold"
    )

    # --------------------------------------------------
    # ② 주별 난이도별 조리 비율 (Stacked Bar)
    # --------------------------------------------------
    level_dict = {}
    for i, week in enumerate(levels["weeks"]):
        week_label = week_labels[i] if i < len(week_labels) else f"{i+1}주차"
        total_count = week.get("total", 0)
        level_dict[week_label] = {"상": 0, "하": 0, "total": total_count}
        for l in week.get("levels", []):
            if l["label"] in ["상", "하"]:
                level_dict[week_label][l["label"]] = l["count"]

    df_levels = pd.DataFrame(level_dict).T.reset_index().rename(columns={"index": "주차"})
    for col in ["상", "하", "total"]:
        if col not in df_levels:
            df_levels[col] = 0

    all_weeks = df_progress["week_label"].tolist()
    df_levels = df_levels.set_index("주차").reindex(all_weeks, fill_value=0).reset_index()
    df_levels["상비율"] = df_levels["상"] / df_levels["total"].replace(0, 1)
    df_levels["하비율"] = df_levels["하"] / df_levels["total"].replace(0, 1)

    # ✅ 막대그래프 색상 테마 통일
    axes[1].bar(df_levels["주차"], df_levels["total"] * df_levels["하비율"], color=COLORS["brown"], label="하")
    axes[1].bar(
        df_levels["주차"],
        df_levels["total"] * df_levels["상비율"],
        bottom=df_levels["total"] * df_levels["하비율"],
        color=COLORS["cream"],
        label="상"
    )

    for i, row in df_levels.iterrows():
        total = row["total"]
        if total > 0:
            if row["하비율"] > 0:
                axes[1].text(
                    i,
                    total * row["하비율"] / 2,
                    f"{row['하비율']*100:.0f}%",
                    ha="center",
                    va="center",
                    color=COLORS["beige"],
                    fontsize=10,
                    fontweight="bold"
                )
            if row["상비율"] > 0:
                axes[1].text(
                    i,
                    total * (row["하비율"] + row["상비율"]/2),
                    f"{row['상비율']*100:.0f}%",
                    ha="center",
                    va="center",
                    color=COLORS["brown"],
                    fontsize=10,
                    fontweight="bold"
                )

    axes[1].set_title(f"{month_label} 주별 난이도별 조리 비율", fontsize=14, color=COLORS["brown"], fontweight="bold")
    axes[1].set_ylabel("조리 횟수", fontsize=11, color=COLORS["brown"], fontweight="bold")
    axes[1].set_xticklabels(df_levels["주차"], fontweight="bold", color=COLORS["brown"])
    axes[1].set_ylim(0, (df_levels["total"].max() or 1) * 1.1)
    axes[1].yaxis.set_major_locator(plt.MaxNLocator(integer=True))

    # --------------------------------------------------
    # ③ 카테고리 비율 (Pie)
    # --------------------------------------------------
    df_cat = pd.DataFrame(categories.get("categories", []))
    if not df_cat.empty:
        df_cat = df_cat.sort_values("count", ascending=False).head(5)
        wedges, texts, autotexts = axes[2].pie(
            df_cat["ratio"],
            labels=df_cat["label"],
            autopct=lambda p: f"{p:.0f}%" if p > 0 else "",
            startangle=110,
            colors=[COLORS["orange"], COLORS["cream"], COLORS["brown"], "#d4a373", "#e6ccb2"],
            pctdistance=0.75,
            textprops={"color": COLORS["brown"], "fontsize": 11, "fontweight": "bold"}
        )
        for t in texts + autotexts:
            t.set_fontsize(11)
        axes[2].set_title(f"{month_label} 카테고리 비율", fontsize=14, color=COLORS["brown"], fontweight="bold")
    else:
        axes[2].text(0.5, 0.5, "데이터 없음", ha="center", va="center", fontsize=14, color=COLORS["brown"], transform=axes[2].transAxes)
        axes[2].set_axis_off()

    # --------------------------------------------------
    # 🔧 전체 레이아웃 마무리
    # --------------------------------------------------
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("ascii")

    return {"image_base64": img_b64}


# ======================================================
# 🧪 로컬 테스트
# ======================================================
if __name__ == "__main__":
    import webbrowser

    app_client = TestClient(app)
    user_id = "0cuhn2uy"
    selected_date = "2025-10-01"

    response = app_client.get(f"/me/stats/visualize?user_id={user_id}&selected_date={selected_date}")
    result = response.json()

    image_data = base64.b64decode(result["image_base64"])
    with open("dashboard_preview.png", "wb") as f:
        f.write(image_data)

    print("✅ 그래프 생성 완료 → dashboard_preview.png")
    webbrowser.open("dashboard_preview.png")
