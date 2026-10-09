"""Bounded public report discovery; search results are candidates until PDF checks pass."""
import os,re
from urllib.parse import urlparse
import requests

def discover(ticker,year,record):
    key=os.getenv('SERPER_API_KEY')
    if not key:return []
    brand=record.get('company_short_name') or ticker
    try:
        r=requests.post('https://google.serper.dev/search',headers={'X-API-KEY':key},
            json={'q':f'"{brand}" {ticker} "{year}" báo cáo thường niên filetype:pdf','gl':'vn','hl':'vi','num':5},timeout=10)
        r.raise_for_status();items=r.json().get('organic',[])
    except (requests.RequestException,ValueError):return []
    issuer=urlparse(record.get('website') or '').hostname
    allowed=['cafef.vn','mediacdn.vn','24hmoney.vn','vietstock.vn','fpts.com.vn','hnx.vn','hose.vn']
    if issuer:allowed.append(issuer.removeprefix('www.'))
    urls=[]
    for item in items:
        url=item.get('link','');host=urlparse(url).hostname or ''
        try:
            if urlparse(url).scheme!='https' or urlparse(url).port not in (None,443):continue
        except ValueError:continue
        if not any(host==d or host.endswith('.'+d) for d in allowed):continue
        if not re.search(r'\.pdf(?:$|\?)',url,re.I):continue
        urls.append(url)
    return list(dict.fromkeys(urls))[:3]
