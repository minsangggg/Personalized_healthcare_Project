"""
Recipe Dashboard API (Monthly Visuals)
프론트엔드 대시보드에서 사용할 월간 요리 통계 시각화 이미지를 생성한다.

How to run:
  - python frontend_api_final.py
  - or: uvicorn frontend_api_final:app --reload

Endpoints:
   - GET /                               → 서버 상태 확인
   - GET /me/stats/progress_visual       → 주별 요리 목표 달성률 라인 차트 (Base64)
   - GET /me/stats/recipe-logs-level_visual  → 주별 난이도 스택 바 차트 (Base64)
   - GET /me/stats/recipe-logs-category_visual → 카테고리 비율 파이 차트 (Base64)
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Dict
import calendar
import os
import io
import base64
import pymysql
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
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
# 🗓 DATE UTILITIES
# ======================================================
def get_month_range(selected_date: datetime):
    year, month = selected_date.year, selected_date.month
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    return first_day, last_day

def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

# ======================================================
# SERVICES — 그래프용 집계 로직
# ======================================================
def fetch_user_goal(db, user_id: str) -> int:
    """사용자의 주간 목표 요리 횟수를 조회하고 기본값(3)을 보정한다."""
    with db.cursor() as cur:
        cur.execute("SELECT goal FROM user_info WHERE id=%s", (user_id,))
        row = cur.fetchone()
    return (row and row.get("goal")) or 3

def fetch_progress(db, user_id: str, start_date: date, end_date: date, weekly_goal: int):
    """
    월 단위로 요리 기록을 집계해 주차별 달성 횟수와 목표 대비 비율을 반환한다.
    weekly_goal 기준으로 주차별 달성률을 계산하고 월간 평균 달성률을 함께 제공한다.
    """
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
    """월간 데이터를 주차별로 나눠 난이도별 조리 횟수와 비율을 계산한다."""
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
        levels = [{"label": r["level"] or "미정", "count": r["cnt"], "ratio": round(r["cnt"]/total, 2)} for r in rows] if total else []
        weekly_data.append({"week_label": f"{start_date.month}-{week_idx}", "total": total, "levels": levels})
        day = week_end + timedelta(days=1)
        week_idx += 1
    return {"weeks": weekly_data}

def fetch_recipe_category_ratio(db, user_id: str, start_date: date, end_date: date):
    """월간 요리 기록을 카테고리로 그룹화해 횟수와 비율을 계산한다."""
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
# STYLE CONFIG — 원래 폰트 & 전체 Bold
# ======================================================
font_path = "C:/Windows/Fonts/malgun.ttf"
font_name = fm.FontProperties(fname=font_path).get_name()
plt.rcParams["font.family"] = font_name
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.weight"] = "bold"

COLORS = {
    "cream": "#FFE7B8",
    "orange": "#F5B14C",
    "brown": "#A5672B",
    "beige": "#FFF6E5",
    "black": "#000000",
}

sns.set_theme(
    style="whitegrid",
    rc={
        "axes.facecolor": COLORS["beige"],
        "figure.facecolor": COLORS["beige"],
        "font.family": font_name,
        "font.weight": "bold",
    }
)

# ======================================================
# FASTAPI APP
# ======================================================
app = FastAPI(title="Recipe Dashboard API (Monthly Only)", version="3.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# VISUAL ENDPOINTS
# ======================================================
@app.get("/me/stats/progress-visual")
def visualize_progress(user_id: str, selected_date: date = Query(...), db=Depends(get_db)):
    """① 주별 요리 목표 달성률 (Line Chart)"""
    selected_dt = datetime.combine(selected_date, datetime.min.time())
    start_date, end_date = get_month_range(selected_dt)
    goal = fetch_user_goal(db, user_id)
    progress = fetch_progress(db, user_id, start_date, end_date, weekly_goal=goal)
    month_label = f"{selected_date.month}월"
    week_labels = ["첫째 주", "둘째 주", "셋째 주", "넷째 주", "다섯째 주"]

    # ✅ 최신 구조 유지 (plot_value, 0% 숨김 등)
    df_progress = pd.DataFrame(progress["weekly"])
    df_progress["week_label"] = week_labels[:len(df_progress)]
    df_progress["weekly_goal_percent"] = df_progress["weekly_goal"] * 100
    df_progress["plot_value"] = df_progress["weekly_goal_percent"].apply(lambda v: v if v > 0 else 0.2)

    fig, ax = plt.subplots(figsize=(7, 5))
    sns.lineplot(
        data=df_progress,
        x="week_label",
        y="plot_value",
        marker="o",
        linewidth=3.5,
        color=COLORS["orange"],
        ax=ax
    )

    ax.set_title(f"{month_label} 요리 목표 달성률 (%)", fontsize=14, color=COLORS["brown"], fontweight="bold")
    ax.set_ylabel("달성률 (%)", fontsize=11, color=COLORS["brown"], fontweight="bold")
    ax.set_xlabel("")
    ymax = max(df_progress["weekly_goal_percent"].max() * 1.1, 10)
    ax.set_ylim(0, ymax)
    ax.set_xticks(range(len(df_progress)))
    ax.set_xticklabels(df_progress["week_label"], fontweight="bold", color=COLORS["brown"])

    # 점 위의 퍼센트 (0%는 표시 안 함)
    for i, val in enumerate(df_progress["weekly_goal_percent"]):
        if val > 0:
            ax.text(
                i,
                df_progress.loc[i, "plot_value"] + ymax * 0.02,
                f"{val:.0f}%",
                ha="center",
                color=COLORS["black"],
                fontsize=9,
                fontweight="bold"
            )

    # 우측 상단에 월간 평균 달성률
    ax.text(
        0.9,
        0.93,
        f"{month_label} 목표 달성률: {progress['monthly_goal']*100:.1f}%",
        transform=ax.transAxes,
        fontsize=12,
        color=COLORS["brown"],
        ha="right",
        fontweight="bold"
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return {"image_base64": base64.b64encode(buf.read()).decode("ascii")}

@app.get("/me/stats/recipe-logs-level-visual")
def visualize_level_ratio(user_id: str, selected_date: date = Query(...), db=Depends(get_db)):
    """② 주별 난이도별 조리 비율 (Stacked Bar)"""
    selected_dt = datetime.combine(selected_date, datetime.min.time())
    start_date, end_date = get_month_range(selected_dt)
    levels = fetch_recipe_level_ratio(db, user_id, start_date, end_date)
    month_label = f"{selected_date.month}월"
    week_labels = ["첫째 주", "둘째 주", "셋째 주", "넷째 주", "다섯째 주"]

    # ✅ 레벨 딕셔너리 구성
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

    # ✅ 주차 정렬 맞추기 (df_progress 기준)
    all_weeks = week_labels[:len(df_levels)]
    df_levels = df_levels.set_index("주차").reindex(all_weeks, fill_value=0).reset_index()

    # ✅ 비율 계산
    df_levels["상비율"] = df_levels["상"] / df_levels["total"].replace(0, 1)
    df_levels["하비율"] = df_levels["하"] / df_levels["total"].replace(0, 1)

    # ✅ 그래프 시작
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(df_levels["주차"], df_levels["total"] * df_levels["하비율"], color=COLORS["brown"], label="하")
    ax.bar(
        df_levels["주차"],
        df_levels["total"] * df_levels["상비율"],
        bottom=df_levels["total"] * df_levels["하비율"],
        color=COLORS["cream"],
        label="상"
    )

    # ✅ 텍스트 (0%는 표시 안 함)
    for i, row in df_levels.iterrows():
        total = row["total"]
        if total > 0:
            if row["하비율"] > 0:
                ax.text(
                    i,
                    total * row["하비율"] / 2,
                    f"{row['하비율']*100:.0f}%",
                    ha="center",
                    va="center",
                    color=COLORS["black"],
                    fontsize=10,
                    fontweight="bold"
                )
            if row["상비율"] > 0:
                ax.text(
                    i,
                    total * (row["하비율"] + row["상비율"]/2),
                    f"{row['상비율']*100:.0f}%",
                    ha="center",
                    va="center",
                    color=COLORS["black"],
                    fontsize=10,
                    fontweight="bold"
                )

    # ✅ 스타일 (원본과 완전 동일)
    ax.set_title(f"{month_label} 주별 난이도별 조리 비율", fontsize=14, color=COLORS["brown"], fontweight="bold")
    ax.set_ylabel("조리 횟수", fontsize=11, color=COLORS["brown"], fontweight="bold")
    ax.set_xticklabels(df_levels["주차"], fontweight="bold", color=COLORS["brown"])
    ax.set_ylim(0, (df_levels["total"].max() or 1) * 1.1)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.legend()

    # ✅ 저장 및 반환
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return {"image_base64": base64.b64encode(buf.read()).decode("ascii")}


@app.get("/me/stats/recipe-logs-category-visual")
def visualize_category_ratio(user_id: str, selected_date: date = Query(...), db=Depends(get_db)):
    """③ 카테고리 비율 (Pie)"""
    selected_dt = datetime.combine(selected_date, datetime.min.time())
    start_date, end_date = get_month_range(selected_dt)
    categories = fetch_recipe_category_ratio(db, user_id, start_date, end_date)
    month_label = f"{selected_date.month}월"

    df_cat = pd.DataFrame(categories.get("categories", []))
    fig, ax = plt.subplots(figsize=(6, 6))
    if not df_cat.empty:
        df_cat = df_cat.sort_values("count", ascending=False).head(5)
        wedges, texts, autotexts = ax.pie(
            df_cat["ratio"], labels=df_cat["label"],
            autopct=lambda p: f"{p:.0f}%" if p > 0 else "",
            startangle=110,
            colors=[COLORS["orange"], COLORS["cream"], COLORS["brown"], "#d4a373", "#e6ccb2"],
            textprops={"color": COLORS["brown"], "fontsize": 11, "fontweight": "bold"}
        )
        for t in autotexts:
            t.set_color(COLORS["black"])
            t.set_fontweight("bold")
        ax.set_title(f"{month_label} 카테고리 비율", fontsize=14, color=COLORS["brown"], fontweight="bold")
    else:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center", fontsize=14, color=COLORS["brown"], fontweight="bold")
        ax.set_axis_off()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return {"image_base64": base64.b64encode(buf.read()).decode("ascii")}

# ======================================================
# LOCAL TEST — TestClient로 미리보기 이미지 생성
# ======================================================
if __name__ == "__main__":
    from fastapi.testclient import TestClient
    import webbrowser

    client = TestClient(app)
    user_id = "irisyshin"
    selected_date = "2025-10-01"

    for path in ["progress-visual", "recipe-logs-level-visual", "recipe-logs-category-visual"]:
        res = client.get(f"/me/stats/{path}?user_id={user_id}&selected_date={selected_date}")
        img_data = base64.b64decode(res.json()["image_base64"])
        filename = f"preview_{path}.png"
        with open(filename, "wb") as f:
            f.write(img_data)
        print(f"✅ {path} → {filename}")
    webbrowser.open("preview_progress_visual.png")
