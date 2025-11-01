import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv


load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """Application settings loaded from environment."""

    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-secret"))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALG", "HS256"))
    access_minutes: int = field(default_factory=lambda: int(os.getenv("ACCESS_MIN", "30")))
    refresh_days: int = field(default_factory=lambda: int(os.getenv("REFRESH_DAYS", "7")))
    access_expire_minutes: int = field(default_factory=lambda: int(os.getenv("ACCESS_EXPIRE_MIN", "30")))
    refresh_expire_days: int = field(default_factory=lambda: int(os.getenv("REFRESH_EXPIRE_DAYS", "7")))
    front_origin: str = field(default_factory=lambda: os.getenv("FRONT_ORIGIN", "http://localhost:5173"))

    send_emails: bool = field(default_factory=lambda: _bool_env("SEND_EMAILS", default=False))
    dev_return_codes: bool = field(default_factory=lambda: _bool_env("DEV_RETURN_CODES", default=False))

    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "127.0.0.1"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "25")))
    smtp_from: str = field(default_factory=lambda: os.getenv("SMTP_FROM", "noreply@cookus.example.com"))
    smtp_starttls: bool = field(default_factory=lambda: _bool_env("SMTP_STARTTLS", default=False))
    smtp_ssl_tls: bool = field(default_factory=lambda: _bool_env("SMTP_SSL_TLS", default=False))

    db_host: str = field(default_factory=lambda: os.getenv("DB_HOST", "127.0.0.1"))
    db_port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "3306")))
    db_user: str = field(default_factory=lambda: os.getenv("DB_USER", ""))
    db_password: str = field(default_factory=lambda: os.getenv("DB_PASS", ""))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", ""))
    db_charset: str = field(default_factory=lambda: os.getenv("DB_CHARSET", "utf8mb4"))

    code_ttl_minutes: int = field(default_factory=lambda: int(os.getenv("CODE_TTL_MIN", "10")))

    @property
    def cors_origins(self) -> List[str]:
        default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
        custom_origins = os.getenv("CORS_ORIGINS")
        if not custom_origins:
            return default_origins
        return [origin.strip() for origin in custom_origins.split(",") if origin.strip()]


settings = Settings()


print(f"[AUTH-BOOT] algo={settings.jwt_algorithm} secret={settings.jwt_secret[:3]}*** len={len(settings.jwt_secret)}")
print(
    "[SMTP]"
    f" host={settings.smtp_host}"
    f" port={settings.smtp_port}"
    f" from={settings.smtp_from}"
    f" STARTTLS={settings.smtp_starttls}"
    f" SSL_TLS={settings.smtp_ssl_tls}"
)
print(
    "[DB]"
    f" host={settings.db_host}"
    f" port={settings.db_port}"
    f" name={settings.db_name}"
)
