from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from nutrition_core import NutritionEngine
from core.database import get_conn
from core import get_current_user

router = APIRouter()

engine: NutritionEngine | None = None


class RecommendRequest(BaseModel):
  age_band: Literal['10대','20대','30대','40대','50대 이상']
  sex: Literal['F','M']
  pregnant_possible: Optional[bool] = False
  shapes: Optional[List[str]] = Field(default_factory=list)
  goals: List[str] = Field(default_factory=list)


@router.on_event("startup")
def _load_engine():
  global engine
  if engine is not None:
    return
  # DB only (PyMySQL via core.database)
  conn = get_conn()
  with conn.cursor() as cur:
    cur.execute(
      """
      SELECT PRDLST_NM, PRIMARY_FNCLTY, RAWMTRL_NM, PRDT_SHAP_CD_NM,
             IFTKN_ATNT_MATR_CN, NTK_MTHD, LAST_UPDT_DTM
      FROM supplements
      """
    )
    rows = cur.fetchall()
  engine = NutritionEngine.from_records(rows)


@router.post('/nutrition/recommend')
def recommend(req: RecommendRequest):
  if engine is None:
    raise HTTPException(500, detail='engine not initialized')
  out = engine.recommend(
    age_band=req.age_band,
    sex=req.sex,
    pregnant_possible=bool(req.pregnant_possible),
    shapes=req.shapes or [],
    goals=req.goals or [],
  )
  return out

# -------- Plans / Calendar / Daily / Take (DB-backed) --------

@router.get('/nutrition/plans')
def list_plans(current_user: str = Depends(get_current_user)):
  uid = current_user
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute(
      """
      SELECT plan_id, supplement_name, time_slot
      FROM supplement_plans
      WHERE user_id=%s AND (deleted_at IS NULL)
      ORDER BY created_at DESC
      """,
      (uid,)
    )
    return cur.fetchall()


@router.post('/nutrition/plans')
def create_plan(body: dict, current_user: str = Depends(get_current_user)):
  uid = current_user
  name = (body.get('supplement_name') or '').strip()
  slot = (body.get('time_slot') or '').strip()
  if not name or not slot:
    raise HTTPException(400, 'invalid payload')
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute(
      """
      INSERT INTO supplement_plans (user_id, supplement_name, time_slot)
      VALUES (%s,%s,%s)
      ON DUPLICATE KEY UPDATE plan_id=LAST_INSERT_ID(plan_id)
      """,
      (uid, name, slot)
    )
    cur.execute("SELECT plan_id, supplement_name, time_slot FROM supplement_plans WHERE plan_id=LAST_INSERT_ID()")
    return cur.fetchone()


@router.delete('/nutrition/plans/{plan_id}')
def delete_plan(plan_id: int, current_user: str = Depends(get_current_user)):
  uid = current_user
  with get_conn() as conn, conn.cursor() as cur:
    # Soft delete (keep row for historical checks)
    cur.execute("UPDATE supplement_plans SET deleted_at=NOW() WHERE user_id=%s AND plan_id=%s", (uid, plan_id))
  return {"ok": True}


@router.put('/nutrition/plans/{plan_id}')
def update_plan(plan_id: int, body: dict, current_user: str = Depends(get_current_user)):
  uid = current_user
  name = (body.get('supplement_name') or '').strip()
  slot = (body.get('time_slot') or '').strip()
  if not name or not slot:
    raise HTTPException(400, 'invalid payload')
  with get_conn() as conn, conn.cursor() as cur:
    # Try update; if unique conflict desired, you can first check duplications
    cur.execute(
      """
      UPDATE supplement_plans
      SET supplement_name=%s, time_slot=%s
      WHERE user_id=%s AND plan_id=%s
      """,
      (name, slot, uid, plan_id)
    )
    cur.execute("SELECT plan_id, supplement_name, time_slot FROM supplement_plans WHERE user_id=%s AND plan_id=%s", (uid, plan_id))
    row = cur.fetchone()
    if not row:
      raise HTTPException(404, 'not found')
    return row


