#!/bin/bash
set -euo pipefail

set -a
source /root/monitoring/.mail_env
set +a

cd /root/monitoring/news

/root/monitoring/news/venv/bin/python3 fetch_news.py
