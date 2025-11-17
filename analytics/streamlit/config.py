import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


ENV_PATH = Path(__file__).resolve().parent / ".env.streamlit"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


@dataclass(frozen=True)
class Settings:
    """Environment-driven configuration."""

    db_host: str = os.getenv("STREAMLIT_DB_HOST", "")
    db_port: int = int(os.getenv("STREAMLIT_DB_PORT", "3306"))
    db_user: str = os.getenv("STREAMLIT_DB_USER", "")
    db_password: str = os.getenv("STREAMLIT_DB_PASSWORD", "")
    db_name: str = os.getenv("STREAMLIT_DB_NAME", "")
    db_charset: str = os.getenv("STREAMLIT_DB_CHARSET", "utf8mb4")
    query_timeout: int = int(os.getenv("STREAMLIT_DB_TIMEOUT", "30"))

    @property
    def is_configured(self) -> bool:
        return all([self.db_host, self.db_user, self.db_password, self.db_name])


settings = Settings()
