"""Kiểm tra các tương tác chính của web mới và tùy chọn hình ảnh trong PDF."""
from pathlib import Path
import json,requests
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8787'
def main():
    qa=Path(__file__).parent/'tmp/qa-redesign';qa.mkdir(parents=True,exist_ok=True)
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1600,'height':1100})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE,wait_until='networkidle');page.wait_for_selector('#result',state='visible',timeout=20000)
        assert page.locator('#stock-name').inner_text()=='FPT'
        assert page.locator('#company-logo img').evaluate('(e)=>e.complete&&e.naturalWidth>0')
        page.screenshot(path=str(qa/'desktop-overview.png'))
        before=page.locator('#chart svg').get_attribute('aria-label')
        page.locator('[data-range="21"]').click()
        assert before!=page.locator('#chart svg').get_attribute('aria-label')
        assert page.locator('#conditions-table tbody tr').count()==5
        for name in ['financial','valuation','news','mining','sources']:
            page.locator(f'[data-pane="{name}"]').click();assert page.locator('#'+name).is_visible()
            page.screenshot(path=str(qa/f'desktop-{name}.png'))
        page.locator('[data-pane="mining"]').click();page.select_option('#keyword-group','esg')
        assert 'môi trường' in page.locator('#keywords').input_value()
        assert page.locator('.document-kpis').count()>=1
        page.locator('[data-pane="overview"]').click()
        assert page.locator('#image-gallery .image-card').count()>=3
        page.locator('#include-images').uncheck()
        url=page.locator('#preview').get_attribute('href');assert 'images=false' in url
        html=requests.get(BASE+url,timeout=40);html.raise_for_status()
        assert 'class="photo-strip"' not in html.text and 'class="company-mark"' not in html.text
        for width in [390,320]:
            page.set_viewport_size({'width':width,'height':844});page.evaluate('scrollTo(0,0)');page.screenshot(path=str(qa/f'mobile-{width}.png'))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        assert not errors,errors
        browser.close()
    print(json.dumps({'tabs':'PASS','ranges':'PASS','photos':'PASS','image_toggle':'PASS','keyword_groups':'PASS','mobile':[390,320],'browser_errors':errors}))
if __name__=='__main__':main()
