from datetime import datetime
from typing import Any, Dict, List

from fastapi import HTTPException

from core import get_conn

from .engine import engine


class RecommendationService:
    """Recommendation and selection workflows."""

    def get_recommendations(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        recent = self._fetch_recent_recommendations(user_id, limit)
        if len(recent) >= limit:
            return recent[:limit]

        engine.recommend(user_id=user_id, limit=limit)
        return self._fetch_recent_cards(user_id, limit)

    def save_selected_recipe(self, user_id: str, recipe_id: int) -> Dict[str, Any]:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT recommend_id
                FROM recommend_recipe
                WHERE id=%s AND recipe_id=%s
                ORDER BY recommend_date DESC
                LIMIT 1
                """,
                (user_id, recipe_id),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(400, "최근 추천 기록이 없습니다.")
            recommend_id = row["recommend_id"]

            cur.execute(
                """
                INSERT INTO selected_recipe (id, recommend_id, recipe_id, selected_date)
                VALUES (%s, %s, %s, NOW())
                """,
                (user_id, recommend_id, recipe_id),
            )
        return {"ok": True}

    def list_selected_recipes(self, user_id: str) -> Dict[str, Any]:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  sr.selected_id,
                  sr.recommend_id,
                  rr.recipe_id,
                  rr.recipe_nm_ko,
                  sr.action,
                  r.cooking_time,
                  r.level_nm,

                  CASE
                    WHEN sr.selected_date REGEXP '^[0-9]{4}/'
                      THEN DATE(STR_TO_DATE(sr.selected_date, '%%Y/%%m/%%d %%H:%%i:%%s'))
                    WHEN sr.selected_date REGEXP '^[0-9]{4}-'
                      THEN DATE(sr.selected_date)
                    WHEN sr.selected_date REGEXP '^[0-9]{4}[.]'
                      THEN DATE(STR_TO_DATE(sr.selected_date, '%%Y.%%m.%%d %%H:%%i:%%s'))
                    ELSE NULL
                  END AS selected_date_only,

                  CASE
                    WHEN sr.selected_date REGEXP '^[0-9]{4}/'
                      THEN STR_TO_DATE(sr.selected_date, '%%Y/%%m/%%d %%H:%%i:%%s')
                    WHEN sr.selected_date REGEXP '^[0-9]{4}-'
                      THEN sr.selected_date
                    WHEN sr.selected_date REGEXP '^[0-9]{4}[.]'
                      THEN STR_TO_DATE(sr.selected_date, '%%Y.%%m.%%d %%H:%%i:%%s')
                    ELSE NULL
                  END AS sort_key

                FROM selected_recipe sr
                JOIN recommend_recipe rr ON sr.recommend_id = rr.recommend_id
                LEFT JOIN recipe r ON rr.recipe_id = r.recipe_id
                WHERE rr.id = %s AND sr.id = %s
                ORDER BY sort_key DESC
                """,
                (user_id, user_id),
            )
            rows = cur.fetchall() or []

        return {
            "user_id": user_id,
            "count": len(rows),
            "recipes": [
                {
                    "selected_id": r["selected_id"],
                    "recommend_id": r["recommend_id"],
                    "recipe_id": r["recipe_id"],
                    "recipe_nm_ko": r["recipe_nm_ko"],
                    "action": r.get("action") if isinstance(r, dict) else None,
                    "cooking_time": r.get("cooking_time"),
                    "level_nm": r.get("level_nm"),
                    "selected_date": self._to_iso_date(r.get("selected_date_only")),
                }
                for r in rows
            ],
        }

    def delete_selected_recipe(self, user_id: str, selected_id: int) -> None:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM selected_recipe
                WHERE selected_id=%s AND id=%s
                LIMIT 1
                """,
                (selected_id, user_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="selected record not found")

            cur.execute(
                """
                DELETE FROM selected_recipe
                WHERE selected_id=%s AND id=%s
                LIMIT 1
                """,
                (selected_id, user_id),
            )
            conn.commit()

    def update_selected_action(self, user_id: str, selected_id: int, action: int) -> Dict[str, Any]:
        if action not in (0, 1):
            raise HTTPException(400, "action must be 0 or 1")

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM selected_recipe
                WHERE selected_id=%s AND id=%s
                LIMIT 1
                """,
                (selected_id, user_id),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="selected record not found")

            cur.execute(
                "UPDATE selected_recipe SET action=%s WHERE selected_id=%s AND id=%s",
                (int(action), selected_id, user_id),
            )
            conn.commit()
        return {"ok": True, "selected_id": selected_id, "action": int(action)}

    def selected_status(self, user_id: str, recipe_id: int) -> Dict[str, Any]:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT sr.selected_id
                FROM selected_recipe sr
                JOIN recommend_recipe rr ON sr.recommend_id = rr.recommend_id
                WHERE sr.id=%s AND rr.id=%s AND rr.recipe_id=%s
                LIMIT 1
                """,
                (user_id, user_id, recipe_id),
            )
            row = cur.fetchone()
        return {"selected": bool(row), "selected_id": (row or {}).get("selected_id")}

    def get_recommendation_detail(self, user_id: str, recommend_id: int) -> Dict[str, Any]:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  rr.recommend_id,
                  rr.id,
                  rr.recipe_id,
                  rr.recipe_nm_ko,
                  rr.ingredient_full,
                  rr.step_text,
                  r.cooking_time,
                  r.level_nm
                FROM recommend_recipe rr
                JOIN recipe r ON r.recipe_id = rr.recipe_id
                WHERE rr.recommend_id = %s AND rr.id = %s
                LIMIT 1
                """,
                (recommend_id, user_id),
            )
            row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return {"recommendation": row}

    def _fetch_recent_recommendations(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT rr.recipe_id, rr.recipe_nm_ko, r.cooking_time, r.level_nm, rr.ingredient_full, rr.step_text
                FROM recommend_recipe rr
                JOIN recipe r ON rr.recipe_id = r.recipe_id
                WHERE rr.id = %s AND rr.recommend_date >= (NOW() - INTERVAL 10 SECOND)
                ORDER BY rr.recommend_date DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return cur.fetchall() or []

    def _fetch_recent_cards(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT rr.recipe_id, rr.recipe_nm_ko, r.cooking_time, r.level_nm, rr.ingredient_full, rr.step_text
                FROM recommend_recipe rr
                JOIN recipe r ON rr.recipe_id = r.recipe_id
                WHERE rr.id = %s
                ORDER BY rr.recommend_date DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return cur.fetchall() or []

    @staticmethod
    def _to_iso_date(value: Any) -> Any:
        try:
            if isinstance(value, datetime):
                return value.date().isoformat()
            return value.isoformat()  # type: ignore[attr-defined]
        except Exception:
            return str(value) if value is not None else None


recommendation_service = RecommendationService()
