# recommend_core2.py
# recommend_core.py (수정 버전)
# recommend_core2.py (최종 안정화 + 스코어링 제한 버전)
# recommend_core2.py (최종 안정화 + 스코어링 제한 버전)

import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
import pymysql
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# NameError 방지: SYSTEM_PROMPT 정의
SYSTEM_PROMPT = (
    "너는 한국어 요리 추천 도우미다. 정확하고 간결하게 쓰며, 사실만 사용한다. "
    "금칙: 후기/감상/광고/스토리/개인경험/의성어/이모지/과장 표현 금지. "
    "조리 순서는 '명령형 실무 지시'만 남기고 불필요 문장은 삭제한다. 단계당 1문장."
)

# -----------------------------
# DB 연결
# -----------------------------
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

# -----------------------------
# 공통 유틸 / 정규화
# -----------------------------
def _norm(s: str) -> str:
    """괄호/슬래시 제거 및 소문자화"""
    s = str(s).lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = s.replace("/", " ").replace("\n", " ").replace(",", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _tokens_from_ingredients_text(text: str) -> List[str]:
    """재료 텍스트에서 토큰을 추출"""
    if not text:
        return []
    t = _norm(text)
    hits = re.findall(r"'([^']+)'", t)
    if hits:
        toks = [x.strip() for x in hits if x.strip()]
    else:
        toks = [x.strip() for x in re.split(r"[ ,]", t) if x.strip()]
    return toks

def _simplify_token(tok: str) -> str:
    """수식어 및 단위 제거 (최소 토큰으로)"""
    t = tok
    modifiers = ["국산", "수입", "생", "중", "대", "小", "대용량", "특대", "유기농", "친환경"]
    t = re.sub(r"\d+\.?\d*", "", t)  # 숫자 제거
    t = re.sub(r"(g|kg|mg|ml|l|개|큰술|작은술|스푼|컵|잔|장|팩|봉|마리|쪽)$", "", t)  # 단위 제거
    for m in modifiers:
        t = t.replace(m, "")
    t = re.sub(r"\s+", "", t)
    return t

# -----------------------------
# DB helpers
# -----------------------------
def pick_random_user_with_fridge() -> str:
    sql = """
    SELECT u.ID AS uid
    FROM user_info u
    JOIN fridge_item f ON f.ID = u.ID
    GROUP BY u.ID
    ORDER BY RAND()
    LIMIT 1
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
        if not row:
            raise RuntimeError("공통 ID 없음")
        return row["uid"]


def get_user_profile(user_id: str) -> Dict[str, Any]:
    sql = "SELECT * FROM user_info WHERE ID=%s"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError("프로필 없음")
    low = {k.lower(): v for k, v in row.items()}
    return {
        "user_id": low.get("id") or low.get("userid"),
        "name": low.get("name"),
        "gender": low.get("gender"),
        "email": low.get("email"),
        "login_id": low.get("login_id") or low.get("id"),
        "password": low.get("password"),
        "goal_per_week": low.get("goal") or low.get("goal_per_week"),
        "cooking_level": low.get("cooking_level") or low.get("cookinglevel") or "하",
    }

def get_user_fridge_item(user_id: str) -> pd.DataFrame:
    sql = """
    SELECT ID AS user_id, ingredient_name AS item_name, quantity AS amount, stored_at AS saved_at
    FROM fridge_item
    WHERE ID=%s
    ORDER BY stored_at DESC
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id,))
        rows = cur.fetchall()
        if not rows:
            raise RuntimeError("냉장고 재료 없음")
        return pd.DataFrame(rows)

# -----------------------------
# LLM/Scoring Helpers
# -----------------------------
def _recipe_tokens_from_text(text: str) -> List[str]:
    """레시피 재료 원문을 정규화된 토큰으로 변환"""
    toks = _tokens_from_ingredients_text(text)
    toks = [_simplify_token(t) for t in toks if t]
    toks = [t for t in toks if len(t) >= 2]
    uniq: List[str] = []
    for t in toks:
        if t and t not in uniq:
            uniq.append(t)
    return uniq

def _fridge_token_set(fridge_df: pd.DataFrame) -> set:
    """냉장고의 재료명을 정규화/단순화해서 집합으로 반환 (매칭, missing 계산용)"""
    if fridge_df is None or fridge_df.empty:
        return set()
    base = fridge_df["item_name"].map(_norm).dropna().astype(str).tolist()
    base = [_simplify_token(x) for x in base]
    return set([t for t in base if t])

def pick_keywords_from_fridge_all(fridge_df: pd.DataFrame, max_n=30) -> List[str]:
    """LIKE 검색용 키워드 (단순화된 이름만 사용)"""
    base = fridge_df["item_name"].map(_norm).dropna().astype(str).tolist()
    kws = [_simplify_token(x) for x in base]
    kws = [k for k in kws if len(k) >= 2]
    return list(set(kws))[:max_n]

