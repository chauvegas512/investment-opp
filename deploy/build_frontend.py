"""Build the Vercel static site with same-origin API/image rewrites."""
import argparse,json,shutil
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
def build(origin):
    parsed=urlparse(origin)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ValueError('Backend must be an HTTPS origin without credentials/path/query')
    target=ROOT/'deploy/vercel';target.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'stocklens/static/index.html',target/'index.html')
    shutil.copytree(ROOT/'stocklens/static',target/'static',dirs_exist_ok=True)
    config={'$schema':'https://openapi.vercel.sh/vercel.json','framework':None,'rewrites':[
        {'source':'/api/:path*','destination':origin.rstrip('/')+'/api/:path*'},
        {'source':'/image-cache/:path*','destination':origin.rstrip('/')+'/image-cache/:path*'}],
        'headers':[{'source':'/api/:path*','headers':[{'key':'Cache-Control','value':'no-store'}]},
        {'source':'/','headers':[{'key':'Cache-Control','value':'no-cache'}]}]}
    (target/'vercel.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    return target
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--backend',required=True)
    print(build(parser.parse_args().backend))
