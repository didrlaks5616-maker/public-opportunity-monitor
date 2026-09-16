#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p "$SCRIPT_DIR/logs"

if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
  echo "ERROR: .env not found. Copy .env.example to .env and fill required secrets." >&2
  exit 2
fi

if [[ ! -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  echo "ERROR: .venv/bin/python not found. Run: bash scripts/setup_vps.sh" >&2
  exit 2
fi

set -a
source "$SCRIPT_DIR/.env"
set +a

export TZ="${TZ:-Asia/Seoul}"
LOG_FILE="$SCRIPT_DIR/logs/monitor-$(date +%Y-%m-%d).log"
echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] START" >> "$LOG_FILE"
set +e
"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/run_monitor.py" >> "$LOG_FILE" 2>&1
STATUS=$?
set -e
echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] END exit=$STATUS" >> "$LOG_FILE"
exit "$STATUS"
