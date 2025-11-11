import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from .jobs import (
  JOB_DEFINITIONS,
  aggregate_event_results,
  CHECK_INTERVAL,
  RANK_AGGREGATION_INTERVAL_HOURS,
)

_base_logger = logging.getLogger("uvicorn.error")
log = _base_logger.getChild("badges.automation.runtime")

_scheduler: Optional[BackgroundScheduler] = None


def start_badge_automation():
  global _scheduler
  if _scheduler:
    log.info("Badge automation scheduler already running.")
    return _scheduler

  scheduler = BackgroundScheduler()
  for name, job, seconds in JOB_DEFINITIONS:
    log.info("Registering badge job '%s' (interval=%ss)", name, seconds)
    scheduler.add_job(job, "interval", seconds=seconds, max_instances=1, id=f"badge-{name}")

  log.info(
    "Registering badge job 'rank-aggregation' (interval=%sh)",
    RANK_AGGREGATION_INTERVAL_HOURS,
  )
  scheduler.add_job(
    aggregate_event_results,
    "interval",
    hours=RANK_AGGREGATION_INTERVAL_HOURS,
    max_instances=1,
    id="badge-rank-aggregation",
  )

  scheduler.start()
  _scheduler = scheduler
  log.info(
    "Badge automation scheduler started (check_interval=%ss, rank_interval=%sh)",
    CHECK_INTERVAL,
    RANK_AGGREGATION_INTERVAL_HOURS,
  )
  return scheduler


def stop_badge_automation():
  global _scheduler
  if not _scheduler:
    return
  try:
    _scheduler.shutdown(wait=False)
    log.info("Badge automation scheduler stopped.")
  finally:
    _scheduler = None
