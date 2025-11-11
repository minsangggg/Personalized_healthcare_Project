import json
import logging
import re
import traceback
from datetime import datetime
from typing import Any, List, Tuple

from fastapi import HTTPException

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

    return merged[:7]


def recommend_recipes(payload: RecommendRequest) -> dict:
    user_id = payload.user_id
    ingredients_payload = payload.ingredients or []
    ingredient_dicts = [ingredient.model_dump() for ingredient in ingredients_payload]
    normalized_ingredients = _normalize_ingredients(ingredient_dicts)
    final_recipes: List[dict] = []

    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT cooking_level, user_name FROM user_info WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if not user:
                    raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

                user_level = user["cooking_level"]
                user_name = user.get("user_name") or user_id

                cur.execute(
                    """
                    SELECT
                        recipe_id,
                        recipe_nm_ko,
                        ingredient_full,
                        level_nm,
                        cooking_time,
                        step_text
                    FROM recipe
                    WHERE level_nm = %s
                    """,
                    (user_level,),
                )
                recipes = cur.fetchall()

                scored = []
                for recipe in recipes:
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
                                "match_count": match_count,
                                "total_ingredients": len(recipe_ingredients),
                            }
                        )

                for item in scored:
                    total = item["total_ingredients"] or 1
                    item["match_ratio"] = round((item["match_count"] / total) * 100, 1)

                filtered = [
                    item for item in scored if item["match_count"] >= 2 or item["match_ratio"] >= 10
                ]
                filtered.sort(key=lambda item: (item["match_count"], item["match_ratio"]), reverse=True)
                top_recipes = filtered[:7]

                adapted_recipes: List[dict] = []
                if top_recipes:
                    try:
                        adapted_recipes = adapt_recipes_with_llm(
                            user_name=user_name,
                            fridge_items=ingredient_dicts,
                            level=user_level,
                            candidates=top_recipes,
                            recent_emphasis=[],
                        )
                    except LLMAdaptationError as exc:
                        logger.warning("LLM adaptation skipped: %s", exc)
                        adapted_recipes = []

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
                            recommend_date
                        )
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        """,
                        (
                            user_id,
                            recipe["recipe_id"],
                            recipe["recipe_nm_ko"],
                            _serialize_text(recipe.get("ingredient_full")),
                            _serialize_text(recipe.get("step_text")),
                        ),
                    )
                    recipe["recommend_id"] = cur.lastrowid
            conn.commit()

        return {"user_level": user["cooking_level"], "recommendations": final_recipes}
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
