import re
from typing import Any, Dict, List, Optional

from core import get_conn

from .models import SaveFridgeIn


class FridgeService:
    """Manage fridge items per user."""

    @staticmethod
    def _split_unit(raw_name: str) -> List[Any]:
        m = re.search(r"\(([^)]+)\)\s*$", str(raw_name))
        if m:
            base = re.sub(r"\([^)]*\)\s*$", "", str(raw_name)).strip()
            return [base, m.group(1).strip()]
        return [str(raw_name).strip(), None]

    @staticmethod
    def _compose_name(name: str, unit: Optional[str]) -> str:
        return name + (f"({unit})" if unit else "")

    def list_items(self, user_id: str) -> List[Dict[str, Any]]:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT ingredient_name AS name_raw, quantity AS qty, stored_at
                FROM fridge_item
                WHERE id=%s
                ORDER BY stored_at DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall() or []

        output: List[Dict[str, Any]] = []
        for row in rows:
            base, unit = self._split_unit(row["name_raw"])
            qty = row["qty"]
            output.append(
                {
                    "name": base,
                    "quantity": int(qty) if qty is not None else 0,
                    "unit": unit,
                }
            )
        return output

    def save_items(self, user_id: str, payload: SaveFridgeIn) -> Dict[str, Any]:
        with get_conn() as conn, conn.cursor() as cur:
            if payload.purgeMissing:
                names_payload = [self._compose_name(it.name, it.unit) for it in payload.items]
                if names_payload:
                    placeholders = ",".join(["%s"] * len(names_payload))
                    cur.execute(
                        f"""
                        DELETE FROM fridge_item
                        WHERE id=%s AND ingredient_name NOT IN ({placeholders})
                        """,
                        (user_id, *names_payload),
                    )
                else:
                    cur.execute("DELETE FROM fridge_item WHERE id=%s", (user_id,))

            for item in payload.items:
                name = self._compose_name(item.name, item.unit)
                quantity = int(item.quantity)
                cur.execute("SELECT quantity FROM fridge_item WHERE id=%s AND ingredient_name=%s", (user_id, name))
                existing = cur.fetchone()
                if existing:
                    if payload.mode == "merge":
                        cur.execute(
                            """
                            UPDATE fridge_item
                            SET quantity=quantity+%s, stored_at=NOW()
                            WHERE id=%s AND ingredient_name=%s
                            """,
                            (quantity, user_id, name),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE fridge_item
                            SET quantity=%s, stored_at=NOW()
                            WHERE id=%s AND ingredient_name=%s
                            """,
                            (quantity, user_id, name),
                        )
                else:
                    cur.execute(
                        """
                        INSERT INTO fridge_item (fridge_id, id, ingredient_name, quantity, stored_at)
                        VALUES (UUID(), %s, %s, %s, NOW())
                        """,
                        (user_id, name, quantity),
                    )
        return {"ok": True}


fridge_service = FridgeService()
