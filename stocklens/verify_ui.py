"""Kiểm tra giao diện, tuỳ chọn báo cáo và lỗi đầu vào trên server localhost."""
from pathlib import Path
import json,requests
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8787';JOB='verified-fpt'
def main():
    qa=Path(__file__).parent/'tmp/qa';qa.mkdir(parents=True,exist_ok=True)
    assert requests.get(BASE+'/api/health',timeout=10).ok
    assert requests.get(BASE+f'/api/jobs/{JOB}/report?depth=invalid',timeout=10).status_code==422
    assert requests.post(BASE+'/api/analyze',json={'ticker':'../FPT'},timeout=10).status_code==422
    assert requests.get(BASE+'/api/jobs/missing',timeout=10).status_code==404
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1500,'height':1000});errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'/?job='+JOB,wait_until='networkidle')
        page.wait_for_selector('#result',state='visible',timeout=15000)
        assert page.locator('#stock-name').inner_text().startswith('FPT')
        page.locator('[data-pane="valuation"]').click()
        assert page.locator('#valuation-table tr').count()==5
        page.select_option('#report-depth','short');page.select_option('#report-horizon','long');page.select_option('#report-risk','cautious')
        url=page.locator('#preview').get_attribute('href')
        assert 'depth=short' in url and 'horizon=long' in url and 'risk=cautious' in url
        markup=requests.get(BASE+url,timeout=30);markup.raise_for_status()
        assert markup.text.count('class="report-page"')==4
        page.screenshot(path=str(qa/'dashboard.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(qa/'mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        assert not errors,errors
        browser.close()
    print(json.dumps({'browser_errors':errors,'report_options':'PASS','mobile':'PASS','validation':'PASS'}))

if __name__=='__main__':main()
