#!/bin/bash
set -euo pipefail

set -a
source /root/monitoring/.mail_env
set +a

cd /root/monitoring/news

timeout 20m /root/monitoring/news/venv/bin/python3 fetch_news.py
