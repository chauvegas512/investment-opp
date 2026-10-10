#!/usr/bin/env bash
set -euo pipefail
systemctl restart stocklens
for i in {1..30}; do
    if curl -sf http://127.0.0.1:8787/api/health; then break; fi
    sleep 2
done
cd /opt/stocklens/current/stocklens
runuser -u stocklens -- env VNSTOCK_DISABLE_AGENT_SETUP=1 PYTHONIOENCODING=utf-8 PLAYWRIGHT_BROWSERS_PATH=/opt/stocklens/browsers /var/lib/stocklens/.venv/bin/python -m unittest discover -s tests -q
python3 - <<'PY'
import urllib.request,json
rows=json.load(urllib.request.urlopen('http://127.0.0.1:8787/api/symbols'))
print('SYMBOLS:',len(rows))
assert len(rows)>=1500
PY
systemctl is-enabled stocklens caddy
