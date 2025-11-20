import os
from pathlib import Path
from typing import Optional

import pymysql
from dotenv import load_dotenv


ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

if not os.getenv("DB_HOST"):
    load_dotenv()
    backend_env = Path(__file__).resolve().parents[2] / "backend" / ".env"
    if backend_env.exists():
        load_dotenv(backend_env)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD") or os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")


def _ensure_db_env():
    missing = [key for key in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME") if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"DB 환경 변수가 없습니다: {', '.join(missing)} (.env 설정을 확인하세요)")


_ensure_db_env()


def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD") or os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        charset=os.getenv("DB_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def T(table: str) -> str:
    return f"{DB_NAME}.{table}"


def query_one(sql: str, params=None) -> Optional[dict]:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchone()
    except Exception as exc:
        print(f"DB 쿼리 에러: {exc}")
        return None
