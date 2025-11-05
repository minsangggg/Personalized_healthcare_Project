from datetime import datetime
from typing import List, Tuple

from fastapi import HTTPException

from app.db.connection import connection_scope
from app.schemas.recommendation import RecommendRequest, SelectedRecipe


def _normalize_ingredients(ingredients: List[dict]) -> List[Tuple[str, str]]:
    normalized = []
    for ingredient in ingredients:
        name = str(ingredient.get("name", "")).strip().lower()
        amount = str(ingredient.get("amount", "")).strip()
        if name:
            normalized.append((name, amount))
    return normalized


def recommend_recipes(payload: RecommendRequest) -> dict:
    user_id = payload.user_id
    ingredients_payload = payload.ingredients or []
    normalized_ingredients = _normalize_ingredients([ingredient.model_dump() for ingredient in ingredients_payload])

    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT cooking_level FROM user_info WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if not user:
                    raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

                user_level = user["cooking_level"]

                cur.execute(
                    """
                    SELECT recipe_id, recipe_nm_ko, ingredient_full, level_nm
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
                                "recipe_name": recipe["recipe_nm_ko"],
                                "level": recipe["level_nm"],
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
                top_recipes = filtered[:3]

                for recipe in top_recipes:
                    cur.execute(
                        """
                        INSERT INTO recommend_recipe (id, recipe_id, recommend_date)
                        VALUES (%s, %s, NOW())
                        """,
                        (user_id, recipe["recipe_id"]),
                    )
            conn.commit()

        return {"user_level": user["cooking_level"], "recommendations": top_recipes}
    except HTTPException:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc


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
                        sr.recipe_id,
                        sr.selected_date,
                        r.recipe_nm_ko,
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
