"""Check actual saved TCB/VJC reports, automatic cover and hidden image controls."""
import json
from pathlib import Path
import requests,pymupdf
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8787'
ROOT=Path(__file__).parent
def main():
    history=requests.get(BASE+'/api/history',timeout=10).json()
    out=ROOT/'tmp/qa-backfill';out.mkdir(parents=True,exist_ok=True)
    results=[];errors=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True)
        for ticker in ['TCB','VJC']:
            item=next(x for x in history if x['ticker']==ticker);job=item['job_id']
            data=requests.get(BASE+'/api/jobs/'+job,timeout=30).json()['data']
            assert data['annual_insights'] and data['news'],ticker
            assert data['signal']['signal_date']=='2026-10-09'
            assert data['data_status']['datasets']
            page=browser.new_page(viewport={'width':1440,'height':1000})
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(BASE+'/?job='+job,wait_until='networkidle')
            page.wait_for_selector('#result',state='visible')
            assert page.locator('#stock-name').inner_text()==ticker
            assert page.locator('#image-gallery').is_hidden()
            assert page.locator('#find-images').is_hidden()
            page.screenshot(path=str(out/(ticker+'-web.png')))
            markup=requests.get(BASE+'/api/jobs/'+job+'/report',timeout=60).text
            assert 'data:image/' in markup,ticker+' cover'
            page.set_content(markup,wait_until='load')
            overflow=page.evaluate("""() => [...document.querySelectorAll('.report-page')].flatMap((p,i)=>{
              const limit=p.querySelector('footer').getBoundingClientRect().top-9;
              return [...p.children].filter(el=>el.tagName!=='FOOTER'&&el.getBoundingClientRect().bottom>limit).map(el=>({page:i+1,text:el.innerText?.slice(0,80)}));})""")
            assert not overflow,(ticker,overflow)
            content=requests.get(BASE+'/api/jobs/'+job+'/pdf',timeout=90);content.raise_for_status()
            with pymupdf.open(stream=content.content,filetype='pdf') as doc:
                assert len(doc)==8,(ticker,len(doc))
                for i,p in enumerate(doc):p.get_pixmap(matrix=pymupdf.Matrix(.65,.65)).save(out/f'{ticker}-{i+1}.png')
            page.close();results.append({'ticker':ticker,'news':len(data['news']),'annual_reports':len(data['annual_insights']),'pdf_pages':8,'cover':'PASS','overflow':overflow})
        browser.close()
    assert not errors,errors
    (out/'validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results),flush=True)
if __name__=='__main__':main()
