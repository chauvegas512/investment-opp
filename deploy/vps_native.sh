#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3-venv caddy fonts-noto-core
id stocklens >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/stocklens --shell /usr/sbin/nologin stocklens
release="$(ls -td /opt/stocklens/releases/* | head -1)"
mkdir -p /opt/stocklens/shared/data /opt/stocklens/shared/archive /opt/stocklens/browsers
chown -R stocklens:stocklens /opt/stocklens/shared/data /var/lib/stocklens
if [ ! -e "$release/stocklens/data" ]; then ln -s /opt/stocklens/shared/data "$release/stocklens/data"; fi
if [ ! -e "$release/dtata  full toping" ]; then mkdir -p "$release/dtata  full toping"; ln -s /opt/stocklens/shared/archive "$release/dtata  full toping/analysis_data"; fi
python3 -m venv /var/lib/stocklens/.venv
/var/lib/stocklens/.venv/bin/pip install --find-links /opt/stocklens/wheels -r "$release/stocklens/requirements.txt"
PLAYWRIGHT_BROWSERS_PATH=/opt/stocklens/browsers /var/lib/stocklens/.venv/bin/python -m playwright install --with-deps chromium
chown -R stocklens:stocklens /var/lib/stocklens
ln -sfn "$release" /opt/stocklens/current
credential_line=''
if [ -f /etc/credstore.encrypted/stocklens_serper ]; then
    credential_line='LoadCredentialEncrypted=serper_key:/etc/credstore.encrypted/stocklens_serper'
fi
if [ -n "${SERPER_API_KEY:-}" ]; then
    mkdir -p /etc/credstore.encrypted
    printf '%s' "$SERPER_API_KEY" | systemd-creds encrypt --with-key=host --name=serper_key - /etc/credstore.encrypted/stocklens_serper.pending
    chmod 600 /etc/credstore.encrypted/stocklens_serper.pending
    mv /etc/credstore.encrypted/stocklens_serper.pending /etc/credstore.encrypted/stocklens_serper
    credential_line='LoadCredentialEncrypted=serper_key:/etc/credstore.encrypted/stocklens_serper'
fi
cat > /opt/stocklens/start-backend.sh <<'START'
#!/usr/bin/env bash
set -euo pipefail
if [ -f "${CREDENTIALS_DIRECTORY:-/nonexistent}/serper_key" ]; then
    export SERPER_API_KEY="$(cat "$CREDENTIALS_DIRECTORY/serper_key")"
fi
exec /var/lib/stocklens/.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8787 --workers 1 --proxy-headers --forwarded-allow-ips 127.0.0.1 --no-access-log
START
chmod 755 /opt/stocklens/start-backend.sh
cat > /etc/systemd/system/stocklens.service <<SERVICE
[Unit]
Description=StockLens investment research API
After=network-online.target
Wants=network-online.target
[Service]
User=stocklens
Group=stocklens
WorkingDirectory=/opt/stocklens/current/stocklens
ExecStart=/opt/stocklens/start-backend.sh
Restart=on-failure
RestartSec=5
Environment=TZ=Asia/Ho_Chi_Minh PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 VNSTOCK_DISABLE_AGENT_SETUP=1 PLAYWRIGHT_BROWSERS_PATH=/opt/stocklens/browsers HOME=/var/lib/stocklens
$credential_line
MemoryMax=1400M
TasksMax=200
NoNewPrivileges=true
PrivateTmp=true
[Install]
WantedBy=multi-user.target
SERVICE
cat > /etc/caddy/Caddyfile <<CADDY
${BACKEND_DOMAIN} {
    encode zstd gzip
    header X-Content-Type-Options nosniff
    header Referrer-Policy strict-origin-when-cross-origin
    reverse_proxy 127.0.0.1:8787
}
CADDY
caddy validate --config /etc/caddy/Caddyfile
systemctl daemon-reload
systemctl enable --now stocklens
systemctl restart caddy
systemctl --no-pager --full status stocklens | sed -n '1,20p'
