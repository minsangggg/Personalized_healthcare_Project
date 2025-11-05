import smtplib
from email.mime.text import MIMEText

from fastapi import HTTPException

from app.core.config import get_settings


def send_email(recipient: str, subject: str, body: str) -> None:
    """Send an email using SMTP credentials from the environment."""
    settings = get_settings()

    if not settings.smtp_sender or not settings.smtp_app_password:
        raise HTTPException(status_code=500, detail="이메일 발송 설정이 완료되지 않았습니다.")

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.smtp_sender
    message["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(settings.smtp_sender, settings.smtp_app_password)
            smtp.send_message(message)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=f"이메일 발송 실패: {exc}") from exc
