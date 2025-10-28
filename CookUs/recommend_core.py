# recommend_core.py
import os, re, json
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher

import pandas as pd
import pymysql
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== Params =====
CARD_LIMIT_DEFAULT = 3
LLM_CANDIDATES_MAX = 10
TOP_WINDOW = 5  # 주재료 창 범위(앞 3~5개)

# ===== DB =====
def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        charset=os.getenv("DB_CHARSET","utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

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
        if not row: raise RuntimeError("공통 ID 없음")
        return row["uid"]

def get_user_profile(user_id: str) -> Dict[str, Any]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM user_info WHERE ID=%s", (user_id,))
        row = cur.fetchone()
        if not row: raise RuntimeError("프로필 없음")
    low = {k.lower(): v for k,v in row.items()}
    return {
        "user_id": low.get("id"),
        "name": low.get("user_name") or low.get("name"),
        "cooking_level": low.get("cooking_level") or "하",
    }

def _fridge_schema():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SHOW COLUMNS FROM fridge_item")
        cols = {r["Field"] for r in cur.fetchall()}
    def pick(cands):
        for c in cands:
            if c in cols: return c
        return None
    return {
        "name":     pick(["ingredient_name","item_name","name","재료"]),
        "qty":      pick(["quantity","qty","amount","용량"]),
        "saved_at": pick(["stored_at","saved_at","updated_at","저장일시"]),
    }

def get_user_fridge_items(user_id: str) -> pd.DataFrame:
    sc = _fridge_schema()
    if not sc["name"] or not sc["qty"]:
        raise RuntimeError("냉장고 스키마 오류")
    sel = [f"ID AS user_id", f"`{sc['name']}` AS item_name", f"`{sc['qty']}` AS amount"]
    if sc["saved_at"]: sel.append(f"`{sc['saved_at']}` AS saved_at")
    order_by = f"ORDER BY `{sc['saved_at']}` DESC" if sc["saved_at"] else ""
    sql = f"SELECT {', '.join(sel)} FROM fridge_item WHERE ID=%s {order_by}"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id,))
        rows = cur.fetchall()
        if not rows: raise RuntimeError("냉장고 재료 없음")
        return pd.DataFrame(rows)

# ===== Text utils =====
def _norm(s: str) -> str:
    s = str(s)
    s = re.sub(r"\(.*?\)", "", s)
    return s.replace("/", " ").strip()

