"""Công thức stock_data_api.industry_valuation, đọc archive; không chạy API/bot cũ."""
from statistics import median
from datetime import date
import hashlib,json
from integration import DATABASE,ROOT,clean
from research_v2 import number

def pe_of(row):
    direct=number(row.get('pe'));cap=number(row.get('market_cap'));profit=number(row.get('net_income_ttm'))
    value=direct if direct is not None and direct>0 else cap/profit if cap is not None and cap>0 and profit is not None and profit>0 else None
    return value if value is not None and 0<value<=200 else None

def context(ticker,price_date):
    from database import connection
    empty={'status':'MISSING','peer_count':0,'median_pe_ttm':None,'peers':[],'actions':[]}
    if not DATABASE.is_file():return empty
    with connection() as c:
        c.row_factory=__import__('sqlite3').Row
        company=c.execute('SELECT ticker,industry,sector FROM companies WHERE ticker=?',(ticker,)).fetchone()
        if not company:return empty
        company=dict(company)
        def peers(field,classification):
            return [dict(r) for r in c.execute('SELECT c.ticker,s.as_of_utc,s.pe,s.market_cap,s.net_income_ttm FROM companies c JOIN financial_snapshot s ON s.ticker=c.ticker WHERE c.'+field+'=? AND s.as_of_utc=(SELECT MAX(x.as_of_utc) FROM financial_snapshot x WHERE x.ticker=s.ticker)',(classification,))]
        field='sector' if company.get('sector') else 'industry';classification=company.get(field) or ''
        rows=peers(field,classification) if classification else []
        if len(rows)<5 and company.get('industry') and field!='industry':field='industry';classification=company['industry'];rows=peers(field,classification)
        accepted=[{**row,'pe_ttm':pe_of(row)} for row in rows if pe_of(row) is not None and str(row.get('as_of_utc',''))[:10]<=price_date]
        values=[row['pe_ttm'] for row in accepted]
        stock=c.execute('SELECT * FROM financial_snapshot WHERE ticker=? AND substr(as_of_utc,1,10)<=? ORDER BY as_of_utc DESC LIMIT 1',(ticker,price_date)).fetchone()
        stock=dict(stock) if stock else {}
        actions=[dict(r) for r in c.execute('SELECT * FROM corporate_actions WHERE ticker=? AND row_valid=1 AND substr(ex_date,1,10)<=? ORDER BY ex_date DESC LIMIT 4',(ticker,price_date))]
    dates=sorted({str(row['as_of_utc'])[:10] for row in accepted});m=median(values) if values else None;stock_pe=pe_of(stock)
    aligned=bool(stock and len(dates)==1 and dates[0]==str(stock['as_of_utc'])[:10])
    return clean({'status':'ARCHIVE_ALIGNED' if aligned else 'ARCHIVE_MIXED_DATES','classification_field':field,'classification':classification,
        'peer_count':len(values),'median_pe_ttm':m,'peers':accepted,'snapshot':stock,'stock_pe_ttm':stock_pe,
        'premium_pct':(stock_pe/m-1)*100 if stock_pe and m and aligned else None,'snapshot_dates':dates,'actions':actions,
        'method':'X10: sector trước; ít hơn 5 bản ghi thì chuyển industry. P/E nguồn dương, nếu thiếu dùng vốn hóa/LNST TTM khi cả hai dương; loại P/E > 200. Mẫu có thể gồm chính mã đang phân tích.',
        'note':'Snapshot lưu trữ, không phải định giá ngành tại phiên giá mới. Chỉ so P/E lưu trữ với mẫu cùng ngày; không gán giá mục tiêu và không đưa vào điểm FA.'})

def enrich_context(b):
    price_date=str(b['prices'][-1]['date'])[:10]
    if DATABASE.is_file():b['x10_context']=context(b['ticker'],price_date)
    elif not b.get('x10_context'):b['x10_context']={'status':'MISSING','peer_count':0,'median_pe_ttm':None,'peers':[],'actions':[]}
    return b
