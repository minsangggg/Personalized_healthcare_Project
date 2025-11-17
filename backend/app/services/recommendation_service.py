import json
import logging
import re
import traceback
from datetime import datetime
from typing import Any, List, Tuple

from fastapi import HTTPException
import json as _json
import re as _re
import hashlib

from app.db.connection import connection_scope
from app.schemas.recommendation import RecommendRequest, SelectedRecipe, SelectedRecipeAction
from app.services.llm_client import LLMAdaptationError, adapt_recipes_with_llm, estimate_recipe_costs

logger = logging.getLogger(__name__)


def _normalize_ingredients(ingredients: List[dict]) -> List[Tuple[str, str]]:
    normalized = []
    for ingredient in ingredients:
        name = str(ingredient.get("name", "")).strip().lower()
        amount = str(ingredient.get("amount", "")).strip()
        if name:
            normalized.append((name, amount))
    return normalized


def _serialize_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _merge_adapted_recipes(originals: List[dict], adapted: List[dict]) -> List[dict]:
    if not adapted:
        return originals

    originals_by_id = {item["recipe_id"]: item for item in originals if item.get("recipe_id") is not None}
    merged: List[dict] = []
    used_ids = set()

    for item in adapted:
        recipe_id = item.get("recipe_id")
        if recipe_id not in originals_by_id:
            continue
        updated = originals_by_id[recipe_id].copy()
        if item.get("recipe_nm_ko"):
            updated["recipe_nm_ko"] = item["recipe_nm_ko"]
        if item.get("ingredient_full"):
            updated["ingredient_full"] = item["ingredient_full"]
        if item.get("step_text"):
            updated["step_text"] = item["step_text"]
        merged.append(updated)
        used_ids.add(recipe_id)

    for recipe in originals:
        if recipe["recipe_id"] not in used_ids:
            merged.append(recipe)

    return merged[:4]


def _normalize_name(value: str) -> str:
    """Lowercase, strip, and remove underscores/spaces for loose matching."""
    return re.sub(r"[\s_]+", "", str(value or "").strip().lower())


def _core_keys(ingredient_full: Any, limit: int = 3) -> List[str]:
    """Extract top N ingredient keys if JSON-like, else return empty list."""
    keys: List[str] = []
    if isinstance(ingredient_full, (dict, list)):
        if isinstance(ingredient_full, dict):
            keys = list(ingredient_full.keys())
    elif isinstance(ingredient_full, str):
        try:
            parsed = _json.loads(ingredient_full)
            if isinstance(parsed, dict):
                keys = list(parsed.keys())
        except _json.JSONDecodeError:
            keys = []
    return [_normalize_name(k) for k in keys[:limit] if str(k).strip()]


def _name_tokens(name: str) -> List[str]:
    tokens = _re.split(r"[\\s/·.,()]+", name or "")
    return [_normalize_name(t) for t in tokens if t.strip()]


