from typing import Any, Dict, List

from core import get_conn


class IngredientService:
    def search(self, query: str) -> List[Dict[str, Any]]:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT ingredient_name FROM ingredient WHERE ingredient_name LIKE %s LIMIT 20",
                (f"%{query}%",),
            )
            rows = cur.fetchall() or []
        return [{"name": r["ingredient_name"]} for r in rows]


ingredient_service = IngredientService()
