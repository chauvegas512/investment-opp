"""Kiểm tra ảnh thực cho mã ngoài bộ mẫu và việc nhúng ảnh đã chọn vào bìa PDF."""
from pathlib import Path
import json,requests
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8787'
def main():
    history=requests.get(BASE+'/api/history',timeout=10).json();item=next(i for i in history if i['ticker']=='FRT');job=item['job_id']
    data=requests.get(BASE+'/api/jobs/'+job,timeout=10).json()['data'];search=data['image_search']
    assert search['status']=='READY' and search['provider']=='Serper'
    assert search['images'] and not any('carfax' in i['source_url'] or 'ebay' in i['source_url'] for i in search['images'])
    qa=Path(__file__).parent/'tmp/qa-dynamic';qa.mkdir(parents=True,exist_ok=True)
    markup=requests.get(BASE+'/api/jobs/'+job+'/report',timeout=40);markup.raise_for_status()
    assert 'class="photo-cover"' in markup.text and 'Giới thiệu công ty' in markup.text
    assert 'ảnh minh họa từ tìm kiếm' in markup.text
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)));page.goto(BASE+'/?job='+job,wait_until='networkidle')
        page.wait_for_selector('#result',state='visible');assert page.locator('#stock-name').inner_text()=='FRT'
        assert page.locator('#image-gallery').is_hidden()
        assert page.locator('#find-images').is_hidden()
        assert any(i.get('selected') for i in search['images'])
        page.screenshot(path=str(qa/'FRT-overview.png'))
        report=browser.new_page();report.set_content(markup.text,wait_until='load');report.locator('.report-page').first.screenshot(path=str(qa/'FRT-cover.png'))
        assert not errors,errors;browser.close()
    print(json.dumps({'ticker':'FRT','images':len(search['images']),'provider':search['provider'],'cover':'PASS','browser_errors':errors}))
if __name__=='__main__':main()