def _ingredient_signature(items: List[dict]) -> str:
    """Build a stable signature string from ingredient list (name/amount)."""
    normalized = []
    for item in items:
        name = _normalize_name(item.get("name", ""))
        if not name:
            continue
        amount = str(item.get("amount") or "").strip()
        normalized.append(f"{name}:{amount}")
    normalized.sort()
    base = ";".join(normalized)
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def recommend_recipes(payload: RecommendRequest) -> dict:
    user_id = payload.user_id
    ingredients_payload = payload.ingredients or []
    ingredient_dicts = [ingredient.model_dump() for ingredient in ingredients_payload]
    normalized_ingredients: List[Tuple[str, str]] = []
    user_names: set[str] = set()
    final_recipes: List[dict] = []
    current_signature = ""
    exclude_ids: set[str] = set()
    exclude_signature = None

    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT cooking_level, user_name FROM user_info WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if not user:
                    raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

                user_level = user["cooking_level"]
                user_name = user.get("user_name") or user_id

                # ✅ fridge_item 테이블에 저장된 사용자의 재료도 함께 사용
                cur.execute(
                    """
                    SELECT ingredient_name, quantity
                    FROM fridge_item
                    WHERE id = %s
                      AND stored_at >= DATE_SUB(NOW(), INTERVAL 28 DAY)
                    """,
                    (user_id,),
                )
                stored_items = cur.fetchall()
                stored_dicts = []
                for item in stored_items:
                    name = item.get("ingredient_name")
                    qty = item.get("quantity")
                    if name:
                        stored_dicts.append({"name": str(name), "amount": str(qty)})

                # 요청으로 받은 재료 + 저장된 재료를 통합(이름 기준 마지막 값 우선)
                merged_items: dict[str, dict] = {}
                for item in ingredient_dicts + stored_dicts:
                    name = str(item.get("name") or "").strip()
                    if not name:
                        continue
                    merged_items[name.lower()] = {"name": name, "amount": str(item.get("amount") or "")}

                merged_list = list(merged_items.values())
                normalized_ingredients = _normalize_ingredients(merged_list)
                user_names = {_normalize_name(name) for name, _ in normalized_ingredients}

                # 요청 기준 시그니처를 사용해 exclude 비교 (프런트와 일치하도록)
                current_signature = payload.exclude_signature or _ingredient_signature(ingredient_dicts)

                if payload.exclude_ids and payload.exclude_signature == current_signature:
                    exclude_ids = {str(x) for x in payload.exclude_ids}
                    exclude_signature = payload.exclude_signature

                cur.execute(
                    """
                    SELECT
                        recipe_id,
                        recipe_nm_ko,
                        ingredient_full,
                        level_nm,
                        cooking_time,
                        step_text,
                        ty_nm AS `type`
                    FROM recipe
                    WHERE level_nm = %s
                      AND (ty_nm IS NULL OR ty_nm <> '빵')
                    """,
                    (user_level,),
                )
                recipes = cur.fetchall()

                scored = []
                for recipe in recipes:
                    if exclude_ids and str(recipe.get("recipe_id")) in exclude_ids:
                        continue
                    # 주요 재료(앞 3개)가 사용자의 재료와 전혀 겹치지 않으면 추천 후보에서 제외
                    core_keys = _core_keys(recipe.get("ingredient_full"), limit=3)
                    if core_keys and not user_names.intersection(core_keys):
                        continue

                    raw_text = (
                        str(recipe["ingredient_full"])
                        .lower()
                        .replace("(", " ")
                        .replace(")", " ")
                        .replace("\n", " ")
                        .replace("/", " ")
                        .replace(",", " ")
                    )
                    recipe_ingredients = [item.strip() for item in raw_text.split() if item.strip()]
                    match_count = 0

                    for ing_name, _ in normalized_ingredients:
                        for recipe_ing in recipe_ingredients:
                            if ing_name in recipe_ing or recipe_ing in ing_name:
                                match_count += 1
                                break

                    if match_count > 0:
                        scored.append(
                            {
                                "recipe_id": recipe["recipe_id"],
                                "recipe_nm_ko": recipe["recipe_nm_ko"],
                                "level_nm": recipe["level_nm"],
                                "ingredient_full": recipe.get("ingredient_full"),
                                "cooking_time": recipe.get("cooking_time"),
                                "step_text": recipe.get("step_text"),
                                "type": recipe.get("type"),
                                "match_count": match_count,
                                "total_ingredients": len(recipe_ingredients),
                            }
                        )

                for item in scored:
                    total = item["total_ingredients"] or 1
                    item["match_ratio"] = round((item["match_count"] / total) * 100, 1)

                # 핵심 재료(ingredient_full 앞 3개) 중 2개 이상이 사용자 재료와 겹치는 레시피만 남김
                filtered = []
                for item in scored:
                    core_keys = _core_keys(item.get("ingredient_full"), limit=3)
                    if len(set(core_keys).intersection(user_names)) >= 2:
                        filtered.append(item)

                filtered.sort(key=lambda item: (item["match_count"], item["match_ratio"]), reverse=True)
                top_recipes = filtered[:4]

                adapted_recipes: List[dict] = []
                if top_recipes:
                    # 레시피명과 주요 재료(앞 3개) 매칭이 충분하면 LLM 스킵
                    def _is_name_aligned(recipe_item: dict) -> bool:
                        name_tokens = _name_tokens(str(recipe_item.get("recipe_nm_ko") or ""))
                        core = _core_keys(recipe_item.get("ingredient_full"), limit=3)
                        overlap = set(name_tokens).intersection(core)
                        return len(overlap) >= 2

                    skip_llm = all(_is_name_aligned(item) for item in top_recipes)

                    # 상위 일부(최대 3개)만 LLM에 보내고 나머지는 원본 유지
                    llm_candidates = top_recipes[:3]
                    passthrough = top_recipes[3:]

                if top_recipes and not skip_llm:
                    try:
                        adapted_recipes = adapt_recipes_with_llm(
                            user_name=user_name,
                            fridge_items=ingredient_dicts,
                            level=user_level,
                            candidates=llm_candidates,
                            recent_emphasis=[],
                        )
                    except LLMAdaptationError as exc:
                        logger.warning("LLM adaptation skipped: %s", exc)
                        adapted_recipes = []
                # LLM 타임아웃/예외 시에는 adapted_recipes가 비어있을 수 있으므로 폴백
                if top_recipes and adapted_recipes is None:
                    adapted_recipes = []
                # LLM을 돌린 결과 + 나머지 원본을 합쳐서 merge 단계로 보냄
                if top_recipes:
                    adapted_recipes = (adapted_recipes or []) + passthrough

                final_recipes = _merge_adapted_recipes(top_recipes, adapted_recipes)

                for recipe in final_recipes:
                    cur.execute(
                        """
                        INSERT INTO recommend_recipe (
                            id,
                            recipe_id,
                            recipe_nm_ko,
                            ingredient_full,
                            step_text,
                            `type`,
                            recommend_date
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            user_id,
                            recipe["recipe_id"],
                            recipe["recipe_nm_ko"],
                            _serialize_text(recipe.get("ingredient_full")),
                            _serialize_text(recipe.get("step_text")),
                            _serialize_text(recipe.get("type")),
                        ),
                    )
                    recipe["recommend_id"] = cur.lastrowid
            conn.commit()

        return {
            "user_level": user["cooking_level"],
            "recommendations": final_recipes,
            "ingredient_signature": current_signature,
        }
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        trace = traceback.format_exc()
        logger.exception('recommend_recipes failed: %s', exc)
        raise HTTPException(status_code=500, detail=f"서버 오류: {trace}") from exc


def save_selected_recipe(payload: SelectedRecipe) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO selected_recipe (id, recommend_id, recipe_id, selected_date)
                    VALUES (%s, %s, %s, %s)
                """
                cur.execute(
                    sql,
                    (
                        payload.user_id,
                        payload.recommend_id,
                        payload.recipe_id,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
            conn.commit()
        return {"message": "선택한 레시피가 저장되었습니다."}
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc


def list_selected_recipes(user_id: str) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        sr.recommend_id,
                        sr.recipe_id,
                        sr.selected_date,
                        sr.action,
                        r.recipe_nm_ko,
                        r.ingredient_full,
                        r.level_nm,
                        r.cooking_time,
                        r.step_text
                    FROM selected_recipe sr
                    JOIN recipe r ON sr.recipe_id = r.recipe_id
                    WHERE sr.id = %s
                    ORDER BY sr.selected_date DESC
                    """,
                    (user_id,),
                )
                recipes = cur.fetchall()
        return {"recipes": recipes}
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc


def update_selected_recipe_action(payload: SelectedRecipeAction) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE selected_recipe
                    SET action = %s, updated_at = NOW()
                    WHERE id = %s AND recommend_id = %s AND recipe_id = %s
                    """,
                    (payload.action, payload.user_id, payload.recommend_id, payload.recipe_id),
                )
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="선택한 레시피를 찾을 수 없습니다.")
            conn.commit()
        return {"message": "상태가 변경되었습니다."}
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc


def delete_selected_recipe(payload: SelectedRecipe) -> dict:
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM selected_recipe
                    WHERE id = %s AND recommend_id = %s AND recipe_id = %s
                    """,
                    (payload.user_id, payload.recommend_id, payload.recipe_id),
                )
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="삭제할 레시피를 찾을 수 없습니다.")
            conn.commit()
        return {"message": "선택한 레시피가 삭제되었습니다."}
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc


def count_monthly_completed_recipes(user_id: str) -> dict:
    """Return the number of recipes completed (action=1) in the current month."""
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS completed_count
                    FROM selected_recipe
                    WHERE id = %s
                      AND action = 1
                      AND selected_date >= DATE_FORMAT(NOW(), '%%Y-%%m-01')
                      AND selected_date < DATE_FORMAT(DATE_ADD(NOW(), INTERVAL 1 MONTH), '%%Y-%%m-01')
                    """,
                    (user_id,),
                )
                row = cur.fetchone() or {"completed_count": 0}
        count_value = row.get("completed_count", 0)
        try:
            count_int = int(count_value)
        except (TypeError, ValueError):
            count_int = 0
        return {"completed_count": count_int}
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc


