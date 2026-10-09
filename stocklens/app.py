"""Single local application for X10 + Annual Report Miner + HoHa PDF."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import secrets
import threading
import time
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from integration import ROOT, clean, status
from analysis import fetch_bundle, ticker_of
from mining import mine_pdf
from reports import report_html, slide_html, pdf_bytes, financial_table, price_chart

app = FastAPI(title='StockLens', version='1.0.0', docs_url='/api/docs', redoc_url=None)
app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
(ROOT/'data/image-cache').mkdir(parents=True,exist_ok=True)
app.mount('/image-cache',StaticFiles(directory=ROOT/'data/image-cache'),name='image-cache')
pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='stocklens')
image_pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='stocklens-images')
image_running=set()
refreshing=set()
lock = threading.Lock()
jobs = {}
TTL = 6*3600


class AnalysisRequest(BaseModel):
    ticker: str = Field(min_length=2,max_length=10)


def job_of(identifier):
    with lock:
        job = jobs.get(identifier)
    if not job:
        from history import load
        job=load(identifier)
        if job:
            with lock: jobs[identifier]=job
    if not job or time.time()-job['started'] > TTL:
        raise HTTPException(404,'Phiên phân tích không còn trong bộ nhớ. Hãy phân tích lại.')
    return job


@app.get('/')
def index():
    return FileResponse(ROOT/'static/index.html',headers={'Cache-Control':'no-store'})

def queue_images(b):
    from company_images import for_company
    from dynamic_images import load,search
    ticker=b['ticker'];state=load(ticker)
    if for_company(ticker):return
    if state.get('status')=='NO_RESULTS' and time.time()-state.get('searched_at',0)<300:return
    with lock:
        if ticker in image_running:return
        image_running.add(ticker)
    def work():
        try:search(ticker,b['company'].get('company_name') or ticker,False,b['company'].get('website'),b['company'].get('company_short_name'))
        finally:
            with lock:image_running.discard(ticker)
    image_pool.submit(work)


@app.get('/api/health')
def health():
    from dynamic_images import provider
    with lock:
        running_count=sum(j['status']=='running' for j in jobs.values())+len(refreshing)
    return {'name':'StockLens','integrations':status(),'data_mode':'live + read-only SQLite archive; no synthetic stock data',
            'license_tier':os.getenv('STOCKLENS_TIER','NOT_CHECKED'),'image_provider':provider(),
            'running_jobs':running_count}


def run_job(identifier,ticker):
    def progress(message):
        with lock:
            jobs[identifier]['message'] = message
    try:
        bundle = fetch_bundle(ticker,progress)
        from history import save
        save(identifier,bundle)
        with lock:
            jobs[identifier].update(status='done',message='Phân tích hoàn tất.',data=bundle)
        queue_images(bundle)
    except Exception as exc:
        # Do not expose raw provider exceptions that might include credential URLs.
        message = str(exc) if isinstance(exc,ValueError) else 'Nguồn dữ liệu gặp lỗi ('+type(exc).__name__+'). Thử lại hoặc kiểm tra kết nối.'
        with lock:
            jobs[identifier].update(status='error',message=message)


@app.post('/api/analyze',status_code=202)
def analyze(request:AnalysisRequest):
    try:
        ticker = ticker_of(request.ticker)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    with lock:
        expired = [i for i,j in jobs.items() if time.time()-j['started']>TTL and j['status']!='running']
        for i in expired:
            jobs.pop(i)
        if sum(j['status']=='running' for j in jobs.values())>=2:
            raise HTTPException(429,'Đang xử lý 2 mã. Đợi phân tích hoàn tất rồi thử lại.')
        if len(jobs)>=30:
            oldest = next((i for i,j in jobs.items() if j['status']!='running'),None)
            if oldest:
                jobs.pop(oldest)
        identifier = secrets.token_urlsafe(18)
        jobs[identifier]={'status':'running','message':'Đang kết nối nguồn dữ liệu…','started':time.time(),'ticker':ticker}
    pool.submit(run_job,identifier,ticker)
    return {'job_id':identifier}


@app.get('/api/history')
def report_history():
    from history import list_reports
    return list_reports()


@app.get('/api/symbols')
def listed_symbols():
    from database import symbols
    return symbols()


@app.get('/api/jobs/{identifier}')
def job(identifier:str):
    current = job_of(identifier)
    data=clean({k:v for k,v in current.items() if k!='started'})
    with lock:data['refresh_status']='RUNNING' if identifier in refreshing else current.get('refresh_status','IDLE')
    if data.get('data'):
        from research import enrich
        if data['data'].get('schema_version')!=4:data['data']=enrich(data['data'])
        queue_images(data['data'])
        from company_images import for_company
        data['data']['images']=for_company(data['data']['ticker'])
        from dynamic_images import load
        data['data']['image_search']=load(data['data']['ticker'])
        with lock:
            if data['data']['ticker'] in image_running:data['data']['image_search']['status']='SEARCHING'
    return data


def bundle_of(identifier):
    job = job_of(identifier)
    if job['status']!='done':
        raise HTTPException(409,'Phân tích chưa hoàn tất.')
    return job['data']

@app.get('/api/jobs/{identifier}/quote')
async def quote(identifier:str,force:bool=False):
    from live_quote import fetch
    return await run_in_threadpool(fetch,bundle_of(identifier)['ticker'],force)

@app.post('/api/jobs/{identifier}/refresh',status_code=202)
def refresh(identifier:str):
    b=bundle_of(identifier)
    with lock:
        if identifier in refreshing:return {'status':'RUNNING'}
        if len(refreshing)+sum(j['status']=='running' for j in jobs.values())>=2:
            raise HTTPException(429,'Đang cập nhật 2 mã. Vui lòng đợi hoàn tất.')
        refreshing.add(identifier)
        jobs[identifier]['refresh_status']='RUNNING'
    def work():
        try:
            from backfill import update
            from history import save
            refreshed=update(b)
            save(identifier,refreshed)
            with lock:jobs[identifier].update(data=refreshed,refresh_status='DONE')
            queue_images(refreshed)
        except Exception as exc:
            with lock:jobs[identifier].update(refresh_status='ERROR',refresh_error=type(exc).__name__)
        finally:
            with lock:refreshing.discard(identifier)
    pool.submit(work);return {'status':'RUNNING'}

@app.post('/api/jobs/{identifier}/images/search')
async def find_company_images(identifier:str,force:bool=False):
    b=bundle_of(identifier)
    from dynamic_images import search
    from company_images import for_company
    curated=next((i for i in for_company(b['ticker']) if not i.get('id')),None)
    website=b['company'].get('website') or (curated.get('source_url') if curated else None)
    return await run_in_threadpool(search,b['ticker'],b['company'].get('company_name') or b['ticker'],force,website,b['company'].get('company_short_name'))

class ImageChoice(BaseModel):
    image_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    use:bool=True

@app.post('/api/jobs/{identifier}/images/select')
def choose_company_image(identifier:str,request:ImageChoice):
    b=bundle_of(identifier)
    from dynamic_images import choose
    try:return choose(b['ticker'],request.image_id,request.use)
    except ValueError as e:raise HTTPException(422,str(e)) from e


@app.get('/api/jobs/{identifier}/chart',response_class=HTMLResponse)
def chart(identifier:str):
    return price_chart(bundle_of(identifier)['prices'])


@app.get('/api/jobs/{identifier}/financial-table')
def financials(identifier:str):
    return {'rows':financial_table(bundle_of(identifier))}


@app.get('/api/jobs/{identifier}/evidence')
def evidence(identifier:str):
    import json
    return Response(json.dumps(bundle_of(identifier),ensure_ascii=False,indent=2),media_type='application/json',
        headers={'Content-Disposition':'attachment; filename="stocklens-evidence.json"'})


@app.post('/api/jobs/{identifier}/mine')
async def mine(identifier:str,request:Request,keywords:str,filename:str='bao-cao.pdf'):
    bundle = bundle_of(identifier)
    if len(keywords)>1600 or len(filename)>160:
        raise HTTPException(422,'Từ khóa hoặc tên file quá dài.')
    content=bytearray()
    # Raw body keeps PDF bytes in RAM instead of multipart temporary files.
    async for chunk in request.stream():
        if len(content)+len(chunk)>20*1024*1024:
            raise HTTPException(413,'PDF tối đa 20 MB.')
        content.extend(chunk)
    if not content.startswith(b'%PDF-'):
        raise HTTPException(422,'File phải là PDF hợp lệ.')
    if len(bundle['mining'])>=5:
        raise HTTPException(422,'Tối đa 5 PDF trong một phiên phân tích.')
    try:
        result = await run_in_threadpool(mine_pdf,bytes(content),keywords,filename)
    except Exception as exc:
        raise HTTPException(422,str(exc) if isinstance(exc,ValueError) else 'Không đọc được PDF.') from exc
    with lock:
        bundle['mining'].append(result)
    from history import save
    await run_in_threadpool(save,identifier,bundle)
    return result


@app.get('/api/jobs/{identifier}/report',response_class=HTMLResponse)
def report(identifier:str,title:str='Báo cáo phân tích cơ hội đầu tư',news:bool=True,mining:bool=True,
           horizon:Literal['short','medium','long']='medium',risk:Literal['cautious','balanced','active']='balanced',depth:Literal['short','full']='full',images:bool=True):
    if len(title)>100:
        raise HTTPException(422,'Tiêu đề tối đa 100 ký tự.')
    return report_html(bundle_of(identifier),title,news,mining,horizon,risk,depth,images)


@app.get('/api/jobs/{identifier}/slides',response_class=HTMLResponse)
def slides(identifier:str):
    return slide_html(bundle_of(identifier))


@app.get('/api/jobs/{identifier}/pdf')
def pdf(identifier:str,title:str='Báo cáo phân tích cơ hội đầu tư',news:bool=True,mining:bool=True,
        horizon:Literal['short','medium','long']='medium',risk:Literal['cautious','balanced','active']='balanced',depth:Literal['short','full']='full',images:bool=True):
    if len(title)>100:
        raise HTTPException(422,'Tiêu đề tối đa 100 ký tự.')
    bundle = bundle_of(identifier)
    try:
        content = pdf_bytes(report_html(bundle,title,news,mining,horizon,risk,depth,images))
    except Exception as exc:
        raise HTTPException(503,'Chưa xuất được PDF ('+type(exc).__name__+'). Kiểm tra Edge hoặc cài Chromium cho Playwright.') from exc
    return Response(content,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="StockLens-{bundle["ticker"]}.pdf"'})
