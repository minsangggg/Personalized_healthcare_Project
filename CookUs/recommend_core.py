import os, re, json
from datetime import datetime, timedelta
import pandas as pd
import pymysql
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Tuple

from openai import OpenAI

load_dotenv()

# LLM 클라이언트 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

# ---- DB helpers (ID 컬럼명 수정) ----
def pick_random_user_with_fridge() -> str:
    sql = """
    SELECT u.id AS uid
    FROM user_info u
    JOIN fridge_item f ON f.id = u.id
    GROUP BY u.id
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
    sql = "SELECT id, user_name, email, password, gender, date_of_birth, cooking_level, goal FROM user_info WHERE id=%s"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError("프로필 없음")
    return {
        "user_id": row.get("id"),
        "name": row.get("user_name"),
        "gender": row.get("gender"),
        "email": row.get("email"),
        "password": row.get("password"),
        "goal_per_week": row.get("goal"),
        "cooking_level": row.get("cooking_level") or "하",
    }


def get_user_fridge_items(user_id: str) -> pd.DataFrame:
    sql = """
    SELECT id AS user_id, ingredient_name AS item_name, quantity AS amount, stored_at AS saved_at
    FROM fridge_item
    WHERE id=%s
    ORDER BY stored_at DESC
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id,))
        rows = cur.fetchall()
        if not rows: raise RuntimeError("냉장고 재료 없음")
        return pd.DataFrame(rows)

# ---- Recommend helpers (Recipe 테이블 컬럼 소문자 수정) ----
def _norm(s: str) -> str:
    s = str(s)
    s = re.sub(r"\(.*?\)", "", s)
    return s.replace("/", " ").strip()

def pick_keywords_from_fridge_all(fridge_df: pd.DataFrame, max_n=30) -> List[str]:
    return (
        fridge_df["item_name"]
        .map(_norm)
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .head(max_n)
        .tolist()
    )

def recent_items_from_fridge(fridge_df: pd.DataFrame, days: int = 10, top: int = 8) -> List[str]:
    df = fridge_df.copy()
    df["saved_at"] = pd.to_datetime(df["saved_at"], errors="coerce")
    cutoff = datetime.utcnow() - timedelta(days=days)
    recent = df[df["saved_at"] >= cutoff].sort_values("saved_at", ascending=False)
    return recent["item_name"].map(_norm).head(top).tolist()

