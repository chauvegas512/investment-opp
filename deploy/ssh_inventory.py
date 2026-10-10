"""Pinned SSH inventory; password stays in RAM and is never placed in shell arguments."""
import socket,base64,hashlib,getpass
import paramiko
HOST='160.22.107.152'
EXPECTED='GniCldCM6UYBaWWzBGggu6g49EOiHLRUhHUYL/iH8rc'
def connect(password,user='root'):
    sock=socket.create_connection((HOST,22),timeout=10)
    transport=paramiko.Transport(sock)
    options=transport.get_security_options()
    options.key_types=tuple(k for k in options.key_types if 'rsa' in k)
    transport.start_client(timeout=15)
    key=transport.get_remote_server_key()
    fingerprint=base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')
    if fingerprint!=EXPECTED:
        transport.close();raise RuntimeError('HOST_KEY_MISMATCH: SHA256:'+fingerprint)
    transport.auth_password(user,password)
    return transport
if __name__=='__main__':
    password=getpass.getpass('VPS password (memory only): ')
    transport=connect(password);password=None
    try:
        channel=transport.open_session();channel.exec_command('uname -a; id; free -h; df -h /; command -v docker || true; ss -ltn | head -15')
        print(channel.makefile('r').read().decode(),flush=True)
        print(channel.makefile_stderr('r').read().decode(),flush=True)
        print('EXIT_STATUS:',channel.recv_exit_status(),flush=True)
    finally:transport.close()
