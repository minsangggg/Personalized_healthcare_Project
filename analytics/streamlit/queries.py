from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from db_client import run_query


AGE_GROUP_CASE = """
CASE
    WHEN u.date_of_birth IS NULL THEN NULL
    WHEN TIMESTAMPDIFF(YEAR, u.date_of_birth, CURDATE()) BETWEEN 20 AND 29 THEN '20대'
    WHEN TIMESTAMPDIFF(YEAR, u.date_of_birth, CURDATE()) BETWEEN 30 AND 39 THEN '30대'
    WHEN TIMESTAMPDIFF(YEAR, u.date_of_birth, CURDATE()) BETWEEN 40 AND 49 THEN '40대'
    WHEN TIMESTAMPDIFF(YEAR, u.date_of_birth, CURDATE()) BETWEEN 50 AND 59 THEN '50대'
    ELSE '기타'
END
"""

EXCLUDED_INGREDIENTS = ("천사채",)
EXCLUDED_INGREDIENT_SET = {name.strip().lower() for name in EXCLUDED_INGREDIENTS}


def _filter_excluded_ingredients(df: pd.DataFrame) -> pd.DataFrame:
    """Remove excluded ingredients from the result DataFrame."""
    if df.empty or not EXCLUDED_INGREDIENT_SET:
        return df

    normalized = (
        df["ingredient_name"]
        .astype(str)
        .str.strip()
        .str.lower()
    )
    mask = normalized.isin(EXCLUDED_INGREDIENT_SET)
    return df[~mask].copy()


def _build_date_clause(column: str, start_date: Optional[str], end_date: Optional[str]):
    clauses: List[str] = []
    params: List[str] = []
    if start_date:
        clauses.append(f"DATE({column}) >= %s")
        params.append(start_date)
    if end_date:
        clauses.append(f"DATE({column}) <= %s")
        params.append(end_date)
    return " AND ".join(clauses), params


def get_age_level_and_time_stats(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, pd.DataFrame]:
    date_clause, params = _build_date_clause("rr.recommend_date", start_date, end_date)

    sql = f"""
    SELECT
        {AGE_GROUP_CASE} AS age_group,
        COALESCE(u.cooking_level, '미지정') AS cooking_level,
        COALESCE(r.cooking_time, 0) AS cooking_time
    FROM user_info u
    JOIN recommend_recipe rr ON rr.id = u.id
    JOIN recipe r ON r.recipe_id = rr.recipe_id
    WHERE rr.recipe_id IS NOT NULL
      {"AND " + date_clause if date_clause else ""}
    """

    df = run_query(sql, params if params else None)
    df = df.dropna(subset=["age_group"])
    if df.empty:
        return {"level_summary": df, "time_distribution": df}

    df["cooking_time"] = pd.to_numeric(df["cooking_time"], errors="coerce").fillna(0)
    level_summary = (
        df.groupby(["age_group", "cooking_level"])
        .agg(
            recommendation_count=("cooking_time", "size"),
            avg_cooking_time=("cooking_time", "mean"),
            median_cooking_time=("cooking_time", "median"),
        )
        .reset_index()
    )

    bins = [0, 15, 30, 60, 90, 120, float("inf")]
    labels = ["<15분", "15-30분", "30-60분", "60-90분", "90-120분", "120분+"]  # type: ignore
    df["time_bucket"] = pd.cut(df["cooking_time"], bins=bins, labels=labels, right=False)
    time_distribution = (
        df.groupby(["age_group", "time_bucket"], observed=False)
        .size()
        .reset_index(name="counts")
        .sort_values(["age_group", "time_bucket"])
    )

    return {
        "level_summary": level_summary,
        "time_distribution": time_distribution,
    }