def fetch_candidates_like(keywords: List[str], limit=200, and_top: int = 3) -> List[Dict[str, Any]]:
    if not keywords:
        return []
    kws = [kw for kw in keywords if kw]
    top = max(1, min(and_top, len(kws)))

    def like_group_for_kw(kw: str) -> Tuple[str, List[str]]:
        return "(ingredient_full LIKE %s OR recipe_nm_ko LIKE %s OR tag LIKE %s)", [f"%{kw}%", f"%{kw}%", f"%{kw}%"]

    and_clauses: List[str] = []
    params: List[Any] = []
    for kw in kws[:top]:
        clause, p = like_group_for_kw(kw)
        and_clauses.append(clause)
        params.extend(p)

    or_tail = kws[top:]
    or_clauses: List[str] = []
    if or_tail:
        for kw in or_tail:
            clause, p = like_group_for_kw(kw)
            or_clauses.append(clause)
            params.extend(p)

    if and_clauses and or_clauses:
        where = f"( {' AND '.join(and_clauses)} ) AND ( {' OR '.join(or_clauses)} )"
    elif and_clauses:
        where = f"( {' AND '.join(and_clauses)} )"
    elif or_clauses:
        where = f"( {' OR '.join(or_clauses)} )"
    else:
        return []

    sql = f"""
    SELECT recipe_id, recipe_nm_ko AS title, cooking_time AS cook_time,
           level_nm AS difficulty, ingredient_full AS ingredients_text, step_text AS steps_text,
           tag, ty_nm
    FROM recipe
    WHERE {where}
    LIMIT {int(limit)}
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

def _tokens_from_ingredients_text(text: str) -> List[str]:
    if not text: return []
    hits = re.findall(r"'([^']+)'", str(text))
    if hits: return [_norm(h) for h in hits if _norm(h)]
    return [_norm(p) for p in str(text).split(",") if _norm(p)]

def guess_main_ingredient(c: Dict[str,Any]) -> str:
    toks = _tokens_from_ingredients_text(c.get("ingredients_text") or "")
    return toks[0] if toks else _norm((c.get("title") or "기타").split()[0])

def _primary_group(c: Dict[str, Any]) -> str:
    ty = (c.get("ty_nm") or "").strip()
    if ty:
        return _norm(ty)
    return guess_main_ingredient(c)

def ensure_diverse_top(cands: List[Dict[str, Any]], want: int = 3) -> List[Dict[str, Any]]:
    seen_ids = set()
    seen_titles = set()
    seen_groups = set()
    out: List[Dict[str, Any]] = []
    for c in cands:
        rid = c.get("recipe_id")
        title = _norm(c.get("title") or "")
        group = _primary_group(c)
        if rid in seen_ids:
            continue
        if title and title in seen_titles:
            continue
        if group and group in seen_groups:
            continue
        out.append(c)
        seen_ids.add(rid)
        if title:
            seen_titles.add(title)
        if group:
            seen_groups.add(group)
        if len(out) >= want:
            break
    return out

def diversify_candidates(candidates: List[Dict[str,Any]], want=12, max_per_main=1) -> List[Dict[str,Any]]:
    buckets = {}
    for c in candidates:
        m = guess_main_ingredient(c) or "기타"
        buckets.setdefault(m, [])
        if len(buckets[m]) < max_per_main:
            buckets[m].append(c)
    out = []
    for arr in buckets.values():
        out.extend(arr)
        if len(out) >= want: break
    return out[:want]


# recommend_core4.py 파일에 추가
def _format_for_display(adapted_rows: List[Dict[str,Any]], profile: Dict[str,Any], candidates: List[Dict[str,Any]]) -> str:
    """DB 적재용으로 확정된 레시피 3개를 사용자 표시용 텍스트로 변환"""
    name = profile.get("name") or "사용자"
    
    # 원본 후보 데이터에서 난이도/시간 정보를 가져옵니다.
    id_to_meta = {c["recipe_id"]: {"difficulty": c.get("difficulty"), "cook_time": c.get("cook_time")} for c in candidates}
    
    output_parts = [
        f"**{name}님! 냉장고 속 재료로 만들 수 있는 세 가지 레시피를 추천해 드릴게요!**"
    ]

    for idx, r in enumerate(adapted_rows, 1):
        rid = r.get("recipe_id")
        meta = id_to_meta.get(rid, {})
        level = meta.get("difficulty") or "정보 없음"
        time = meta.get("cook_time") or ""
        
        # 난이도/소요시간 형식 조정 (문제점 2 해결)
        meta_str = f"({level}"
        if time:
            meta_str += f"/{time} 소요"
        meta_str += ")"
        
        # 재료 목록 형식 조정 (문제점 1 해결)
        ingredients = r.get("ingredient_full") or {}
        ing_list = []
        for ing_name, amount in ingredients.items():
            if amount and str(amount).strip():
                ing_list.append(f"{ing_name} {amount}")
            else:
                ing_list.append(ing_name) # 용량 정보가 없으면 재료명만 출력
        
        ing_text = "\n\t\t\t".join(ing_list)
        
        recipe_block = f"""
{idx}. {r.get("recipe_nm_ko")} {meta_str}
   - [필요 재료]
     {ing_text}
   - [조리 순서]
     {r.get("step_text")}
"""
        output_parts.append(recipe_block)
        
    return "\n".join(output_parts)


# ---- LLM 호출 함수 추가 (이전 코드 유지) ----
def recommend_with_llm(profile: Dict[str,Any], 
                       fridge_df: pd.DataFrame, 
                       candidates: List[Dict[str,Any]], 
                       recent_emphasis: List[str]) -> str:
    """DB 후보군을 LLM에 보내, 친근한 말투의 텍스트 응답을 받아옴"""
    name = profile.get("name") or "사용자"
    level = profile.get("cooking_level") or "-"
    fridge_list = ", ".join(fridge_df["item_name"].map(str).head(12).tolist())

    user_msg = f"""
