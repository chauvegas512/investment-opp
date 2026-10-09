import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import numpy as np
from indicators import technical_frame,technical_research
from company_adapter import extract_overview
from research_v2 import enrich
from test_integration import bundle_fixture

def candles(close):
    return [{'date':d.strftime('%Y-%m-%d'),'open':v,'high':v+1,'low':v-1,'close':v,'volume':100} for d,v in zip(pd.bdate_range('2025-01-01',periods=len(close)),close)]

class DataTests(unittest.TestCase):
    def test_wilder_rsi_known_sample(self):
        close=[44.34,44.09,44.15,43.61,44.33,44.83,45.10,45.42,45.84,46.08,45.89,46.03,45.61,46.28,46.28,46.00]
        f=technical_frame(candles(close))
        self.assertAlmostEqual(f.rsi14.iloc[14],70.464135,places=5)
        self.assertAlmostEqual(f.rsi14.iloc[15],66.249619,places=5)
    def test_flat_and_rising_rsi_atr(self):
        for prices,rsi in [([100]*40,50),(list(range(100,140)),100)]:
            f=technical_frame(candles(prices));self.assertEqual(f.rsi14.iloc[-1],rsi);self.assertAlmostEqual(f.atr14.iloc[-1],2)
        f=technical_frame(candles([100]*40));self.assertEqual(f.macd.iloc[-1],0);self.assertEqual(f.macd_signal.iloc[-1],0)
    def test_support_uses_prior_sessions(self):
        rows=candles([100]*30);rows[-1]['low']=10;rows[-1]['high']=1000
        last=technical_frame(rows).iloc[-1];self.assertEqual(last.support20,99);self.assertEqual(last.resistance20,101)
    def test_benchmark_aligns_dates_and_keeps_negative_sign(self):
        prices=candles(np.linspace(200,100,300));bench=candles(np.linspace(100,150,300))[:-1]
        r=technical_research(prices,bench);last=r['comparisons'][0]
        self.assertLess(last['stock_return'],0);self.assertGreater(last['benchmark_return'],0)
        self.assertEqual(last['end_date'],bench[-1]['date']);self.assertTrue(r['warnings'])
        self.assertAlmostEqual(last['excess_pp'],(last['stock_return']-last['benchmark_return'])*100)
    def test_missing_rsi_and_ma_are_not_zero(self):
        f=technical_frame(candles([100]*5));self.assertTrue(pd.isna(f.rsi14.iloc[-1]));self.assertTrue(pd.isna(f.ma200.iloc[-1]))
    def test_duplicate_shares_use_market_cap_consistency(self):
        frame=pd.DataFrame([['TEST',100,100000,1000,800]],columns=['symbol','current_price','market_cap','issue_share','issue_share'])
        result=extract_overview(frame,'TEST');self.assertEqual(result['shares_outstanding'],1000)
        self.assertEqual(result['shares_status'],'PROVIDER_CONSISTENT')
    def test_parent_equity_and_ttm_valuation(self):
        b=bundle_fixture();b['company'].update(shares_outstanding=1000,shares_status='PROVIDER_CONSISTENT')
        for period in ['2025-Q3','2025-Q4','2026-Q1','2026-Q2']:
            for key,value in [('net_income_parent',10000),('equity',100000),('non_controlling_equity',20000)]:
                b['quarterly'].append({'report_period':period,'item_code':key,'value':value})
        v=enrich(b)['research']['valuation'];self.assertEqual(v['parent_profit_ttm'],40000);self.assertEqual(v['equity_parent'],80000)
        self.assertEqual(v['pb_reference'],50000*1000/80000);self.assertFalse(v['scenarios'])
    def test_growth_does_not_skip_missing_previous_year(self):
        b=bundle_fixture();b['annual']=[r for r in b['annual'] if r['report_period']!='2024']
        self.assertIsNone(enrich(b)['research']['metrics']['revenue_growth'])
    def test_bank_masks_generic_score(self):
        b=bundle_fixture();b['company']['is_bank']=True;b=enrich(b)
        self.assertIsNone(b['signal']['fa_score']);self.assertIsNone(b['signal']['unified_score'])
        self.assertIsNone(b['research']['metrics']['current_ratio']);self.assertTrue(b['research']['quality']['bank'])

if __name__=='__main__':unittest.main()
