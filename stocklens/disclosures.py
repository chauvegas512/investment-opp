"""Dữ kiện đã kiểm chứng từ công bố gốc; luôn giữ ngày và kiểm tra với nguồn tính toán."""
import json
from datetime import date
from integration import ROOT,clean

def issuer_facts(ticker,price_date):
    data=json.loads((ROOT/'resources/verified_disclosures.json').read_text(encoding='utf-8')).get(ticker)
    if not data:return {}
    cutoff=date.fromisoformat(str(price_date)[:10])
    output={**data}
    for key in ('shares','half_year','comparable_growth','basis_change'):
        if data.get(key) and date.fromisoformat(data[key]['published_date'])>cutoff:output.pop(key,None)
    return clean(output)

def attach(bundle):
    if not bundle.get('prices'):return bundle
    from datetime import timedelta
    cutoff=date.fromisoformat(str(bundle['prices'][-1]['date'])[:10])
    events=json.loads((ROOT/'resources/verified_events.json').read_text(encoding='utf-8')).get(bundle['ticker'],[])
    valid=[n for n in events if cutoff-timedelta(days=90)<=date.fromisoformat(n['published_date'])<=cutoff]
    bundle['news']=valid+[n for n in bundle.get('news',[]) if n.get('url') not in {v['url'] for v in valid}]
    facts=issuer_facts(bundle['ticker'],bundle['prices'][-1]['date'])
    bundle['issuer_disclosures']=facts
    if not facts:return bundle
    shares=facts.get('shares')
    if shares:
        vendor=bundle['company'].get('shares_outstanding')
        bundle['company']['shares_outstanding']=shares['value']
        bundle['company']['shares_as_of']=shares['as_of']
        bundle['company']['shares_source']=shares['url']
        bundle['company']['market_cap']=shares['value']*bundle['prices'][-1]['close']
        bundle['company']['market_cap_basis']='Giá chốt báo cáo × số cổ phiếu trong công bố ngày '+shares['as_of']
    for key,label in [('shares','Số cổ phiếu - công bố FPT'),('half_year','BCTC bán niên FPT đã soát xét'),('basis_change','Thay đổi phương pháp hợp nhất FPT'),('comparable_growth','Tăng trưởng trên cơ sở so sánh FPT công bố')]:
        item=facts.get(key)
        if item and not any(s['url']==item['url'] for s in bundle['sources']):
            bundle['sources'].append({'name':label,'url':item['url'],'as_of':item.get('as_of') or item.get('period') or item.get('effective_date'),'published_date':item['published_date'],'verified_at':facts['verified_at']})
    if facts.get('basis_change'):
        note='FPT đổi phương pháp hợp nhất từ 2026: chặn YoY doanh thu/LNST hợp nhất giữa hai cơ sở chưa điều chỉnh.'
        if note not in bundle['warnings']:bundle['warnings'].append(note)
    return bundle
