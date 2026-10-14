import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def send_email(
    recipient: str,
    subject: str,
    text_body: str,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.MAIL_FROM_NAME}<{settings.MAIL_FROM_EMAIL}>"
    message["To"] = recipient
    message.set_content(text_body)

    context = ssl.create_default_context()

    with smtplib.SMTP(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        timeout=20,
    ) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()

        smtp.login(
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD,
        )
        smtp.send_message(message)
