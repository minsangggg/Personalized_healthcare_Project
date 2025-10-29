# app.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, re, secrets, hashlib
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Literal

import pandas as pd
import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Depends, Response, Request, Cookie
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from recommend_core import recommend_json as recommend_json_llm

from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
from datetime import timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_MIN = int(os.getenv("ACCESS_MIN", "30"))
REFRESH_DAYS = int(os.getenv("REFRESH_DAYS", "7"))

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

@app.get("/me")
def me(current_user: str = Depends(get_current_user)):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id AS user_id, user_name FROM user_info WHERE id=%s", (current_user,))
        row = cur.fetchone()
        if not row: raise HTTPException(404, "User not found")
        return row

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

# ── LLM 추천 + 안전 fallback ─────────────────
def _fallback_recipes(n: int = 3) -> List[Dict[str, Any]]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT recipe_id,
                   recipe_nm_ko AS title,
                   cooking_time AS cook_time,
                   level_nm     AS difficulty,
                   ingredient_full AS ingredients_text,
                   step_text    AS steps_text
            FROM recipe
            ORDER BY RAND()
            LIMIT %s
        """, (n,))
        return cur.fetchall() or []

@app.get("/me/recommendations")
def me_recommendations(current_user: str = Depends(get_current_user)):
    uid = current_user

    data: Any = None
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(recommend_json_llm, user_id=uid, limit=3, exclude_ids=None)
            data = fut.result(timeout=8)
    except (FuturesTimeout, Exception):
        data = None

    if isinstance(data, list):
        items = data
    else:
        items = (data or {}).get("recommended_db_candidates") \
             or (data or {}).get("recommended") \
             or []

    items = (items or [])[:3]
    if not items:
        items = _fallback_recipes(3)

    try:
        with get_conn() as conn, conn.cursor() as cur:
            for r in items:
                rid = r.get("recipe_id") or r.get("id")
                if rid is not None:
                    cur.execute(
                        "INSERT INTO recommend_recipe (id, recipe_id, recommend_date) VALUES (%s,%s,NOW())",
                        (uid, int(rid))
                    )
    except Exception:
        pass

    out = []
    for r in items:
        rid = r.get("recipe_id") or r.get("id")
        if rid is None: continue
        out.append({
            "id": int(rid),
            "title": r.get("title") or r.get("recipe_nm_ko") or "",
            "cook_time": r.get("cook_time") or r.get("cooking_time"),
            "difficulty": r.get("difficulty") or r.get("level_nm"),
            "ingredients_text": r.get("ingredients_text") or "",
            "steps_text": r.get("steps_text") or "",
            "step_tip": r.get("step_tip") or "",
        })
    return out

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
          r.recipe_nm_ko AS title,
          r.cooking_time,
          r.level_nm AS difficulty,

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
        JOIN recipe r ON rr.recipe_id = r.recipe_id
        WHERE rr.id = %s
        ORDER BY sort_key DESC
        """
        cur.execute(sql, (current_user,))
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
                "title": r["title"],
                "cooking_time": r.get("cooking_time"),
                "difficulty": r.get("difficulty"),
                "selected_date": to_yyyy_mm_dd(r.get("selected_date_only")),
            }
            for r in rows
        ],
    }
    
# 레시피 상세 조회
@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int, current_user: str = Depends(get_current_user)):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
            r.recipe_id   AS id,
            r.recipe_nm_ko AS title,
            r.cooking_time AS cook_time,
            r.level_nm     AS difficulty,
            r.ingredient_full AS ingredients_text,
            r.step_text AS steps_text,
            NULL AS step_tip
            FROM recipe r
            WHERE r.recipe_id = %s
            """,
            (recipe_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recipe not found")
    return {"recipe": row}