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

    def add(self, name: str) -> Dict[str, Any]:
        clean = (name or "").strip()
        if not clean:
            raise ValueError("재료 이름을 입력해주세요.")
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingredient (ingredient_name)
                VALUES (%s)
                ON DUPLICATE KEY UPDATE ingredient_name=VALUES(ingredient_name)
                """,
                (clean,),
            )
        return {"name": clean}


ingredient_service = IngredientService()