def recent_items_from_fridge(fridge_df: pd.DataFrame, days: int = 10, top: int = 8) -> List[str]:
    df = fridge_df.copy()
    df["saved_at"] = pd.to_datetime(df["saved_at"], errors="coerce")
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = df[df["saved_at"] >= cutoff].sort_values("saved_at", ascending=False)
    return recent["item_name"].map(_norm).head(top).tolist()

def _fetch_candidates_like_any(keywords: List[str], limit=300) -> List[Dict[str, Any]]:
    """DB에서 넓게 후보를 뽑아옴"""
    if not keywords:
        return []
    kws = keywords[:12]
    where = " OR ".join(["ingredient_full LIKE %s"] * len(kws))
    params = [f"%{kw}%" for kw in kws]
    sql = f"""
    SELECT recipe_id,
           recipe_nm_ko AS title,
           cooking_time AS cook_time,
           level_nm AS difficulty,
           ingredient_full AS ingredients_text,
           step_text AS steps_text,
           tag
    FROM recipe
    WHERE {where}
    LIMIT {int(limit)}
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

def _score_and_filter(recipes: List[Dict[str, Any]], fridge_tokens: set) -> List[Dict[str, Any]]:
    """유사 일치 스코어링: 엄격하게 필터링 후 정렬"""
    scored: List[Dict[str, Any]] = []
    fridge_list = list(fridge_tokens)

    for r in recipes:
        recipe_tokens = _recipe_tokens_from_text(r.get("ingredients_text") or "")
        if not recipe_tokens:
            continue

        match_count = 0
        matched_in_recipe = set()

        # 1. 매칭 횟수 계산 (유사/부분 일치)
        for ing_name in fridge_list:
            for rt in recipe_tokens:
                if ing_name in rt or rt in ing_name:
                    if rt not in matched_in_recipe:
                        match_count += 1
                        matched_in_recipe.add(rt)
                    break

        total = max(len(recipe_tokens), 1)
        ratio = match_count / total

        # 2. 엄격한 필터링: 2개 이상 겹치고 매칭률 10% 이상인 경우만 통과
        if match_count >= 2 and ratio >= 0.10:
            rr = dict(r)
            rr["match_count"] = match_count
            rr["match_ratio"] = round(ratio * 100, 1)
            scored.append(rr)

    # 3. 정렬: match_count (개수) > match_ratio (비율) 내림차순
    scored.sort(key=lambda x: (x["match_count"], x["match_ratio"]), reverse=True)
    return scored

# -----------------------------
# LLM Logic (2단계)
# -----------------------------
def _compact_candidates(cands: List[Dict[str, Any]], max_ing=12) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in cands:
        toks = _tokens_from_ingredients_text(c.get("ingredients_text") or "")
        out.append({
            "recipe_id": c["recipe_id"],
            "title": c.get("title"),
            "difficulty_raw": (c.get("difficulty") or "").strip(),
            "cook_time": c.get("cook_time"),
            "ingredients": toks[:max_ing],
            "match_count": c.get("match_count", 0),
            "match_ratio": c.get("match_ratio", 0),
            "tag": c.get("tag"),
        })
    return out

def llm_pick_top3_json(profile, fridge_df, cands: List[Dict[str, Any]], recent_emphasis: List[str]) -> List[int]:
    name = profile.get("name") or "사용자"
    level = profile.get("cooking_level") or "-"
    fridge_list = ", ".join(fridge_df["item_name"].map(str).head(12).tolist())
    compact = _compact_candidates(cands)

    user_msg = f"""
[사용자]
- 이름: {name}
- 요리 레벨: {level}
- 냉장고 재료: {fridge_list}
- 최근 저장 재료(신선도 우선): {recent_emphasis}

[작업]
아래 후보 레시피 전체(cands)에서 사용자에게 가장 적합한 3개를 선정하세요.
선정시 가중치: match_count(매칭 개수)와 match_ratio(충당률)이 높을수록 우선, 난이도는 '{level}'에 과하지 않게, 주재료 중복 최소화.

cands(JSON):
{json.dumps(compact, ensure_ascii=False)}

