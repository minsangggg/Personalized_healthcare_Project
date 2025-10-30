from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Tuple

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

def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

def fetch_user_goal(db, user_id: str) -> int:
    with db.cursor() as cur:
        cur.execute("SELECT goal FROM user_info WHERE id=%s", (user_id,))
        row = cur.fetchone()
    return (row and row.get("goal")) or 3

def fetch_progress(db, user_id: str, start_date: Optional[date], end_date: Optional[date], weekly_goal: int):
    start_dt, end_dt_inc = _parse_dates(start_date, end_date)

    sql = """
      SELECT DATE(selected_date) AS d, COUNT(*) AS c
      FROM selected_recipe
      WHERE id = %s AND selected_date >= %s AND selected_date < %s
      GROUP BY DATE(selected_date) ORDER BY d
    """
    with db.cursor() as cur:
        cur.execute(sql, (user_id, start_dt, end_dt_inc))
        rows = cur.fetchall()

    day_counts = {r["d"]: int(r["c"]) for r in rows}
    total = sum(day_counts.values())

    ts: List[dict] = []
    day = start_dt.date()
    end_excl = (end_dt_inc - timedelta(days=1)).date()
    while day <= end_excl:
        ts.append({"date": day, "count": day_counts.get(day, 0)})
        day += timedelta(days=1)

    weekly_map: Dict[date, int] = {}
    for t in ts:
        w = _week_start(t["date"])
        weekly_map[w] = weekly_map.get(w, 0) + t["count"]

    weekly = [{"week_start": w, "count": c, "attainment": min(c/max(weekly_goal,1), 1.0)}
              for w, c in sorted(weekly_map.items())]
    goal_attainment = (sum(w["attainment"] for w in weekly)/len(weekly)) if weekly else 0.0

    return {
        "period_start": start_dt.date(),
        "period_end": end_excl,
        "total": total,
        "timeseries": ts,
        "weekly": weekly,
        "goal_attainment": goal_attainment
    }
