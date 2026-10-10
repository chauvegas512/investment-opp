#!/usr/bin/env bash
set -euo pipefail
ip -4 route
ip -4 addr show
python3 -u - <<'PY'
import socket,concurrent.futures
hosts=['acme-v02.api.letsencrypt.org','api.zerossl.com','registry-1.docker.io','stocklens-investment.vercel.app','google.com','api.vietcap.com.vn']
def check(host):
    for ip in sorted({r[4][0] for r in socket.getaddrinfo(host,443,socket.AF_INET,socket.SOCK_STREAM)}):
        try:
            s=socket.create_connection((ip,443),timeout=5);s.close();print(host,ip,'TCP_OK',flush=True)
        except OSError as e:print(host,ip,type(e).__name__,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as p:list(p.map(check,hosts))
PY
systemctl --no-pager --full status caddy | sed -n '1,14p'