출력은 아래 '정확한 JSON'만 반환. 다른 텍스트 금지.
{{
  "picks": [111111, 222222, 333333]
}}
"""
    rsp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "반드시 JSON만 출력한다. 키는 picks 하나, 값은 정수 recipe_id 3개 배열."},
            {"role": "user", "content": user_msg},
        ],
    )
    raw = rsp.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
        picks = data.get("picks") or []
        picks = [int(x) for x in picks if isinstance(x, (int, str)) and str(x).isdigit()]
        return picks[:3]
    except Exception:
        return [c["recipe_id"] for c in cands[:3]]

def render_text_from_picks(profile, fridge_df, chosen: List[Dict[str, Any]], recent_emphasis: List[str]) -> str:
    name = profile.get("name") or "사용자"
    level = profile.get("cooking_level") or "-"
    fridge_list = ", ".join(fridge_df["item_name"].map(str).head(12).tolist())

    ftoks = _fridge_token_set(fridge_df)
    clean: List[Dict[str, Any]] = []
    for c in chosen:
        toks = _tokens_from_ingredients_text(c.get("ingredients_text") or "")
        c2 = {
            "recipe_id": c["recipe_id"],
            "title": c.get("title"),
            "difficulty_raw": (c.get("difficulty") or "").strip(),
            "cook_time": c.get("cook_time"),
            "ingredients_text": c.get("ingredients_text") or "",
            "steps_text": c.get("steps_text") or "",
        }
        miss: List[str] = []
        for t in toks:
            t2 = _simplify_token(t)
            # missing 조건: 냉장고 토큰(ftoks)과 부분적으로도 겹치지 않는 재료만 포함
            if t2 and all((t2 not in f) and (f not in t2) for f in ftoks):
                miss.append(t)
        c2["missing"] = miss[:6]
        clean.append(c2)

    user_msg = f"""
[요약]
- {name}님의 냉장고 재료: {fridge_list}
- 최근 재료(신선도): {recent_emphasis}
- 요리 레벨: {level}

[선정된 3개(원본)]
{json.dumps(clean, ensure_ascii=False)}

[출력 규칙]
- 아래 '형식'을 반드시 지킬 것.
- 난이도는 difficulty_raw 값을 '그대로' 출력.
- 조리 순서는 steps_text에서 '조리 지시'만 남기고 후기/감상/광고/느낌/잡담/이모지 제거. 단계당 1문장으로 정리.
- [대체 재료 TIP]은 각 레시피마다 최소 1줄 포함.
  - missing 배열의 각 재료마다 1~2개 실무적인 대체안과 한 줄 이유를 제시.
  - missing이 비어 있어도, 일반적 치환 1~2개를 제안하여 섹션을 유지.
- 섹션 제목 뒤 콜론(:) 금지, 이모지/이모티콘 금지.

[형식]
"**{name}님! 냉장고 속 재료로 만들기 좋은 상위 3가지 요리를 추천드릴게요.**"

1. 레시피명 (ID: recipe_id, 난이도/시간: '쉬움, 20분 소요')
  - [필요 재료]
    (ingredients_text 원문을 재료 목록으로 정리)
  - [조리 순서]
    1) ...
    2) ...
  - [대체 재료 TIP]
    · (재료명) → (대체안 1/2, 한 줄 이유)

2. ...
3. ...
"""
    rsp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=3000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    return rsp.choices[0].message.content

# -------------------------------
# Public API
# -------------------------------
def recommend_json(user_id: Optional[str], limit: int = 3, exclude_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    uid = user_id or pick_random_user_with_fridge()
    profile = get_user_profile(uid)
    fridge = get_user_fridge_item(uid)

    keywords = pick_keywords_from_fridge_all(fridge, max_n=30)
    recent = recent_items_from_fridge(fridge, days=10, top=8)

    # 1. DB에서 넓게 수집 (300개)
    raw_cands = _fetch_candidates_like_any(keywords, limit=300)  # 함수명 주의!
    if not raw_cands:
        return {"error": "레시피 후보가 없습니다."}

    # 2. 스코어링 및 필터링 (유사 일치 로직 적용)
    fridge_tokens = _fridge_token_set(fridge)
    scored = _score_and_filter(raw_cands, fridge_tokens)

    # 3. LLM 후보 제한 (상위 50개만 LLM에 전달)
    llm_cands = scored[:50]

    # 이미 본 ID 제외
    exclude_set = set(exclude_ids or [])
    cands = [c for c in llm_cands if c["recipe_id"] not in exclude_set]
    if not cands:
        return {"error": "새롭게 추천할 후보가 더 없습니다."}

    # (A) LLM이 Top3 recipe_id를 JSON으로 선정
    pick_ids = llm_pick_top3_json(profile, fridge, cands, recent)
    if len(pick_ids) < 3:
        # 부족하면 후보에서 보충
        more = [c["recipe_id"] for c in cands if c["recipe_id"] not in pick_ids][: (3 - len(pick_ids))]
        pick_ids.extend(more)

    # 선택된 상세 레코드
    by_id = {c["recipe_id"]: c for c in raw_cands}
    chosen = [by_id[i] for i in pick_ids if i in by_id][:3]

    # (B) 그 3개로 자연어 출력 생성
    llm_text = render_text_from_picks(profile, fridge, chosen, recent)

    # 냉장고 샘플(이름(용량))
    def _fmt(row: pd.Series) -> str:
        name = str(row["item_name"])
        amt = row.get("amount")
        if pd.isna(amt) or str(amt).strip() == "":
            return name
        return f"{name}({amt})"

    fridge_sample = fridge.apply(_fmt, axis=1).head(12).tolist()

    return {
        "userId": uid,
        "fridgeSample": fridge_sample,
        "recentEmphasis": recent,
        "llm_recommendation_text": llm_text,
        "picks": [int(x) for x in pick_ids[:3]],
    }