@router.get('/nutrition/calendar')
def month_status(month: str, current_user: str = Depends(get_current_user)):
  if not month or len(month) != 7:
    raise HTTPException(400, 'invalid month')
  uid = current_user
  with get_conn() as conn, conn.cursor() as cur:
    # Determine the first month the user registered any supplement (including soft-deleted)
    cur.execute("SELECT MIN(created_at) AS first_created FROM supplement_plans WHERE user_id=%s", (uid,))
    r = cur.fetchone()
    first_created = r and r.get('first_created')
    if not first_created:
      return []  # no plans at all -> show nothing
    # Compare requested month with the first registration month (YYYY-MM)
    first_ym = f"{first_created.year:04d}-{first_created.month:02d}"
    if month < first_ym:
      return []
    sql = (
      """
      WITH RECURSIVE d AS (
        SELECT DATE(CONCAT(%s, '-01')) AS dt
        UNION ALL
        SELECT dt + INTERVAL 1 DAY FROM d WHERE dt < LAST_DAY(CONCAT(%s, '-01'))
      )
      SELECT d.dt AS date,
             (SELECT COUNT(*) FROM supplement_plans p WHERE p.user_id=%s AND p.deleted_at IS NULL) AS total,
             COALESCE(SUM(CASE WHEN c.taken=1 THEN 1 ELSE 0 END), 0) AS taken
      FROM d
      LEFT JOIN supplement_checks c
        ON c.user_id=%s AND c.date=d.dt
      GROUP BY d.dt
      ORDER BY d.dt
      """
    )
    cur.execute(sql, (month, month, uid, uid))
    # pymysql DictCursor returns datetime.date; align with frontend expectations (YYYY-MM-DD)
    rows = cur.fetchall()
    return [{"date": r["date"].isoformat() if hasattr(r["date"], 'isoformat') else r["date"], "total": r["total"], "taken": r["taken"]} for r in rows]


@router.get('/nutrition/daily')
def daily(date: str, current_user: str = Depends(get_current_user)):
  uid = current_user
  with get_conn() as conn, conn.cursor() as cur:
    # Include active plans + any plans that have a check on the requested date (even if soft-deleted)
    sql = (
      """
      WITH base AS (
        SELECT plan_id FROM supplement_plans WHERE user_id=%s AND deleted_at IS NULL
        UNION
        SELECT DISTINCT plan_id FROM supplement_checks WHERE user_id=%s AND date=%s
      )
      SELECT p.plan_id, p.supplement_name, p.time_slot,
             COALESCE(c.taken, 0) AS taken
      FROM base b
      JOIN supplement_plans p ON p.plan_id=b.plan_id AND p.user_id=%s
      LEFT JOIN supplement_checks c
        ON c.user_id=%s AND c.plan_id=p.plan_id AND c.date=%s
      ORDER BY p.created_at DESC
      """
    )
    cur.execute(sql, (uid, uid, date, uid, uid, date))
    return cur.fetchall()


@router.post('/nutrition/take')
def set_taken(body: dict, current_user: str = Depends(get_current_user)):
  uid = current_user
  try:
    plan_id = int(body.get('plan_id'))
  except Exception:
    raise HTTPException(400, 'invalid plan_id')
  date = (body.get('date') or '').strip()
  taken = 1 if body.get('taken') else 0
  if not date:
    raise HTTPException(400, 'invalid date')
  with get_conn() as conn, conn.cursor() as cur:
    cur.execute(
      """
      INSERT INTO supplement_checks (user_id, plan_id, date, taken)
      VALUES (%s,%s,%s,%s)
      ON DUPLICATE KEY UPDATE taken=VALUES(taken), updated_at=NOW()
      """,
      (uid, plan_id, date, taken)
    )
  return {"ok": True}
