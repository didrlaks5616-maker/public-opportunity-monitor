#!/usr/bin/env bash
set -u

echo "== Network check (no API keys required) =="
echo "Public IP:"
(curl -4 -fsS --connect-timeout 15 --max-time 30 https://api.ipify.org && echo) || echo "PUBLIC_IP FAILED"

check_host() {
  local host="$1"
  echo "--- $host ---"
  if command -v getent >/dev/null 2>&1; then
    getent ahostsv4 "$host" | awk '{print $1}' | sort -u | sed 's/^/IPv4 /' || true
  else
    echo "DNS: getent unavailable"
  fi
  curl -4 -sS -o /dev/null -w "HTTP=%{http_code} CONNECT=%{time_connect} TOTAL=%{time_total}\n" --connect-timeout 15 --max-time 30 "https://$host/" || echo "HTTPS FAILED"
}

check_host "apis.data.go.kr"
check_host "www.bizinfo.go.kr"
