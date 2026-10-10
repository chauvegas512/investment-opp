import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
import app,database
class DeploymentTests(unittest.TestCase):
    def test_symbols_exist_without_optional_archive(self):
        with patch.object(database,'DATABASE',Path('/does-not-exist/stocks.sqlite')):
            rows=database.symbols()
        self.assertGreater(len(rows),1000)
        self.assertIn('TCB',{r['ticker'] for r in rows})
        self.assertEqual(len(rows),len({r['ticker'] for r in rows}))
    def test_analysis_shares_capacity_with_refresh(self):
        with patch.object(app,'jobs',{}),patch.object(app,'refreshing',{'one','two'}):
            with self.assertRaises(HTTPException) as caught:app.analyze(app.AnalysisRequest(ticker='TCB'))
            self.assertEqual(caught.exception.status_code,429)
            self.assertEqual(app.jobs,{})
    def test_pdf_capacity_returns_busy_without_starting_browser(self):
        app.pdf_slot.acquire()
        try:
            with patch.object(app,'bundle_of',return_value={}),patch.object(app,'pdf_bytes') as render:
                with self.assertRaises(HTTPException) as caught:app.pdf('example')
                self.assertEqual(caught.exception.status_code,429);render.assert_not_called()
        finally:app.pdf_slot.release()
if __name__=='__main__':unittest.main()
