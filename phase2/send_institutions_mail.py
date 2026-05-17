import os
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

HTML_FILE = Path("/root/monitoring/output/institutions_today_preview.html")

SMTP_HOST = os.getenv("RG_SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("RG_SMTP_PORT", "587").strip())
SMTP_USER = os.getenv("RG_SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("RG_SMTP_APP_PASSWORD", "").strip()
MAIL_FROM  = os.getenv("RG_MAIL_FROM", SMTP_USER).strip()

MAIL_TO = os.getenv("INSTITUTIONS_MAIL_TO", "").strip()
MAIL_CC = os.getenv("INSTITUTIONS_MAIL_CC", "").strip()
MAIL_BCC = os.getenv("INSTITUTIONS_MAIL_BCC", "").strip()

SUBJECT_PREFIX = os.getenv("INSTITUTIONS_MAIL_SUBJECT_PREFIX", "Günlük Kurumsal Duyuru Özeti").strip()

MONTHS_TR = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}


def require_env(value: str, name: str) -> str:
    if not value:
        raise SystemExit(f"Eksik ortam değişkeni: {name}")
    return value


def split_emails(value: str) -> list[str]:
    if not value:
        return []
    parts = [x.strip() for x in value.split(",")]
    return [x for x in parts if x]


def build_subject() -> str:
    target_date = os.getenv("TARGET_DATE", "").strip()

    if target_date:
        dt = datetime.strptime(target_date, "%Y-%m-%d")
    else:
        dt = datetime.now()

    return f"{SUBJECT_PREFIX} - {dt.day} {MONTHS_TR[dt.month]} {dt.year}"

def load_html() -> str:
    if not HTML_FILE.exists():
        raise SystemExit(f"HTML preview dosyası bulunamadı: {HTML_FILE}")

    content = HTML_FILE.read_text(encoding="utf-8", errors="replace").strip()
    if not content:
        raise SystemExit("HTML preview dosyası boş")
    return content


def build_message(html_content: str) -> tuple[MIMEMultipart, list[str]]:
    smtp_user = require_env(SMTP_USER, "RG_SMTP_USER")
    mail_to = require_env(MAIL_TO, "INSTITUTIONS_MAIL_TO")

    to_list = split_emails(mail_to)
    cc_list = split_emails(MAIL_CC)
    bcc_list = split_emails(MAIL_BCC)

    if not to_list:
        raise SystemExit("Geçerli bir INSTITUTIONS_MAIL_TO değeri bulunamadı")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = build_subject()
    msg["From"] = MAIL_FROM
    msg["To"] = ", ".join(to_list)

    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    html_part = MIMEText(html_content, "html", "utf-8")
    msg.attach(html_part)

    recipients = to_list + cc_list + bcc_list
    return msg, recipients


def send_mail(msg: MIMEMultipart, recipients: list[str]) -> None:
    smtp_user = require_env(SMTP_USER, "RG_SMTP_USER")
    smtp_password = require_env(SMTP_PASSWORD, "RG_SMTP_APP_PASSWORD")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipients, msg.as_string())


def main() -> None:
    html_content = load_html()
    msg, recipients = build_message(html_content)
    send_mail(msg, recipients)
    print("Institutions mail sent successfully.")


if __name__ == "__main__":
    main()
