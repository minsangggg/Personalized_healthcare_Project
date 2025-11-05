import os
from typing import Optional
from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.orm import sessionmaker
import pandas as pd


def get_database_url() -> Optional[str]:
    url = os.getenv('DB_URL')
    if url:
        return url
    # Fallback components
    host = os.getenv('DB_HOST')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    name = os.getenv('DB_NAME')
    port = os.getenv('DB_PORT', '3306')
    if host and user and name:
        return f"mysql+pymysql://{user}:{password or ''}@{host}:{port}/{name}?charset=utf8mb4"
    return None


def create_session():
    url = get_database_url()
    if not url:
        return None, None
    engine = create_engine(url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def load_supplements_df(engine) -> pd.DataFrame:
    md = MetaData()
    tbl = Table('supplements', md, autoload_with=engine)
    stmt = select(tbl)
    with engine.connect() as conn:
        df = pd.read_sql(stmt, conn)
    return df
