#!/usr/bin/env bash
set -euo pipefail
cd /opt/stocklens/current/stocklens
runuser -u stocklens -- env PLAYWRIGHT_BROWSERS_PATH=/opt/stocklens/browsers /var/lib/stocklens/.venv/bin/python -u - <<'PY'
import requests,time,json
from pathlib import Path
import pymupdf
from playwright.sync_api import sync_playwright
base='http://127.0.0.1:8787'
out=Path('data/deployment-qa');out.mkdir(exist_ok=True)
results=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    for ticker in ['FPT','TCB','VJC']:
        r=requests.post(base+'/api/analyze',json={'ticker':ticker},timeout=20);r.raise_for_status();job=r.json()['job_id']
        start=time.time();last=0
        while time.time()-start<900:
            r=requests.get(base+'/api/jobs/'+job,timeout=90);r.raise_for_status();state=r.json()
            if time.time()-last>25:print(ticker,state['status'],state.get('message'),flush=True);last=time.time()
            if state['status']!='running':break
            time.sleep(3)
        assert state['status']=='done',state.get('message')
        data=state['data']
        for i in range(30):
            if data.get('images'):break
            time.sleep(2);data=requests.get(base+'/api/jobs/'+job,timeout=90).json()['data']
        markup=requests.get(base+'/api/jobs/'+job+'/report',timeout=90);markup.raise_for_status()
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.set_content(markup.text,wait_until='load')
        overflow=page.evaluate("""() => [...document.querySelectorAll('.report-page')].flatMap((p,i)=>{
          const limit=p.querySelector('footer').getBoundingClientRect().top-9;
          return [...p.children].filter(el=>el.tagName!=='FOOTER'&&el.getBoundingClientRect().bottom>limit).map(el=>({page:i+1,text:el.innerText?.slice(0,60)}));})""")
        assert not overflow,(ticker,overflow)
        r=requests.get(base+'/api/jobs/'+job+'/pdf',timeout=150);r.raise_for_status()
        (out/(ticker+'.pdf')).write_bytes(r.content)
        with pymupdf.open(stream=r.content,filetype='pdf') as doc:
            assert len(doc)==8,(ticker,len(doc))
            doc[0].get_pixmap(matrix=pymupdf.Matrix(.8,.8)).save(out/(ticker+'-cover.png'))
        result={'ticker':ticker,'job_id':job,'pdf_pages':8,'pdf_bytes':len(r.content),'news':len(data.get('news',[])),
          'annual_reports':len(data.get('annual_insights',[])),'images':len(data.get('images',[])),
          'signal_date':data.get('signal',{}).get('signal_date'),'overflow':overflow}
        results.append(result);(out/'validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
        print(json.dumps(result),flush=True);page.close()
    browser.close()
PY
