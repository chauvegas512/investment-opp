"""BCTN mọi ticker: catalog Miner -> local/cache -> công bố/CDN -> khai phá thật."""
import json,time,threading,re
from pathlib import Path
from integration import ROOT,module
DEFAULT_TERMS='rủi ro, quản trị, chuyển đổi số, trí tuệ nhân tạo, phát triển bền vững, môi trường, bảo mật'
CACHE=ROOT/'data/annual-mining';_guard=threading.Lock();_locks={}

def validate_pdf(raw):
    import pymupdf
    if not raw.startswith(b'%PDF-'):raise ValueError('NOT_PDF')
    with pymupdf.open(stream=raw,filetype='pdf') as doc:
        if doc.page_count<8 or doc.page_count>500 or doc.is_encrypted:raise ValueError('NOT_ANNUAL_REPORT')

def verify_identity(raw,ticker,year,record):
    import pymupdf
    from company_identity import headline_matches,norm
    with pymupdf.open(stream=raw,filetype='pdf') as doc:
        text=' '.join(doc[i].get_text() for i in range(min(16,len(doc))))
    if len(text.strip())<300 or text_coverage(raw)<.25:return 'NEEDS_OCR_VERIFICATION'
    matched=headline_matches(text,ticker,record.get('company_name') or ticker,record.get('company_short_name'))
    if not matched:raise ValueError('ISSUER_IDENTITY_MISMATCH')
    content=norm(text)
    if str(year) not in content:raise ValueError('REPORT_YEAR_MISMATCH')
    return 'ISSUER_AND_YEAR_MATCHED'

def download(url):
    import requests
    with requests.get(url,stream=True,timeout=(8,25),headers={'User-Agent':'Mozilla/5.0'}) as resp:
        resp.raise_for_status();raw=bytearray()
        for block in resp.iter_content(256*1024):
            raw.extend(block)
            if len(raw)>35*1024*1024:raise ValueError('PDF_TOO_LARGE')
    data=bytes(raw);validate_pdf(data);return data

def text_coverage(raw):
    import pymupdf
    with pymupdf.open(stream=raw,filetype='pdf') as doc:
        return sum(len(p.get_text().strip())>=30 for p in doc)/len(doc)

def fetch(ticker,force=False):
    from mining import catalog,mine_pdf
    from report_modules import excerpt
    CACHE.mkdir(parents=True,exist_ok=True)
    with _guard:lock=_locks.setdefault(ticker,threading.Lock())
    with lock:
        meta=CACHE/(ticker+'.json')
        cached=json.loads(meta.read_text(encoding='utf-8')) if meta.is_file() else {}
        if meta.is_file() and not force:
            if time.time()-cached.get('at',0)<7*86400 and cached.get('documents') and cached.get('mining_version')==2:return cached['documents']
        records=[r for r in catalog().search(ticker=ticker,limit=40) if r.get('ticker')==ticker]
        known=json.loads((ROOT/'resources/annual_sources.json').read_text(encoding='utf-8')).get(ticker)
        attempts=[];documents=[]
        for record in records[:2]:
            year=int(record['year']);filename=f'{ticker}_{year}_BCTN.pdf';path=CACHE/filename;raw=None;source_url=None
            if path.is_file():
                try:raw=path.read_bytes();validate_pdf(raw);source_url=next((d.get('source_url') for d in cached.get('documents',[]) if d.get('report_year')==year),None)
                except Exception:raw=None
            local=record.get('local_path')
            if raw is None and local and Path(local).is_file():
                try:raw=Path(local).read_bytes();validate_pdf(raw);source_url=record.get('website')
                except Exception:raw=None
            urls=[]
            if known and known['year']==year:urls.append(known['url'])
            base='https://cafef1.mediacdn.vn/Images/Uploaded/DuLieuDownload/BCTC/'
            urls.extend(base+name for name in [record.get('file_name') or filename,f'{ticker}_{year%100:02}CN_BCTN.pdf',f'{ticker}_{year%100:02}N_BCTN.pdf'])
            if raw is None or text_coverage(raw)<.25:
                from annual_discovery import discover
                urls=urls[:1]+discover(ticker,year,record)+urls[1:]
                for url in dict.fromkeys(urls):
                    try:
                        candidate=download(url);verify_identity(candidate,ticker,year,record)
                        if raw is not None and text_coverage(candidate)<=text_coverage(raw):continue
                        raw=candidate;source_url=url;path.write_bytes(raw)
                        if text_coverage(raw)>=.25:break
                    except Exception as e:attempts.append({'year':year,'source':url,'status':type(e).__name__})
            if raw is None:continue
            try:identity=verify_identity(raw,ticker,year,record)
            except ValueError as e:
                attempts.append({'year':year,'source':source_url,'status':str(e)});continue
            terms=DEFAULT_TERMS
            if record.get('icb_l1')=='Ngân hàng':terms+=', tín dụng, nợ xấu, an toàn vốn, NIM, CAR'
            result=mine_pdf(raw,terms,filename)
            result['findings']=[{**f,'snippet':excerpt(f)} for f in result['findings'][:2]];result['findings_limit']=2
            result.update(source_url=source_url or record.get('website'),report_year=year,published_date=known.get('published_date') if known and known['year']==year else None,
                source='Annual Miner catalog / BCTN công bố',automatic=True,identity_status=identity)
            documents.append(result);break
        # Nếu chưa có trong catalog nhưng có nguồn công bố được cấu hình.
        if not records and known:
            raw=download(known['url']);result=mine_pdf(raw,DEFAULT_TERMS,f'{ticker}_{known["year"]}_BCTN.pdf')
            result['findings']=[{**f,'snippet':excerpt(f)} for f in result['findings'][:2]]
            result.update(source_url=known['url'],report_year=known['year'],published_date=known.get('published_date'),automatic=True,findings_limit=2);documents=[result]
        meta.write_text(json.dumps({'at':time.time(),'ticker':ticker,'documents':documents,'attempts':attempts,'mining_version':2,'status':'MINED' if documents else 'SOURCE_UNAVAILABLE'},ensure_ascii=False,indent=2),encoding='utf-8')
        return documents

def status(ticker):
    path=CACHE/(ticker+'.json')
    return json.loads(path.read_text(encoding='utf-8')).get('status','NOT_FETCHED') if path.is_file() else 'NOT_FETCHED'
