import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

smtp_user = os.environ["RG_SMTP_USER"]
smtp_pass = os.environ["RG_SMTP_APP_PASSWORD"]
mail_from = os.environ.get("RG_MAIL_FROM", smtp_user)

import os; recipients = [r.strip() for r in os.environ.get("INSTITUTIONS_MAIL_TO", "").split(",") if r.strip()]
to_email = ", ".join(recipients)

today     = datetime.now()
subject   = f"{today.strftime('%d.%m.%Y')} Tarihli Resmî Gazete"

with open("/root/rg_mail.html", "r", encoding="utf-8") as f:
    html_body = f.read()

if 'resmigazete.gov.tr' not in html_body or "madde" not in html_body:
    print("No content found. Mail not sent.")
    raise SystemExit(0)

msg = MIMEMultipart("alternative")
msg["Subject"] = subject
msg["From"]    = mail_from
msg["To"]      = to_email

msg.attach(MIMEText(html_body, "html", "utf-8"))

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(smtp_user, smtp_pass)
    server.sendmail(smtp_user, recipients, msg.as_string())

print("Mail sent successfully.")