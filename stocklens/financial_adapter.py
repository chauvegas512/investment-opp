"""Annual Miner local parquet -> the shared financial row contract, exact aliases only."""
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from integration import MINER,clean

ALIASES={
    'bs_tong_cong_tai_san':'total_assets',
    'bs_tong_tai_san':'total_assets',
    'bs_tai_san_ngan_han':'current_assets',
    'bs_no_ngan_han':'current_liabilities',
    'is_doanh_thu_thuan':'revenue',
    'is_doanh_so_thuan':'revenue',
    'is_lai_lo_thuan_sau_thue':'net_income',
    'is_loi_nhuan_sau_thue':'net_income',
    'is_co_dong_cua_cong_ty_me':'net_income_parent',
    'cf_luu_chuyen_tien_thuan_tu_cac_hoat_dong_san_xuat_kinh_doanh':'operating_cash_flow',
}

def miner_rows(ticker):
    root=MINER/'src/arminer/data/bctc_data'
    rows=[]
    for statement in ('balance_sheet','income_statement','cash_flow'):
        for path in (root/statement).glob('*.parquet'):
            frame=pd.read_parquet(path,filters=[('ticker','==',ticker)])
            for row in frame.to_dict('records'):
                raw=row['item_code'];code=ALIASES.get(raw)
                if code is None: continue
                rows.append({'ticker':ticker,'report_period':str(row['year']),'period_type':'annual',
                    'statement':statement,'item_code':code,'raw_item_code':raw,'item_name':row['item_name'],
                    'value':row['value'],'unit':'VND','source':'Annual Report Miner bundled BCTC',
                    'source_file':row['source_file'],'source_sheet':row['source_sheet'],
                    'published_date':None,'fetched_at':datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(timespec='seconds')})
    return pd.DataFrame(clean(rows))
