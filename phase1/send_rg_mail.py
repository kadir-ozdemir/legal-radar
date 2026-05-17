import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

smtp_user = os.environ["RG_SMTP_USER"]
smtp_pass = os.environ["RG_SMTP_APP_PASSWORD"]
mail_from = os.environ.get("RG_MAIL_FROM", smtp_user)

recipients = [r.strip() for r in os.environ.get("INSTITUTIONS_MAIL_TO", smtp_user).split(",") if r.strip()]
to_email  = recipients[0] if recipients else smtp_user
bcc_email = recipients[1] if len(recipients) > 1 else ""

today = datetime.now()
today_key = today.strftime("%Y-%m-%d")
subject = f"{today.strftime('%d.%m.%Y')} Tarihli Resmi Gazete"

state_dir = "/root/.rg_state"
state_file = os.path.join(state_dir, "last_sent_date.txt")

os.makedirs(state_dir, exist_ok=True)

with open("/root/rg_mail.html", "r", encoding="utf-8") as f:
    html_body = f.read()

if 'resmigazete.gov.tr' not in html_body or "madde" not in html_body:
    print("No content found. Mail not sent.")
    raise SystemExit(0)

if os.path.exists(state_file):
    with open(state_file, "r", encoding="utf-8") as f:
        last_sent = f.read().strip()
    if last_sent == today_key:
        print(f"Mail already sent for {today_key}. Skipping.")
        raise SystemExit(0)

msg = MIMEMultipart("alternative")
msg["Subject"] = subject
msg["From"] = mail_from
msg["To"] = to_email

part = MIMEText(html_body, "html", "utf-8")
msg.attach(part)

all_recipients = [r for r in [to_email, bcc_email] if r]

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(smtp_user, smtp_pass)
    server.sendmail(smtp_user, all_recipients, msg.as_string())

with open(state_file, "w", encoding="utf-8") as f:
    f.write(today_key)

print("Mail sent successfully.")
