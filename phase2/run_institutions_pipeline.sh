#!/usr/bin/env bash

ENV_FILE="/root/monitoring/.mail_env"
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

set -euo pipefail

BASE_DIR="/root/monitoring"
SCRIPT_DIR="$BASE_DIR/institutions"
OUTPUT_DIR="$BASE_DIR/output"

LOG_FILE="$OUTPUT_DIR/institutions_cron.log"
ERROR_LOG_FILE="$OUTPUT_DIR/institutions_error.log"

mkdir -p "$OUTPUT_DIR"

export TARGET_DATE="${TARGET_DATE:-$(date -d "yesterday" +%F)}"

run_pipeline() {
  /root/monitoring/venv/bin/python3 "$SCRIPT_DIR/institutions_fetch_all.py"
  /root/monitoring/venv/bin/python3 "$SCRIPT_DIR/institutions_enrich_all.py"
  /root/monitoring/venv/bin/python3 "$SCRIPT_DIR/institutions_mail_preview.py"
  /root/monitoring/venv/bin/python3 "$SCRIPT_DIR/send_institutions_mail.py"
}

send_error_mail() {
  python3 "$SCRIPT_DIR/send_institutions_error_mail.py" || true
}

{
  echo "============================================================"
  echo "Pipeline start: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "TARGET_DATE=$TARGET_DATE"
  echo "============================================================"
} >> "$LOG_FILE"

if run_pipeline >> "$LOG_FILE" 2>> "$ERROR_LOG_FILE"; then
  echo "Pipeline success: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
else
  {
    echo "Pipeline failed: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "TARGET_DATE=$TARGET_DATE"
    echo "Last 200 lines of error log:"
    tail -n 200 "$ERROR_LOG_FILE"
  } >> "$LOG_FILE"

  send_error_mail >> "$LOG_FILE" 2>> "$ERROR_LOG_FILE"
  exit 1
fi
