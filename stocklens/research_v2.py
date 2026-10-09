"""Phân tích có bằng chứng và trạng thái dữ liệu, không tạo đầu vào thay thế."""
import math,re
from integration import clean

def number(value):
    try:
        value=float(value)
        return value if math.isfinite(value) else None
    except (TypeError,ValueError):return None

def divide(a,b):return a/b if a is not None and b is not None and b>0 else None
def growth(a,b):
    value=divide(a,b)
    return value-1 if value is not None else None

def period_previous(period,years=0,quarters=0):
    m=re.fullmatch(r'(\d{4})-Q([1-4])',period)
    if not m:return str(int(period)-years) if period.isdigit() else ''
    year,q=map(int,m.groups());n=year*4+q-1-years*4-quarters
    return f'{n//4}-Q{n%4+1}'

def values_for(rows,period):
    from analysis import VCI_ALIASES
    values={}
    for row in rows:
        if str(row['report_period'])!=str(period):continue
        key=VCI_ALIASES.get(row.get('statement'),{}).get(row.get('raw_item_code'),row['item_code'])
        if row.get('statement')=='income_statement' and row.get('raw_item_code') in ('net_interest_income','total_operating_income'):key=row['raw_item_code']
        values[key]=number(row['value'])
    if values.get('equity') is not None and values.get('non_controlling_equity') is not None:
        values['equity_parent']=values['equity']-values['non_controlling_equity']
    return values

