"""Chỉ báo từ OHLCV thật; giữ tham số, ngày và số phiên để tái lập."""
import numpy as np
import pandas as pd
from integration import clean

def wilder(series,period):
    values=pd.to_numeric(series,errors='coerce').to_numpy(dtype=float)
    out=np.full(len(values),np.nan)
    valid=np.flatnonzero(np.isfinite(values))
    if len(valid)<period:return pd.Series(out,index=series.index)
    first=valid[0];seed=first+period-1
    if not np.isfinite(values[first:seed+1]).all():return pd.Series(out,index=series.index)
    out[seed]=values[first:seed+1].mean()
    for i in range(seed+1,len(values)):
        if np.isfinite(values[i]) and np.isfinite(out[i-1]):out[i]=(out[i-1]*(period-1)+values[i])/period
    return pd.Series(out,index=series.index)

def technical_frame(records):
    frame=pd.DataFrame(records)
    if frame.empty:return frame
    frame['date']=pd.to_datetime(frame['date']).dt.normalize()
    frame=frame.sort_values('date').drop_duplicates('date',keep='last').reset_index(drop=True)
    for k in ['open','high','low','close','volume','adjusted_close']:
        if k in frame:frame[k]=pd.to_numeric(frame[k],errors='coerce')
    # Giá phân tích cùng chuỗi điều chỉnh của X10; co giãn OHLC theo hệ số nguồn nếu cần.
    adjusted=frame.get('adjusted_close',frame.close).fillna(frame.close)
    factor=adjusted/frame.close
    for key in ['open','high','low']:frame[key]=frame[key]*factor
    frame['close']=adjusted
    for period in [20,50,200]:frame[f'ma{period}']=frame.close.rolling(period,min_periods=period).mean()
    delta=frame.close.diff()
    gain=wilder(delta.clip(lower=0),14);loss=wilder((-delta).clip(lower=0),14)
    frame['rsi14']=100-100/(1+gain/loss)
    frame.loc[(gain==0)&(loss==0),'rsi14']=50
    frame.loc[(gain>0)&(loss==0),'rsi14']=100
    frame['macd']=frame.close.ewm(span=12,adjust=False,min_periods=12).mean()-frame.close.ewm(span=26,adjust=False,min_periods=26).mean()
    frame['macd_signal']=frame.macd.ewm(span=9,adjust=False,min_periods=9).mean()
    frame['macd_hist']=frame.macd-frame.macd_signal
    previous=frame.close.shift()
    tr=pd.concat([frame.high-frame.low,(frame.high-previous).abs(),(frame.low-previous).abs()],axis=1).max(axis=1)
    frame['atr14']=wilder(tr,14)
    # Ngưỡng quan sát dùng 20 phiên TRƯỚC phiên cuối, không nhìn trước dữ liệu.
    frame['support20']=frame.low.shift(1).rolling(20,min_periods=20).min()
    frame['resistance20']=frame.high.shift(1).rolling(20,min_periods=20).max()
    frame['volume_mean20']=frame.volume.shift(1).rolling(20,min_periods=20).mean()
    frame['volume_ratio20']=frame.volume/frame.volume_mean20
    return frame

def technical_research(prices,benchmark):
    f=technical_frame(prices)
    if f.empty:return {'status':'MISSING','series':[],'comparisons':[],'warnings':['Chưa có chuỗi giá hợp lệ.']}
    row=f.iloc[-1];latest=clean(row.to_dict());latest['date']=str(row.date.date())
    interpretations=[]
    ready=[p for p in [20,50,200] if pd.notna(row.get(f'ma{p}'))]
    below=[str(p) for p in ready if row.close<row[f'ma{p}']]
    above=[str(p) for p in ready if row.close>=row[f'ma{p}']]
    interpretations.append('Giá dưới MA'+', MA'.join(below)+'.' if below else ('Giá trên các MA đủ dữ liệu.' if ready else 'Chưa đủ phiên tính MA.'))
    if pd.notna(row.rsi14):
        label='vùng dưới 30' if row.rsi14<30 else ('vùng trên 70' if row.rsi14>70 else 'vùng 30–70')
        interpretations.append(f'RSI(14) {row.rsi14:.1f}: {label}; cần xác nhận xu hướng, không suy ra hành động mua/bán từ RSI riêng lẻ.')
    if pd.notna(row.macd_hist):
        interpretations.append('MACD '+('trên' if row.macd>=0 else 'dưới')+' đường 0; histogram '+('dương' if row.macd_hist>=0 else 'âm')+'. Giao cắt chỉ xác nhận khi so với phiên trước.')
    support,resistance=row.support20,row.resistance20
    if pd.notna(support) and pd.notna(resistance):
        interpretations.append(f'Vùng tham khảo 20 phiên trước: {support:,.0f}–{resistance:,.0f} VND; giá cuối '+('dưới hỗ trợ.' if row.close<support else 'trên kháng cự.' if row.close>resistance else 'nằm trong vùng.'))
    b=pd.DataFrame(benchmark)
    comparisons=[];performance=[];warnings=[]
    if not b.empty:
        b['date']=pd.to_datetime(b.date).dt.normalize();b['benchmark_close']=pd.to_numeric(b.get('adjusted_close',b.close),errors='coerce').fillna(pd.to_numeric(b.close,errors='coerce'))
        joined=f[['date','close']].merge(b[['date','benchmark_close']].drop_duplicates('date'),on='date').dropna().sort_values('date')
        if not joined.empty:
            for label,sessions in [('1 tháng',21),('3 tháng',63),('6 tháng',126),('12 tháng',252)]:
                if len(joined)<=sessions:
                    comparisons.append({'period':label,'sessions':sessions,'status':'MISSING','stock_return':None,'benchmark_return':None,'excess_pp':None});continue
                first,last=joined.iloc[-sessions-1],joined.iloc[-1]
                a=last.close/first.close-1;c=last.benchmark_close/first.benchmark_close-1
                comparisons.append({'period':label,'sessions':sessions,'start_date':str(first.date.date()),'end_date':str(last.date.date()),'stock_return':a,'benchmark_return':c,'excess_pp':(a-c)*100,'status':'READY'})
            last=joined.tail(253).copy()
            last['stock_index']=last.close/last.close.iloc[0]*100;last['benchmark_index']=last.benchmark_close/last.benchmark_close.iloc[0]*100
            last['date']=last.date.dt.strftime('%Y-%m-%d');performance=last[['date','stock_index','benchmark_index']].to_dict('records')
        if not joined.empty and joined.date.iloc[-1]!=f.date.iloc[-1]:warnings.append('VN-Index thiếu phiên giá cuối; so sánh chốt tại ngày chung gần nhất.')
    else:warnings.append('Thiếu benchmark; không suy ra sức mạnh tương đối.')
    f['date']=f.date.dt.strftime('%Y-%m-%d')
    return clean({'status':'READY','latest':latest,'series':f.tail(320).to_dict('records'),'comparisons':comparisons,'performance':performance,'interpretations':interpretations,'warnings':warnings,
        'method':'RSI/ATR Wilder(14), hạt giống SMA 14 mẫu; MACD EMA(12,26), signal EMA(9), adjust=False và hạt giống giá đầu chuỗi. Hỗ trợ/kháng cự: min low/max high 20 phiên trước. Lợi suất: cùng ngày, 21/63/126/252 phiên chung; không gồm cổ tức tiền mặt.'})
