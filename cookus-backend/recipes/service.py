from typing import Any, Dict

from fastapi import HTTPException

from core import get_conn


class RecipeService:
    def get_recipe(self, recipe_id: int) -> Dict[str, Any]:
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


recipe_service = RecipeService()
