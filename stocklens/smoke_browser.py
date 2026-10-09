"""Exercise the actual search button against live data; fail on browser errors."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge',headless=True)
    try:
        page=browser.new_page(viewport={'width':1500,'height':1000})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://127.0.0.1:8787/',wait_until='networkidle')
        assert not errors,errors
        page.locator('#ticker').fill('FPT')
        page.locator('#analyze').click()
        page.wait_for_function('currentJob !== null',timeout=10000)
        print(json.dumps({'job_id':page.evaluate('currentJob')},ensure_ascii=True),flush=True)
        page.wait_for_url('**/?job=*',timeout=360000)
        assert not errors,errors
        print(json.dumps({'url':page.url,'name':page.locator('#stock-name').inner_text(),'errors':errors},ensure_ascii=True),flush=True)
    except Exception:
        directory=Path('tmp/qa')
        directory.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(directory/'browser-failure.png'),full_page=True)
        print(json.dumps({'message':page.locator('#message').inner_text(),'errors':errors},ensure_ascii=True),flush=True)
        raise
    finally:
        browser.close()
