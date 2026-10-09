"""Tìm ảnh động cho ticker, cache ảnh công khai; khóa chỉ đọc từ env của tiến trình."""
import asyncio,hashlib,io,json,threading,time,re,unicodedata
from pathlib import Path
from urllib.parse import urlparse
import aiohttp
from PIL import Image
from integration import ROOT,clean

CACHE=ROOT/'data/image-cache';TTL=6*3600
_guard=threading.Lock();_locks={}

def auto_select(data):
    if data.get('selection_disabled') or any(r.get('selected') for r in data.get('images',[])):return False
    photos=[r for r in data.get('images',[]) if r.get('width',0)>=600 and r.get('height',0)>=300 and 1.2<=r['width']/r['height']<=3 and 'logo' not in (r.get('title','')+' '+r.get('original_url','')).lower()]
    if not photos:return False
    photos[0].update(selected=True,selection_method='AUTO_RELEVANCE');return True

def relevant(row,ticker,name,website=None,brand=None):
    def norm(text):
        text=unicodedata.normalize('NFKD',str(text).replace('đ','d').replace('Đ','D')).encode('ascii','ignore').decode().lower()
        return re.sub(r'[^a-z0-9]+',' ',text).strip()
    text=norm(row.get('title','')+' '+row.get('source_url',''));company=norm(name)
    if website:
        host=urlparse(website if '://' in website else 'https://'+website).hostname or ''
        source=urlparse(row.get('source_url','')).hostname or ''
        host=host.lower().removeprefix('www.')
        if host and (source==host or source.endswith('.'+host)):return True
    if brand and len(norm(brand))>=4 and norm(brand) in text:return True
    company=re.sub(r'^(ctcp|cong ty co phan|cong ty|ngan hang tmcp)\s+','',company)
    if len(company.replace(' ',''))>=10 and company.replace(' ','') in text.replace(' ',''):return True
    stop={'ctcp','cong','ty','co','phan','ngan','hang','tmcp','viet','nam','jsc','company','corporation','tap','doan'}
    words={w for w in company.split() if len(w)>=3 and w not in stop and w!=ticker.lower()}
    ticker_match=bool(re.search(r'\b'+re.escape(ticker.lower())+r'\b',text))
    matches=sum(bool(re.search(r'\b'+re.escape(w)+r'\b',text)) for w in words)
    aliases={'FRT':['fpt retail','fptshop','frt vn','long chau'],'MBB':['mbbank','mb bank','quan doi'],'PAN':['thepangroup','pan group','tap doan pan']}
    if ticker_match and not words and any(w in text for w in ['logo','company','corporation','tap doan','cong ty','software']):return True
    return (ticker_match and matches>=1) or matches>=2 or any(a in text for a in aliases.get(ticker,[]))

def provider():
    import os
    return 'Serper' if os.getenv('SERPER_API_KEY') else 'Google' if os.getenv('GOOGLE_API_KEY') and os.getenv('GOOGLE_CSE_ID') else 'Brave' if os.getenv('BRAVE_API_KEY') else 'Bing'

def load(ticker):
    if not re.fullmatch(r'[A-Z][A-Z0-9]{1,9}',ticker):return {'status':'NOT_SEARCHED','images':[]}
    path=CACHE/(ticker+'.json')
    if not path.is_file():return {'status':'NOT_SEARCHED','images':[]}
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,OSError):return {'status':'NOT_SEARCHED','images':[]}

def selected(ticker,inline=False):
    out=[]
    for row in load(ticker).get('images',[]):
        if not row.get('selected'):continue
        if not re.fullmatch(r'[a-f0-9]{32}\.(png|jpg|webp|gif)',row.get('filename','')):continue
        path=CACHE/row['filename']
        if not path.is_file():continue
        entry={**row,'role':'company','search_title':row.get('title'),'title':'Ảnh minh họa doanh nghiệp / '+ticker}
        if inline:
            import base64
            entry['src']='data:'+row['mime']+';base64,'+base64.b64encode(path.read_bytes()).decode()
        out.append(entry)
    return out

