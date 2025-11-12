# db.py
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")              # 예: lgup3
DB_CHAR = os.getenv("DB_CHARSET", "utf8mb4")

def get_conn():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset=DB_CHAR,
        cursorclass=pymysql.cursors.DictCursor, autocommit=True
    )

# 스키마.테이블 fully-qualified로 쓰고 싶을 때
def T(table: str) -> str:
    return f"`{DB_NAME}`.`{table}`"
