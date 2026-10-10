#!/usr/bin/env bash
set -euo pipefail
chown -R stocklens:stocklens /opt/stocklens/shared/data/image-cache
journalctl -u stocklens --no-pager -n 35 | grep -E 'Serper|Search|WARNING|error|Error' || true
cd /opt/stocklens/current/stocklens
runuser -u stocklens -- env PLAYWRIGHT_BROWSERS_PATH=/opt/stocklens/browsers /var/lib/stocklens/.venv/bin/python -u - <<'PY'
import requests,json
from pathlib import Path
import pymupdf
base='http://127.0.0.1:8787';out=Path('data/deployment-qa')
rows=json.loads((out/'validation.json').read_text())
for row in rows:
    job=row['job_id'];data=requests.get(base+'/api/jobs/'+job,timeout=90).json()['data']
    assert data['images'],row['ticker']+' image missing'
    markup=requests.get(base+'/api/jobs/'+job+'/report',timeout=90).text
    assert 'data:image/' in markup
    pdf=requests.get(base+'/api/jobs/'+job+'/pdf',timeout=150);pdf.raise_for_status()
    (out/(row['ticker']+'.pdf')).write_bytes(pdf.content)
    with pymupdf.open(stream=pdf.content,filetype='pdf') as doc:
        assert len(doc)==8
        doc[0].get_pixmap(matrix=pymupdf.Matrix(.8,.8)).save(out/(row['ticker']+'-cover.png'))
    row.update(images=len(data['images']),pdf_bytes=len(pdf.content));print(json.dumps(row),flush=True)
(out/'validation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
PY
