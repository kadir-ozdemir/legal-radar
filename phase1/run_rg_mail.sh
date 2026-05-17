#!/bin/bash
set -e

ENV_FILE="/root/monitoring/.mail_env"
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

python3 /root/rg_extract.py > /root/rg_mail.html
python3 /root/send_rg_mail.py