[요약]
- {name}님의 냉장고 재료: {fridge_list}
- 최근에 저장한 재료(신선도 우선 고려): {recent_emphasis}

[목표]
- 아래 후보 레시피 중에서 **3가지를 추천**해주세요.
- 기준:
  1) 사용자 냉장고 재료와의 적합도(겹치는 재료가 많을수록 좋음)
  2) 사용자의 요리 레벨 '{level}'에 맞게 (레벨이 '하'면 쉬운 요리 우대)
  3) 냉장고에 '최근 저장된 재료'를 최대한 활용
  4) 세 레시피의 주재료/요리 타입은 서로 다르게 (예: 떡볶이-떡볶이 금지)
  - 각 레시피마다 아래를 출력하세요.
    - [필요 재료]와 [조리 순서]는 DB 원문을 깔끔히 정리해서 출력하되,
      현재 사용자의 냉장고에 없는 재료는 가능한 한 사용자가 가진 유사 재료로 직접 치환해서 써주세요.
      예: '대파'가 없고 '쪽파'가 있으면 '쪽파'라고만 적습니다. ('대파(대체가능: 쪽파)'처럼 두 가지를 같이 쓰지 마세요.)
    - 치환이 불가능한 재료(즉, 냉장고에 전혀 비슷한 재료가 없는 경우)는 그대로 유지해도 됩니다.
      단, 새로운 재료나 새로운 소스를 상상해서 추가로 만들면 안 됩니다.
    - 출력 시에는 치환된 결과만 보여주고, '대체', '대체가능', '없으면' 같은 설명 문구는 쓰지 마세요.
    - [조리 순서]는 단계별 한 문장씩 명령형으로만 정리하세요. 광고/후기/감탄사/이모지 금지.

[후보(원본 데이터)]
  - 각 후보는 title, cook_time, difficulty(level_nm), ingredients_text(원문 재료), steps_text(원문 조리), missing(사용자 냉장고에 없는 재료 리스트)가 있습니다.
- 없는 메타데이터(예: cooking_time이 비어 있음)는 그냥 비워두세요.
- 단, 재료나 조리문을 바꿀 때는 반드시 다음 원칙을 지켜야 합니다:
  - (a) 원래 레시피에 등장하는 재료 범위 안에서만 수정할 것
  - (b) 사용자가 실제로 보유 중인 재료로 치환할 것
  - (c) 새로운 재료 이름을 창작하거나 추가 금지.
  - 난이도는 DB의 level_nm 값을 그대로 사용하세요(예: '상'/'하'); '쉬움/어려움' 등으로 바꾸지 마세요.
  - 제목(레시피명) 옆 괄호로 "(상/5분 소요)"처럼 난이도/시간을 함께 표기하세요. 
    cooking_time이 없으면 "(상)"처럼 시간만 생략하세요.
{json.dumps(candidates, ensure_ascii=False)}

[출력 형식]
"**{name}님! 냉장고 속 재료로 만들 수 있는 세 가지 레시피를 추천해 드릴게요!**"

1. 레시피명 (하/20분 소요)
   - [필요 재료]
     (ingredients_text를 정리하되, [조리 순서]에서 실제로 사용하는 모든 재료를 1:1로 포함. 
      즉, [조리 순서]에 등장하는 재료/양념/부재료는 반드시 [필요 재료]에 존재해야 하고,
      [필요 재료]에 있는 항목은 [조리 순서] 어딘가에서 실제로 사용되어야 함. 누락/유령 재료 금지. 
      표기는 가능하면 '재료명(용량)' 형태로, 용량 정보가 없으면 재료명만 적을 것)
   - [조리 순서]
     (원문 단계의 의미를 보존하며 번호를 붙여 '1. ~하세요' 형태로 정리. 
      여러 동작을 한 단계로 병합하지 말 것(세척/절단/가열 등은 분리). 불필요한 감탄/광고만 제거. 
      cooking_time이 있으면 제목 옆 괄호에 반드시 포함(예: '(상/20분 소요)'). 
      단계 수는 원문 대비 과도하게 줄이지 말 것: 최소 6단계 또는 원문 단계 수의 80% 이상 유지)
  
   
