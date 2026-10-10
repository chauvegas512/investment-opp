#!/usr/bin/env bash
set -euo pipefail
iptables -S INPUT
iptables -S OUTPUT
nft list ruleset | sed -n '1,100p'
curl -sS --connect-timeout 5 --max-time 10 -o /dev/null -w 'public-http:%{http_code}\n' "http://${BACKEND_DOMAIN}/api/health" || true
journalctl -u caddy -n 6 --no-pager
