from typing import Any

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema

from .settings import settings


class EmailService:
    """Wrap FastMail sending with development friendly behaviour."""

    def __init__(self):
        self._config = ConnectionConfig(
            MAIL_USERNAME="",
            MAIL_PASSWORD="",
            MAIL_FROM=settings.smtp_from,
            MAIL_SERVER=settings.smtp_host,
            MAIL_PORT=settings.smtp_port,
            MAIL_STARTTLS=settings.smtp_starttls,
            MAIL_SSL_TLS=settings.smtp_ssl_tls,
            USE_CREDENTIALS=False,
            VALIDATE_CERTS=False,
        )
        self._fast_mail = FastMail(self._config)

    async def send_email(self, to_email: str, subject: str, body_text: str) -> None:
        msg = MessageSchema(subject=subject, recipients=[to_email], body=body_text, subtype="plain")

        if not settings.send_emails:
            print(f"[DEV EMAIL] To={to_email}\nSubject={subject}\n{body_text}")
            return

        try:
            await self._fast_mail.send_message(msg)
        except Exception as exc:  # pragma: no cover - log and swallow to match previous behaviour
            print(f"[EMAIL ERROR] {exc}")


email_service = EmailService()
