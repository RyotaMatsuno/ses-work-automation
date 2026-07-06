from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.utils import formatdate

from dotenv import dotenv_values

ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
SMTP_HOST = "mail65.onamae.ne.jp"
SMTP_PORT = 465
MATSUNO_EMAIL = "r-matsuno@terra-ltd.co.jp"

config = dotenv_values(ENV_PATH)
OUTREACH_FROM_EMAIL = config.get("OUTREACH_FROM_EMAIL", MATSUNO_EMAIL)
OUTREACH_MAIL_PASSWORD = config.get(
    "OUTREACH_MAIL_PASSWORD",
    config.get("SESSALES_MAIL_PASSWORD", ""),
)
SENDER_NAME = config.get("SENDER_NAME", "")
SENDER_COMPANY = config.get("SENDER_COMPANY", "株式会社TERRA")


def send_mail(
    to_email: str,
    subject: str,
    body: str,
    *,
    dry_run: bool = True,
    cc_email: str = MATSUNO_EMAIL,
) -> bool:
    if dry_run:
        print(f"[dry_run] send_mail skipped: to={to_email}, cc={cc_email}, subject={subject}")
        return True

    if not OUTREACH_MAIL_PASSWORD:
        raise RuntimeError("OUTREACH_MAIL_PASSWORD or SESSALES_MAIL_PASSWORD is not set.")

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = OUTREACH_FROM_EMAIL
    message["To"] = to_email
    message["Cc"] = cc_email
    message["Date"] = formatdate(localtime=True)

    recipients = [to_email]
    if cc_email:
        recipients.append(cc_email)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(OUTREACH_FROM_EMAIL, OUTREACH_MAIL_PASSWORD)
        smtp.sendmail(OUTREACH_FROM_EMAIL, recipients, message.as_string())

    return True
