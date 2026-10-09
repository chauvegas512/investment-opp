"""Metadata VCI: xử lý cột trùng tên trước khi chuyển JSON."""
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from integration import clean

def extract_overview(frame,ticker):
    if frame.empty:return {}
    row=frame.iloc[0]
    def entries(key):return [row.iloc[i] for i,col in enumerate(frame.columns) if col==key]
    def first(key):return next((v for v in entries(key) if v is not None and str(v) not in ('nan','None','')),None)
    if str(first('symbol')).upper()!=ticker:return {}
    price,cap=first('current_price'),first('market_cap')
    shares=None;candidates=[]
    for value in entries('issue_share'):
        try:
            n=float(value)
            if math.isfinite(n) and n>0:candidates.append(n)
        except (ValueError,TypeError):pass
    if price and cap:shares=next((n for n in candidates if abs(n*float(price)/float(cap)-1)<1e-4),None)
    elif len(set(candidates))==1:shares=candidates[0]
    return clean({'shares_outstanding':shares,'listing_date':first('listing_date'),'is_bank':first('is_bank'),
        'provider_current_price':price,'provider_market_cap':cap,
        'overview_fetched_at':datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(timespec='seconds'),
        'overview_source':'https://trading.vietcap.com.vn/','share_candidates':list(dict.fromkeys(candidates)),
        'shares_status':'PROVIDER_CONSISTENT' if shares else 'UNVERIFIED_DUPLICATE_COLUMNS'})

def fetch(ticker):
    from vnstock import Company
    return extract_overview(Company(symbol=ticker,source='VCI').overview(),ticker)
