#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""
find_images.py - Tim anh logo/cong ty tu web theo query.

Usage:
    python find_images.py "FPT logo"
    python find_images.py "VPBank headquarters" --limit 5
    python find_images.py "Vingroup brand" --download ./output

Tai su dung trong code khac:
    from find_images import search_images
    results = await search_images("FPT logo", limit=5)
"""
import argparse
import asyncio
import hashlib
import html
import json
import ipaddress
import os
import socket
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

# -- API keys (dat bien moi truong hoac dien truc tiep) ----------------------
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")   # console.cloud.google.com
GOOGLE_CSE_ID  = os.environ.get("GOOGLE_CSE_ID", "")    # programmablesearchengine.google.com
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")   # https://serper.dev
BRAVE_API_KEY  = os.environ.get("BRAVE_API_KEY", "")    # https://api.search.brave.com


# -- Network helpers ---------------------------------------------------------

class PublicResolver(aiohttp.abc.AbstractResolver):
    """Chan SSRF - chi cho phep IP public."""
    async def resolve(self, host, port=0, family=socket.AF_INET):
        records = await asyncio.get_running_loop().getaddrinfo(
            host, port, family=family, type=socket.SOCK_STREAM
        )
        ips = list(dict.fromkeys(r[4][0] for r in records))
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise ValueError(f"Private/unresolvable host: {host}")
        return [
            {"hostname": host, "host": ip, "port": port,
             "family": family, "proto": 0, "flags": socket.AI_NUMERICHOST}
            for ip in ips
        ]

    async def close(self):
        pass


# -- HTML parser fallback (Bing) ---------------------------------------------

class BingImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attrs = dict(attrs)
        m = attrs.get("m")
        if not m:
            return
        try:
            data = json.loads(html.unescape(m))
            if data.get("murl"):
                self.results.append({
                    "url": data["murl"],
                    "source_url": data.get("purl", ""),
                    "title": data.get("t", ""),
                })
        except (ValueError, TypeError):
            pass


# -- Search providers --------------------------------------------------------

async def _search_google(session: aiohttp.ClientSession, query: str, limit: int) -> list[dict]:
    """Google Custom Search API - searchType=image.
    Docs: https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
    Quota va gia theo dieu kien hien hanh cua nha cung cap.
    """
    # API tra toi da 10 ket qua 1 lan, phai phan trang neu limit > 10
    results: list[dict] = []
    for start in range(1, min(limit, 20) + 1, 10):
        params = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CSE_ID,
            "q": query,
            "searchType": "image",
            "num": min(10, limit - len(results)),
            "start": start,
            "safe": "active",
        }
        async with session.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
        ) as resp:
            resp.raise_for_status()
            payload = await resp.json()
        items = payload.get("items") or []
        results.extend([
            {
                "url": i.get("link", ""),
                "source_url": i.get("image", {}).get("contextLink", ""),
                "title": i.get("title", ""),
                "width": i.get("image", {}).get("width", 0),
                "height": i.get("image", {}).get("height", 0),
            }
            for i in items
        ])
        if len(items) < 10:  # het ket qua, khong phan trang nua
            break
    return results[:limit]


async def _search_serper(session: aiohttp.ClientSession, query: str, limit: int) -> list[dict]:
    async with session.post(
        "https://google.serper.dev/images",
        headers={"X-API-KEY": SERPER_API_KEY},
        json={"q": query, "num": limit},
    ) as resp:
        resp.raise_for_status()
        payload = await resp.json()
    return [
        {
            "url": i.get("imageUrl", ""),
            "source_url": i.get("link", ""),
            "title": i.get("title", ""),
        }
        for i in payload.get("images", [])
    ]


async def _search_brave(session: aiohttp.ClientSession, query: str, limit: int) -> list[dict]:
    async with session.get(
        "https://api.search.brave.com/res/v1/images/search",
        headers={"X-Subscription-Token": BRAVE_API_KEY},
        params={"q": query, "count": limit, "safesearch": "strict"},
    ) as resp:
        resp.raise_for_status()
        payload = await resp.json()
    return [
        {
            "url": i.get("properties", {}).get("url", ""),
            "source_url": i.get("url", ""),
            "title": i.get("title", ""),
        }
        for i in payload.get("results", [])
    ]


async def _search_bing(session: aiohttp.ClientSession, query: str, limit: int) -> list[dict]:
    """Fallback khong can API key - scrape HTML Bing Images."""
    async with session.get(
        "https://www.bing.com/images/search",
        params={"q": query, "count": limit},
        allow_redirects=False,
    ) as resp:
        resp.raise_for_status()
        chunks, size = [], 0
        async for chunk in resp.content.iter_chunked(32768):
            size += len(chunk)
            if size > 3_000_000:
                raise ValueError("Bing response too large")
            chunks.append(chunk)
        raw = b"".join(chunks)
    parser = BingImages()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return parser.results[:limit]


# -- Main search function ----------------------------------------------------

async def search_images(query: str, limit: int = 10) -> list[dict]:
    """
    Tim anh theo query. Uu tien: Google -> Serper -> Brave -> Bing.

    Returns:
        list[dict] voi keys: url, source_url, title
    """
    global GOOGLE_API_KEY,GOOGLE_CSE_ID,SERPER_API_KEY,BRAVE_API_KEY
    GOOGLE_API_KEY=os.environ.get('GOOGLE_API_KEY','');GOOGLE_CSE_ID=os.environ.get('GOOGLE_CSE_ID','')
    SERPER_API_KEY=os.environ.get('SERPER_API_KEY','');BRAVE_API_KEY=os.environ.get('BRAVE_API_KEY','')
    timeout = aiohttp.ClientTimeout(total=20)
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    )
    connector = aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False)

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={"User-Agent": user_agent},
        trust_env=False,
    ) as session:
        try:
            if GOOGLE_API_KEY and GOOGLE_CSE_ID:
                print(f"[Google] Tim: {query!r} ...")
                results = await _search_google(session, query, limit)
            elif SERPER_API_KEY:
                print(f"[Serper] Tim: {query!r} ...")
                results = await _search_serper(session, query, limit)
            elif BRAVE_API_KEY:
                print(f"[Brave]  Tim: {query!r} ...")
                results = await _search_brave(session, query, limit)
            else:
                print(f"[Bing]   Tim: {query!r} (fallback, khong can API key) ...")
                results = await _search_bing(session, query, limit)
        except Exception as exc:
            print(f"  [WARNING] Search that bai: {type(exc).__name__}")
            return []

    # Loc URL hop le + trung
    seen: set[str] = set()
    clean: list[dict] = []
    for r in results:
        url = str(r.get("url", "")).strip()
        if not url or url in seen:
            continue
        try:
            p = urlparse(url)
            if p.scheme not in ("http", "https"):
                continue
        except Exception:
            continue
        seen.add(url)
        clean.append(r)

    return clean[:limit]


# -- Optional: download anh ve local ----------------------------------------

async def download_images(results: list[dict], out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    connector = aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False)
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(
        connector=connector, timeout=timeout, trust_env=False
    ) as session:
        sem = asyncio.Semaphore(4)

        async def _dl(idx: int, item: dict) -> None:
            async with sem:
                url = item["url"]
                try:
                    async with session.get(url, allow_redirects=True) as resp:
                        resp.raise_for_status()
                        raw = await resp.read()
                    ext = Path(urlparse(url).path).suffix[:5] or ".jpg"
                    name = hashlib.sha256(url.encode()).hexdigest()[:16] + ext
                    path = out / f"{idx:02d}_{name}"
                    path.write_bytes(raw)
                    print(f"  OK  Da tai: {path.name}  ({len(raw):,} bytes)")
                except Exception as exc:
                    print(f"  ERR Loi tai anh: {type(exc).__name__}")

        await asyncio.gather(*[_dl(i, item) for i, item in enumerate(results)])


# -- CLI ---------------------------------------------------------------------

async def main() -> None:
    parser = argparse.ArgumentParser(description="Tim anh tren web theo query")
    parser.add_argument("query", nargs="+", help="Cau truy van tim anh")
    parser.add_argument(
        "--limit", type=int, default=10,
        help="So anh toi da (default: 10)"
    )
    parser.add_argument(
        "--download", metavar="DIR",
        help="Tai anh ve thu muc chi dinh (optional)"
    )
    args = parser.parse_args()

    query = " ".join(args.query)
    results = await search_images(query, limit=args.limit)

    if not results:
        print("Khong tim thay anh nao.")
        return

    print(f"\nTim duoc {len(results)} anh cho: {query!r}\n")
    for i, r in enumerate(results, 1):
        # encode safe: tranh crash tren terminal Windows cp1252
        title = (r.get("title") or "")[:70].encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
        url   = r["url"]
        src   = (r.get("source_url") or "")[:80]
        print(f"  [{i:2d}] {title}")
        print(f"       URL: {url}")
        if src:
            print(f"       Src: {src}")
        print()

    if args.download:
        print(f"Dang tai anh ve: {args.download}")
        await download_images(results, args.download)


if __name__ == "__main__":
    asyncio.run(main())
