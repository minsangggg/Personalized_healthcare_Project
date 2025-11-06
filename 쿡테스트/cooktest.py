import pymysql
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from dotenv import load_dotenv
from pathlib import Path

# ======================================================
# CONFIG & DB
# ======================================================
ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

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
# ROUTER INIT
# ======================================================
router = APIRouter()

# ======================================================
# Helper Function — 이벤트 상태 계산
# ======================================================
def get_event_status(start_date, end_date):
    today = datetime.now().date()
    start = start_date.date() if isinstance(start_date, datetime) else start_date
    end = end_date.date() if isinstance(end_date, datetime) else end_date

    if start <= today <= end:
        return "진행중"
    elif today < start:
        return "예정"
    else:
        return "종료"


# ======================================================
# 1. /events — 전체 이벤트 리스트
# ======================================================
@router.get("/events", tags=["Events"])
def get_all_events(conn=Depends(get_db)):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                e.event_name,
                e.start_date,
                e.end_date,
                COUNT(b.event_id) AS board_count
            FROM event e
            LEFT JOIN board b ON e.event_id = b.event_id
            GROUP BY e.event_id
            ORDER BY e.start_date DESC;
        """)
        events = cursor.fetchall()

    for e in events:
        e["status"] = get_event_status(e["start_date"], e["end_date"])

    return events


# ======================================================
# 2. /events/{event_id} — 특정 이벤트 게시글 목록
# ======================================================
@router.get("/events/{event_id}", tags=["Events"])
def get_event_boards(event_id: int, conn=Depends(get_db)):
    """
    특정 이벤트 상세:
      - 이벤트 기본 정보 + 게시글 수 + 상태
      - 게시글 리스트 (user_id, title, like_count, created_at)
      - 좋아요 TOP3
    """
    with conn.cursor() as cursor:
        # 이벤트 기본정보 + 게시글 수
        cursor.execute("""
            SELECT 
                e.event_name,
                e.event_description,
                e.start_date,
                e.end_date,
                COUNT(b.event_id) AS board_count
            FROM event e
            LEFT JOIN board b ON e.event_id = b.event_id
            WHERE e.event_id = %s
            GROUP BY e.event_id;
        """, (event_id,))
        event = cursor.fetchone()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # 게시글 목록
        cursor.execute("""
            SELECT 
                content_id,
                user_id,
                content_title,
                DATE(created_at) AS created_at,
                like_count
            FROM board
            WHERE event_id = %s
            ORDER BY created_at DESC;
        """, (event_id,))
        boards = cursor.fetchall()

        # 좋아요 TOP3
        cursor.execute("""
            SELECT 
                content_id,
                user_id,
                content_title,
                like_count
            FROM board
            WHERE event_id = %s
            ORDER BY like_count DESC
            LIMIT 3;
        """, (event_id,))
        top3 = cursor.fetchall()

    # 상태 계산
    event["status"] = get_event_status(event["start_date"], event["end_date"])
    event["top3"] = top3
    event["boards"] = boards
    return event


# ======================================================
# 3. /events/{event_id}/{content_id} — 게시글 상세보기
# ======================================================
@router.get("/events/{event_id}/{content_id}", tags=["Events"])
def get_event_board_detail(event_id: int, content_id: int, conn=Depends(get_db)):
    """
    게시글 상세 보기:
      - user_id, title, text, img_url, like_count, created_at
    """
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT 
                user_id,
                content_title,
                content_text,
                img_url,
                like_count,
                DATE(created_at) AS created_at
            FROM board
            WHERE event_id = %s AND content_id = %s;
        """, (event_id, content_id))
        board = cursor.fetchone()

    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    return board