def enrich(bundle):
    bundle['schema_version']=4
    from disclosures import attach
    from indicators import technical_research
    attach(bundle)
    from x10_context import enrich_context
    enrich_context(bundle)
    facts=bundle.get('issuer_disclosures',{});basis=facts.get('basis_change',{}).get('effective_date','9999-01-01')
    company=bundle['company'];bank=bool(company.get('is_bank')) or 'ngân hàng' in str(company.get('industry','')).lower() or 'ngân hàng' in str(company.get('sector','')).lower() or 'ngân hàng' in str(company.get('company_name','')).lower()
    news=[]
    for original in bundle.get('news',[]):
        item=dict(original);title=item.get('title','');name=str(company.get('company_name') or bundle['ticker'])
        from company_identity import headline_matches
        from urllib.parse import urlparse
        issuer=(urlparse(company.get('website') or '').hostname or '').removeprefix('www.')
        host=(urlparse(item.get('url') or '').hostname or '').removeprefix('www.')
        official=bool(issuer and item.get('company_confirmed') and (host==issuer or host.endswith('.'+issuer)))
        if not official and not headline_matches(title,bundle['ticker'],name,company.get('company_short_name')):continue
        words=title.split();item['title']=' '.join(words[:25])+('…' if len(words)>25 else '');item.pop('summary',None)
        item.setdefault('event_date',None);item.setdefault('verification','Báo chí đã kiểm tra ngày/danh tính; diễn biến chưa xác minh độc lập.')
        item.setdefault('impact','Chưa rõ');item.setdefault('channel','Giá và kỳ vọng thị trường' if re.search(r'giảm|tăng|giá|phiên|vốn hóa',title,re.I) else 'Sự kiện doanh nghiệp')
        item.setdefault('follow_up','Đối chiếu công bố doanh nghiệp và giá/khối lượng; không suy ra biến động lợi nhuận từ tiêu đề.')
        news.append(item)
    bundle['news']=news
    annual=bundle.get('annual',[]);quarterly=bundle.get('quarterly',[])
    years=sorted({str(r['report_period']) for r in annual});year=years[-1] if years else ''
    a=values_for(annual,year);prior=values_for(annual,str(int(year)-1)) if year else {}
    debt=a['short_term_borrowings']+a['long_term_borrowings'] if a.get('short_term_borrowings') is not None and a.get('long_term_borrowings') is not None else None
    metrics={'year':year,'revenue_growth':growth(a.get('revenue'),prior.get('revenue')),'profit_growth':growth(a.get('net_income'),prior.get('net_income')),
        'eps_growth':growth(a.get('eps'),prior.get('eps')),'cash_conversion':None if bank else divide(a.get('operating_cash_flow'),a.get('net_income')),
        'bank_nii_growth':growth(a.get('net_interest_income'),prior.get('net_interest_income')),
        'current_ratio':None if bank else divide(a.get('current_assets'),a.get('current_liabilities')),
        'profit_margin':divide(a.get('net_income'),a.get('revenue')),'gross_margin':divide(a.get('gross_profit'),a.get('revenue')),
        'borrowings':debt,'debt_equity':None if bank else divide(debt,a.get('equity')),
        'net_debt':debt-a['cash_and_cash_equivalents'] if debt is not None and a.get('cash_and_cash_equivalents') is not None else None,
        'operating_cash_flow':a.get('operating_cash_flow'),'eps_reported':a.get('eps')}
    periods=sorted({str(r['report_period']) for r in quarterly});qperiod=periods[-1] if periods else ''
    q=values_for(quarterly,qperiod);qprev=values_for(quarterly,period_previous(qperiod,quarters=1));qyear=values_for(quarterly,period_previous(qperiod,years=1))
    basis_cross=bool(qperiod and qperiod[:4]+'-01-01'>=basis and period_previous(qperiod,years=1)[:4]+'-01-01'<basis)
    comparisons=[]
    items=[('net_interest_income','Thu nhập lãi thuần'),('net_income','LNST hợp nhất'),('net_income_parent','LNST cổ đông mẹ'),('total_operating_income','Tổng thu nhập hoạt động')] if bank else [('revenue','Doanh thu thuần'),('net_income','LNST hợp nhất'),('net_income_parent','LNST cổ đông mẹ'),('gross_profit','Lợi nhuận gộp')]
    for key,label in items:
        suppress=basis_cross and key!='net_income_parent'
        comparisons.append({'item_code':key,'label':label,'period':qperiod,'value':q.get(key),
            'yoy':None if suppress else growth(q.get(key),qyear.get(key)),
            'qoq':None if qperiod.endswith('Q1') and qperiod[:4]+'-01-01'==basis else growth(q.get(key),qprev.get(key)),
            'yoy_period':period_previous(qperiod,years=1),'qoq_period':period_previous(qperiod,quarters=1),
            'status':'Khác cơ sở hợp nhất' if suppress else ('Thiếu kỳ so sánh' if qyear.get(key) is None else 'Cùng kỳ nguồn')})
    half=facts.get('half_year',{});checks=[]
    if half:
        for key in ['revenue','net_income','net_income_parent','operating_cash_flow']:
            v1=values_for(quarterly,'2026-Q1').get(key);v2=values_for(quarterly,'2026-Q2').get(key)
            actual=v1+v2 if v1 is not None and v2 is not None else None
            checks.append({'item_code':key,'provider_sum':actual,'issuer_value':half[key],
                'matched':actual is not None and abs(actual-half[key])<=max(1e6,abs(half[key])*1e-7),
                'source_page':half['cash_flow_page'] if key=='operating_cash_flow' else half['income_page']})
    price=number(bundle['prices'][-1]['close']) if bundle.get('prices') else None
    shares=number(company.get('shares_outstanding'));share_status='ISSUER_VERIFIED' if facts.get('shares') else company.get('shares_status','UNVERIFIED')
    cap=price*shares if price and shares else None
    four=[period_previous(qperiod,quarters=i) for i in range(4)] if qperiod else []
    profits=[values_for(quarterly,p).get('net_income_parent') for p in four]
    parent_ttm=sum(profits) if len(profits)==4 and all(p is not None for p in profits) else None
    equity=q.get('equity_parent')
    if half and qperiod=='2026-Q2':equity=half['equity']-half['non_controlling_equity']
    ready=share_status in ['ISSUER_VERIFIED','PROVIDER_CONSISTENT'] and not bundle.get('database_audit',{}).get('archive_finance')
    pe=divide(cap,parent_ttm) if ready else None;pb=divide(cap,equity) if ready else None
    valuation={'period':year,'eps':a.get('eps'),'eps_annual_reported':a.get('eps'),
        'eps_ttm_proxy':divide(parent_ttm,shares) if ready else None,'pe_reference':pe,'pb_reference':pb,
        'market_cap':cap,'share_count':shares,'share_status':share_status,'shares_as_of':company.get('shares_as_of') or company.get('overview_fetched_at'),
        'ttm_periods':four,'parent_profit_ttm':parent_ttm,'book_period':qperiod,'equity_parent':equity,
        'scenarios':[],'status':'RATIOS_ONLY' if pe or pb else 'MISSING_INPUTS',
        'note':'P/E tham khảo = vốn hóa theo giá chốt / LNST cổ đông mẹ 4 quý liên tiếp; P/B = vốn hóa / vốn thuộc cổ đông mẹ kỳ gần nhất. EPS TTM quy đổi chưa trừ điều chỉnh quỹ thưởng/phúc lợi như EPS kế toán công bố.',
        'peer_note':'Chưa có tập doanh nghiệp so sánh cùng ngày và cùng định nghĩa. Không kết luận rẻ/đắt so ngành, không xuất giá mục tiêu từ P/E giả định.'}
    technical=technical_research(bundle.get('prices',[]),bundle.get('benchmark',[]));t=technical.get('latest',{})
    missing=[]
    for label,value in [('RSI(14)',t.get('rsi14')),('MACD(12,26,9)',t.get('macd_hist')),('Cổ phiếu hiện hành',shares),('LNST mẹ 4 quý',parent_ttm),('Vốn thuộc cổ đông mẹ',equity)]:
        if value is None:missing.append(label)
    if not half:missing.append('BCTC kỳ mới chưa được đối chiếu công bố gốc cho mã này')
    if share_status=='PROVIDER_CONSISTENT':missing.append('Ngày hiệu lực số cổ phiếu chưa được xác nhận bằng công bố gốc; overview chỉ ghi thời điểm lấy')
    if any(not row.get('published_date') for row in annual):missing.append('Ngày công bố một số dòng BCTC chưa có từ nguồn VCI')
    if half and any(not c['matched'] for c in checks):missing.append('Số liệu quý chưa khớp BCTC bán niên soát xét')
    signal=bundle['signal']
    if bank:
        signal.setdefault('original_generic_decision_reason',signal.get('decision_reason'))
        signal.setdefault('original_generic_fa_coverage',signal.get('fa_coverage'))
        signal.update(final_action='DATA_REVIEW',action_label='Ngân hàng: cần đánh giá chuyên ngành')
        for key in ('fa_score','fa_coverage','unified_score','debt_equity','current_ratio','net_debt_ebitda'):signal[key]=None
        signal['decision_reason']='DATA_REVIEW; ngân hàng; FA và unified_score không áp dụng; TA='+str(signal.get('ta_score'))+'; cần NIM, NPL, bao phủ nợ xấu, CAR đã kiểm chứng.'
        missing.extend(['NIM, NPL, bao phủ nợ xấu và CAR chưa xác minh'])
    fa=number(signal.get('fa_score'));coverage=number(signal.get('fa_coverage'))
    effective=50+(fa-50)*(coverage or 0) if fa is not None else None
    if signal.get('hard_reject_reason'):effective=0
    sensitivity=[{'fa_weight':w,'ta_weight':1-w,'score':effective*w+number(signal['ta_score'])*(1-w) if effective is not None and number(signal.get('ta_score')) is not None else None} for w in [.2,.5,.8]]
    bundle['research']={'metrics':metrics,'valuation':valuation,'technical':technical,'quarterly_comparison':comparisons,
        'quality':{'missing':missing,'bank':bank,'quarter_cash_flow_basis':'Độc lập quý đã đối chiếu tổng 6 tháng' if half and all(c['matched'] for c in checks) else 'Chưa xác minh độc lập/lũy kế; không cộng dòng tiền TTM',
            'checks':checks,'latest_annual':year,'latest_quarter':qperiod,'price_date':str(bundle['prices'][-1]['date'])[:10] if bundle.get('prices') else None,
            'technical_sessions':len(bundle.get('prices',[])),'fa_coverage':coverage,'verified_primary':bool(half),'source_updated_at':bundle['created_at']},
        'latest_quarter_values':q,'weight_sensitivity':sensitivity,
        'conclusion':'Kết luận bám dữ liệu và điều kiện xác nhận; điểm sàng lọc không phải xác suất lợi nhuận.',
        'horizon_note':'Điểm X10 20% FA / 80% TA thiên về ngắn hạn; 50/50 và 80/20 chỉ kiểm tra độ nhạy, không tự đổi khuyến nghị.'}
    from thesis import build
    bundle['research']['thesis']=build(bundle)
    from data_status import build as status_build
    bundle['data_status']=status_build(bundle)
    return clean(bundle)
