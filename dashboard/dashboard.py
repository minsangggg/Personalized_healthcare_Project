# =========================
# import & 환경설정
# =========================
from fastapi import FastAPI, Depends
import pymysql
import os
from dotenv import load_dotenv

# ✅ .env 파일 로드 (DB 환경변수)
load_dotenv()

# =========================
# DB 연결
# =========================
def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        charset=os.getenv("DB_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

# FastAPI용 DB 종속성 
def get_db():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()

# =========================
# FastAPI 앱 생성
# =========================
app = FastAPI(title="Recipe Dashboard API")

# =========================
# 테스트 API
# =========================
@app.get("/test-db")
def test_db(db = Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("SELECT NOW() AS now_time;")
        result = cursor.fetchone()
    return {"db_time": result["now_time"]}

@app.get("/")
def home():
    return {"message": "서버 정상 작동 중입니다 🚀"}
