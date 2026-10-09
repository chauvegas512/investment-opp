"""Khớp lệnh VCI có timestamp; không dùng giá trong phiên thay tín hiệu EOD."""
import time,threading,math
from datetime import datetime,time as dt_time
from zoneinfo import ZoneInfo
import pandas as pd
from integration import clean
TZ=ZoneInfo('Asia/Ho_Chi_Minh');_cache={};_lock=threading.Lock()

def market_open(now=None):
    now=now or datetime.now(TZ);t=now.time().replace(tzinfo=None)
    return now.weekday()<5 and (dt_time(9)<=t<=dt_time(11,30) or dt_time(13)<=t<=dt_time(14,45))

def normalize_trade(row,ticker,now=None):
    now=now or datetime.now(TZ);stamp=pd.Timestamp(row['time'])
    if stamp.tzinfo is None:stamp=stamp.tz_localize(TZ)
    age=(pd.Timestamp(now)-stamp).total_seconds();price=float(row['price'])*1000
    if not math.isfinite(price) or not math.isfinite(age) or price<=0 or age< -120:raise ValueError('INVALID_TRADE')
    fresh=age<=300 and market_open(now)
    return clean({'ticker':ticker,'price_vnd':price,'matched_volume':row.get('volume'),'source':'VCI / Vnstock intraday','source_time':stamp.isoformat(),
        'fetched_at':now.isoformat(timespec='seconds'),'age_seconds':age,'fresh':fresh,'market_open':market_open(now),
        'status':'RECENT_TRADE' if fresh else 'MARKET_CLOSED_LAST_TRADE' if not market_open(now) else 'STALE_TRADE',
        'note':'Giá khớp nguồn VCI đã đổi nghìn VND sang VND; không thay giá đóng cửa trong FA/TA.'})

def fetch(ticker,force=False):
    with _lock:
        old=_cache.get(ticker)
        if old and not force and time.time()-old[0]<(30 if market_open() else 300):return old[1]
    try:
        from vnstock import Quote
        frame=Quote(symbol=ticker,source='VCI').intraday(page_size=2)
        if frame.empty:raise ValueError('NO_TRADES')
        if frame.attrs.get('symbol') and frame.attrs['symbol']!=ticker:raise ValueError('WRONG_SYMBOL')
        result=normalize_trade(frame.sort_values('time').iloc[-1].to_dict(),ticker)
    except Exception as e:result={'ticker':ticker,'status':'UNAVAILABLE','error':type(e).__name__,'note':'Chưa lấy được khớp lệnh có thời điểm; không coi bản lưu là realtime.'}
    with _lock:_cache[ticker]=(time.time(),result)
    return result

def closed_daily(frame,now=None):
    now=now or datetime.now(TZ)
    if frame.empty:return frame
    dates=pd.to_datetime(frame['date']).dt.date
    # Sau 15:00 mới chấp nhận thanh EOD trong ngày; vẫn chờ nguồn cập nhật nếu chưa có.
    cutoff=now.date()
    if now.time().replace(tzinfo=None)<dt_time(15):return frame.loc[dates<cutoff].copy()
    return frame.loc[dates<=cutoff].copy()
