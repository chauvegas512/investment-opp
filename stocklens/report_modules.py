"""Chuẩn hóa tám module PDF từ engine X10 và kết quả Annual Miner."""
import hashlib,json
from research_v2 import values_for,number,divide,growth
from integration import clean

def excerpt(f):
    text=f.get('snippet','');term=f.get('keyword','');pos=text.casefold().find(term.casefold())
    if pos<0:return ' '.join(text.split()[:12])
    return ' '.join((text[:pos].split()[-4:]+text[pos:].split()[:8])[:12])

def build(b,include_mining=True):
    s=b['signal'];r=b['research'];bank=r['quality']['bank'];config=b.get('methodology',{})
    n=lambda v:'Chưa có' if v is None else f'{v:,.1f}'
    p=lambda v:'Chưa có' if v is None else f'{v*100:+.1f}%'
    threshold=config.get('minimum_volume_ratio',.8)
    conditions=[{'name':'Momentum','key':'momentum_pass','weight':30,'rule':'R3m, R6m, R12m đều > 0','value':' / '.join(p(s.get(k)) for k in ['return_3m','return_6m','return_12m'])},
        {'name':'Relative Strength','key':'rs_pass','weight':25,'rule':'R6m cổ phiếu - R6m VN-Index > 0','value':p(s.get('rs_6m'))},
        {'name':'Trend','key':'trend_pass','weight':25,'rule':'Giá > MA50 > MA200','value':' / '.join(n(s.get(k)) for k in ['close','ma50','ma200'])+' VND'},
        {'name':'Breakout 20 phiên','key':'breakout_pass','weight':15,'rule':'Giá > đỉnh đóng cửa 20 phiên trước','value':n(s.get('close'))+' / '+n(s.get('high_close20'))+' VND'},
        {'name':'Volume','key':'volume_pass','weight':5,'rule':f'KL / TB20 phiên trước ≥ {threshold:g}×','value':n(s.get('volume_ratio'))+'×'}]
    for c in conditions:
        weight_key={'momentum_pass':'momentum','rs_pass':'relative_strength','trend_pass':'trend','breakout_pass':'breakout','volume_pass':'volume'}[c['key']]
        c['weight']=config.get('component_weights',{}).get(weight_key,c['weight'])
        c['status']='Chưa đủ' if s.get('ta_status')!='READY' else 'Đạt' if s.get(c['key']) else 'Chưa đạt'
    entry=config.get('entry_score',60);liquidity=config.get('minimum_average_trading_value_20d',2e9)
    gates=[{'name':f'Điểm ≥ {entry:g}','ok':number(s.get('unified_score')) is not None and s['unified_score']>=entry},
        {'name':f'Thanh khoản TB20 ≥ {liquidity/1e9:g} tỷ/phiên','ok':number(s.get('avg_trading_value_20d')) is not None and s['avg_trading_value_20d']>=liquidity},
        {'name':'VN-Index hỗ trợ','ok':s.get('market_bull')}, {'name':'TA đủ đầu vào / giá mới','ok':s.get('ta_status')=='READY' and s.get('price_fresh')},
        {'name':'Chỉ tiêu ngành đủ kiểm chứng' if bank else 'Không bị loại FA','ok':not s.get('hard_reject_reason') and not bank}]
    reasons={'MARKET_DEFENSIVE':'VN-Index chưa trên MA chế độ thị trường; chưa cho phép mở mới theo X10.',
        'SCORE_BELOW_ENTRY':f'Điểm chưa đạt ngưỡng {entry:g}/100.', 'ILLIQUID':'Thanh khoản chưa đạt ngưỡng chiến lược.',
        'STALE_PRICE':'Giá chưa đủ mới.', 'MISSING_TA':'TA chưa đủ đầu vào.', 'FA_HARD_REJECT':'Chạm điều kiện loại trừ FA.', 'OUTSIDE_TOP_N':'Ngoài nhóm được chọn toàn thị trường.'}
    reason='Ngân hàng thiếu bộ chỉ tiêu chuyên ngành đã kiểm chứng; không áp dụng FA chung.' if bank else reasons.get(s.get('watch_reason'),s.get('action_label') or 'Cần kiểm tra dữ liệu.')
    if s.get('final_action')=='DATA_REVIEW' and not bank:reason=s.get('action_label') or 'Chưa đủ dữ liệu; xem cảnh báo và nguồn trước khi kết luận.'
    groups=[{'name':name,'value':None if bank else s.get(key+'_score'),'coverage':None if bank else s.get(key+'_coverage'),'weight':weight,'key':key} for name,key,weight in [('Sinh lời / Quality','quality',.4),('Tăng trưởng / Growth','growth',.25),('Định giá / Value','value',.2),('An toàn / Safety','safety',.15)]]
    years=sorted({str(row['report_period']) for row in b.get('annual',[])})[-5:];trend=[]
    for y in years:
        a=values_for(b['annual'],y);old=values_for(b['annual'],str(int(y)-1))
        avg=lambda key:(a[key]+old[key])/2 if a.get(key) is not None and old.get(key) is not None else None
        trend.append({'year':y,'roe':divide(a.get('net_income'),avg('equity')),'roa':divide(a.get('net_income'),avg('total_assets')),
            'margin':divide(a.get('net_income'),a.get('revenue')) if not bank else None})
    docs=(b.get('annual_insights',[])+b.get('mining',[])) if include_mining else []
    seen=set();documents=[]
    for d in docs:
        if d['sha256'] in seen:continue
        seen.add(d['sha256']);documents.append({**d,'excerpts':[{**f,'snippet':excerpt(f)} for f in d.get('findings',[])[:2]],'metrics_ready':bool(d.get('metrics') is not None)})
    return clean({'conditions':conditions,'gates':gates,'decision':reason,'groups':groups,'health_trend':trend,'documents':documents,
        'strategy_hash':hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()[:12],
        'configuration':{'entry':entry,'exit':config.get('exit_score',35),'fa_weight':config.get('fa_weight',.2),'volume_ratio':threshold}})
