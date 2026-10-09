"""Ảnh doanh nghiệp có nguồn: dùng script tìm ảnh của người dùng, xác minh trước khi nhúng."""
import base64,json,re
from pathlib import Path
from integration import ROOT

REGISTRY=ROOT/'resources/company_images.json'

def for_company(ticker,inline=False):
    rows=json.loads(REGISTRY.read_text(encoding='utf-8')).get(ticker,[]) if REGISTRY.is_file() else []
    from dynamic_images import selected
    out=selected(ticker,inline)
    for row in rows:
        filename=row.get('filename','')
        if not re.fullmatch(r'[A-Za-z0-9_-]+\.(png|jpg|jpeg|webp|svg)',filename):continue
        path=ROOT/'static/company-images'/filename
        if not path.is_file():continue
        entry={**row,'url':'/static/company-images/'+filename}
        if inline:
            mime={'svg':'image/svg+xml','png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp'}[path.suffix[1:]]
            entry['src']='data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
        out.append(entry)
    return out

async def search_company(ticker,company_name,limit=6):
    # Kết quả tìm chỉ là ứng viên; không tự coi ảnh/logo là đã xác minh.
    from find_images import search_images
    return await search_images(ticker+' '+company_name+' logo company',limit=limit)
