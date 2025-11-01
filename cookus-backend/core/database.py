import pymysql

from .settings import settings


def get_conn():
    """Return a configured pymysql connection."""
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset=settings.db_charset,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