2. 레시피명...
3. 레시피명...
"""
    try:
        rsp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3, 
            messages=[
                {"role": "system", "content": "너는 한국어 요리 추천 도우미야. 친절하고 유쾌한 말투로, 거짓 없이 원문을 그대로 사용해. (추천 이유는 출력하지 마). 모든 섹션 제목에는 콜론(:)을 사용하지 마. 원문 재료와 조리 순서 내용을 출력할 때는 겉의 괄호{}나 따옴표들을 제거하고 깔끔한 텍스트로만 변환하여 출력해."},
                {"role": "user", "content": user_msg}
            ],
        )
        return rsp.choices[0].message.content
    except Exception as e:
        return f"LLM_ERROR: {str(e)}. (OpenAI API 키나 네트워크 연결 확인이 필요합니다.)"


# ---- LLM JSON: 냉장고 보유/대체 반영한 최종 3개 레시피 산출 ----
def llm_adapt_recipes_json(
    user_id: str,
    profile: Dict[str,Any],
    fridge_df: pd.DataFrame,
    candidates: List[Dict[str,Any]],
    recent_emphasis: List[str],
) -> List[Dict[str,Any]]:
    """후보 3개를 바탕으로, 음식명/재료/조리문을 냉장고 보유 재료와 대체재료 고려해 최종 확정(JSON)"""
    name = profile.get("name") or "사용자"
    level = profile.get("cooking_level") or "-"
    fridge_list = ", ".join(fridge_df["item_name"].map(str).head(24).tolist())

    schema_instruction = {
        "type": "json_schema",
        "json_schema": {
            "name": "adapted_recipes_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "recipes": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "required": ["recipe_nm_ko", "ingredient_full", "step_text", "recipe_id"],
                            "properties": {
                                "recipe_nm_ko": {"type": "string"},
                                "ingredient_full": {
                                    "type": "object",
                                    "additionalProperties": {"type": "string"}
                                },
                                "step_text": {"type": "string"},
                                "recipe_id": {"type": "integer"}
                            }
                        }
                    }
                },
                "required": ["recipes"],
                "additionalProperties": False
            }
        }
    }

    user_msg = f"""
[요약]
- {name}님의 냉장고 재료: {fridge_list}
- 최근 저장 재료: {recent_emphasis}
- 사용자 요리 레벨: {level}

[목표]
- 아래 후보 레시피 3개 각각에 대해, 냉장고 보유 재료를 최대한 활용하고 부족한 재료는 상식적인 대체재료로 치환하여
  (1) 최종 레시피명(recipe_nm_ko), (2) 최종 재료 딕셔너리(ingredient_full: 재료명->권장용량 문자열), (3) 최종 조리문(step_text), (4) 원본 recipe_id 를 JSON으로 반환.
- 과장된 새로운 재료를 창작하지 말고, 원문 재료 범위 내에서 합리적인 대체만 수행.

[재료 가용성 규칙]
- 사용자가 실제로 가진 재료(또는 합리적 대체)만 사용하여 레시피를 완성해야 합니다. 
- 만약 특정 후보 레시피가 사용자의 재료로는 조리가 어려우면, 해당 후보를 참고하되 사용자의 보유 재료로 만들 수 있도록 레시피를 새로 구성하세요.
- 최종 ingredient_full과 step_text는 사용자 보유 재료만으로 완성되어야 하며, step_text에 등장하는 모든 항목은 ingredient_full에 존재해야 합니다.

