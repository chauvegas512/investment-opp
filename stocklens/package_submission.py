"""Package only the runtime source/data; omit environments, secrets, caches and retired tasks."""
from pathlib import Path
import hashlib,json,re,zipfile
from integration import ROOT,WORKSPACE,BOT,MINER,HOHA,DATABASE

def files():
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT)
        if not p.is_file() or set(rel.parts)&{'tmp','data','__pycache__','.git','.agents','.codex'}:continue
        if p.name.startswith('.env') or p.name in {'upgrade_ui.py','AGENTS.md'}:continue
        if 'output' in rel.parts and p.name not in {'StockLens-FPT.pdf','StockLens-VCB.pdf','FPT-evidence.json','VCB-evidence.json','FPT-source-verification.json','PDF-validation.json'}:continue
        if p.suffix.lower() in {'.py','.ps1','.md','.html','.css','.js','.txt','.json','.pdf','.svg','.png','.jpg','.jpeg','.webp'} or p.name=='.gitignore':yield p
    for name in ['vn_stock_scraper_complete.py','strategy_engine.py','strategy_config.json','model_portfolio.py']:
        yield BOT/name
    for p in (MINER/'src/arminer').rglob('*.py'):
        if p.relative_to(MINER).as_posix() in {'src/arminer/utils/env.py','src/arminer/__init__.py'}:continue
        yield p
    for folder in [MINER/'src/arminer/data/bctc_data',MINER/'data/zenodo_catalog',MINER/'data/gap_filler']:
        for p in folder.rglob('*'):
            if p.is_file() and p.suffix.lower() in {'.parquet','.json','.csv'}:yield p
    for name in ['LICENSE','README.md']:
        if (MINER/name).is_file():yield MINER/name
    for name in ['presentation_dna.py','smart_layout_renderer.py','smart_image_composition.py','smart_slide_finish.py','smart_illustrations.py','smart_product_showcase.py']:
        yield HOHA/'services'/name
    yield HOHA/'assets/iconify/lucide-curated.json'
    for p in (MINER/'tests/fixtures').glob('*.csv'):
        yield p
    hoha_root=HOHA.parent.parent
    for name in ['LICENSE','NOTICE','MODIFICATIONS.md','THIRD_PARTY_NOTICES.md']:
        if (hoha_root/name).is_file():yield hoha_root/name
    for name in ['__init__.py','schema.py','charts.py']:
        yield WORKSPACE/'report_engine'/name
    yield DATABASE

def main():
    destination=ROOT/'output/StockLens-midterm.zip'
    items=sorted(set(files()))
    manifest=[]
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
        for p in items:
            if p.suffix in {'.py','.json','.html','.css','.js','.svg','.ps1','.md','.txt'}:
                raw=p.read_text(encoding='utf-8',errors='replace')
                if re.search(r'vnstock_[0-9a-f]{32}|hf_[A-Za-z0-9]{25,}',raw):
                    raise ValueError('Credential-shaped literal detected; file omitted from package: '+p.name)
            relative=p.relative_to(WORKSPACE).as_posix()
            archive.write(p,relative)
            manifest.append({'path':relative,'bytes':p.stat().st_size})
        archive.writestr('PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2))
        archive.writestr('README_FIRST.txt','Extract this ZIP keeping all folders. On Windows, run stocklens/setup.ps1 once if needed, then stocklens/start.ps1. Open http://127.0.0.1:8787. For the verified FPT demo: activate the shared .venv, cd stocklens, run python run.py --restore-evidence output/FPT-evidence.json. Source licenses and limitations are in stocklens/docs/BAN_GIAO.md and THIRD_PARTY_NOTICES.md. No credentials are included.\n')
    with zipfile.ZipFile(destination) as archive:
        bad=archive.testzip()
        assert bad is None,bad
    print(json.dumps({'package':str(destination),'files':len(items),'bytes':destination.stat().st_size}))

if __name__=='__main__':main()
