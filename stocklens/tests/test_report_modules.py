import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_integration import bundle_fixture
from research import enrich
from report_modules import build
from x10_context import pe_of

class ModuleTests(unittest.TestCase):
    def test_x10_pe_filter_and_fallback(self):
        self.assertEqual(pe_of({'pe':12,'market_cap':100,'net_income_ttm':10}),12)
        self.assertEqual(pe_of({'pe':None,'market_cap':100,'net_income_ttm':10}),10)
        self.assertIsNone(pe_of({'pe':201,'market_cap':100,'net_income_ttm':10}))
        self.assertIsNone(pe_of({'pe':None,'market_cap':100,'net_income_ttm':-1}))
    def test_conditions_are_engine_flags_not_reinterpreted(self):
        b=enrich(bundle_fixture());b['signal']['breakout_pass']=False
        m=build(b);self.assertEqual(m['conditions'][3]['status'],'Chưa đạt')
        self.assertEqual(m['groups'][2]['value'],b['signal'].get('value_score'))
    def test_keyword_metrics_count_beyond_saved_findings(self):
        import pymupdf
        from mining import mine_pdf
        doc=pymupdf.open();page=doc.new_page()
        for i in range(90):page.insert_text((30,30+i*7),'risk')
        result=mine_pdf(doc.tobytes(),'risk','TEST.pdf');doc.close()
        self.assertEqual(result['metrics']['frequency'],90)
        self.assertEqual(len(result['findings']),80)
        self.assertEqual(result['metrics']['diversity'],1)
        self.assertEqual(result['metrics']['normalized_score'],10000)
        self.assertTrue(result['findings_truncated'])

if __name__=='__main__':unittest.main()
