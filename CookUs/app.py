# app.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, secrets, hashlib
import random
import string
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Literal

import pandas as pd
import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Depends, Response, Request, Cookie, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from recommend_core import recommend_json

from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
from datetime import timezone
from fastapi.security import HTTPBearer
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_MIN = int(os.getenv("ACCESS_MIN", "30"))
REFRESH_DAYS = int(os.getenv("REFRESH_DAYS", "7"))

SEND_EMAILS = os.getenv("SEND_EMAILS", "false").lower() == "true"
DEV_RETURN_CODES = os.getenv("DEV_RETURN_CODES", "false").lower() == "true"

ACCESS_EXPIRE_MIN   = int(os.getenv("ACCESS_EXPIRE_MIN", "30"))
REFRESH_EXPIRE_DAYS = int(os.getenv("REFRESH_EXPIRE_DAYS", "7"))
FRONT_ORIGIN        = os.getenv("FRONT_ORIGIN", "http://localhost:5173")

SMTP_HOST = os.getenv("SMTP_HOST", "127.0.0.1")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@cookus.example.com")
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "false").lower() == "true"
SMTP_SSL_TLS  = os.getenv("SMTP_SSL_TLS", "false").lower() == "true"

print(f"[AUTH-BOOT] algo={JWT_ALG} secret={JWT_SECRET[:3]}*** len={len(JWT_SECRET)}")
print(f"[SMTP] host={SMTP_HOST} port={SMTP_PORT} from={SMTP_FROM} STARTTLS={SMTP_STARTTLS} SSL_TLS={SMTP_SSL_TLS}")

# =========================
# 메일 설정 & 인증코드 저장소(메모리)
# =========================
mail_conf = ConnectionConfig(
    MAIL_USERNAME="",
    MAIL_PASSWORD="",
    MAIL_FROM=SMTP_FROM,
    MAIL_SERVER=SMTP_HOST,
    MAIL_PORT=SMTP_PORT,
    MAIL_STARTTLS=SMTP_STARTTLS,
    MAIL_SSL_TLS=SMTP_SSL_TLS,
    USE_CREDENTIALS=False,
    VALIDATE_CERTS=False,
)
fast_mail = FastMail(mail_conf)

# purpose: "find_id" / "find_pw"  (키는 email 기준, find_pw는 id도 같이 저장)
verification_store: Dict[str, Dict[str, Any]] = {}
CODE_TTL_MIN = 10

def _code_key(purpose: str, email: str) -> str:
    return f"{purpose}:{email}"

def _make_code(n: int = 6) -> str:
    return "".join(random.choices(string.digits, k=n))

async def send_email(to_email: str, subject: str, body_text: str):
    msg = MessageSchema(subject=subject, recipients=[to_email], body=body_text, subtype="plain")

    # 개발모드: 실제 발송하지 않음
    if not SEND_EMAILS:
        print(f"[DEV EMAIL] To={to_email}\nSubject={subject}\n{body_text}")
        return
    try:
        await fast_mail.send_message(msg)
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")

def _utc_now():
    return datetime.now(timezone.utc)

