"""Giới thiệu ngắn từ nguồn công ty hoặc metadata, tách khỏi nhận định đầu tư."""
import json
from integration import ROOT
def get(bundle):
    known=json.loads((ROOT/'resources/company_profiles.json').read_text(encoding='utf-8')).get(bundle['ticker'])
    if known:return known
    c=bundle['company'];name=c.get('company_name') or bundle['ticker'];sector=c.get('sector') or c.get('industry')
    if c.get('company_profile'):
        words=c['company_profile'].split()
        return {'summary':' '.join(words[:24])+('…' if len(words)>24 else ''),'source_url':c.get('overview_source') or 'https://trading.vietcap.com.vn/','status':'PROFILE_EXCERPT'}
    summary=name+' được ghi nhận trong nhóm '+sector+'.' if sector else name+' là doanh nghiệp được phân tích trong báo cáo này.'
    if c.get('exchange'):summary+=' Cổ phiếu '+bundle['ticker']+' giao dịch trên '+c['exchange']+'.'
    return {'summary':summary,'source_url':c.get('overview_source') or 'https://trading.vietcap.com.vn/','verified_at':c.get('overview_fetched_at'),'status':'METADATA_SUMMARY'}
