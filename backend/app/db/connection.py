from contextlib import contextmanager
from typing import Iterator

import pymysql

from app.core.config import get_settings


settings = get_settings()


def get_connection() -> pymysql.connections.Connection:
    """Return a new MariaDB connection."""
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


@contextmanager
def connection_scope() -> Iterator[pymysql.connections.Connection]:
    """Context manager that ensures the connection is closed."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
