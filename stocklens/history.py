"""Persist user-requested analysis results, without credentials or provider payload logs."""
import json
import sqlite3
import time
from integration import ROOT,clean

def connect():
    (ROOT/'data').mkdir(exist_ok=True)
    db=sqlite3.connect(ROOT/'data/stocklens.sqlite',timeout=15)
    db.execute('CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY,ticker TEXT,created TEXT,bundle TEXT)')
    return db

def save(identifier,bundle):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO reports VALUES (?,?,?,?)',(identifier,bundle['ticker'],bundle['created_at'],json.dumps(clean(bundle),ensure_ascii=False)))

def list_reports():
    with connect() as db:
        return [dict(zip(('job_id','ticker','created_at'),row)) for row in db.execute('SELECT id,ticker,created FROM reports ORDER BY created DESC LIMIT 30')]

def load(identifier):
    with connect() as db:
        row=db.execute('SELECT bundle FROM reports WHERE id=?',(identifier,)).fetchone()
    if not row:return None
    bundle=json.loads(row[0]);bundle['restored_from_export']=True
    if bundle.get('schema_version')!=4:
        from company_identity import attach
        from research import enrich
        attach(bundle['company'],bundle['ticker']);bundle=enrich(bundle);save(identifier,bundle)
    from datetime import datetime,date
    from zoneinfo import ZoneInfo
    latest=date.fromisoformat(str(bundle['prices'][-1]['date'])[:10])
    if not 0<=(datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()-latest).days<=7:
        bundle['signal'].update(final_action='DATA_REVIEW',action_label='Bản lưu: cần cập nhật giá')
        bundle['warnings'].append('Giá trong lịch sử đã cũ; phân tích lại trước khi sử dụng.')
    return {'status':'done','ticker':bundle['ticker'],'message':'Đang xem bản lưu có ngày và nguồn gốc.','started':time.time(),'data':bundle}
