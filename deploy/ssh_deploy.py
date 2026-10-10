"""Upload the reviewed release and provision StockLens; secrets stay out of source/logs."""
import getpass,subprocess,tarfile,time,shlex
from pathlib import Path
from ssh_inventory import connect
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    password=getpass.getpass('VPS password (memory only): ')
    image_key=getpass.getpass('Serper key (memory only, blank to skip): ')
    transport=connect(password);password=None
    try:
        target=ROOT/'deploy/tmp/stocklens-release.tar.gz';target.parent.mkdir(parents=True,exist_ok=True)
        paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
        with tarfile.open(target,'w:gz',compresslevel=1) as archive:
            for rel in paths:
                p=ROOT/rel
                if p.is_file() and not any(part in {'.git','.vercel','tmp','__pycache__'} for part in p.relative_to(ROOT).parts) and not p.name.startswith('.env'):
                    archive.add(p,arcname=rel,recursive=False)
        sftp=__import__('paramiko').SFTPClient.from_transport(transport)
        print('Uploading release:',target.stat().st_size,'bytes',flush=True)
        sftp.put(str(target),'/tmp/stocklens-release.tar.gz');sftp.close()
        script=(ROOT/'deploy/vps_setup.sh').read_text(encoding='utf-8')
        prefix='export BACKEND_DOMAIN=stocklens.160.22.107.152.sslip.io\n'
        if image_key:prefix+='export SERPER_API_KEY='+shlex.quote(image_key)+'\n'
        image_key=None
        channel=transport.open_session();channel.exec_command('bash -s')
        channel.sendall((prefix+script).encode());channel.shutdown_write();prefix=None
        while not channel.exit_status_ready() or channel.recv_ready() or channel.recv_stderr_ready():
            if channel.recv_ready():print(channel.recv(65536).decode(errors='replace'),end='',flush=True)
            if channel.recv_stderr_ready():print(channel.recv_stderr(65536).decode(errors='replace'),end='',flush=True)
            time.sleep(.2)
        result=channel.recv_exit_status();print('\nDEPLOY_EXIT_STATUS:',result,flush=True)
        if result:raise SystemExit(result)
    finally:transport.close()
