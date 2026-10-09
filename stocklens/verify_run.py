"""Validate a completed real-data run, export its PDF and render pages for QA."""
from pathlib import Path
import argparse
import json
import time

import requests
import pymupdf
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('job_id')
    args=parser.parse_args()
    base='http://127.0.0.1:8787'
    output=Path(__file__).resolve().parent/'output'
    qa=Path(__file__).resolve().parent/'tmp'/'qa'
    output.mkdir(exist_ok=True)
    qa.mkdir(parents=True,exist_ok=True)
    response=requests.get(base+'/api/jobs/'+args.job_id,timeout=15)
    response.raise_for_status()
    job=response.json()
    if job['status']!='done':
        raise RuntimeError('Run is not completed: '+job['status'])
    data=job['data']
    # The saved sample keeps source links rather than copying article body text.
    saved=json.loads(json.dumps(data))
    for article in saved.get('news',[]):
        article.pop('summary',None)
    (output/'FPT-evidence.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    # Cross-check 2025 group revenue/profit against FPT's own rounded annual report.
    latest={r['item_code']:r['value'] for r in data['annual'] if r['report_period']=='2025'}
    assert abs(latest['revenue']-70113e9)<1e9,latest['revenue']
    assert abs(latest['net_income']-11232e9)<1e9,latest['net_income']
    verification={'period':'2025','source':'https://bctn2025.fpt.com/',
                  'revenue_vnd':latest['revenue'],'group_net_profit_vnd':latest['net_income'],
                  'official_rounded_billions':{'revenue':70113,'group_net_profit':11232},
                  'comparison':'Passed; within rounding tolerance of one billion VND.'}
    (output/'FPT-source-verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
    assert requests.post(base+'/api/analyze',json={'ticker':'../FPT'},timeout=10).status_code==422
    assert requests.get(base+'/api/jobs/nonexistent',timeout=10).status_code==404
    assert requests.post(base+'/api/jobs/'+args.job_id+'/mine',params={'keywords':'risk'},data=b'not pdf',timeout=10).status_code==422
    markup=requests.get(base+'/api/jobs/'+args.job_id+'/report?news=true',timeout=30)
    markup.raise_for_status()
    (qa/'report.html').write_text(markup.text,encoding='utf-8')
    pdf=requests.get(base+'/api/jobs/'+args.job_id+'/pdf?news=true',timeout=90)
    pdf.raise_for_status()
    assert pdf.content.startswith(b'%PDF-')
    pdf_path=output/'StockLens-FPT.pdf'
    pdf_path.write_bytes(pdf.content)
    with pymupdf.open(pdf_path) as document:
        count=document.page_count
        assert count==markup.text.count('class="report-page"')
        for index,page in enumerate(document):
            page.get_pixmap(matrix=pymupdf.Matrix(1,1)).save(qa/f'page-{index+1:02}.png')
        text='\n'.join(page.get_text() for page in document)
        assert 'FPT' in text
        assert '\ufffd' not in text
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True)
        try:
            page=browser.new_page(viewport={'width':1500,'height':1000})
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(base+'/?job='+args.job_id,wait_until='networkidle')
            page.wait_for_selector('#result',state='visible',timeout=20000)
            page.screenshot(path=str(qa/'dashboard.png'),full_page=True)
            assert page.locator('#stock-name').inner_text().startswith('FPT')
            assert not errors,errors
            page.locator('[data-pane="valuation"]').click()
            assert page.locator('#valuation-table table').is_visible()
            assert page.locator('#valuation-table tr').count()==5
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(qa/'mobile.png'),full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            report=browser.new_page(viewport={'width':1280,'height':720})
            report.set_content(markup.text,wait_until='load')
            overflow=report.evaluate('''() => [...document.querySelectorAll('.report-page')].flatMap((page,i)=>{
                const bounds=page.getBoundingClientRect(); const walker=document.createTreeWalker(page,NodeFilter.SHOW_TEXT);const errors=[];
                let node;while(node=walker.nextNode()){if(!node.textContent.trim()||['STYLE','SCRIPT'].includes(node.parentElement.tagName))continue;
                    const range=document.createRange();range.selectNodeContents(node);
                    for(const box of range.getClientRects()){if(box.width>0&&box.height>0&&(box.left<bounds.left-2||box.right>bounds.right+2||box.top<bounds.top-2||box.bottom>bounds.bottom+2))errors.push({page:i+1,text:node.textContent.slice(0,80)});}}
                return errors;})''')
            assert not overflow,overflow
        finally:browser.close()
    print(json.dumps({'ticker':data['ticker'],'price_date':data['signal'].get('signal_date'),
                      'annual_rows':len(data['annual']),'quarterly_rows':len(data['quarterly']),
                      'news':len(data['news']),'catalog_reports':len(data['reports']),
                      'pdf_pages':count,'browser_errors':errors,'overflow':overflow},ensure_ascii=True))


if __name__=='__main__':
    main()