def create_access_refresh(sub: str) -> tuple[str, str]:
    now = _utc_now()
    access = jwt.encode(
        {"sub": sub, "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=ACCESS_MIN)).timestamp())},
        JWT_SECRET, algorithm=JWT_ALG
    )
    refresh = jwt.encode(
        {"sub": sub, "iat": int(now.timestamp()), "exp": int((now + timedelta(days=REFRESH_DAYS)).timestamp())},
        JWT_SECRET, algorithm=JWT_ALG
    )
    return access, refresh

bearer = HTTPBearer(auto_error=False)

def get_current_user(request: Request, _=Depends(bearer)) -> str:
    auth = request.headers.get("Authorization", "").strip()
    if not auth:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth
    if token.lower().startswith("bearer "):
        token = token.split(None, 1)[1].strip()
        if token.lower().startswith("bearer "):
            token = token.split(None, 1)[1].strip()

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid payload")
        return str(sub)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def issue_tokens(sub: str) -> tuple[str, str, str]:
    jti = secrets.token_urlsafe(24)
    now = _utc_now()
    access = jwt.encode(
        {"sub": sub, "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=ACCESS_MIN)).timestamp())},
        JWT_SECRET, algorithm=JWT_ALG
    )
    refresh = jwt.encode(
        {"sub": sub, "jti": jti, "iat": int(now.timestamp()), "exp": int((now + timedelta(days=REFRESH_DAYS)).timestamp())},
        JWT_SECRET, algorithm=JWT_ALG
    )
    return access, refresh, jti

def save_refresh_jti(user_id: str, jti: str, exp: datetime, ua: str|None=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
          INSERT INTO user_refresh_token(user_id, jti_hash, expires_at, user_agent, revoked)
          VALUES (%s,%s,%s,%s,0)
        """, (user_id, _hash(jti), exp, ua))

# ── ENV / DB ─────────────────────────────────
load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

def get_conn():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset=DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor, autocommit=True,
    )

def to_iso(v):
    if v is None: return None
    if isinstance(v, (datetime, date)): return v.isoformat()
    try: return pd.to_datetime(v).isoformat()
    except Exception: return str(v)

# ── APP / CORS ───────────────────────────────
app = FastAPI(title="CookUS API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
)

# ── 공통 ─────────────────────────────────────
def split_unit(nm: str) -> tuple[str, Optional[str]]:
    m = re.search(r"\(([^)]+)\)\s*$", str(nm))
    if m: return (re.sub(r"\([^)]*\)\s*$", "", str(nm)).strip(), m.group(1).strip())
    return (str(nm).strip(), None)

# ── 스키마 ───────────────────────────────────
class AuthLoginIn(BaseModel):
    id: str
    password: str

class AuthSignupIn(BaseModel):
    id: str
    user_name: str
    email: str
    password: str
    gender: Literal["male","female"]
    date_of_birth: Optional[str] = None
    cooking_level: Literal["상","하"]
    goal: int = Field(0, ge=0, le=21)
    
class MeUpdateIn(BaseModel):
    user_name: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[Literal['male', 'female']] = None
    date_of_birth: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    goal: Optional[int] = Field(None, ge=0, le=21)
    cooking_level: Optional[Literal['상', '하']] = None

class SaveItem(BaseModel):
    name: str
    quantity: int = Field(1, ge=1)
    unit: Optional[str] = None

class SaveFridgeIn(BaseModel):
    items: List[SaveItem]
    mode: Literal["merge","replace"] = "merge"
    purgeMissing: bool = False

class SelectIn(BaseModel):
    recipe_id: int

class SelectedActionIn(BaseModel):
    action: int = Field(..., ge=0, le=1)

# ----- FAQ -----
def ensure_faq_table():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS faq (
              faq_id BIGINT AUTO_INCREMENT PRIMARY KEY,
              question VARCHAR(255) NOT NULL,
              answer MEDIUMTEXT NOT NULL,
              category VARCHAR(50) NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              is_visible TINYINT(1) NOT NULL DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )


@app.get("/faq")
def list_faq(
    query: Optional[str] = Query(None, description="검색어 (질문/답변/분류)"),
    category: Optional[str] = Query(None, description="카테고리 정확히 일치 필터"),
    limit: int = Query(30, ge=1, le=100),
):
    ensure_faq_table()
    clauses = ["is_visible=1"]
    params: list[Any] = []
    if query:
        clauses.append("(question LIKE %s OR answer LIKE %s OR category LIKE %s)")
        like = f"%{query}%"
        params.extend([like, like, like])
    if category:
        clauses.append("category = %s")
        params.append(category)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
      SELECT faq_id, question, answer, category, created_at, updated_at, is_visible
      FROM faq
      {where}
      ORDER BY created_at DESC
      LIMIT %s
    """
    params.append(int(limit))
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall() or []
    return {"count": len(rows), "items": rows}


@app.get("/faq/categories")
def list_faq_categories():
    ensure_faq_table()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT category
            FROM faq
            WHERE is_visible=1 AND category IS NOT NULL AND category <> ''
            ORDER BY category
            """
        )
        rows = cur.fetchall() or []
    return {"items": [r.get("category") for r in rows if r.get("category") is not None]}

# ── Health ───────────────────────────────────
@app.get("/health")
def health():
    return {"ok": True}

# ── Auth ─────────────────────────────────────
@app.post("/auth/login")
def auth_login(b: AuthLoginIn, request: Request, response: Response):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id AS user_id, user_name, password
            FROM user_info
            WHERE id=%s
              AND (is_deleted IS NULL OR is_deleted = 0)
            LIMIT 1
        """, (b.id,))
        row = cur.fetchone()
        if not row or row["password"] != b.password:
            raise HTTPException(401, "아이디 또는 비밀번호가 올바르지 않습니다.")

        access, refresh, jti = issue_tokens(row["user_id"])
        exp = datetime.utcnow() + timedelta(days=REFRESH_DAYS)
        save_refresh_jti(row["user_id"], jti, exp, request.headers.get("user-agent"))

        response.set_cookie(
            key="refresh", value=refresh,
            httponly=True, secure=False,
            samesite="lax", path="/auth/refresh", max_age=REFRESH_DAYS*24*3600
        )
        return {"accessToken": access, "user": {"user_id": row["user_id"], "user_name": row["user_name"]}}

# ── Auth: signup ─────────────────────────────
@app.post("/auth/signup")
def auth_signup(b: AuthSignupIn, request: Request, response: Response):
    # 필수값 체크
    if not b.id or not b.password:
        raise HTTPException(400, "id/password required")

    with get_conn() as conn, conn.cursor() as cur:
        # 아이디 중복 확인
        cur.execute("SELECT id FROM user_info WHERE id=%s LIMIT 1", (b.id,))
        if cur.fetchone():
            raise HTTPException(409, "user exists")

        # DB 컬럼명은 스키마에 맞춰 수정
        cur.execute("""
            INSERT INTO user_info
              (id, user_name, gender, email, date_of_birth, password, goal, cooking_level)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            b.id, b.user_name, b.gender, b.email,
            (b.date_of_birth or "1999-12-31"),
            b.password, b.goal, b.cooking_level
        ))

    # 가입 직후 바로 로그인처럼 토큰 발급
    access, refresh, jti = issue_tokens(b.id)
    exp = datetime.utcnow() + timedelta(days=REFRESH_DAYS)
    save_refresh_jti(b.id, jti, exp, request.headers.get("user-agent"))

    response.set_cookie(
        key="refresh", value=refresh,
        httponly=True, secure=False, samesite="lax",
        path="/auth/refresh", max_age=REFRESH_DAYS*24*3600
    )
    return {"accessToken": access, "user": {"user_id": b.id, "user_name": b.user_name}}

@app.post("/auth/refresh")
def auth_refresh(response: Response, refresh: Optional[str] = Cookie(default=None)):
    if not refresh:
        raise HTTPException(401, "No refresh cookie")
    try:
        payload = jwt.decode(refresh, JWT_SECRET, algorithms=[JWT_ALG])
        sub = payload["sub"]; jti = payload.get("jti")
        if not jti: raise HTTPException(401, "Invalid refresh")

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, revoked, expires_at FROM user_refresh_token WHERE user_id=%s AND jti_hash=%s",
                        (sub, _hash(jti)))
            row = cur.fetchone()
            if not row or row["revoked"] or row["expires_at"] < datetime.utcnow():
                raise HTTPException(401, "Refresh invalid")

            cur.execute("UPDATE user_refresh_token SET revoked=1 WHERE id=%s", (row["id"],))

        access, new_refresh, new_jti = issue_tokens(sub)
        save_refresh_jti(sub, new_jti, datetime.utcnow()+timedelta(days=REFRESH_DAYS))
        response.set_cookie(
            key="refresh", value=new_refresh,
            httponly=True, secure=False, samesite="lax", path="/auth/refresh",
            max_age=REFRESH_DAYS*24*3600
        )
        return {"accessToken": access}
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Refresh expired")
    except Exception:
        raise HTTPException(401, "Invalid refresh")

@app.post("/auth/logout")
def auth_logout(response: Response, refresh: Optional[str] = Cookie(default=None)):
    response.delete_cookie(key="refresh", path="/auth/refresh")
    if refresh:
        try:
            payload = jwt.decode(refresh, JWT_SECRET, algorithms=[JWT_ALG])
            sub = payload["sub"]; jti = payload.get("jti")
            if jti:
                with get_conn() as conn, conn.cursor() as cur:
                    cur.execute("UPDATE user_refresh_token SET revoked=1 WHERE user_id=%s AND jti_hash=%s",
                                (sub, _hash(jti)))
        except Exception:
            pass
    return {"ok": True}

# ---- 회원 탈퇴 ----
@app.delete("/me/delete")
def delete_me(response: Response, current_user: str = Depends(get_current_user), payload: Dict[str, Any] = Body(...)):
    pw  = str(payload.get("password", "")).strip()
    pw2 = str(payload.get("password_confirm", "")).strip()
    if not pw or not pw2:
        raise HTTPException(400, "password / password_confirm required")
    if pw != pw2:
        raise HTTPException(400, "passwords do not match")

    uid = current_user
    with get_conn() as conn, conn.cursor() as cur:
        # 비밀번호 확인 및 탈퇴 안된 사용자 확인
        cur.execute(
            """
            SELECT id, password
            FROM user_info
            WHERE id=%s
              AND (is_deleted IS NULL OR is_deleted = 0)
            LIMIT 1
            """,
            (uid,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "account already deleted or not found")
        if str(row["password"]) != pw:
            raise HTTPException(401, "invalid password")

        # 비식별화 + 탈퇴 플래그
        cur.execute(
            """
            UPDATE user_info
            SET user_name = %s,
                email = %s,
                password = %s,
                is_deleted = 1
            WHERE id=%s
            """,
            ("**", "**", "**", uid),
        )
        conn.commit()

    # refresh 쿠키 제거
    response.delete_cookie(key="refresh", path="/auth/refresh")
    return {"ok": True, "message": "그동안 이용해주셔서 감사합니다. 계정이 삭제 처리되었습니다."}

@app.get("/me")
def me(current_user: str = Depends(get_current_user)):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT
                id             AS user_id,
                user_name      AS user_name,
                email          AS email,
                gender         AS gender,
                date_of_birth  AS date_of_birth,
                goal           AS goal,
                cooking_level  AS cooking_level
            FROM user_info
            WHERE id = %s
        """, (current_user,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="user not found")

    return row

@app.put("/me")
def update_me(b: MeUpdateIn, current_user: str = Depends(get_current_user)):
    fields = []
    params = []

    if b.user_name is not None:
        fields.append("user_name=%s"); params.append(b.user_name.strip())
    if b.email is not None:
        fields.append("email=%s"); params.append(b.email.strip())
    if b.gender is not None:
        fields.append("gender=%s"); params.append(b.gender)
    if b.date_of_birth is not None:
        fields.append("date_of_birth=%s"); params.append(b.date_of_birth or None)
    if b.goal is not None:
        fields.append("goal=%s"); params.append(int(b.goal))
    if b.cooking_level is not None:
        fields.append("cooking_level=%s"); params.append(b.cooking_level)

    if not fields:
        raise HTTPException(400, "no fields to update")

    with get_conn() as conn, conn.cursor() as cur:
        sql = f"UPDATE user_info SET {', '.join(fields)} WHERE id=%s"
        cur.execute(sql, (*params, current_user))
        # 변경된 최신값 다시 반환
        cur.execute("""
            SELECT
                id AS user_id, user_name, email, gender,
                date_of_birth, goal, cooking_level
            FROM user_info WHERE id=%s
        """, (current_user,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "user not found")
        return row

# =========================
# 아이디 찾기: 코드발송 → 코드검증 후 ID 반환
# =========================
@app.post("/auth/find-id")
async def find_id_send_code(payload: Dict[str, Any] = Body(...)):
    # 이름(선택) + 이메일(필수)
    username = (payload.get("username") or "").strip()
    email    = (payload.get("email") or "").strip()
    if not email:
        raise HTTPException(400, "email required")

    # 이메일(+선택적으로 이름)으로 사용자 존재 확인
    with get_conn() as conn, conn.cursor() as cur:
        if username:
            cur.execute("SELECT id FROM user_info WHERE email=%s AND user_name=%s", (email, username))
        else:
            cur.execute("SELECT id FROM user_info WHERE email=%s", (email,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "no user with that email (and name)")

        user_id = row["id"]

    # 인증코드 생성/저장
    code = _make_code()
    key = _code_key("find_id", email)
    verification_store[key] = {
        "code": code,
        "expires_at": _utc_now() + timedelta(minutes=CODE_TTL_MIN),
        "user_id": user_id,
    }

    # 메일 발송
    try:
        await send_email(
            to_email=email,
            subject="[CookUS] 아이디 찾기 인증코드",
            body_text=f"인증코드: {code}\n(유효기간 {CODE_TTL_MIN}분)\n이 코드를 앱에 입력하면 아이디를 확인할 수 있어요.",
        )
    except Exception as e:
        # 개발 중에는 200으로 계속 진행(응답에 dev_code 있으니 테스트 가능)
        print(f"[MAIL SEND WARN] {e}")

    # 개발 편의: 코드 되돌려주기
    resp = {"ok": True}
    if DEV_RETURN_CODES:
        resp["dev_code"] = code
        resp["expires_in_sec"] = CODE_TTL_MIN * 60
    return resp



# 아이디 찾기: 코드 검증
@app.post("/auth/find-id/verify")
def find_id_verify(payload: Dict[str, Any] = Body(...)):
    """
    Request:
      { "email": "<사용자 이메일>", "code": "<인증코드>" }
    Response:
      { "user_id": "<해당 사용자의 ID>" }
    """
    email = (payload.get("email") or "").strip()
    code  = (payload.get("code") or "").strip()
    if not email or not code:
        raise HTTPException(status_code=400, detail="email/code required")

    key = _code_key("find_id", email)           # 예: "find_id:<email>"
    data = verification_store.get(key)
    if not data:
        raise HTTPException(status_code=400, detail="no pending verification")

    # 만료 확인
    if _utc_now() > data["expires_at"]:
        verification_store.pop(key, None)
        raise HTTPException(status_code=400, detail="code expired")

    # 코드 비교
    if code != data["code"]:
        raise HTTPException(status_code=400, detail="invalid code")

    user_id = data["user_id"]

    # 1회성 사용: 성공 시 즉시 삭제
    verification_store.pop(key, None)

    return {"user_id": user_id}



# =========================
# 비밀번호 찾기: 코드발송 → 코드검증+변경
# =========================
@app.post("/auth/find-password")
async def find_pw_send_code(payload: Dict[str, Any] = Body(...)):
    user_id = (payload.get("id") or "").strip()
    email   = (payload.get("email") or "").strip()
    if not user_id or not email:
        raise HTTPException(400, "id/email required")

    # id + email 매칭 확인
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM user_info WHERE id=%s AND email=%s", (user_id, email))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "no match for id+email")

    # 인증코드 생성/저장
    code = _make_code()
    key = _code_key("find_pw", email)
    verification_store[key] = {
        "code": code,
        "expires_at": _utc_now() + timedelta(minutes=CODE_TTL_MIN),
        "user_id": user_id,
    }

    # 메일 발송
    await send_email(
        to_email=email,
        subject="[CookUS] 비밀번호 재설정 인증코드",
        body_text=f"인증코드: {code}\n(유효기간 {CODE_TTL_MIN}분)\n이 코드를 앱에 입력하면 비밀번호를 변경할 수 있어요.",
    )

    # 개발 편의: 코드 되돌려주기
    resp = {"ok": True}
    if DEV_RETURN_CODES:
        resp["dev_code"] = code
        resp["expires_in_sec"] = CODE_TTL_MIN * 60
    return resp



@app.put("/auth/password-set")
def password_set(payload: Dict[str, Any] = Body(...)):
    user_id = (payload.get("id") or "").strip()
    email   = (payload.get("email") or "").strip()
    code    = (payload.get("code") or "").strip()
    new_pw  = (payload.get("new_password") or "").strip()
    if not user_id or not email or not code or not new_pw:
        raise HTTPException(400, "id/email/code/new_password required")

    key = _code_key("find_pw", email)
    data = verification_store.get(key)
    if not data:
        raise HTTPException(400, "no pending verification")
    if _utc_now() > data["expires_at"]:
        verification_store.pop(key, None)
        raise HTTPException(400, "code expired")
    if code != data["code"] or data["user_id"] != user_id:
        raise HTTPException(400, "invalid code")

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE user_info SET password=%s WHERE id=%s AND email=%s", (new_pw, user_id, email))
    verification_store.pop(key, None)
    return {"ok": True}


# ── Ingredient 검색 ──────────────────────────
@app.get("/ingredients/search")
def ingredients_search(q: str = Query(..., description="검색어")):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT ingredient_name FROM ingredient WHERE ingredient_name LIKE %s LIMIT 20", (f"%{q}%",))
        rows = cur.fetchall() or []
        return [{"name": r["ingredient_name"]} for r in rows]

# ── 냉장고 ────────────────────────────────────
@app.get("/me/ingredients")
def me_ingredients_get(current_user: str = Depends(get_current_user)):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT ingredient_name AS name_raw, quantity AS qty, stored_at
            FROM fridge_item
            WHERE id=%s
            ORDER BY stored_at DESC
        """, (current_user,))
        rows = cur.fetchall() or []
    out = []
    for r in rows:
        base, unit = split_unit(r["name_raw"])
        out.append({"name": base, "quantity": int(r["qty"]) if r["qty"] is not None else 0, "unit": unit})
    return out

@app.post("/me/ingredients")
def me_ingredients_post(b: SaveFridgeIn, current_user: str = Depends(get_current_user)):
    with get_conn() as conn, conn.cursor() as cur:
        if b.purgeMissing:
            names_payload = [it.name + (f"({it.unit})" if it.unit else "") for it in b.items]
            if names_payload:
                ph = ",".join(["%s"] * len(names_payload))
                cur.execute(f"""
                    DELETE FROM fridge_item
                    WHERE id=%s AND ingredient_name NOT IN ({ph})
                """, (current_user, *names_payload))
            else:
                cur.execute("DELETE FROM fridge_item WHERE id=%s", (current_user,))
        for it in b.items:
            nm = it.name + (f"({it.unit})" if it.unit else "")
            q = int(it.quantity)
            cur.execute("SELECT quantity FROM fridge_item WHERE id=%s AND ingredient_name=%s", (current_user, nm))
            ex = cur.fetchone()
            if ex:
                if b.mode == "merge":
                    cur.execute("""
                        UPDATE fridge_item
                        SET quantity=quantity+%s, stored_at=NOW()
                        WHERE id=%s AND ingredient_name=%s
                    """, (q, current_user, nm))
                else:
                    cur.execute("""
                        UPDATE fridge_item
                        SET quantity=%s, stored_at=NOW()
                        WHERE id=%s AND ingredient_name=%s
                    """, (q, current_user, nm))
            else:
                cur.execute("""
                    INSERT INTO fridge_item (fridge_id, id, ingredient_name, quantity, stored_at)
                    VALUES (UUID(), %s, %s, %s, NOW())
                """, (current_user, nm, q))
    return {"ok": True}

@app.get("/me/recommendations")
def get_recommendations(
    current_user: str = Depends(get_current_user),
    limit: int = Query(
        3,
        ge=1,
        le=5,
        description="추천 레시피 개수 (기본 3개)",
    ),
):
    try:
        with get_conn() as conn, conn.cursor() as cur:
            # 0) 최근 10초 이내 이미 추천된 것이 있으면 그대로 반환(중복 적재 방지)
            cur.execute(
                """
                SELECT rr.recipe_id, rr.recipe_nm_ko, r.cooking_time, r.level_nm, rr.ingredient_full, rr.step_text
                FROM recommend_recipe rr
                JOIN recipe r ON rr.recipe_id = r.recipe_id
                WHERE rr.id = %s AND rr.recommend_date >= (NOW() - INTERVAL 10 SECOND)
                ORDER BY rr.recommend_date DESC
                LIMIT %s
                """,
                (current_user, limit),
            )
            recent_rows = cur.fetchall() or []
        if len(recent_rows) >= limit:
            return JSONResponse(content=recent_rows[:limit], status_code=200)

        # 1) 추천 실행 및 DB 적재
        _ = recommend_json(user_id=current_user, limit=limit)

        # 2) 방금 적재된 레코드 기준으로 카드 데이터 반환 (DB 저장값과 동일)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT rr.recipe_id, rr.recipe_nm_ko, r.cooking_time, r.level_nm, rr.ingredient_full, rr.step_text
                FROM recommend_recipe rr
                JOIN recipe r ON rr.recipe_id = r.recipe_id
                WHERE rr.id = %s
                ORDER BY rr.recommend_date DESC
                LIMIT %s
                """,
                (current_user, limit),
            )
            rows = cur.fetchall() or []
        return JSONResponse(content=rows, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── 선택 저장 / 조회 ─────────────────────────
@app.post("/me/selected-recipe")
def me_selected_recipe(b: SelectIn, current_user: str = Depends(get_current_user)):
    uid = current_user
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT recommend_id
            FROM recommend_recipe
            WHERE id=%s AND recipe_id=%s
            ORDER BY recommend_date DESC
            LIMIT 1
        """, (uid, b.recipe_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(400, "최근 추천 기록이 없습니다.")
        recommend_id = row["recommend_id"]

        cur.execute("""
            INSERT INTO selected_recipe (id, recommend_id, recipe_id, selected_date)
            VALUES (%s, %s, %s, NOW())
        """, (uid, recommend_id, b.recipe_id))

    return {"ok": True}

@app.get("/recipes/selected")
def get_selected_recipes(current_user: str = Depends(get_current_user)):
    with get_conn() as conn, conn.cursor() as cur:
        sql = """
        SELECT
          sr.selected_id,
          sr.recommend_id,
          rr.recipe_id,
          rr.recipe_nm_ko,
          sr.action,
          r.cooking_time,
          r.level_nm,

          CASE
            WHEN sr.selected_date REGEXP '^[0-9]{4}/'
              THEN DATE(STR_TO_DATE(sr.selected_date, '%%Y/%%m/%%d %%H:%%i:%%s'))
            WHEN sr.selected_date REGEXP '^[0-9]{4}-'
              THEN DATE(sr.selected_date)
            WHEN sr.selected_date REGEXP '^[0-9]{4}[.]'
              THEN DATE(STR_TO_DATE(sr.selected_date, '%%Y.%%m.%%d %%H:%%i:%%s'))
            ELSE NULL
          END AS selected_date_only,

          CASE
            WHEN sr.selected_date REGEXP '^[0-9]{4}/'
              THEN STR_TO_DATE(sr.selected_date, '%%Y/%%m/%%d %%H:%%i:%%s')
            WHEN sr.selected_date REGEXP '^[0-9]{4}-'
              THEN sr.selected_date
            WHEN sr.selected_date REGEXP '^[0-9]{4}[.]'
              THEN STR_TO_DATE(sr.selected_date, '%%Y.%%m.%%d %%H:%%i:%%s')
            ELSE NULL
          END AS sort_key

        FROM selected_recipe sr
        JOIN recommend_recipe rr ON sr.recommend_id = rr.recommend_id
        LEFT JOIN recipe r ON rr.recipe_id = r.recipe_id
        WHERE rr.id = %s AND sr.id = %s
        ORDER BY sort_key DESC
        """
        cur.execute(sql, (current_user, current_user))
        rows = cur.fetchall() or []

    def to_yyyy_mm_dd(x):
      try:
          return x.isoformat()
      except Exception:
          return str(x) if x is not None else None

    return {
        "user_id": current_user,
        "count": len(rows),
        "recipes": [
            {
                "selected_id": r["selected_id"],
                "recommend_id": r["recommend_id"],
                "recipe_id": r["recipe_id"],
                "recipe_nm_ko": r["recipe_nm_ko"],
                "action": r.get("action") if isinstance(r, dict) else None,
                "cooking_time": r.get("cooking_time"),
                "level_nm": r.get("level_nm"),
                "selected_date": to_yyyy_mm_dd(r.get("selected_date_only")),
            }
            for r in rows
        ],
    }
    
@app.delete("/me/selected-recipe/{selected_id}")
def delete_selected_recipe(selected_id: int, current_user: str = Depends(get_current_user)):
    uid = current_user
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT 1
            FROM selected_recipe
            WHERE selected_id=%s AND id=%s
            LIMIT 1
        """, (selected_id, uid))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="selected record not found")

        cur.execute("""
            DELETE FROM selected_recipe
            WHERE selected_id=%s AND id=%s
            LIMIT 1
        """, (selected_id, uid))
        conn.commit()
    return Response(status_code=204)   

# 선택 항목 action 토글 (0/1)
@app.patch("/me/selected-recipe/{selected_id}/action")
def update_selected_action(selected_id: int, b: SelectedActionIn, current_user: str = Depends(get_current_user)):
    uid = current_user
    if b.action not in (0, 1):
        raise HTTPException(400, "action must be 0 or 1")
    with get_conn() as conn, conn.cursor() as cur:
        # 권한 확인
        cur.execute(
            """
            SELECT 1 FROM selected_recipe
            WHERE selected_id=%s AND id=%s
            LIMIT 1
            """,
            (selected_id, uid),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="selected record not found")
        cur.execute(
            "UPDATE selected_recipe SET action=%s WHERE selected_id=%s AND id=%s",
            (int(b.action), selected_id, uid),
        )
        conn.commit()
    return {"ok": True, "selected_id": selected_id, "action": int(b.action)}
    
@app.get("/me/selected-recipe/status")
def selected_status(recipe_id: int, current_user: str = Depends(get_current_user)):
    uid = current_user
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
          SELECT sr.selected_id
          FROM selected_recipe sr
          JOIN recommend_recipe rr ON sr.recommend_id = rr.recommend_id
          WHERE sr.id=%s AND rr.id=%s AND rr.recipe_id=%s
          LIMIT 1
        """, (uid, uid, recipe_id))
        row = cur.fetchone()
    return {"selected": bool(row), "selected_id": (row or {}).get("selected_id")}   


# 레시피 상세 조회
@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int, current_user: str = Depends(get_current_user)):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
            r.recipe_id,
            r.recipe_nm_ko,
            r.cooking_time,
            r.level_nm,
            r.ingredient_full,
            r.step_text
            FROM recipe r
            WHERE r.recipe_id = %s
            """,
            (recipe_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recipe not found")
    return {"recipe": row}


# 추천 레코드 상세 조회 (recommend_recipe.recommend_id 기준)
@app.get("/recommendations/{recommend_id}")
def get_recommendation_detail(recommend_id: int, current_user: str = Depends(get_current_user)):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              rr.recommend_id,
              rr.id,
              rr.recipe_id,
              rr.recipe_nm_ko,
              rr.ingredient_full,
              rr.step_text,
              r.cooking_time,
              r.level_nm
            FROM recommend_recipe rr
            JOIN recipe r ON r.recipe_id = rr.recipe_id
            WHERE rr.recommend_id = %s AND rr.id = %s
            LIMIT 1
            """,
            (recommend_id, current_user),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recommendation not found")
    return {"recommendation": row}


