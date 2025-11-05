from functools import lru_cache
from typing import List, Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Personalized Healthcare API"
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    db_host: str = Field(default="211.51.163.232", env="DB_HOST")
    db_port: int = Field(default=19306, env="DB_PORT")
    db_user: str = Field(default="lgup3", env="DB_USER")
    db_password: str = Field(default="lgup3P@ssw0rd", env="DB_PASSWORD")
    db_name: str = Field(default="lgup3", env="DB_NAME")

    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")

    smtp_sender: str = Field(default="parkss6468@gmail.com", env="SMTP_SENDER")
    smtp_app_password: str = Field(default="brlr fsrn eceu oukm", env="SMTP_APP_PASSWORD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()  # type: ignore[call-arg]
