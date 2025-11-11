# ============================================================
# badge_title/service.py — 대표 칭호 선택/변경 로직
# ============================================================

from fastapi import HTTPException
import pymysql
import os
from dotenv import load_dotenv
from pathlib import Path
# ============================================================
# CONFIG & DB
# ============================================================
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


def select_user_title(user_id: str, badge_id: int):
    """
    대표 칭호(뱃지) 선택/변경 서비스 로직.
    - 기존 대표 칭호(is_displayed=1) 전부 해제
    - 새로 선택한 뱃지 is_displayed=1 설정
    """
    db = get_conn()
    try:
        with db.cursor() as cur:
            # 1️⃣ 기존 대표 칭호 해제
            cur.execute(
                "UPDATE user_badges SET is_displayed = 0 WHERE user_id = %s;",
                (user_id,)
            )

            # 2️⃣ 새로 선택한 뱃지 지정
            cur.execute(
                """
                UPDATE user_badges
                SET is_displayed = 1
                WHERE user_id = %s AND badge_id = %s;
                """,
                (user_id, badge_id)
            )

            # 3️⃣ 검증
            cur.execute(
                """
                SELECT badge_id
                FROM user_badges
                WHERE user_id = %s AND badge_id = %s AND is_displayed = 1;
                """,
                (user_id, badge_id)
            )
            selected = cur.fetchone()

            if not selected:
                raise HTTPException(
                    status_code=400,
                    detail="해당 뱃지를 보유하고 있지 않거나 잘못된 badge_id입니다."
                )

            return {
                "message": "대표 칭호가 변경되었습니다.",
                "user_id": user_id,
                "badge_id": selected["badge_id"],
            }

    finally:
        db.close()