def _try_json_load(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None

# --- dict-형 문자열에서 "키만" 순서대로 뽑기 (단일/이중 따옴표 모두) ---
_key_colon_re = re.compile(r"""['"]([^'"]+)['"]\s*:""")  # e.g. '양파': or "양파":
def _extract_ordered_keys_from_mapping_text(s: str) -> List[str]:
    # 1) 진짜 JSON object면 그대로 키 순서 사용(파이썬은 입력 순서 유지)
    js = _try_json_load(s)
    if isinstance(js, dict):
        return list(js.keys())

    # 2) 파이썬 dict 스타일(단일따옴표 포함)일 때 키만 추출
    keys = _key_colon_re.findall(s)
    if keys:
        return keys

    return []

# --- ingredients_text → 토큰 리스트(순서 유지, 키 우선) ---
def _tokens_from_ingredients_text(text: Any) -> List[str]:
    if text is None:
        return []

    # dict/list 그대로 들어오면 처리
    if isinstance(text, dict):
        return list(text.keys())
    if isinstance(text, list):
        seen, out = set(), []
        for el in text:
            if isinstance(el, dict):
                for k in el.keys():
                    t = _norm(k)
                    if t and t not in seen:
                        seen.add(t); out.append(t)
            else:
                t = _norm(el)
                if t and t not in seen:
                    seen.add(t); out.append(t)
        return out

    # 문자열인 경우
    s = str(text).strip()
    if not s:
        return []

    # 1) 매핑 텍스트(딕셔너리처럼 보임) ⇒ 키만 순서대로
    keys = _extract_ordered_keys_from_mapping_text(s)
    if keys:
        return [ _norm(k) for k in keys if _norm(k) ]

    # 2) JSON 배열/객체 시도
    js = _try_json_load(s)
    if js is not None:
        return _tokens_from_ingredients_text(js)

    # 3) 따옴표 토큰 우선, 없으면 구분자 split
    hits = re.findall(r"'([^']+)'|\"([^\"]+)\"", s)
    flat = [x for a,b in hits for x in (a,b) if x]
    base = flat if flat else re.split(r"[\n,|，、]+", s)

    seen, out = set(), []
    for t in base:
        t = _norm(t)
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out

# ===== Canon / synonyms =====
PANTRY = {
    "소금","설탕","후추","물","간장","식용유","올리브유","참기름","마요네즈","케첩","머스타드",
    "다진마늘","깨","깨소금","고춧가루","고추장","된장","맛술","버터","치즈","치킨스톡","육수",
    "식초","맛소금","참깨","조미료","msg"
}
_SYNONYM_GROUPS = [
    {"대파","파","쪽파"},
    {"돼지고기","삼겹살","목살","돈육"},
    {"소고기","쇠고기","한우","우육"},
    {"닭고기","닭","닭가슴살","닭다리","닭봉"},
    {"감자","알감자"},
    {"양파","적양파"},
    {"고추","청양고추","풋고추","홍고추"},
    {"국수","면","소면","중면","우동면"},
    {"쌀","밥"},
]
_SYNONYM_MAP: dict[str,str] = {w: sorted(g, key=len)[0] for g in _SYNONYM_GROUPS for w in g}
_unit_re = re.compile(r"\b\d+(\.\d+)?\s*(g|kg|ml|l|cup|컵|스푼|큰술|작은술|tsp|tbsp|개|장|줌)\b", re.I)

def _canon_token(s: str) -> str:
    s = _norm(s)
    s = _unit_re.sub("", s)
    s = re.sub(r"\s+", "", s).lower()
    return _SYNONYM_MAP.get(s, s)

def _tokenize_recipe(text: Any) -> List[str]:
    toks = _tokens_from_ingredients_text(text)
    out, seen = [], set()
    for t in toks:
        c = _canon_token(t)
        if c and c not in seen:
            seen.add(c); out.append(c)
    return out

def _build_fridge_set(fridge_df: pd.DataFrame) -> set[str]:
    names = fridge_df["item_name"].astype(str).map(_canon_token)
    core = [t for t in names if t and t not in PANTRY]
    if len(core) < 2: core += [t for t in names if t in PANTRY][:3]
    return set(core)

# ===== Main / First-ingredient helpers =====
def _first_ingredient_raw(text: Any) -> Optional[str]:
    if isinstance(text, dict):
        for k in text.keys():
            return _norm(k)
        return None
    if isinstance(text, list):
        if not text: return None
        el = text[0]
        if isinstance(el, dict):
            for k in el.keys():
                return _norm(k)
            return None
        return _norm(el)

    s = str(text).strip()
    if not s:
        return None
    keys = _extract_ordered_keys_from_mapping_text(s)
    if keys:
        return _norm(keys[0]) if keys else None
    js = _try_json_load(s)
    if js is not None:
        return _first_ingredient_raw(js)
    toks = _tokens_from_ingredients_text(s)
    return _norm(toks[0]) if toks else None

def guess_main_ingredient(c: Dict[str, Any], fridge_set: Optional[set]=None) -> str:
    first_raw = _first_ingredient_raw(c.get("ingredients_text") or "")
    if first_raw:
        return _canon_token(first_raw)
    toks = _tokenize_recipe(c.get("ingredients_text") or "")
    return toks[0] if toks else _canon_token((c.get("title") or "기타").split()[0])

# ===== Candidate search =====
def fetch_candidates_like(keywords: List[str], limit=400, use_or=False) -> List[Dict[str, Any]]:
    if not keywords: return []
    conj = " OR " if use_or else " AND "
    parts, params = [], []
    for kw in keywords:
        parts.append("(ingredient_full LIKE %s OR recipe_nm_ko LIKE %s)")
        like = f"%{kw}%"
        params.extend([like, like])
    where = conj.join(parts)
    sql = f"""
    SELECT recipe_id,
           recipe_nm_ko AS title,
           cooking_time AS cook_time,
           level_nm     AS difficulty,
           ingredient_full AS ingredients_text,
           step_text    AS steps_text
    FROM recipe
    WHERE {where}
    LIMIT {int(limit)}
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

# ===== Fuzzy overlap =====
def _fuzzy_overlap(fridge_set: set[str], recipe_tokens: List[str]) -> dict:
    rec = list(dict.fromkeys(recipe_tokens))
    rec_core = [t for t in rec if t not in PANTRY]
    window = rec[:TOP_WINDOW] if len(rec) >= 3 else rec[:3]

    top_exact = len(set(window) & fridge_set)
    exact = len(set(rec) & fridge_set)

    rest_f = [f for f in fridge_set if f not in rec]
    rest_r = [r for r in rec if r not in fridge_set]
    substr = 0; fuzzy = 0; used_r = set()
    for f in rest_f:
        hit = None
        for r in rest_r:
            if r in used_r: continue
            if f in r or r in f:
                hit = r; substr += 1; used_r.add(r); break
        if hit: continue
        for r in rest_r:
            if r in used_r: continue
            if SequenceMatcher(None, f, r).ratio() >= 0.84:
                fuzzy += 1; used_r.add(r); break

    coverage = (exact / max(1, len(rec_core))) if rec_core else (exact / max(1, len(rec)))
    matched_any = (set(rec) & fridge_set) | used_r
    missing_core = [t for t in rec_core if t not in matched_any]
    return {
        "top_exact": top_exact,
        "exact": exact,
        "substr": substr,
        "fuzzy": fuzzy,
        "coverage": round(coverage, 3),
        "missing_core": missing_core
    }

# ===== Filter & score — 첫 번째 재료 하드 조건 =====
def _basic_score_and_filter(
    cands: List[dict],
    fridge_set: set,
    min_exact: int = 1,
    min_coverage: float = 0.20,
    max_missing: int = 8,
):
    out = []
    for c in cands:
        first_raw = _first_ingredient_raw(c.get("ingredients_text") or "")
        first_can = _canon_token(first_raw) if first_raw else ""
        if not first_can or first_can not in fridge_set:
            continue

        rec_tokens = _tokenize_recipe(c.get("ingredients_text") or "")
        if not rec_tokens: continue

        m = _fuzzy_overlap(fridge_set, rec_tokens)
        if (m["exact"] < min_exact) and (m["coverage"] < min_coverage):
            continue
        if m["coverage"] < min_coverage:
            continue
        if len(m["missing_core"]) > max_missing:
            continue

        score = (
            10.0
            + 5*m["top_exact"] + 3*m["exact"] + 1.6*m["substr"] + 1.2*m["fuzzy"]
            + int(m["coverage"]*8)
            - 1.2*len(m["missing_core"])
            - 0.001*(c.get("cook_time") or 9999)
        )
        c["_score"] = float(score)
        c["_coverage"] = m["coverage"]
        c["_missing_count"] = len(m["missing_core"])
        c["_main"] = first_can
        out.append(c)

    out.sort(key=lambda x: (-x.get("_score",0), x.get("cook_time") or 9999))
    return out

# ===== Misc =====
def pick_keywords_from_fridge_all(fridge_df: pd.DataFrame, max_n=30) -> List[str]:
    return (
        fridge_df["item_name"].map(_norm)
        .dropna().astype(str).str.strip().drop_duplicates()
        .head(max_n).tolist()
    )

def _fmt_name_amount_row(row):
    name = str(row.get("item_name", "")).strip()
    if not name: return ""
    amt = row.get("amount")
    if pd.isna(amt) or str(amt).strip() == "": return name
    return f"{name}({amt})"

# ===== LLM (프롬프트 유지) =====
def recommend_with_llm(profile: Dict[str,Any], fridge_df: pd.DataFrame, candidates: List[Dict[str,Any]], recent_emphasis: List[str]) -> str:
    name = profile.get("name") or "사용자"
    level = profile.get("cooking_level") or "-"
    fridge_list = ", ".join(fridge_df["item_name"].map(str).head(12).tolist())
    user_msg = f"""
[요약]
- {name}님의 냉장고 재료: {fridge_list}

[목표]
- 아래 후보 레시피 중에서 **3가지를 추천**해주세요.
- 기준:
  1) 사용자 냉장고 재료와의 적합도(겹치는 재료가 많을수록 좋음)
  2) 사용자의 요리 레벨 '{level}'에 맞게 (레벨이 '하'면 쉬운 요리 우대)
  3) 냉장고 재료 저장일시가 최신인 재료를 활용한 요리 우선
  4) 세 레시피의 주재료는 서로 겹치지 않게
  - 각 레시피마다 아래를 포함하세요.
  - [필요 재료]와 [조리 순서]는 **DB 원문을 깔끔히 정리 (레시피와 관계없는 부호나 문자 삭제)**해서 출력
  - 만약 사용자 냉장고에 없는 재료가 있다면 **[대체 재료 TIP]** 섹션에서
    그 재료별로 1~2개 대체안을 제시(국룰/요리상식 기반, 간단한 이유 포함).
    대체안이 필요 없으면 이 섹션은 생략.

