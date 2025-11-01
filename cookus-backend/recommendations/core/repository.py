"""Database access helpers for recommendation workflow."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from core import get_conn


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
    sql = (
        "SELECT id, user_name, email, password, gender, date_of_birth, cooking_level, goal "
        "FROM user_info WHERE id=%s"
    )
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
    if not rows:
        raise RuntimeError("냉장고 재료 없음")
    return pd.DataFrame(rows)


def fetch_candidates_like(keywords: List[str], limit: int = 200, and_top: int = 3) -> List[Dict[str, Any]]:
    if not keywords:
        return []
    keywords = [kw for kw in keywords if kw]
    if not keywords:
        return []

    def like_group_for_kw(kw: str) -> Tuple[str, List[str]]:
        return "(ingredient_full LIKE %s OR recipe_nm_ko LIKE %s)", [f"%{kw}%", f"%{kw}%"]

    top = max(1, min(and_top, len(keywords))) if and_top else 0

    and_clauses: List[str] = []
    params: List[Any] = []
    for kw in keywords[:top]:
        clause, values = like_group_for_kw(kw)
        and_clauses.append(clause)
        params.extend(values)

    or_clauses: List[str] = []
    for kw in keywords[top:]:
        clause, values = like_group_for_kw(kw)
        or_clauses.append(clause)
        params.extend(values)

    if and_clauses and or_clauses:
        where = f"( {' AND '.join(and_clauses)} ) AND ( {' OR '.join(or_clauses)} )"
    elif and_clauses:
        where = f"( {' AND '.join(and_clauses)} )"
    elif or_clauses:
        where = f"( {' OR '.join(or_clauses)} )"
    else:
        return []

    sql = f"""
    SELECT recipe_id, recipe_nm_ko, cooking_time, level_nm, ingredient_full, step_text, ty_nm
    FROM recipe
    WHERE {where}
    ORDER BY RAND()
    LIMIT {int(limit)}
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_candidates_or_only(keywords: List[str], limit: int = 300) -> List[Dict[str, Any]]:
    keywords = [kw for kw in keywords if kw]
    if not keywords:
        return []

    clauses = []
    params: List[Any] = []
    for kw in keywords:
        clauses.append("(ingredient_full LIKE %s OR recipe_nm_ko LIKE %s)")
        params.extend([f"%{kw}%", f"%{kw}%"])
    where = " OR ".join(clauses)
    sql = f"""
    SELECT recipe_id, recipe_nm_ko, cooking_time, level_nm, ingredient_full, step_text, ty_nm
    FROM recipe
    WHERE {where}
    ORDER BY RAND()
    LIMIT {int(limit)}
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def recent_recommend_recipe_ids(user_id: str, lookback_days: int = 0) -> List[int]:
    sql = """
    SELECT recipe_id
    FROM recommend_recipe
    WHERE id=%s AND recommend_date >= CURDATE()
    ORDER BY recommend_date DESC
    LIMIT 100
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (user_id,))
        rows = cur.fetchall() or []
    return [int(row["recipe_id"]) for row in rows if row.get("recipe_id") is not None]


def random_recipes_excluding(excluded_ids: Sequence[int], limit: int) -> List[Dict[str, Any]]:
    excluded_ids = list(excluded_ids)
    with get_conn() as conn, conn.cursor() as cur:
        if excluded_ids:
            placeholders = ",".join(["%s"] * len(excluded_ids))
            sql = f"""
            SELECT recipe_id, recipe_nm_ko, cooking_time, level_nm, ingredient_full, step_text, ty_nm
            FROM recipe
            WHERE recipe_id NOT IN ({placeholders})
            ORDER BY RAND() LIMIT %s
            """
            cur.execute(sql, (*excluded_ids, limit))
        else:
            sql = """
            SELECT recipe_id, recipe_nm_ko, cooking_time, level_nm, ingredient_full, step_text, ty_nm
            FROM recipe
            ORDER BY RAND() LIMIT %s
            """
            cur.execute(sql, (limit,))
        return cur.fetchall() or []


def ensure_recommend_recipe_table() -> None:
    sql = """
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
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)


def insert_recommend_recipes(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    insert_sql = """
    INSERT INTO recommend_recipe (id, recipe_nm_ko, ingredient_full, step_text, recipe_id)
    VALUES (%s, %s, %s, %s, %s)
    """
    exists_sql = """
    SELECT 1 FROM recommend_recipe
    WHERE id=%s AND recipe_id=%s AND recommend_date >= (NOW() - INTERVAL 2 MINUTE)
    LIMIT 1
    """

    with get_conn() as conn, conn.cursor() as cur:
        for row in rows:
            user_id = row.get("id")
            recipe_id = row.get("recipe_id")
            if user_id is None or recipe_id is None:
                continue
            cur.execute(exists_sql, (user_id, recipe_id))
            if cur.fetchone():
                continue
            cur.execute(
                insert_sql,
                (
                    user_id,
                    row.get("recipe_nm_ko"),
                    json.dumps(row.get("ingredient_full") or {}, ensure_ascii=False),
                    row.get("step_text"),
                    recipe_id,
                ),
            )


__all__ = [
    "pick_random_user_with_fridge",
    "get_user_profile",
    "get_user_fridge_items",
    "fetch_candidates_like",
    "fetch_candidates_or_only",
    "recent_recommend_recipe_ids",
    "random_recipes_excluding",
    "ensure_recommend_recipe_table",
    "insert_recommend_recipes",
]
