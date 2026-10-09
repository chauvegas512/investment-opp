"""Khai phá tự động nguồn BCTN đã nhận diện; metadata không thay nội dung PDF."""
from functools import lru_cache
import json
from integration import ROOT
DEFAULT_TERMS='rủi ro, quản trị, chuyển đổi số, trí tuệ nhân tạo, phát triển bền vững, môi trường, bảo mật'

@lru_cache(maxsize=8)
def fetch(ticker):
    import requests
    from mining import mine_pdf
    item=json.loads((ROOT/'resources/annual_sources.json').read_text(encoding='utf-8')).get(ticker)
    if not item:return []
    with requests.get(item['url'],stream=True,timeout=45) as resp:
        resp.raise_for_status();data=bytearray()
        for chunk in resp.iter_content(256*1024):
            data.extend(chunk)
            if len(data)>30*1024*1024:raise ValueError('BCTN nguồn lớn hơn 30 MB')
    if not data.startswith(b'%PDF-'):raise ValueError('Nguồn không trả PDF')
    result=mine_pdf(bytes(data),DEFAULT_TERMS,f'{ticker}_{item["year"]}_BCTN.pdf')
    # Công bố công khai: chỉ lưu hai trích đoạn ngắn; số đếm vẫn tính toàn văn.
    from report_modules import excerpt
    result['findings']=[{**f,'snippet':excerpt(f)} for f in result['findings'][:2]]
    result['findings_limit']=2
    result.update(source_url=item['url'],report_year=item['year'],published_date=item['published_date'],source='Công bố doanh nghiệp / Annual Miner',automatic=True)
    return [result]
