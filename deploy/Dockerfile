FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=Asia/Ho_Chi_Minh VNSTOCK_DISABLE_AGENT_SETUP=1 PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
WORKDIR /app
COPY stocklens/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && python -m playwright install --with-deps chromium \
    && apt-get update && apt-get install -y --no-install-recommends fonts-noto-core \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 stocklens
COPY --chown=stocklens:stocklens stocklens /app/stocklens
COPY taikhoanx10_bot_tele-main /app/taikhoanx10_bot_tele-main
COPY vn-annual-report-miner-main /app/vn-annual-report-miner-main
COPY HoHa-slide-pdf-core-2026-10-09 /app/HoHa-slide-pdf-core-2026-10-09
COPY report_engine /app/report_engine
RUN mkdir -p /app/stocklens/data && chown -R stocklens:stocklens /app/stocklens/data
USER stocklens
WORKDIR /app/stocklens
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=8s --start-period=45s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/api/health',timeout=5)" || exit 1
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8787", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
