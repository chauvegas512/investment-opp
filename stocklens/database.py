"""Read-only access to the user's X10 archive. Never launch its retired pipeline."""
from contextlib import contextmanager
import sqlite3
import pandas as pd
from integration import DATABASE, clean

@contextmanager
def connection():
    conn=sqlite3.connect(DATABASE.as_uri()+'?mode=ro',uri=True,timeout=10)
    conn.execute('PRAGMA query_only=ON')
    try:
        yield conn
    finally:
        conn.close()

def archive(ticker):
    if not DATABASE.is_file():
        return {}
    with connection() as conn:
        company=pd.read_sql_query('SELECT * FROM companies WHERE ticker=?',conn,params=[ticker])
        frames={}
        for name in ('price_daily','benchmark_daily','financial_annual','financial_quarterly'):
            symbol='VNINDEX' if name=='benchmark_daily' else ticker
            suffix=' AND date>=? ORDER BY date' if name.endswith('daily') else ' AND row_valid=1'
            params=[symbol,'2024-01-01'] if name.endswith('daily') else [symbol]
            frames[name]=pd.read_sql_query('SELECT * FROM '+name+' WHERE ticker=?'+suffix,conn,params=params)
        frames['company']=clean(company.iloc[0].to_dict()) if not company.empty else {}
        return frames

def symbols():
    from integration import module,MINER
    classifier=module('arminer.data.industry').IndustryClassifier(workspace_root=MINER)
    classifier.initialize()
    rows={ticker:{'ticker':ticker,'company_name':info.get('name') or ticker,'exchange':info.get('exchange'),'sector':info.get('icb_l1')} for ticker,info in classifier._ticker_full_map.items()}
    if DATABASE.is_file():
        with connection() as conn:
            for row in pd.read_sql_query('SELECT ticker,company_name,exchange,sector FROM companies',conn).to_dict('records'):
                rows[row['ticker']]={**rows.get(row['ticker'],{}),**{k:v for k,v in row.items() if v is not None and not pd.isna(v) and v!=''}}
    return clean([rows[ticker] for ticker in sorted(rows)])

def comparison(live, stored):
    """Record discrepancies rather than mixing financial concepts or provider vintages."""
    if live.empty or stored.empty: return []
    rows=[]
    for code in ('revenue','net_income','equity','total_assets'):
        a=live[live.item_code==code]; b=stored[stored.item_code==code]
        if a.empty or b.empty: continue
        common=set(a.report_period.astype(str)) & set(b.report_period.astype(str))
        if not common: continue
        year=max(common)
        x=a[a.report_period.astype(str)==year]; y=b[b.report_period.astype(str)==year]
        if x.empty or y.empty: continue
        lv,sv=float(x.iloc[-1].value),float(y.iloc[-1].value)
        if lv and abs(lv-sv)/abs(lv)>.01:
            rows.append({'item_code':code,'period':year,'live_value':lv,'archive_value':sv,'difference_pct':(sv/lv-1)*100,'resolution':'USE_LIVE_VCI; ARCHIVE_NOT_MERGED'})
    return rows