[후보(원본 데이터)]
- 각 후보는 title, cook_time, difficulty, ingredients_text(원문 재료), steps_text(원문 조리), missing(사용자 냉장고에 없는 재료 리스트)가 있습니다.
- 없는 값은 비워두고 **새로 만들어 넣거나 추측하지 마세요**.
{json.dumps(candidates, ensure_ascii=False)}

[출력 형식 — 형식 엄수]
"**{name}님! 냉장고 속 재료로 만들 수 있는 세 가지 레시피를 추천해 드릴게요!**"

1. 레시피명 (난이도/시간: 예: '쉬움, 20분 소요')
   - [필요 재료]
     (ingredients_text 내용을 깔끔하게 목록으로)
   - [조리 순서]
     (steps_text 내용을 단계별 줄바꿈)
   - [대체 재료 TIP]
     (missing 재료가 있을 때만, 재료별로 간단히 대체안 1~2개. 없으면 섹션 생략)
   
2. 레시피명...
3. 레시피명...

- [대체 재료 TIP]
    - 재료이름: 대체안1 / 대체안2 — 이유 간단히
    - ...
    
[형식 제약]
- 섹션 제목은 반드시 대괄호 포함 형태로 정확히: [필요 재료], [조리 순서], [대체 재료 TIP]
- 불릿은 무조건 하이픈+공백으로 시작: "- "
- 괄호{{}}나 따옴표는 제거하고 깔끔한 텍스트만 사용
- 추천 이유/코멘트는 쓰지 말 것
"""
    try:
        rsp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {"role":"system","content":"너는 한국어 요리 추천 도우미다. 형식 엄수."},
                {"role":"user","content":user_msg},
            ],
        )
        return rsp.choices[0].message.content
    except Exception as e:
        return f"LLM_ERROR: {str(e)}. (OpenAI API 키/네트워크 확인)"

# ===== Public =====
def recommend_json(user_id: Optional[str], limit: int = CARD_LIMIT_DEFAULT, exclude_ids: Optional[List[int]] = None) -> Dict[str,Any]:
    uid = user_id or pick_random_user_with_fridge()
    profile = get_user_profile(uid)
    fridge = get_user_fridge_items(uid)

    keywords = (
        fridge["item_name"].astype(str).map(_norm)
        .dropna().str.strip().drop_duplicates().head(30).tolist()
    )

    # 후보 검색
    cands = fetch_candidates_like(keywords, limit=800, use_or=False) or []
    if not cands:
        cands = fetch_candidates_like(keywords, limit=1000, use_or=True) or []
    if exclude_ids:
        ex = set(exclude_ids)
        cands = [c for c in cands if c["recipe_id"] not in ex]

    # 냉장고 토큰 세트
    fridge_set = _build_fridge_set(fridge)

    scored = _basic_score_and_filter(
        cands, fridge_set,
        min_exact=1, min_coverage=0.20, max_missing=8
    )

    if len(scored) < limit:
        quick = sorted(cands, key=lambda x: (x.get("cook_time") or 9999))
        for r in quick:
            if r in scored: continue
            first_raw = _first_ingredient_raw(r.get("ingredients_text") or "")
            if not first_raw: continue
            if _canon_token(first_raw) not in fridge_set:  # 하드조건
                continue
            scored.append(r)
            if len(scored) >= limit: break

    groups: Dict[str, List[dict]] = {}
    for r in scored:
        m = r.get("_main") or _canon_token(_first_ingredient_raw(r.get("ingredients_text") or "") or "")
        r["_main"] = m
        groups.setdefault(m, []).append(r)

    mains = sorted(groups.keys(), key=lambda m: -groups[m][0].get("_score",0))
    final: List[dict] = []
    for m in mains:
        final.append(groups[m][0])
        if len(final) >= limit: break
    if len(final) < limit:
        for r in scored:
            if r in final: continue
            final.append(r)
            if len(final) >= limit: break

    # LLM pool + missing
    llm_pool = final[:LLM_CANDIDATES_MAX] if final else scored[:LLM_CANDIDATES_MAX]
    def fill_missing(arr: list[dict]):
        for c in arr:
            toks = _tokenize_recipe(c.get("ingredients_text") or "")
            c["missing"] = [t for t in toks if t and t not in fridge_set][:6]
    fill_missing(llm_pool); fill_missing(final)

    # 냉장고 샘플
    try:
        fridge_sample = fridge.apply(lambda r: f"{r['item_name']}({r['amount']})" if pd.notna(r.get("amount")) and str(r.get("amount")).strip()!="" else str(r['item_name']), axis=1).dropna().tolist()
        fridge_sample = [s for s in fridge_sample if s][:8]
    except Exception:
        fridge_sample = fridge.get("item_name", pd.Series([], dtype=str)).astype(str).head(8).tolist()

    # LLM 텍스트
    llm_text = recommend_with_llm(profile, fridge, llm_pool, [])

    return {
        "userId": uid,
        "fridgeSample": fridge_sample,
        "recentEmphasis": [],
        "llm_recommendation_text": llm_text,
        "recommended_db_candidates": final[:limit],
    }
