"""Bind only localhost. Credentials from stdin/environment stay in process memory."""
import argparse
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8787)
    parser.add_argument('--stdin-key',action='store_true')
    parser.add_argument('--stdin-image-key',action='store_true',help='Read Serper key with hidden input; keep only in process memory.')
    parser.add_argument('--restore-evidence',help='Restore a genuine previously exported evidence JSON for local presentation.')
    args = parser.parse_args()
    if args.stdin_key:
        if sys.stdin.isatty():
            import getpass
            key = getpass.getpass('Vnstock key (memory only): ').strip()
        else:
            key = sys.stdin.readline().strip()
        if key:
            os.environ['VNSTOCK_API_KEY']=key
    else:
        # Load only an existing user-owned .env; never create it or call setup_api_key.
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent/'.env')
    if args.stdin_image_key:
        import getpass
        image_key=getpass.getpass('Serper key (memory only): ').strip()
        if image_key:os.environ['SERPER_API_KEY']=image_key
    # Server verification without SDK setup_api_key (which persists credentials).
    if os.getenv('VNSTOCK_API_KEY'):
        import requests
        try:
            response = requests.get('https://vnstocks.com/api/vnstock/license/verify',
                params={'api_key':os.environ['VNSTOCK_API_KEY'],'device_id':'stocklens-midterm'},timeout=20)
            data = response.json() if response.ok else {}
            os.environ['STOCKLENS_LICENSE_HTTP_STATUS']=str(response.status_code)
            tier = (data.get('subscription') or {}).get('tier')
            os.environ['STOCKLENS_TIER'] = str(tier or 'unverified').upper()
            print('License tier: '+os.environ['STOCKLENS_TIER'], flush=True)
        except Exception:
            os.environ['STOCKLENS_TIER']='UNVERIFIED'
            print('License tier: UNVERIFIED', flush=True)
    import uvicorn
    if args.restore_evidence:
        import json
        import time
        from datetime import datetime
        from zoneinfo import ZoneInfo
        import app
        evidence_path=Path(args.restore_evidence)
        if evidence_path.stat().st_size>5*1024*1024:
            raise ValueError('Evidence JSON exceeds 5 MB')
        evidence=json.loads(evidence_path.read_text(encoding='utf-8'))
        required={'ticker','company','signal','prices','annual','quarterly','sources','news','reports','warnings','mining'}
        if not required<=set(evidence):
            raise ValueError('Not a StockLens evidence bundle')
        now=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
        price_date=datetime.fromisoformat(evidence['signal']['signal_date']).date()
        if not 0<=(now.date()-price_date).days<=7:
            evidence['signal']['final_action']='DATA_REVIEW'
            evidence['signal']['action_label']='Bản lưu - cần cập nhật dữ liệu'
            evidence['warnings'].append('Đây là kết quả đã lưu; giá cần cập nhật trước khi đánh giá ở thời điểm hiện tại.')
        evidence['restored_from_export']=True
        from research import enrich
        from database import archive,comparison
        import pandas as pd
        cached=archive(evidence['ticker'])
        evidence['database_audit']={'read_only':True,'archive_finance':False,'conflicts':comparison(pd.DataFrame(evidence['annual']),cached.get('financial_annual',pd.DataFrame()))}
        from financial_adapter import miner_rows
        miner=miner_rows(evidence['ticker'])
        evidence['miner_financial_audit']={'rows':miner.to_dict('records'),'conflicts':comparison(pd.DataFrame(evidence['annual']),miner)}
        enrich(evidence)
        from history import save
        save('verified-fpt',evidence)
        app.jobs['verified-fpt']={'status':'done','message':'Đang xem dữ liệu thực đã lưu; ngày và nguồn giữ nguyên.',
            'started':time.time(),'ticker':evidence['ticker'],'data':evidence}
        print('Saved evidence: http://127.0.0.1:'+str(args.port)+'/?job=verified-fpt',flush=True)
    uvicorn.run('app:app',host='127.0.0.1',port=args.port,log_level='warning',access_log=False)


if __name__=='__main__':
    main()