async def _fetch(ticker,name,website=None,brand=None):
    from find_images import search_images,PublicResolver
    # Dùng tên pháp lý để hạn chế nhầm ticker với từ thông thường.
    identity=brand or name
    queries=[f'"{identity}" {ticker} trụ sở cửa hàng nhà máy',f'"{identity}" {ticker} doanh nghiệp']
    responses=await asyncio.gather(*(search_images(q,limit=4) for q in queries))
    found=[];seen=set()
    for rows in responses:
        for row in rows:
            if not relevant(row,ticker,name,website,brand):continue
            if row['url'] in seen:continue
            seen.add(row['url']);found.append(row)
    sem=asyncio.Semaphore(3)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(resolver=PublicResolver(),use_dns_cache=False),timeout=aiohttp.ClientTimeout(total=15),trust_env=False) as session:
        async def download(row):
            async with sem:
                try:
                    if urlparse(row['url']).scheme not in ('https','http'):return None
                    async with session.get(row['url'],allow_redirects=True,max_redirects=3) as resp:
                        resp.raise_for_status();raw=bytearray()
                        async for chunk in resp.content.iter_chunked(65536):
                            raw.extend(chunk)
                            if len(raw)>5*1024*1024:return None
                    with Image.open(io.BytesIO(raw)) as image:
                        width,height=image.size;fmt=image.format
                        if width<100 or height<60 or width*height>24_000_000 or fmt not in ('PNG','JPEG','WEBP','GIF'):return None
                        image.verify()
                    ext={'PNG':'png','JPEG':'jpg','WEBP':'webp','GIF':'gif'}[fmt];mime={'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp','GIF':'image/gif'}[fmt]
                    identifier=hashlib.sha256((ticker+row['url']).encode()).hexdigest()[:32];filename=identifier+'.'+ext
                    (CACHE/filename).write_bytes(raw)
                    source=row.get('source_url') or row['url']
                    if urlparse(source).scheme not in ('http','https'):source=row['url']
                    return {'id':identifier,'filename':filename,'mime':mime,'title':' '.join((row.get('title') or ticker+' / ảnh tìm được').split()[:25]),
                        'original_url':row['url'],'source_url':source,'url':'/image-cache/'+filename,
                        'width':width,'height':height,'verification_status':'CANDIDATE','verification':'Ảnh tìm được; chưa đối chiếu nội dung với công bố doanh nghiệp.',
                        'selected':False,'role':'candidate','sha256':hashlib.sha256(raw).hexdigest()}
                except Exception:return None
        return [r for r in await asyncio.gather(*(download(row) for row in found[:8])) if r]

def search(ticker,name,force=False,website=None,brand=None):
    CACHE.mkdir(parents=True,exist_ok=True)
    with _guard:lock=_locks.setdefault(ticker,threading.Lock())
    with lock:
        previous=load(ticker)
        if not force and previous.get('relevance_version')==2 and time.time()-previous.get('searched_at',0)<TTL:
            if auto_select(previous):(CACHE/(ticker+'.json')).write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf-8')
            return previous
        rows=asyncio.run(_fetch(ticker,name,website,brand));chosen={r['original_url'] for r in previous.get('images',[]) if r.get('selected')}
        for row in rows:row['selected']=row['original_url'] in chosen
        for row in previous.get('images',[]):
            if row.get('selected') and relevant(row,ticker,name,website,brand) and row['original_url'] not in {r['original_url'] for r in rows}:rows.append(row)
        result=clean({'status':'READY' if rows else 'NO_RESULTS','ticker':ticker,'company_name':name,'relevance_version':2,'selection_disabled':previous.get('selection_disabled',False),'provider':provider(),'searched_at':time.time(),'images':rows})
        auto_select(result)
        (CACHE/(ticker+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return result

def choose(ticker,identifier,use=True):
    with _guard:lock=_locks.setdefault(ticker,threading.Lock())
    with lock:
        data=load(ticker);row=next((r for r in data.get('images',[]) if r['id']==identifier),None)
        if row is None:raise ValueError('Ảnh không thuộc kết quả tìm kiếm của mã này.')
        if use:
            for item in data['images']:item['selected']=False
        row['selected']=use
        row['selection_method']='USER_CHOICE';data['selection_disabled']=not use
        (CACHE/(ticker+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        return data
