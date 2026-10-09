"""Dùng master catalog Miner cho tên, website và phân ngành mọi ticker."""
import re,unicodedata
def norm(text):
    text=unicodedata.normalize('NFKD',str(text).replace('đ','d').replace('Đ','D')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+',' ',text).strip()
def headline_matches(title,ticker,name,short_name=None):
    t=norm(title)
    if re.search(r'\b'+re.escape(ticker.lower())+r'\b',t):return True
    if name and len(norm(name))>=8 and norm(name) in t:return True
    brand=norm(short_name or '')
    if len(brand)>=4 and (brand in t or brand.replace(' ','') in t.replace(' ','')):return True
    parts=[p for p in brand.split() if len(p)>=5 and p not in {'company','corporation','group','retail','bank','securities'}]
    return any(re.search(r'\b'+re.escape(p)+r'\b',t) for p in parts)
def attach(company,ticker):
    from mining import catalog
    rows=catalog().search(ticker=ticker,limit=2)
    row=next((r for r in rows if r.get('ticker')==ticker),{})
    for key in ['website','ir_portal','company_short_name','icb_l1','icb_l2','icb_l3','icb_l4','icb_code']:
        if not company.get(key) and row.get(key):company[key]=row[key]
    if str(company.get('icb_code','')).startswith('835') or 'ngân hàng' in str(company.get('company_name','')).lower():company['is_bank']=True
    return company
