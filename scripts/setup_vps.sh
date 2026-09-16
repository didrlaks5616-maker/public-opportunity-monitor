#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "== VPS setup =="
command -v python3 >/dev/null || { echo "ERROR: python3 not found. Install Python 3 first."; exit 1; }
python3 --version
if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "ERROR: Python venv module is unavailable. On Debian/Ubuntu run: sudo apt install python3-venv"
  exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
mkdir -p logs
chmod +x run.sh scripts/network_check.sh

if [[ ! -f .env ]]; then
  echo "NOTICE: .env does not exist. Run: cp .env.example .env && nano .env && chmod 600 .env"
else
  chmod 600 .env
  echo ".env found and permissions set to 600."
fi

echo "Timezone check:"
if command -v timedatectl >/dev/null 2>&1; then
  timedatectl | sed -n '1,8p'
else
  date
fi

echo "Setup complete. Next: bash scripts/network_check.sh"
