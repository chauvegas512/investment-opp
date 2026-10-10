"""Repack installed pure-Python runtime distributions for a private VPS transfer."""
from importlib.metadata import distribution
from pathlib import Path
import zipfile,csv,io,hashlib,base64
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'deploy/tmp/wheels';out.mkdir(parents=True,exist_ok=True)
for name in ['vnstock','vnai','vnstock_ezchart']:
    dist=distribution(name);wheel=dist.read_text('WHEEL') or ''
    if 'Root-Is-Purelib: true' not in wheel or 'Tag: py3-none-any' not in wheel:raise RuntimeError('Not a portable pure-Python wheel: '+name)
    target=out/(name.replace('-','_')+'-'+dist.version+'-py3-none-any.whl');rows=[];record=None
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for entry in dist.files or []:
            rel=Path(str(entry))
            if '..' in rel.parts or '__pycache__' in rel.parts or rel.suffix=='.pyc' or rel.name in {'INSTALLER','REQUESTED','direct_url.json'}:continue
            if rel.name=='RECORD':record=rel.as_posix();continue
            path=dist.locate_file(entry)
            if not path.is_file():continue
            data=path.read_bytes();arc=rel.as_posix();archive.writestr(arc,data)
            rows.append([arc,'sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('='),len(data)])
        if not record:raise RuntimeError('Missing wheel RECORD')
        buf=io.StringIO();writer=csv.writer(buf,lineterminator='\n');writer.writerows(rows+[[record,'','']]);archive.writestr(record,buf.getvalue())
    print(target.name,target.stat().st_size)