def estimate_monthly_savings(user_id: str) -> dict:
    """Estimate delivery vs ingredient savings for this month's completed recipes."""
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        r.recipe_id,
                        r.recipe_nm_ko,
                        r.ingredient_full,
                        COUNT(*) AS cook_count
                    FROM selected_recipe sr
                    JOIN recipe r ON sr.recipe_id = r.recipe_id
                    WHERE sr.id = %s
                      AND sr.action = 1
                      AND sr.selected_date >= DATE_FORMAT(NOW(), '%%Y-%%m-01')
                      AND sr.selected_date < DATE_FORMAT(DATE_ADD(NOW(), INTERVAL 1 MONTH), '%%Y-%%m-01')
                    GROUP BY r.recipe_id, r.recipe_nm_ko, r.ingredient_full
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc

    if not rows:
        return {
            "total_savings": 0,
            "per_recipe": [],
            "notes": "이번 달에 진행완료된 레시피가 없습니다.",
        }

    ingredient_counts: dict[str, int] = {}
    def _normalize_name(token: str) -> str | None:
        match = re.search(r"[가-힣]+", token)
        if match:
            return match.group(0)
        token = token.strip()
        return token or None

    def _extract_ingredient_names(raw_text: str) -> List[str]:
        items: List[str] = []
        if not raw_text:
            return items
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                for entry in parsed:
                    if isinstance(entry, str):
                        name = _normalize_name(entry)
                        if name:
                            items.append(name)
                if items:
                    return items
        except json.JSONDecodeError:
            pass
        # Fallback: split by newline or comma
        for token in re.split(r"[\n,]+", raw_text):
            name = _normalize_name(token)
            if name:
                items.append(name)
        return items
    recipes_payload = []
    for row in rows:
        name = row.get("recipe_nm_ko") or "레시피"
        count = int(row.get("cook_count") or 1)
        ingredients_text = row.get("ingredient_full") or ""
        recipes_payload.append(
            {"name": name, "count": count, "ingredients_text": ingredients_text}
        )

        for ingredient_name in _extract_ingredient_names(ingredients_text):
            ingredient_counts[ingredient_name] = ingredient_counts.get(ingredient_name, 0) + count

    def _fallback_estimate() -> dict:
        per_recipe = []
        total_ingredient = 0
        total_delivery = 0
        for payload in recipes_payload:
            count = int(payload["count"])
            ingredient_lines = [
                line.strip()
                for line in (payload.get("ingredients_text") or "").splitlines()
                if line.strip()
            ]
            ingredient_cost = 4500 + max(0, len(ingredient_lines)) * 400
            delivery_price = ingredient_cost + 6000
            savings = max(0, delivery_price - ingredient_cost) * count
            total_ingredient += ingredient_cost * count
            total_delivery += delivery_price * count
            per_recipe.append(
                {
                    "name": payload["name"],
                    "count": count,
                    "ingredient_cost": ingredient_cost,
                    "delivery_price": delivery_price,
                    "savings": savings,
                }
            )
        return {
            "per_recipe": per_recipe,
            "total_ingredient_cost": total_ingredient,
            "total_delivery_cost": total_delivery,
            "total_savings": total_delivery - total_ingredient,
            "notes": "추정치는 기본 단가 규칙을 사용했습니다.",
        }

    try:
        llm_response = estimate_recipe_costs(recipes_payload)
    except LLMAdaptationError:
        llm_response = _fallback_estimate()

    total_savings = llm_response.get("total_savings", 0)
    try:
        total_savings_int = int(total_savings)
    except (TypeError, ValueError):
        total_savings_int = 0

    top_ingredients = sorted(
        ingredient_counts.items(), key=lambda kv: kv[1], reverse=True
    )[:3]

    return {
        "total_savings": total_savings_int,
        "per_recipe": llm_response.get("per_recipe", []),
        "notes": llm_response.get("notes"),
        "ingredients_top": [
            {"name": name, "count": count} for name, count in top_ingredients
        ],
    }