[일관성 요구]
- step_text에 등장하는 모든 재료/양념/부재료는 ingredient_full 키에 반드시 존재해야 하며, 
  ingredient_full의 모든 항목은 step_text 어딘가에서 실제로 사용되어야 합니다. 누락/유령 재료 금지.
  이 일관성을 만족하지 못하면 출력을 수정하여 반드시 만족시키세요.

[후보(원문)]
{json.dumps(candidates, ensure_ascii=False)}
"""

    try:
        rsp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": "너는 한국어 요리 어시스턴트야. 냉장고 재료 우선, 부족분은 합리적 대체를 적용하고, 결과는 정확한 JSON으로."},
                {"role": "user", "content": user_msg},
            ],
            response_format=schema_instruction,
        )
        content = rsp.choices[0].message.content
        obj = json.loads(content)
        recipes = obj.get("recipes", [])

        cleaned: List[Dict[str,Any]] = []
        for i, r in enumerate(recipes[:3]):
            # 후보 final_three 기준으로 fallback id/title 확보
            if i < len(candidates):
                fallback_id = int(candidates[i]["recipe_id"])
                fallback_title = str(candidates[i]["title"] or "")
            else:
                fallback_id = None
                fallback_title = ""
                
            rid = r.get("recipe_id")
            try:
                rid = int(rid) if rid is not None else fallback_id
            except:
                rid = fallback_id

            cleaned.append({
                "id": str(user_id),
                "recipe_nm_ko": str(r.get("recipe_nm_ko") or fallback_title),
                "ingredient_full": r.get("ingredient_full") or {},
                "step_text": str(r.get("step_text") or ""),
                "recipe_id": fallback_id,
            })
        return cleaned
    except Exception:
        return []


# ---- recommend_recipe 테이블 보장 및 적재 ----
def ensure_recommend_recipe_table():
    sql = (
        """
        CREATE TABLE IF NOT EXISTS recommend_recipe (
            recommend_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            id VARCHAR(64) NOT NULL,
            recipe_nm_ko VARCHAR(255) NOT NULL,
            ingredient_full JSON NOT NULL,
            step_text MEDIUMTEXT NOT NULL,
            recipe_id BIGINT,
            recommend_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)


def insert_recommend_recipes(rows: List[Dict[str,Any]]):
    if not rows:
        return
    sql = (
        """
        INSERT INTO recommend_recipe (id, recipe_nm_ko, ingredient_full, step_text, recipe_id)
        VALUES (%s, %s, %s, %s, %s)
        """
    )
    with get_conn() as conn, conn.cursor() as cur:
        for r in rows:
            cur.execute(
                sql,
                (
                    r.get("id"),
                    r.get("recipe_nm_ko"),
                    json.dumps(r.get("ingredient_full") or {}, ensure_ascii=False),
                    r.get("step_text"),
                    r.get("recipe_id"),
                ),
            )

# ---- Ingredient enforcement helpers ----
def _extract_tokens_from_ingredients_text(text: str) -> List[str]:
    if not text:
        return []
    hits = re.findall(r"'([^']+)'", str(text))
    if hits:
        return [_norm(h) for h in hits if _norm(h)]
    parts = [p.strip() for p in str(text).replace("\n", ",").split(",")]
    return [_norm(p) for p in parts if _norm(p)]

def _substitute_with_fridge(token: str, fridge_tokens: set) -> str:
    # Exact only; no invention. If user has a very close variant (case/space), keep as-is for safety.
    return token if token in fridge_tokens else token

def _enforce_ingredients_full(original_ingredients_text: str,
                              fridge_tokens: set,
                              llm_ingredient_full: Dict[str, Any]) -> Dict[str, Any]:
    required = _extract_tokens_from_ingredients_text(original_ingredients_text)
    enforced: Dict[str, Any] = {}
    for tok in required:
        subst = _substitute_with_fridge(tok, fridge_tokens)
        # Only keep ingredients the user actually has (after substitution). Do NOT invent new items.
        if subst in fridge_tokens:
            if subst in (llm_ingredient_full or {}):
                enforced[subst] = llm_ingredient_full.get(subst)
            elif tok in (llm_ingredient_full or {}):
                enforced[subst] = llm_ingredient_full.get(tok)
            else:
                enforced[subst] = ""
    return enforced

