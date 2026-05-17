import os
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

ERROR_LOG_FILE = Path("/root/monitoring/output/institutions_error.log")

SMTP_HOST = os.getenv("RG_SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("RG_SMTP_PORT", "587").strip())
SMTP_USER = os.getenv("RG_SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("RG_SMTP_APP_PASSWORD", "").strip()
MAIL_FROM  = os.getenv("RG_MAIL_FROM", SMTP_USER).strip()

MAIL_TO = os.getenv("INSTITUTIONS_ERROR_MAIL_TO", "").strip() or os.getenv("INSTITUTIONS_MAIL_TO", "").strip()
MAIL_CC = os.getenv("INSTITUTIONS_ERROR_MAIL_CC", "").strip()
MAIL_BCC = os.getenv("INSTITUTIONS_ERROR_MAIL_BCC", "").strip()

TARGET_DATE = os.getenv("TARGET_DATE", "").strip()


def require_env(value: str, name: str) -> str:
    if not value:
        raise SystemExit(f"Eksik ortam değişkeni: {name}")
    return value


def split_emails(value: str) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def read_error_tail() -> str:
    if not ERROR_LOG_FILE.exists():
        return "Hata log dosyası bulunamadı."

    lines = ERROR_LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = lines[-200:] if lines else ["Hata logu boş."]
    return "\n".join(tail)


def build_subject() -> str:
    date_part = TARGET_DATE if TARGET_DATE else datetime.now().strftime("%Y-%m-%d")
    return f"Institutions Pipeline Hata Bildirimi - {date_part}"


def build_message(error_text: str) -> tuple[MIMEMultipart, list[str]]:
    smtp_user = require_env(SMTP_USER, "RG_SMTP_USER")
    smtp_password = require_env(SMTP_PASSWORD, "RG_SMTP_APP_PASSWORD")
    mail_to = require_env(MAIL_TO, "INSTITUTIONS_ERROR_MAIL_TO veya INSTITUTIONS_MAIL_TO")

    to_list = split_emails(mail_to)
    cc_list = split_emails(MAIL_CC)
    bcc_list = split_emails(MAIL_BCC)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = build_subject()
    msg["From"] = MAIL_FROM
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; font-size: 14px; color: #111;">
        <h2>Institutions Pipeline Hata Bildirimi</h2>
        <p><strong>TARGET_DATE:</strong> {TARGET_DATE or 'tanımsız'}</p>
        <p>Pipeline çalışması sırasında hata oluştu. Son log çıktısı aşağıdadır:</p>
        <pre style="white-space: pre-wrap; background: #f6f8fa; border: 1px solid #ddd; padding: 12px; border-radius: 6px;">{error_text}</pre>
      </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg, to_list + cc_list + bcc_list


def send_mail(msg: MIMEMultipart, recipients: list[str]) -> None:
    smtp_user = require_env(SMTP_USER, "RG_SMTP_USER")
    smtp_password = require_env(SMTP_PASSWORD, "RG_SMTP_APP_PASSWORD")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipients, msg.as_string())


def main() -> None:
    error_text = read_error_tail()
    msg, recipients = build_message(error_text)
    send_mail(msg, recipients)
    print("Error notification mail sent successfully.")


if __name__ == "__main__":
    main()
