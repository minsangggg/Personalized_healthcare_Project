import pymysql
import os
from dotenv import load_dotenv

load_dotenv()  # .env 로드

try:
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5
    )
    print("✅ DB 연결 성공!")
    with conn.cursor() as cur:
        cur.execute("SELECT NOW() AS now_time;")
        print(cur.fetchone())
    conn.close()

except Exception as e:
    print("❌ DB 연결 실패:", e)
