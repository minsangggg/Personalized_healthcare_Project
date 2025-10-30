from datetime import date, datetime, timedelta
from typing import Optional, Tuple

def _parse_dates(start_date: Optional[date], end_date: Optional[date]) -> Tuple[datetime, datetime]:
    if not start_date and not end_date:
        end_dt = datetime.combine(date.today(), datetime.min.time())
        start_dt = end_dt - timedelta(days=27)
    elif start_date and not end_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(date.today(), datetime.min.time())
    elif not start_date and end_date:
        end_dt = datetime.combine(end_date, datetime.min.time())
        start_dt = end_dt - timedelta(days=27)
    else:
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.min.time())
    return start_dt, end_dt + timedelta(days=1)

def fetch_recipe_category_ratio(db, user_id: str, start_date: Optional[date], end_date: Optional[date]):
    start_dt, end_dt_inc = _parse_dates(start_date, end_date)
    sql = """
      SELECT r.ty_nm AS category, COUNT(*) AS cnt
      FROM selected_recipe s
      JOIN recipe r ON s.recipe_id = r.recipe_id
      WHERE s.id = %s AND s.selected_date >= %s AND s.selected_date < %s
      GROUP BY r.ty_nm
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, start_dt, end_dt_inc))
        rows = cur.fetchall()

    total = sum([r["cnt"] for r in rows]) or 1
    data = [
        {"label": r["category"] or "기타", "count": int(r["cnt"]), "ratio": round(r["cnt"]/total, 3)}
        for r in rows
    ]
    return {"user_id": user_id, "total": total, "categories": data}
