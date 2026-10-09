import sys,unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dynamic_images import relevant,load,choose,selected,auto_select
class DynamicImageTests(unittest.TestCase):
    def test_unrelated_car_is_rejected_for_frt(self):
        self.assertFalse(relevant({'title':'Used Ford Transit for Sale','source_url':'https://carfax.com/used-ford'},'FRT','CTCP Bán lẻ Kỹ thuật số FPT'))
        self.assertTrue(relevant({'title':'FPT Retail','source_url':'https://frt.vn/en'},'FRT','CTCP Bán lẻ Kỹ thuật số FPT'))
    def test_cache_path_traversal_is_rejected(self):
        self.assertEqual(load('../FRT')['images'],[])
    def test_short_legal_name_still_matches_brand_logo(self):
        self.assertTrue(relevant({'title':'FPT Corporation logo','source_url':'https://example.com/fpt'},'FPT','CTCP FPT'))
    def test_official_website_and_short_brand_can_match(self):
        self.assertTrue(relevant({'title':'Trụ sở ngân hàng','source_url':'https://www.mbbank.com.vn/about'},'MBB','Ngân hàng TMCP Quân đội','https://mbbank.com.vn'))
        self.assertTrue(relevant({'title':'Eximbank logo','source_url':'https://example.com'},'EIB','Ngân hàng TMCP Xuất nhập khẩu Việt Nam',None,'Eximbank'))
    def test_select_only_known_cached_image(self):
        with tempfile.TemporaryDirectory() as d,patch('dynamic_images.CACHE',Path(d)):
            identifier='a'*32;filename=identifier+'.png';(Path(d)/filename).write_bytes(b'fixture')
            (Path(d)/'FRT.json').write_text(json.dumps({'images':[{'id':identifier,'filename':filename,'mime':'image/png','selected':False}]}))
            choose('FRT',identifier);self.assertEqual(len(selected('FRT')),1)
            with self.assertRaises(ValueError):choose('FRT','b'*32)
            choose('FRT',identifier,False);self.assertEqual(selected('FRT'),[])
    def test_auto_cover_respects_manual_disable(self):
        d={'images':[{'width':1200,'height':675,'title':'Công ty','original_url':'https://example.com/branch.jpg','selected':False}]}
        self.assertTrue(auto_select(d));self.assertEqual(d['images'][0]['selection_method'],'AUTO_RELEVANCE')
        d['images'][0]['selected']=False;d['selection_disabled']=True;self.assertFalse(auto_select(d))
if __name__=='__main__':unittest.main()
