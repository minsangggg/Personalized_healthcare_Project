from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from urllib.parse import quote_plus

from config import settings


class DatabaseNotConfigured(RuntimeError):
    """Raised when mandatory DB settings are missing."""


_engine: Optional[Engine] = None


def get_engine() -> Engine:
    global _engine
    if not settings.is_configured:
        raise DatabaseNotConfigured(
            "DB 연결 정보가 없습니다. analytics/streamlit/.env.streamlit 파일을 확인하세요."
        )

    if _engine is None:
        password = quote_plus(settings.db_password)
        conn_str = (
            f"mysql+pymysql://{settings.db_user}:{password}"
            f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
            f"?charset={settings.db_charset}"
        )
        _engine = create_engine(conn_str, pool_pre_ping=True, connect_args={"connect_timeout": settings.query_timeout})
    return _engine


def run_query(sql: str, params: Optional[Iterable[Any]] = None) -> pd.DataFrame:
    """Execute a SELECT query and return the result as a DataFrame."""
    engine = get_engine()
    exec_params = tuple(params) if params is not None else None
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params=exec_params)
    return df


def healthcheck() -> Dict[str, Any]:
    """Simple diagnostic info."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "message": "DB 연결 성공"}
    except Exception as exc:  # pragma: no cover - best effort logging
        return {"ok": False, "message": str(exc)}
