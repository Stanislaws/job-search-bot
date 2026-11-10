"""Send the digest through Gmail SMTP using an App Password (myaccount.google.com/apppasswords)."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send(subject: str, html_body: str, text_body: str) -> str:
    sender = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    to = os.getenv("EMAIL_TO") or sender

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"Job Search Bot <{sender}>"
    msg["To"] = to
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(sender, password)
        s.send_message(msg)
    return to
