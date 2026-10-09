"""Bổ sung mọi ticker theo cùng pipeline, giữ nguồn và thời điểm riêng từng dataset."""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from integration import module,clean

def update(b,progress=lambda s:None):
    import copy
    b=copy.deepcopy(b)
    from analysis import normalize_prices,evaluate,VCI_ALIASES
    from live_quote import closed_daily,fetch as quote
    from mining import latest_news,reports_for
    from annual_insights import fetch
    from company_identity import attach
    from research import enrich
    now=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'));ticker=b['ticker'];attach(b['company'],ticker)
    annual_date=max((r.get('fetched_at','') for r in b.get('annual',[])),default='')
    if not b.get('annual') or not b.get('quarterly') or not annual_date.startswith(now.date().isoformat()):
        from analysis import finance_rows
        annual,_=finance_rows(ticker,'year');quarterly,_=finance_rows(ticker,'quarter')
        if not annual.empty:b['annual']=clean(annual.to_dict('records'))
        if not quarterly.empty:b['quarterly']=clean(quarterly.to_dict('records'))
    for row in b.get('annual',[])+b.get('quarterly',[]):
        row['item_code']=VCI_ALIASES.get(row.get('statement'),{}).get(row.get('raw_item_code'),row['item_code'])
    scraper=module('vn_stock_scraper_complete')
    progress('Cập nhật giá chốt phiên và VN-Index…')
    for field,symbol in [('prices',ticker),('benchmark','VNINDEX')]:
        try:
            frame,_=scraper.fetch_ta_daily_range(symbol,now-timedelta(days=850),now)
            frame=closed_daily(normalize_prices(frame),now)
            if not frame.empty:b[field]=clean(frame.tail(420).to_dict('records'))
        except Exception:pass
    signal,warnings=evaluate(b['company'],pd.DataFrame(b['prices']),pd.DataFrame(b['benchmark']),pd.DataFrame(b['annual']),now)
    b['signal']=signal
    retained=[w for w in b.get('warnings',[]) if 'SQLite' in w or 'lưu trữ' in w or 'hợp nhất' in w]
    b['warnings']=list(dict.fromkeys(retained+warnings))
    progress('Bổ sung BCTN, bản tin đa nguồn và khớp lệnh…')
    b['reports']=reports_for(ticker)
    try:b['annual_insights']=fetch(ticker)
    except Exception as e:b['annual_source_status']={'status':'UNAVAILABLE','error':type(e).__name__}
    try:
        fresh=latest_news(ticker,b['company']['company_name'],b['company'].get('company_short_name'),b['company'].get('website'))
        retained=[]
        for item in b.get('news',[]):
            date=pd.to_datetime(item.get('published_date'),errors='coerce',utc=True)
            if item.get('company_confirmed') and not pd.isna(date) and 0<=(pd.Timestamp.now(tz='UTC')-date).total_seconds()<=90*86400:
                retained.append(item)
        combined={item['url']:item for item in retained+fresh}
        b['news']=sorted(combined.values(),key=lambda item:pd.to_datetime(item['published_date'],utc=True),reverse=True)[:6]
        b['news_source_status']={'status':'UPDATED' if fresh else 'NO_NEW_VERIFIED_ARTICLES','retained_articles':len(retained)}
    except Exception as e:b['news_source_status']={'status':'UNAVAILABLE','error':type(e).__name__}
    b['latest_quote']=quote(ticker);b['refreshed_at']=now.isoformat(timespec='seconds')
    b.setdefault('data_updates',{}).update(prices=now.isoformat(timespec='seconds'),news=now.isoformat(timespec='seconds'))
    return enrich(clean(b))
