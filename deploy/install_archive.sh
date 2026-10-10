#!/usr/bin/env bash
set -euo pipefail
mkdir -p /opt/stocklens/shared/archive
gzip -dc /tmp/stocklens-archive.sqlite.gz > /opt/stocklens/shared/archive/stocks_analysis.sqlite.pending
python3 - <<'PY'
import sqlite3
path='/opt/stocklens/shared/archive/stocks_analysis.sqlite.pending'
with sqlite3.connect('file:'+path+'?mode=ro',uri=True) as db:
    result=db.execute('PRAGMA quick_check').fetchone()[0]
    if result!='ok':raise RuntimeError('Archive integrity check failed')
    print('Archive integrity:',result,'/ companies:',db.execute('SELECT count(*) FROM companies').fetchone()[0])
PY
chmod 444 /opt/stocklens/shared/archive/stocks_analysis.sqlite.pending
mv /opt/stocklens/shared/archive/stocks_analysis.sqlite.pending /opt/stocklens/shared/archive/stocks_analysis.sqlite
