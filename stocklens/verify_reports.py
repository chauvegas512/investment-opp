"""Xuất và kiểm tra cả PDF đầy đủ/tóm tắt bằng dữ liệu thực đã lưu."""
from pathlib import Path
import json
import pymupdf
from playwright.sync_api import sync_playwright
from research import enrich
from reports import report_html,pdf_bytes

ROOT=Path(__file__).parent

def verify():
    results=[]
    for ticker in ['FPT','VCB']:
        b=enrich(json.loads((ROOT/f'output/{ticker}-evidence.json').read_text(encoding='utf-8')))
        qa=ROOT/'tmp/pdfs'/ticker;qa.mkdir(parents=True,exist_ok=True)
        for depth,count in [('full',8),('short',4)]:
            markup=report_html(b,depth=depth)
            (qa/f'{depth}.html').write_text(markup,encoding='utf-8')
            content=pdf_bytes(markup)
            path=ROOT/f'output/StockLens-{ticker}.pdf' if depth=='full' else qa/'short.pdf'
            path.write_bytes(content)
            with pymupdf.open(stream=content,filetype='pdf') as doc:
                assert doc.page_count==count,(ticker,depth,doc.page_count)
                text='\n'.join(p.get_text() for p in doc)
                assert '\ufffd' not in text
                assert 'phương pháp' in text.lower()
                assert '12×, 16×, 20×' not in text
                for i,p in enumerate(doc):
                    if depth=='full':p.get_pixmap(matrix=pymupdf.Matrix(1.15,1.15)).save(qa/f'page-{i+1:02}.png')
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True)
                page=browser.new_page();page.set_content(markup,wait_until='load')
                overflow=page.evaluate('''() => [...document.querySelectorAll('.report-page')].flatMap((p,i)=>{
                  const limit=p.querySelector('footer').getBoundingClientRect().top-9;const errors=[];
                  for(const el of p.children){if(el.tagName==='FOOTER')continue;const r=el.getBoundingClientRect();if(r.bottom>limit)errors.push({page:i+1,tag:el.tagName,bottom:r.bottom-limit,text:el.innerText?.slice(0,90)});}
                  return errors;})''')
                browser.close()
                assert not overflow,(ticker,depth,overflow)
            results.append({'ticker':ticker,'depth':depth,'pages':count,'overflow':overflow,'bytes':len(content)})
        (ROOT/f'output/{ticker}-evidence.json').write_text(json.dumps(b,ensure_ascii=False,indent=2),encoding='utf-8')
        if ticker=='FPT':
            assert all(x['matched'] for x in b['research']['quality']['checks'])
            assert b['research']['valuation']['share_count']==1885727648
            assert b['research']['quarterly_comparison'][0]['yoy'] is None
        else:assert b['signal']['fa_score'] is None and b['signal']['unified_score'] is None
    (ROOT/'output/PDF-validation.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results),flush=True)

if __name__=='__main__':verify()