def get_age_group_top_ingredients(top_n: int = 3) -> pd.DataFrame:
    exclusion_clause = ""
    exclusion_params: List[str] = []
    if EXCLUDED_INGREDIENTS:
        placeholders = ", ".join(["%s"] * len(EXCLUDED_INGREDIENTS))
        exclusion_clause = f"AND fi.ingredient_name NOT IN ({placeholders})"
        exclusion_params = list(EXCLUDED_INGREDIENTS)

    sql = f"""
    SELECT
        age_group.age_group,
        fi.ingredient_name,
        COUNT(*) AS item_count
    FROM fridge_item fi
    JOIN (
        SELECT
            u.id,
            {AGE_GROUP_CASE} AS age_group
        FROM user_info u
    ) AS age_group ON age_group.id = fi.id
    WHERE age_group.age_group IS NOT NULL
      {exclusion_clause}
    GROUP BY age_group.age_group, fi.ingredient_name
    ORDER BY age_group.age_group, item_count DESC
    """

    df = run_query(sql, exclusion_params if exclusion_params else None)
    df = _filter_excluded_ingredients(df)
    if df.empty:
        return df

    df = df.sort_values(["age_group", "item_count"], ascending=[True, False]).copy()
    df["rank"] = df.groupby("age_group").cumcount() + 1
    ranked = df[df["rank"] <= top_n].copy()
    return ranked.reset_index(drop=True)


def get_hourly_app_usage(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> pd.DataFrame:
    rec_clause, rec_params = _build_date_clause("rr.recommend_date", start_date, end_date)
    sel_clause, sel_params = _build_date_clause("sr.selected_date", start_date, end_date)

    sql = f"""
    SELECT hour_slot, source, SUM(events) AS events
    FROM (
        SELECT
            HOUR(rr.recommend_date) AS hour_slot,
            '추천' AS source,
            COUNT(*) AS events
        FROM recommend_recipe rr
        WHERE rr.recommend_date IS NOT NULL
          {"AND " + rec_clause if rec_clause else ""}
        GROUP BY hour_slot

        UNION ALL

        SELECT
            HOUR(sr.selected_date) AS hour_slot,
            '선택' AS source,
            COUNT(*) AS events
        FROM selected_recipe sr
        WHERE sr.selected_date IS NOT NULL
          {"AND " + sel_clause if sel_clause else ""}
        GROUP BY hour_slot
    ) AS hourly
    GROUP BY hour_slot, source
    ORDER BY hour_slot
    """

    params = []
    if rec_params:
        params.extend(rec_params)
    if sel_params:
        params.extend(sel_params)

    df = run_query(sql, params if params else None)
    if df.empty:
        return df

    df["hour_label"] = (
        df["hour_slot"]
        .apply(lambda h: f"{int(h):02d}:00" if pd.notna(h) and str(h).isdigit() else str(h))
        .fillna("미기록")
    )
    return df


def get_top_ingredients_overall(limit: int = 10) -> pd.DataFrame:
    exclusion_clause = ""
    exclusion_params: List[str] = []
    if EXCLUDED_INGREDIENTS:
        placeholders = ", ".join(["%s"] * len(EXCLUDED_INGREDIENTS))
        exclusion_clause = f"WHERE fi.ingredient_name NOT IN ({placeholders})"
        exclusion_params = list(EXCLUDED_INGREDIENTS)

    sql = """
    SELECT
        fi.ingredient_name,
        COUNT(*) AS item_count
    FROM fridge_item fi
    {where_clause}
    GROUP BY fi.ingredient_name
    ORDER BY item_count DESC
    LIMIT %s
    """.format(where_clause=exclusion_clause or "")

    params: List[Any] = []
    if exclusion_params:
        params.extend(exclusion_params)
    params.append(limit)

    df = run_query(sql, params)
    df = _filter_excluded_ingredients(df)
    return df


def get_ingredient_trend(keyword: str = "계란", window: str = "day") -> pd.DataFrame:
    time_expr = "DATE(STR_TO_DATE(fi.stored_at, '%%Y-%%m-%%d %%H:%%i:%%S'))"
    if window == "week":
        time_expr = "DATE_FORMAT(STR_TO_DATE(fi.stored_at, '%%Y-%%m-%%d %%H:%%i:%%S'), '%%x-%%v')"
    elif window == "month":
        time_expr = "DATE_FORMAT(STR_TO_DATE(fi.stored_at, '%%Y-%%m-%%d %%H:%%i:%%S'), '%%Y-%%m')"

    sql = f"""
    SELECT
        {time_expr} AS bucket,
        COUNT(*) AS mentions
    FROM fridge_item fi
    WHERE fi.ingredient_name LIKE %s
    GROUP BY bucket
    ORDER BY bucket
    """

    df = run_query(sql, [f"%{keyword}%"])
    return df
