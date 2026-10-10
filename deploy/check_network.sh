#!/usr/bin/env bash
set -euo pipefail
for url in https://registry-1.docker.io/v2/ https://mirror.gcr.io/v2/ https://pypi.org/simple/ https://cdn.playwright.dev/ https://public.ecr.aws/v2/; do
    printf '%s ' "$url"
    curl -I -sS --connect-timeout 5 --max-time 8 -o /dev/null -w '%{http_code}\n' "$url" || true
done
ls -td /opt/stocklens/releases/* | sed -n '1,2p'
