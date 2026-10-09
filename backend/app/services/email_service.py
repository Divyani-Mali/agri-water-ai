import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_password_reset_email(email: str, reset_url: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Reset your Smart Irrigation AI password"
    message["From"] = settings.SMTP_FROM
    message["To"] = email
    message.set_content(
        "We received a request to reset your password. "
        f"Use this one-time link within 30 minutes: {reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        if settings.SMTP_STARTTLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(message)