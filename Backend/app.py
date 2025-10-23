from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pymysql
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# FastAPI 앱 초기화
app = FastAPI()

# CORS (React와 통신 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MariaDB 연결 설정
def get_connection():
    return pymysql.connect(
        host="211.51.163.232",   # ✅ 원격 DB 주소
        port=19306,   
        user="lgup3",           
        password="lgup3P@ssw0rd",      
        database="lgup3",        
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

# ----------------------------
# 회원가입용 데이터 모델
# ----------------------------
class SignupRequest(BaseModel):
    user_id: str
    password: str
    name: str
    birth: str

# ✅ 회원가입 API
@app.post("/signup")
def signup(user: SignupRequest):
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # 중복 아이디 검사
            cur.execute("SELECT * FROM user_info WHERE user_id = %s", (user.user_id,))
            existing = cur.fetchone()
            if existing:
                raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")

            # 새 회원 저장
            sql = "INSERT INTO user_info (user_id, password, name, birth) VALUES (%s, %s, %s, %s)"
            cur.execute(sql, (user.user_id, user.password, user.name, user.birth))
            conn.commit()

        return {"message": "회원가입 성공!"}

    except Exception as e:
        print("❌ DB Error:", e)
        raise HTTPException(status_code=500, detail="서버 오류")

    finally:
        conn.close()

# ----------------------------
# 로그인용 데이터 모델
# ----------------------------
class LoginRequest(BaseModel):
    user_id: str
    password: str

# ✅ 로그인 API
@app.post("/login")
def login(user: LoginRequest):
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            sql = "SELECT * FROM user_info WHERE user_id = %s AND password = %s"
            cur.execute(sql, (user.user_id, user.password))
            result = cur.fetchone()

            if result:
                return {"message": "로그인 성공", "name": result["name"]}
            else:
                raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    except Exception as e:
        print("❌ 로그인 에러:", e)
        raise HTTPException(status_code=500, detail="서버 오류")

    finally:
        conn.close()


# ----------------------------
# 추천 API (요리 레벨 기반)
# ----------------------------
@app.get("/recommend/{user_id}")
def recommend(user_id: str):
    """
    로그인된 사용자의 COOKING_LEVEL(요리 난이도)에 맞는 레시피를 추천하는 API
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # 1️⃣ 사용자 요리 레벨 조회
            cur.execute("SELECT COOKING_LEVEL FROM user_info_dummy_data WHERE ID = %s", (user_id,))
            user = cur.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            user_level = user["COOKING_LEVEL"]

            # 2️⃣ 같은 난이도의 레시피 가져오기 (10개만)
            cur.execute(
                "SELECT RECIPE_ID, RECIPE_NM_KO, SUMRY, LEVEL_NM FROM recipe WHERE LEVEL_NM = %s LIMIT 10",
                (user_level,)
            )
            recipes = cur.fetchall()

        return {
            "user_level": user_level,
            "recommendations": recipes
        }

    except Exception as e:
        print("❌ 추천 API 에러:", e)
        raise HTTPException(status_code=500, detail="서버 오류")

    finally:
        conn.close()
