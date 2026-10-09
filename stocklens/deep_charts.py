"""Biểu đồ nghiên cứu: nến, RSI/MACD, so sánh chung ngày và khối lượng."""
import base64,io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np,pandas as pd

NAVY='#1B1233';TEAL='#6C3BFF';RED='#FF4F9A';GREY='#887BA5';GOLD='#BE9400'

def uri(fig):
    out=io.BytesIO();fig.savefig(out,format='png',dpi=190,bbox_inches='tight',facecolor='white');plt.close(fig)
    return 'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()

def style(ax):
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15);ax.tick_params(labelsize=7)

def technical(data):
    f=pd.DataFrame(data.get('series',[])).tail(120).reset_index(drop=True)
    if f.empty:return None
    fig,axes=plt.subplots(3,1,figsize=(7.4,6.2),sharex=True,gridspec_kw={'height_ratios':[3.1,1,1.15]},layout='constrained')
    a,r,m=axes;x=np.arange(len(f))
    for i,row in f.iterrows():
        color=TEAL if row.close>=row.open else RED
        a.vlines(i,row.low/1000,row.high/1000,color=color,lw=.7)
        body=max(abs(row.close-row.open)/1000,.02)
        a.add_patch(Rectangle((i-.32,min(row.open,row.close)/1000),.64,body,facecolor=color,edgecolor=color,lw=.4))
    for key,color in [('ma20',TEAL),('ma50',NAVY),('ma200',GOLD)]:a.plot(x,pd.to_numeric(f[key],errors='coerce')/1000,label=key.upper(),color=color,lw=1)
    for key,label,color in [('support20','Hỗ trợ 20',GREY),('resistance20','Kháng cự 20',RED)]:
        val=f[key].iloc[-1]
        if pd.notna(val):a.axhline(val/1000,label=label,color=color,ls='--',lw=.7)
    a.set_ylabel('Nghìn VND',fontsize=8);a.legend(fontsize=6.5,ncol=3,loc='upper left',frameon=False)
    r.plot(x,pd.to_numeric(f.rsi14,errors='coerce'),color=TEAL,lw=1);r.axhline(30,color=GREY,lw=.6,ls='--');r.axhline(70,color=GREY,lw=.6,ls='--');r.set_ylim(0,100);r.set_ylabel('RSI(14)',fontsize=8)
    macd=pd.to_numeric(f.macd,errors='coerce');signal=pd.to_numeric(f.macd_signal,errors='coerce');hist=pd.to_numeric(f.macd_hist,errors='coerce')
    m.bar(x,hist/1000,color=[TEAL if pd.notna(v) and v>=0 else RED for v in hist],width=.7,alpha=.55);m.plot(x,macd/1000,label='MACD',color=NAVY,lw=1);m.plot(x,signal/1000,label='Signal',color=GOLD,lw=1);m.axhline(0,color=GREY,lw=.6);m.set_ylabel('MACD / nghìn VND',fontsize=7);m.legend(fontsize=6,ncol=2,loc='upper left',frameon=False)
    ticks=np.linspace(0,len(f)-1,min(5,len(f))).astype(int);m.set_xticks(ticks);m.set_xticklabels(f.date.iloc[ticks].astype(str).str[:10],fontsize=7)
    for ax in axes:style(ax)
    return uri(fig)

def performance(data):
    f=pd.DataFrame(data.get('performance',[]))
    if f.empty:return None
    fig,ax=plt.subplots(figsize=(7.4,2.6),layout='constrained')
    dates=pd.to_datetime(f.date);ax.plot(dates,f.stock_index,label='Cổ phiếu',color=TEAL,lw=1.4);ax.plot(dates,f.benchmark_index,label='VN-Index',color=NAVY,lw=1.2);ax.axhline(100,color=GREY,ls='--',lw=.7);ax.set_ylabel('Gốc = 100',fontsize=8);ax.legend(fontsize=8,frameon=False,ncol=2);style(ax)
    return uri(fig)

def volume(data):
    f=pd.DataFrame(data.get('series',[])).tail(120)
    if f.empty:return None
    fig,ax=plt.subplots(figsize=(7.4,1.7),layout='constrained')
    dates=pd.to_datetime(f.date);ax.bar(dates,f.volume/1e6,color=[TEAL if c>=o else RED for c,o in zip(f.close,f.open)],width=1,alpha=.55);ax.plot(dates,pd.to_numeric(f.volume_mean20,errors='coerce')/1e6,color=NAVY,lw=1,label='TB20 phiên trước');ax.set_ylabel('Triệu cổ phiếu',fontsize=8);ax.legend(fontsize=7,frameon=False);style(ax)
    return uri(fig)

def strategy_price(data):
    f=pd.DataFrame(data.get('series',[])).tail(120).reset_index(drop=True)
    if f.empty:return None
    fig,(ax,vol)=plt.subplots(2,1,figsize=(7.3,3.65),sharex=True,gridspec_kw={'height_ratios':[3,1]},layout='constrained');x=np.arange(len(f))
    ax.plot(x,f.close/1000,color=TEAL,label='Giá',lw=1.5)
    for key,color in [('ma20',RED),('ma50','#0098AE'),('ma200',GOLD)]:ax.plot(x,pd.to_numeric(f[key],errors='coerce')/1000,label=key.upper(),lw=1,color=color)
    ax.set_ylabel('Nghìn VND',fontsize=8);ax.legend(fontsize=7,ncol=4,frameon=False)
    vol.bar(x,f.volume/1e6,color=GREY,alpha=.55);vol.plot(x,pd.to_numeric(f.volume_mean20,errors='coerce')/1e6,color=TEAL,lw=.8)
    vol.set_ylabel('Triệu CP',fontsize=7);ticks=np.linspace(0,len(f)-1,min(5,len(f))).astype(int);vol.set_xticks(ticks);vol.set_xticklabels(f.date.iloc[ticks].astype(str).str[:10],fontsize=7)
    for a in (ax,vol):style(a)
    return uri(fig)

def health(rows):
    f=pd.DataFrame(rows)
    if f.empty:return None
    fig,ax=plt.subplots(figsize=(7.3,2.4),layout='constrained')
    for key,label,color in [('roe','ROE',TEAL),('roa','ROA',RED),('margin','Biên LNST','#0098AE')]:
        if pd.to_numeric(f[key],errors='coerce').notna().any():ax.plot(f.year,pd.to_numeric(f[key],errors='coerce')*100,marker='o',ms=3,label=label,color=color)
    ax.set_ylabel('%',fontsize=8);ax.legend(fontsize=7,ncol=3,frameon=False);style(ax);return uri(fig)

def relative(data,ticker):
    if data.get('premium_pct') is None:return None
    fig,ax=plt.subplots(figsize=(7.3,2.1),layout='constrained')
    vals=[data['stock_pe_ttm'],data['median_pe_ttm']];bars=ax.barh([ticker+' / lưu trữ','Trung vị nhóm'],vals,color=[TEAL,RED],height=.48)
    for bar,value in zip(bars,vals):ax.text(value+.1,bar.get_y()+bar.get_height()/2,f'{value:.2f}×',va='center',fontsize=9)
    ax.set_xlim(0,max(vals)*1.25);ax.set_xlabel('P/E TTM / lần',fontsize=8);style(ax);return uri(fig)
