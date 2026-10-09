"""Synthetic fixtures are used only in tests, never in production analysis."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from analysis import ticker_of, evaluate, normalize_prices, normalize_financial_frame
from integration import clean, status
from mining import mine_pdf
from reports import report_html, pdf_bytes


def fixture():
    dates = pd.bdate_range(end='2026-10-09',periods=550)
    def price(ticker,start,end):
        close = np.linspace(start,end,len(dates))
        return pd.DataFrame({'ticker':ticker,'date':dates.strftime('%Y-%m-%d'),'open':close,'high':close*1.01,
                             'low':close*.99,'close':close,'adjusted_close':close,'volume':1_000_000,
                             'source':'TEST FIXTURE ONLY'})
    prices, benchmark = price('TEST',10000,50000),price('VNINDEX',1000,1200)
    company={'ticker':'TEST','company_name':'TEST FIXTURE — không phải dữ liệu doanh nghiệp','sector':'Test','industry':'Test','exchange':'TEST','trading_status':'normal'}
    rows=[]
    base={'net_income':20e9,'equity':100e9,'total_assets':180e9,'revenue':200e9,'gross_profit':70e9,
          'operating_cash_flow':25e9,'total_liabilities':80e9,'cash_and_cash_equivalents':20e9,
          'short_term_borrowings':10e9,'long_term_borrowings':10e9,'ebit':30e9,'is_ebitda':35e9,
          'profit_before_tax':25e9,'current_assets':90e9,'current_liabilities':30e9,'interest_expense':2e9,
          'eps':2000,'depreciation':4e9,'amortization':1e9}
    for year in range(2021,2026):
        for code,value in base.items():
            rows.append({'ticker':'TEST','report_period':str(year),'item_code':code,'value':value*(1.1**(year-2021)),
                         'statement':'test','source':'TEST FIXTURE ONLY'})
    annual=pd.DataFrame(rows)
    now=datetime(2026,10,9,12,tzinfo=ZoneInfo('Asia/Ho_Chi_Minh'))
    return company,prices,benchmark,annual,now


def bundle_fixture():
    company,prices,benchmark,annual,now=fixture()
    signal,warnings=evaluate(company,prices,benchmark,annual,now)
    return clean({'ticker':'TEST','company':company,'signal':signal,'warnings':warnings,'created_at':now.isoformat(),
                  'prices':prices.to_dict('records'),'annual':annual.to_dict('records'),'quarterly':[],
                  'benchmark':benchmark.to_dict('records'),'news':[],'reports':[],'mining':[],
                  'sources':[{'name':'TEST FIXTURE ONLY','url':'https://example.com','as_of':'2026-10-09'}],
                  'diagnostics':[],'methodology':{}})


class AnalysisTests(unittest.TestCase):
    def test_financial_aliases_preserve_profit_scope_and_periods(self):
        frame=pd.DataFrame([
            {'item_id':'sales','item':'Gross sales','2025':110.,'2024':90.},
            {'item_id':'net_sales','item':'Net sales','2025':100.,'2024':80.},
            {'item_id':'net_profit_loss_after_tax','item':'Group profit','2025':20.,'2024':10.},
            {'item_id':'attributable_to_parent_company','item':'Parent profit','2025':15.,'2024':8.}])
        rows=normalize_financial_frame(frame,'TEST','income_statement','year')
        values={(r['item_code'],r['report_period']):r['value'] for r in rows}
        self.assertEqual(values['revenue','2025'],100.)
        self.assertEqual(values['gross_revenue','2025'],110.)
        self.assertEqual(values['net_income','2025'],20.)
        self.assertEqual(values['net_income_parent','2025'],15.)
        self.assertEqual(values['revenue','2024'],80.)

    def test_original_modules_exist(self):
        s=status()
        self.assertTrue(s['x10_engine'] and s['annual_report_miner'] and s['hoha_renderer'])

    def test_ticker_validation_and_json(self):
        self.assertEqual(ticker_of(' fpt '),'FPT')
        for ticker in ('../FPT','<script>','FPT;DROP','ĐẦU'):
            with self.assertRaises(ValueError):ticker_of(ticker)
        self.assertEqual(clean({'nan':np.nan,'inf':np.inf,'n':pd.NA}),{'nan':None,'inf':None,'n':None})

    def test_engine_with_full_fixture(self):
        args=fixture()
        signal,warnings=evaluate(*args)
        self.assertFalse(warnings)
        self.assertEqual(signal['ta_status'],'READY')
        self.assertEqual(signal['fa_status'],'READY')
        self.assertAlmostEqual(signal['unified_score'],.2*signal['effective_fa']+.8*signal['ta_score'])
        self.assertIsNone(signal['universe_rank'])

    def test_missing_fa_cannot_pass(self):
        company,prices,benchmark,annual,now=fixture()
        signal,warnings=evaluate(company,prices,benchmark,pd.DataFrame(),now)
        self.assertEqual(signal['final_action'],'DATA_REVIEW')
        self.assertTrue(warnings)

    def test_stale_and_future_prices_cannot_pass(self):
        company,prices,benchmark,annual,now=fixture()
        for shift in (-40,40):
            p,b=prices.copy(),benchmark.copy()
            p['date']=(pd.to_datetime(p['date'])+pd.Timedelta(days=shift)).dt.strftime('%Y-%m-%d')
            b['date']=(pd.to_datetime(b['date'])+pd.Timedelta(days=shift)).dt.strftime('%Y-%m-%d')
            signal,warnings=evaluate(company,p,b,annual,now)
            self.assertEqual(signal['final_action'],'DATA_REVIEW')
            self.assertTrue(any('độ mới' in w for w in warnings))

    def test_invalid_candle_removed(self):
        _,prices,*_=fixture()
        prices.loc[prices.index[-1],'low']=9999999
        normalized=normalize_prices(prices)
        self.assertEqual(len(normalized),len(prices)-1)

    def test_missing_benchmark(self):
        company,prices,benchmark,annual,now=fixture()
        signal,warnings=evaluate(company,prices,pd.DataFrame(),annual,now)
        self.assertEqual(signal['final_action'],'DATA_REVIEW')
        self.assertTrue(any('VN-Index' in w for w in warnings))


class EvidenceTests(unittest.TestCase):
    def test_current_ratio_uses_current_balances(self):
        from integration import module
        fn=module('arminer.data.financial').FinancialDataProvider.RATIO_FORMULAS['current_ratio']
        self.assertEqual(fn({'current_assets':90,'current_liabilities':30,'total_assets':180,'total_debt':80}),3)
        self.assertIsNone(fn({'total_assets':180,'total_debt':80}))
        self.assertIsNone(fn({'current_assets':90,'current_liabilities':0}))

    def test_missing_inputs_do_not_create_target_prices(self):
        from research import enrich
        b=enrich(bundle_fixture())
        v=b['research']['valuation']
        self.assertEqual(v['status'],'MISSING_INPUTS')
        self.assertEqual(v['scenarios'],[])
        self.assertIsNone(v['pe_reference'])

    def test_incidental_market_news_is_excluded(self):
        from research import enrich
        b=bundle_fixture();b['news']=[{'title':'Market roundup of banks','summary':'Mentions TEST in body'}, {'title':'TEST announces quarterly results'}]
        self.assertEqual([r['title'] for r in enrich(b)['news']],['TEST announces quarterly results'])

    def test_sqlite_archive_is_read_only(self):
        import sqlite3
        from integration import DATABASE
        if not DATABASE.is_file():self.skipTest('Database X10 tùy chọn, không nằm trong Git')
        from database import connection,archive
        with connection() as conn:
            self.assertEqual(conn.execute('PRAGMA query_only').fetchone()[0],1)
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute('CREATE TABLE stocklens_test_forbidden (id INTEGER)')
        data=archive('FPT')
        self.assertEqual(data['company']['ticker'],'FPT')
        self.assertFalse(data['price_daily'].empty)

    def test_pdf_mining_page_reference(self):
        import pymupdf
        document=pymupdf.open()
        document.new_page().insert_text((40,60),'Annual report: revenue and growth.')
        document.new_page().insert_text((40,60),'Liquidity risk and cash flow.')
        result=mine_pdf(document.tobytes(),'revenue, liquidity risk','test.pdf')
        document.close()
        self.assertEqual(result['pages'],2)
        self.assertEqual({f['page'] for f in result['findings']},{1,2})
        self.assertEqual(len(result['sha256']),64)

    def test_report_escapes_untrusted_title(self):
        markup=report_html(bundle_fixture(),'<script>alert(1)</script>')
        self.assertNotIn('<script>alert(1)</script>',markup)
        self.assertIn('STOCKLENS',markup)
        self.assertIn('không phải dự báo lợi nhuận',markup)

    def test_negative_returns_keep_sign_and_no_unlabelled_kpi(self):
        bundle=bundle_fixture()
        bundle['prices']=list(reversed(bundle['prices']))
        for i,row in enumerate(bundle['prices']):row['date']=pd.bdate_range(end='2026-10-09',periods=len(bundle['prices']))[i].strftime('%Y-%m-%d')
        company,_,_,_,now=fixture()
        bundle['signal'],_=evaluate(company,pd.DataFrame(bundle['prices']),pd.DataFrame(bundle['benchmark']),pd.DataFrame(bundle['annual']),now)
        markup=report_html(bundle)
        from research import enrich
        ret=bundle['signal']['return_3m']
        self.assertLess(ret,0)
        self.assertIn(f'{ret*100:,.1f}%',markup)
        self.assertNotIn('data-layout-archetype="kpi"',markup)

    def test_actual_pdf_contains_all_pages(self):
        import pymupdf
        markup=report_html(bundle_fixture())
        content=pdf_bytes(markup)
        self.assertTrue(content.startswith(b'%PDF-'))
        with pymupdf.open(stream=content,filetype='pdf') as document:
            self.assertEqual(document.page_count,markup.count('class="report-page"'))
            text='\n'.join(page.get_text() for page in document)
            self.assertIn('TEST',text)
            self.assertIn('phương pháp',text.lower())
            self.assertIn('Chưa lấy được',text)


if __name__=='__main__':
    unittest.main()
