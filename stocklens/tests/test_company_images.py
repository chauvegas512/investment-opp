import sys,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from company_images import for_company
from find_images import BingImages
class ImageTests(unittest.TestCase):
    def test_images_have_provenance_and_local_paths(self):
        rows=for_company('FPT');self.assertTrue(rows)
        self.assertTrue(all(r['source_url'].startswith('https://') and r['url'].startswith('/static/company-images/') for r in rows))
        self.assertTrue(any(r['role']=='logo' for r in rows))
    def test_unrecognized_ticker_does_not_get_wrong_logo(self):
        self.assertEqual(for_company('../FPT'),[])
        self.assertEqual(for_company('NOT-A-STOCK'),[])
    def test_offline_inline_image_is_available(self):
        self.assertTrue(all(r['src'].startswith('data:image/') for r in for_company('VCB',inline=True)))
    def test_bing_parser_requires_valid_metadata(self):
        parser=BingImages();parser.feed('<a m="broken"></a>')
        self.assertEqual(parser.results,[])
if __name__=='__main__':unittest.main()
