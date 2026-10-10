#!/usr/bin/env bash
set -euo pipefail
systemctl is-active stocklens caddy
ss -ltn | sed -n '1,12p'
if command -v ufw >/dev/null; then ufw status; fi
journalctl -u caddy -n 40 --no-pager
curl -sS --connect-timeout 5 --max-time 10 https://acme-v02.api.letsencrypt.org/directory | head -c 300 || true
