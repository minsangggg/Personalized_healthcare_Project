from datetime import datetime
from typing import List, Optional
import uuid

import logging
import pymysql
from fastapi import HTTPException

from app.db.connection import connection_scope
from app.schemas.ingredient import IngredientItem


logger = logging.getLogger(__name__)


def add_ingredient(item: IngredientItem) -> dict:
    """Insert a new ingredient item into the fridge_item table."""
    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO fridge_item (fridge_id, id, ingredient_name, quantity, stored_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        quantity = VALUES(quantity),
                        stored_at = VALUES(stored_at)
                """
                raw_amount = str(item.amount or "").strip()
                try:
                    normalized = raw_amount.lower().rstrip("g").strip()
                    quantity_value = int(float(normalized)) if normalized else 1
                except (TypeError, ValueError):
                    quantity_value = 1

                cur.execute(
                    sql,
                    (
                        str(uuid.uuid4()),
                        item.user_id,
                        item.name,
                        quantity_value,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
            conn.commit()
        return {"message": f"{item.name} added successfully."}
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception(
            "Failed to add ingredient",
            extra={"user_id": item.user_id, "ingredient": item.name, "amount": item.amount},
        )
        raise HTTPException(status_code=500, detail=f"Failed to add ingredient: {exc}") from exc


def search_ingredient_names(keyword: str = "", limit: int = 15) -> List[str]:
    """Return ingredient names from the ingredient master table."""
    trimmed = keyword.strip()
    like_term = f"%{trimmed}%" if trimmed else "%"
    safe_limit = max(1, min(limit, 50))
    column_candidates = (
        "ingredient_name",
        "name",
        "ingredient_nm",
        "INGREDIENT_NAME",
        "NAME",
        "INGREDIENT_NM",
    )

    try:
        with connection_scope() as conn:
            with conn.cursor() as cur:
                last_error: Optional[Exception] = None
                for column_name in column_candidates:
                    sql = f"""
                        SELECT DISTINCT {column_name} AS ingredient_name
                        FROM ingredient
                        WHERE {column_name} LIKE %s
                        ORDER BY {column_name}
                        LIMIT %s
                    """
                    try:
                        cur.execute(sql, (like_term, safe_limit))
                    except pymysql.err.ProgrammingError as exc:
                        last_error = exc
                        continue

                    rows = cur.fetchall()
                    return [
                        str(row["ingredient_name"]).strip()
                        for row in rows
                        if row.get("ingredient_name")
                    ]

                if last_error is not None:
                    raise last_error

                return []
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(
            status_code=500, detail=f"Failed to load ingredient list: {exc}"
        ) from exc
