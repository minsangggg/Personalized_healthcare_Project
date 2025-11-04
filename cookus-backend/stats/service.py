from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from core import get_conn


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _month_range(d: date) -> Tuple[date, date]:
    first = d.replace(day=1)
    # next month first day then -1 day
    if first.month == 12:
        next_first = date(first.year + 1, 1, 1)
    else:
        next_first = date(first.year, first.month + 1, 1)
    last = next_first - timedelta(days=1)
    return first, last


def _difficulty_to_score(level_nm: Optional[str]) -> Optional[int]:
    """Map difficulty label to ordinal score for averaging."""
    if not level_nm:
        return None
    m = {
        # Korean labels commonly seen in the dataset
        "하": 1,
        "중": 2,
        "상": 3,
        # Fallbacks in case of alternative representations
        "LOW": 1,
        "MID": 2,
        "HIGH": 3,
    }
    return m.get(str(level_nm).strip().upper(), m.get(str(level_nm).strip(), None))


@dataclass
class ProgressStat:
    weeklyRate: float
    cookedCount: int
    avgDifficulty: Optional[float]
    avgMinutes: Optional[float]


class StatsService:
    def _fetch_user_goal(self, user_id: str) -> int:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT goal FROM user_info WHERE id=%s", (user_id,))
            row = cur.fetchone()
        return int(row["goal"]) if row and row.get("goal") is not None else 3

    def _week_bounds(self, selected: date) -> Tuple[date, date]:
        start = _week_start(selected)
        end = start + timedelta(days=6)
        return start, end

    def get_progress(self, user_id: str, selected: Optional[date] = None) -> ProgressStat:
        """Return weekly KPI numbers for dashboard cards.

        - weeklyRate: cookedCount / user_weekly_goal * 100
        - cookedCount: number of cooked entries (selected_recipe.action=1) in the current week
        - avgDifficulty: average difficulty mapped to 1..3 over cooked recipes this week
        - avgMinutes: average cooking_time over cooked recipes this week
        """
        selected = selected or date.today()
        week_start, week_end = self._week_bounds(selected)
        goal = max(1, self._fetch_user_goal(user_id))

        with get_conn() as conn, conn.cursor() as cur:
            # Count cooked this week
            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM selected_recipe
                WHERE id=%s AND action=1 AND selected_date >= %s AND selected_date < %s
                """,
                (user_id, week_start, week_end + timedelta(days=1)),
            )
            cooked_row = cur.fetchone() or {"cnt": 0}
            cooked = int(cooked_row.get("cnt") or 0)

            # Join with recipe for difficulty & time averages
            cur.execute(
                """
                SELECT r.level_nm, r.cooking_time
                FROM selected_recipe s
                JOIN recipe r ON s.recipe_id = r.recipe_id
                WHERE s.id=%s AND s.action=1 AND s.selected_date >= %s AND s.selected_date < %s
                """,
                (user_id, week_start, week_end + timedelta(days=1)),
            )
            rows = cur.fetchall() or []

        diffs: List[int] = []
        times: List[float] = []
        for r in rows:
            score = _difficulty_to_score(r.get("level_nm"))
            if score is not None:
                diffs.append(score)
            t = r.get("cooking_time")
            # cooking_time may be stored as string or int; try to coerce
            try:
                if t is not None:
                    times.append(float(t))
            except Exception:
                pass

        weekly_rate = round((cooked / goal) * 100.0, 1) if goal > 0 else 0.0
        avg_diff = round(sum(diffs) / len(diffs), 2) if diffs else None
        avg_min = round(sum(times) / len(times), 1) if times else None

        return ProgressStat(
            weeklyRate=weekly_rate,
            cookedCount=cooked,
            avgDifficulty=avg_diff,
            avgMinutes=avg_min,
        )

    def get_level_distribution(self, user_id: str, selected: Optional[date] = None) -> List[Dict[str, Any]]:
        """Return monthly distribution by difficulty level_nm.

        Output: [{ label: level_nm, count: int }, ...]
        """
        selected = selected or date.today()
        month_start, month_end = _month_range(selected)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.level_nm AS label, COUNT(*) AS count
                FROM selected_recipe s
                JOIN recipe r ON s.recipe_id = r.recipe_id
                WHERE s.id=%s AND s.action=1 AND s.selected_date >= %s AND s.selected_date < %s
                GROUP BY r.level_nm
                """,
                (user_id, month_start, month_end + timedelta(days=1)),
            )
            rows = cur.fetchall() or []
        # Normalize label to non-empty
        return [{"label": (r.get("label") or "기타"), "count": int(r.get("count") or 0)} for r in rows]

    def get_category_distribution(self, user_id: str, selected: Optional[date] = None) -> List[Dict[str, Any]]:
        """Return monthly distribution by recipe category (ty_nm)."""
        selected = selected or date.today()
        month_start, month_end = _month_range(selected)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.ty_nm AS label, COUNT(*) AS count
                FROM selected_recipe s
                JOIN recipe r ON s.recipe_id = r.recipe_id
                WHERE s.id=%s AND s.action=1 AND s.selected_date >= %s AND s.selected_date < %s
                GROUP BY r.ty_nm
                """,
                (user_id, month_start, month_end + timedelta(days=1)),
            )
            rows = cur.fetchall() or []
        return [{"label": (r.get("label") or "기타"), "count": int(r.get("count") or 0)} for r in rows]


    def get_progress_trend(self, user_id: str, selected: Optional[date] = None) -> Dict[str, Any]:
        """Return monthly weekly trend of achievement rate.

        - For each week in the month, compute cooked count and rate = cooked/goal*100.
        - monthRate is the average of weekly rates over the month (rounded to 1 decimal).
        """
        selected = selected or date.today()
        month_start, month_end = _month_range(selected)

        # Build week ranges that cover the month (Mon-Sun windows intersecting the month)
        weeks: List[Tuple[date, date]] = []
        cur_start = _week_start(month_start)
        while cur_start <= month_end:
            cur_end = cur_start + timedelta(days=6)
            # Only include weeks that intersect the month
            if cur_end >= month_start and cur_start <= month_end:
                weeks.append((cur_start, cur_end))
            cur_start = cur_start + timedelta(days=7)

        goal = max(1, self._fetch_user_goal(user_id))
        week_items: List[Dict[str, Any]] = []

        month_total_cooked = 0
        month_goal_sum = 0.0

        with get_conn() as conn, conn.cursor() as cur:
            for idx, (ws, we) in enumerate(weeks, start=1):
                # Label by week order within the month: 1주차, 2주차 ...
                label = f"{idx}주차"
                # Segment for this week that lies within the month
                seg_start = max(ws, month_start)
                seg_end_excl = min(we + timedelta(days=1), month_end + timedelta(days=1))
                seg_days = (seg_end_excl - seg_start).days
                seg_days = max(0, min(7, seg_days))

                # Cooked count only within the segment
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM selected_recipe
                    WHERE id=%s AND action=1 AND selected_date >= %s AND selected_date < %s
                    """,
                    (user_id, seg_start, seg_end_excl),
                )
                row = cur.fetchone() or {"cnt": 0}
                cooked = int(row.get("cnt") or 0)
                month_total_cooked += cooked

                # Scale weekly goal by days in segment
                scaled_goal = (goal * (seg_days / 7.0)) if seg_days > 0 else 0.0
                month_goal_sum += scaled_goal

                rate = round(((cooked / scaled_goal) * 100.0), 1) if scaled_goal > 0 else 0.0
                week_items.append({
                    "week": label,
                    "rate": rate,
                    "cooked": cooked,
                    "goal": round(scaled_goal, 2),
                })

        # Monthly goal = sum of scaled weekly goals within the month
        month_rate = round((month_total_cooked / month_goal_sum) * 100.0, 1) if month_goal_sum > 0 else 0.0
        return {"monthRate": month_rate, "weeks": week_items}

    def get_level_weekly(self, user_id: str, selected: Optional[date] = None) -> List[Dict[str, Any]]:
        """Return monthly weekly distribution by difficulty.

        Only '상' and '하' are returned (no '중').
        Output rows: { week, 상, 하, total }
        """
        selected = selected or date.today()
        month_start, month_end = _month_range(selected)

        weeks: List[Tuple[date, date]] = []
        cur_start = _week_start(month_start)
        while cur_start <= month_end:
            cur_end = cur_start + timedelta(days=6)
            if cur_end >= month_start and cur_start <= month_end:
                weeks.append((cur_start, cur_end))
            cur_start = cur_start + timedelta(days=7)

        rows_out: List[Dict[str, Any]] = []
        with get_conn() as conn, conn.cursor() as cur:
            for idx, (ws, we) in enumerate(weeks, start=1):
                label = f"{idx}주차"
                
                # Count only in-month segment for each week
                seg_start = max(ws, month_start)
                seg_end_excl = min(we + timedelta(days=1), month_end + timedelta(days=1))
                
                cur.execute(
                    """
                    SELECT r.level_nm AS level, COUNT(*) AS cnt
                    FROM selected_recipe s
                    JOIN recipe r ON s.recipe_id = r.recipe_id
                    WHERE s.id=%s AND s.action=1 AND s.selected_date >= %s AND s.selected_date < %s
                    GROUP BY r.level_nm
                    """,
                    (user_id, seg_start, seg_end_excl),
                )
                rows = cur.fetchall() or []
                hi = 0
                lo = 0
                for r in rows:
                    lvl = (r.get("level") or "").strip()
                    cnt = int(r.get("cnt") or 0)
                    if lvl == "상" or lvl.upper() == "HIGH":
                        hi += cnt
                    elif lvl == "하" or lvl.upper() == "LOW":
                        lo += cnt
                    # deliberately ignore '중'
                total = hi + lo
                rows_out.append({"week": label, "상": hi, "하": lo, "total": total})

        return rows_out


stats_service = StatsService()

