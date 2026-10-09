import sys,unittest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from company_identity import headline_matches
from live_quote import normalize_trade,closed_daily
from test_integration import bundle_fixture
from research import enrich
class PipelineTests(unittest.TestCase):
    def test_brand_headlines_match_without_stock_code(self):
        self.assertTrue(headline_matches('Techcombank công bố kết quả kinh doanh','TCB','Ngân hàng TMCP Kỹ thương Việt Nam','Techcombank'))
        self.assertTrue(headline_matches('Vietjet mở đường bay mới','VJC','CTCP Hàng không Vietjet','Vietjet Air'))
        self.assertFalse(headline_matches('Toàn thị trường đồng loạt tăng','TCB','Ngân hàng TMCP Kỹ thương Việt Nam','Techcombank'))
    def test_trade_units_and_closed_market_label(self):
        tz=ZoneInfo('Asia/Ho_Chi_Minh');now=datetime(2026,10,9,16,tzinfo=tz)
        r=normalize_trade({'time':datetime(2026,10,9,14,45,tzinfo=tz),'price':32.35,'volume':100},'TCB',now)
        self.assertAlmostEqual(r['price_vnd'],32350);self.assertFalse(r['fresh']);self.assertEqual(r['status'],'MARKET_CLOSED_LAST_TRADE')
    def test_provisional_daily_bar_does_not_enter_eod(self):
        f=pd.DataFrame({'date':['2026-10-08','2026-10-09'],'close':[100,110]})
        now=datetime(2026,10,9,14,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
        self.assertEqual(len(closed_daily(f,now)),1)
    def test_quality_has_dataset_states(self):
        b=enrich(bundle_fixture());self.assertEqual(b['schema_version'],4)
        self.assertTrue(any(x['key']=='annual_report' for x in b['data_status']['datasets']))
    def test_context_prefers_prose_over_contents(self):
        import pymupdf
        from mining import mine_pdf
        doc=pymupdf.open()
        for i in range(10):
            page=doc.new_page()
            page.insert_text((40,80),'Table of contents risk risk risk' if i==0 else 'The company manages operational risk through regular monitoring of suppliers and customer demand. Management reviews these controls every quarter to support continuity.' if i==9 else 'Introduction')
        result=mine_pdf(doc.tobytes(),'risk','example.pdf');doc.close()
        self.assertEqual(result['findings'][0]['page'],10)
    def test_invalid_trade_price_is_rejected(self):
        with self.assertRaises(ValueError):normalize_trade({'time':'2026-10-09 14:00','price':float('nan')},'TCB')
if __name__=='__main__':unittest.main()
