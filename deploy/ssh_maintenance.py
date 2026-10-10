"""Run a reviewed maintenance script and optional archive transfer with pinned SSH."""
import argparse,getpass,shlex,time,json,re,hashlib
from pathlib import Path
import paramiko
from ssh_inventory import connect
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--script',required=True);parser.add_argument('--archive',action='store_true');parser.add_argument('--image-key',action='store_true');parser.add_argument('--wheels',action='store_true')
parser.add_argument('--sync-files',nargs='*',default=[])
parser.add_argument('--download-qa',action='store_true')
parser.add_argument('--image-cache',action='store_true')
if __name__=='__main__':
    args=parser.parse_args();password=getpass.getpass('VPS password (memory only): ')
    key=getpass.getpass('Serper key (memory only): ') if args.image_key else None
    transport=connect(password);password=None
    try:
        if args.image_cache:
            source=ROOT.parent/'stocklens/data/image-cache'
            remote='/opt/stocklens/shared/data/image-cache/'
            sftp=paramiko.SFTPClient.from_transport(transport)
            for manifest in source.glob('*.json'):
                if not re.fullmatch(r'[A-Z][A-Z0-9]{1,9}',manifest.stem):continue
                data=json.loads(manifest.read_text(encoding='utf-8'));valid=[]
                for row in data.get('images',[]):
                    name=row.get('filename','')
                    if not re.fullmatch(r'[a-f0-9]{32}\.(png|jpg|webp|gif)',name):continue
                    file=source/name
                    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=row.get('sha256'):continue
                    sftp.put(str(file),remote+name);sftp.chmod(remote+name,0o644);valid.append(row)
                if not valid:continue
                data['images']=valid
                with sftp.file(remote+manifest.name,'w') as f:f.write(json.dumps(data,ensure_ascii=False).encode())
                sftp.chmod(remote+manifest.name,0o644)
                print('Migrated image cache:',manifest.stem,len(valid),flush=True)
            sftp.close()
        if args.sync_files:
            sftp=paramiko.SFTPClient.from_transport(transport)
            for rel in args.sync_files:
                path=Path(rel)
                if path.is_absolute() or '..' in path.parts or not str(path).startswith('stocklens'):raise ValueError('Invalid source path')
                sftp.put(str(ROOT/path),'/opt/stocklens/current/'+path.as_posix());print('Synced source:',path.as_posix(),flush=True)
            sftp.close()
        if args.wheels:
            sftp=paramiko.SFTPClient.from_transport(transport)
            try:sftp.stat('/opt/stocklens/wheels')
            except FileNotFoundError:sftp.mkdir('/opt/stocklens/wheels')
            for wheel in (ROOT/'deploy/tmp/wheels').glob('*.whl'):sftp.put(str(wheel),'/opt/stocklens/wheels/'+wheel.name);print('Uploaded runtime:',wheel.name,flush=True)
            sftp.close()
        if args.archive:
            sftp=paramiko.SFTPClient.from_transport(transport);last=[0]
            def progress(done,total):
                if time.time()-last[0]>10:
                    print('Archive upload:',round(done/total*100,1),'%',flush=True);last[0]=time.time()
            sftp.put(str(ROOT/'deploy/tmp/archive.sqlite.gz'),'/tmp/stocklens-archive.sqlite.gz',callback=progress);sftp.close()
        prefix='export BACKEND_DOMAIN=stocklens.160.22.107.152.sslip.io\n'
        if key:prefix+='export SERPER_API_KEY='+shlex.quote(key)+'\n'
        key=None
        script=Path(args.script).read_text(encoding='utf-8')
        channel=transport.open_session();channel.exec_command('bash -s');channel.sendall((prefix+script).encode());channel.shutdown_write();prefix=None
        while not channel.exit_status_ready() or channel.recv_ready() or channel.recv_stderr_ready():
            if channel.recv_ready():print(channel.recv(65536).decode(errors='replace'),end='',flush=True)
            if channel.recv_stderr_ready():print(channel.recv_stderr(65536).decode(errors='replace'),end='',flush=True)
            time.sleep(.2)
        result=channel.recv_exit_status();print('\nREMOTE_EXIT_STATUS:',result,flush=True)
        if result:raise SystemExit(result)
        if args.download_qa:
            sftp=paramiko.SFTPClient.from_transport(transport)
            target=ROOT/'deploy/tmp/qa';target.mkdir(parents=True,exist_ok=True)
            remote='/opt/stocklens/shared/data/deployment-qa/'
            for name in ['validation.json','FPT.pdf','TCB.pdf','VJC.pdf','FPT-cover.png','TCB-cover.png','VJC-cover.png']:
                sftp.get(remote+name,str(target/name));print('Downloaded QA:',name,flush=True)
            sftp.close()
    finally:transport.close()