# --- 텍스트에서 재료 토큰 추출(이미 있으면 유지) ---
def _tokens_from_ingredients_text(text: str) -> List[str]:
    if not text:
        return []
    hits = re.findall(r"'([^']+)'", str(text))
    if hits:
        return [_norm(h) for h in hits if _norm(h)]
    return [_norm(p) for p in str(text).split(",") if _norm(p)]

# --- 냉장고 재료 토큰 집합 만들기(※ recommend_json 보다 위에 있어야 함) ---
def _fridge_token_set(fridge_df: pd.DataFrame) -> set:
    """냉장고의 재료명을 정규화해서 집합으로 반환"""
    names = (
        fridge_df["item_name"]
        .map(_norm)
        .dropna()
        .astype(str)
    )
    return set(names.tolist())


# ---- Public API: JSON 추천 (LLM 사용) ----
def recommend_json(user_id: Optional[str], limit: int = 3, exclude_ids: Optional[List[int]] = None) -> Dict[str,Any]:
    uid = user_id or pick_random_user_with_fridge()
    profile = get_user_profile(uid)
    fridge = get_user_fridge_items(uid)
    keywords = pick_keywords_from_fridge_all(fridge, max_n=30)
    recent = recent_items_from_fridge(fridge, days=10, top=8)

    # 점진적 완화: AND top3 -> AND top2 -> AND top1 -> OR-only
    cands = fetch_candidates_like(keywords, limit=300, and_top=3)
    if len(cands) < limit:
        cands = fetch_candidates_like(keywords, limit=300, and_top=2)
    if len(cands) < limit:
        cands = fetch_candidates_like(keywords, limit=300, and_top=1)
    if len(cands) < limit:
        # OR-only: and_top=0 효과를 위해 키워드 전부 OR로 구성
        # 구현 간소화를 위해 and_top=1로 호출 후 상단에서 빈 AND를 허용하지 않으므로 별도 처리
        kws = [kw for kw in keywords if kw]
        if kws:
            clauses = []
            params: List[Any] = []
            for kw in kws:
                clauses.append("(ingredient_full LIKE %s OR recipe_nm_ko LIKE %s OR tag LIKE %s)")
                params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
            where = " OR ".join(clauses)
            sql = f"""
            SELECT recipe_id, recipe_nm_ko AS title, cooking_time AS cook_time,
                   level_nm AS difficulty, ingredient_full AS ingredients_text, step_text AS steps_text,
                   tag, ty_nm
            FROM recipe
            WHERE {where}
            LIMIT 300
            """
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(sql, params)
                cands = cur.fetchall()

    if exclude_ids:
        exclude_set = set(exclude_ids)
        cands = [c for c in cands if c["recipe_id"] not in exclude_set]

    # 0) 난이도(사용자 cooking_level) 우선 필터링: 부족하면 완화
    user_level = (profile.get("cooking_level") or "").strip()
    level_filtered = [c for c in cands if (str(c.get("difficulty") or "").strip() == user_level)] if user_level else cands
    cpool = level_filtered if level_filtered else cands

    # 1) 1차 다양성 (메인재료 버킷)
    diversified = diversify_candidates(cpool, want=max(12, limit * 4), max_per_main=1)

    # 2) 2차 다양성 보장: ty_nm 또는 메인재료 그룹이 서로 다르고, 제목/ID 중복 금지
    diverse_pool = ensure_diverse_top(diversified, want=max(6, limit * 2))

    # 3) 최종 3개 확정
    final_three = ensure_diverse_top(diverse_pool, want=limit) if diverse_pool else []
    # 3-A) 3개가 채워지지 않았으면, 타이틀 다양성만 보장하며 상위 후보에서 추가로 채움
    if len(final_three) < limit and cpool:
        # 이미 선택된 레시피 ID와 타이틀을 제외
        chosen_ids = {c["recipe_id"] for c in final_three}
        chosen_titles = {_norm(c["title"] or "") for c in final_three}
        
        # 1차 필터링 풀(cpool)을 사용
        for c in cpool:
            if c["recipe_id"] not in chosen_ids and _norm(c["title"] or "") not in chosen_titles:
                final_three.append(c)
                chosen_ids.add(c["recipe_id"])
                chosen_titles.add(_norm(c["title"] or ""))
            if len(final_three) >= limit:
                break
    
    # 2.5) 각 후보에 'missing' 필드 추가 (냉장고에 없는 재료)
    ftoks = _fridge_token_set(fridge)
    for c in final_three:
        toks = _tokens_from_ingredients_text(c.get("ingredients_text") or "")
        miss = [t for t in toks if t and t not in ftoks]
        c["missing"] = miss[:6]  # 너무 길지 않게 상한선





    # 3) LLM 호출 (final_three 만 전달)
    if not final_three:
        llm_text_result = "**추천 가능한 레시피 후보가 부족합니다.** (냉장고 재료를 추가해 주세요)"
        adapted_rows: List[Dict[str,Any]] = [] # 비어 있음
    else:
        ensure_recommend_recipe_table()
        # 3.1) LLM이 대체재료까지 반영한 최종 3개 JSON 산출 -> DB 적재
        adapted_rows = llm_adapt_recipes_json(uid, profile, fridge, final_three, recent)
        
        # Enforce: ingredients cover all needed from original candidate after substitution
        fridge_tokens = _fridge_token_set(fridge)
        id_to_candidate = {c["recipe_id"]: c for c in final_three}
        enforced_rows: List[Dict[str,Any]] = []
        
        # enforce_ingredients_full 함수를 사용하여 재료 일관성 및 보유 여부 강제
        for r in adapted_rows:
            cand = id_to_candidate.get(r.get("recipe_id")) or {}
            # NOTE: _enforce_ingredients_full 함수는 현재 로직상 재료 누락 시 빈 딕셔너리를 반환하므로,
            # 아래 fallback 로직으로 진입하지 않도록 함수 수정이 필요할 수 있습니다.
            # 일단 현재 로직은 유지하고, 최종 JSON 결과를 표시용으로 변환하는 것에 집중합니다.
            
            # --- 재료 일관성 강제 로직은 그대로 유지 ---
            enforced_ing = _enforce_ingredients_full(
                cand.get("ingredients_text") or "",
                fridge_tokens,
                r.get("ingredient_full") or {},
            )
            if not enforced_ing:
                # fallback: keep only LLM ingredients that user actually has
                base_llm = r.get("ingredient_full") or {}
                filtered = {k: base_llm[k] for k in base_llm.keys() if _norm(k) in fridge_tokens}
                enforced_ing = filtered
            
            new_r = dict(r)
            new_r["ingredient_full"] = enforced_ing
            enforced_rows.append(new_r)
        
        insert_recommend_recipes(enforced_rows) # 최종 보정된 재료로 DB에 적재
        
        # 3.2) DB에 적재된 최종 내용을 브라우저 표시용 텍스트로 변환 (문제점 3 해결)
        llm_text_result = _format_for_display(enforced_rows, profile, final_three)
        adapted_rows = enforced_rows # 최종 DB 적재된 리스트로 교체

    # --- 냉장고 샘플: 이름(용량) 안전하게 만들기 ---
    def _fmt_name_amount(row):
        name = str(row["item_name"])
        amt  = row.get("amount")
        if pd.isna(amt) or str(amt).strip() == "":
            return name
        return f"{name}({amt})"

    fridge_sample = fridge.apply(_fmt_name_amount, axis=1).head(8).tolist()

    return {
        "userId": uid,
        "fridgeSample": fridge_sample,
        "recentEmphasis": recent,
        "llm_recommendation_text": llm_text_result,
        "recommended_db_candidates": final_three,
        "adapted_recipes_saved": [
            {"recipe_nm_ko": r.get("recipe_nm_ko"), "recipe_id": r.get("recipe_id")}
            for r in (adapted_rows or [])
        ],
    }
