#!/usr/bin/env bash
set -euo pipefail
systemctl restart stocklens
for i in {1..30}; do
    if curl -sf http://127.0.0.1:8787/api/health >/dev/null; then break; fi
    sleep 2
done
python3 - <<'PY'
import urllib.request,json
from pathlib import Path
rows=json.loads(Path('/opt/stocklens/shared/data/deployment-qa/validation.json').read_text())
for row in rows:
    j=json.load(urllib.request.urlopen('http://127.0.0.1:8787/api/jobs/'+row['job_id'],timeout=90))
    assert j['status']=='done' and j['data']['ticker']==row['ticker']
    print('PERSISTENCE_PASS:',row['ticker'])
PY
systemctl is-active stocklens caddy
