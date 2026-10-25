"""Explicit, individually approved outbound messages only."""
import os
import smtplib
import ssl
from email.message import EmailMessage


class MailError(RuntimeError):
    pass


def available():
    required = ("VALDRIQ_SMTP_HOST", "VALDRIQ_SMTP_FROM")
    return all(os.getenv(key, "").strip() for key in required)


def deliver(recipient, subject, body):
    if not available():
        raise MailError("SMTP ist nicht konfiguriert.")
    if "\r" in subject or "\n" in subject:
        raise MailError("Betreff darf keine Zeilenumbrüche enthalten.")
    host = os.environ["VALDRIQ_SMTP_HOST"]
    port = int(os.getenv("VALDRIQ_SMTP_PORT", "587"))
    username = os.getenv("VALDRIQ_SMTP_USER", "")
    password = os.getenv("VALDRIQ_SMTP_PASSWORD", "")
    message = EmailMessage()
    message["From"] = os.environ["VALDRIQ_SMTP_FROM"]
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    try:
        if port == 465:
            client = smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context())
        elif os.getenv("VALDRIQ_SMTP_STARTTLS", "true").lower() == "true":
            client = smtplib.SMTP(host, port, timeout=20)
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
        else:
            raise MailError("Unsicherer SMTP-Verbindungsaufbau ist nicht erlaubt. STARTTLS oder Port 465 verwenden.")
        with client:
            if username:
                client.login(username, password)
            client.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise MailError(f"SMTP-Versand fehlgeschlagen: {type(exc).__name__}") from exc
