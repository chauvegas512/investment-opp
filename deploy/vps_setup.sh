#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
if ! command -v docker >/dev/null; then
    apt-get update
    apt-get install -y docker.io docker-compose-v2 docker-buildx
fi
systemctl enable --now docker
mkdir -p /opt/stocklens/releases
cd /opt/stocklens/releases
release="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$release"
tar -xzf /tmp/stocklens-release.tar.gz -C "$release"
cd "$release/deploy"
docker compose -p stocklens up -d --build
ln -sfn "/opt/stocklens/releases/$release" /opt/stocklens/current
docker compose -p stocklens ps
