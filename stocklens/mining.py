"""Use original arminer catalog, article extractor and exact keyword matcher."""
from __future__ import annotations
from functools import lru_cache
from datetime import datetime
import hashlib
from zoneinfo import ZoneInfo

from integration import MINER, clean, module


@lru_cache(maxsize=1)
def catalog():
    return module('arminer.data.catalog').UnifiedCatalog(workspace_root=MINER)


def reports_for(ticker):
    rows = catalog().search(ticker=ticker, limit=30)
    # The catalog uses substring search for a single token; require exact ticker here.
    return clean([{k: row.get(k) for k in ('record_id', 'ticker', 'year', 'file_name', 'source', 'status', 'file_size_mb','website','ir_portal','company_short_name','archive_period','relative_path')}
                  for row in rows if row.get('ticker', '').upper() == ticker])


def latest_news(ticker, company_name,short_name=None,website=None):
    miner = module('arminer.data.news_scraper')
    # Limited number of verified articles rather than crawling every news portal.
    from company_identity import headline_matches
    links=[]
    from concurrent.futures import ThreadPoolExecutor
    def discover(scraper):
        try:return scraper.get_article_links(ticker,max_links=5)
        except Exception:return []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for found in pool.map(discover,[miner.CafeFScraper,miner.VnEconomyScraper,miner.TinNhanhCKScraper]):links.extend(found)
    if website:
        try:
            import requests
            # Skip unavailable issuer hosts before the Miner's multi-sitemap discovery.
            requests.get(website,timeout=3,headers={'User-Agent':'Mozilla/5.0'}).raise_for_status()
            class Resolver:
                def get_company(self,t):return {'name':company_name,'short_name':short_name or ticker,'website':website}
                def resolve_website(self,t):return website
            links.extend(miner.CompanyWebsiteScraper(Resolver()).get_article_links(ticker,max_links=5))
        except Exception:pass
    links=list(dict.fromkeys(links))[:16]
    import requests
    def extract(url):
        try:
            resp = requests.get(url, timeout=12, headers={'User-Agent': 'Mozilla/5.0'})
            resp.raise_for_status()
            article = miner.UniversalNewsExtractor.extract_from_html(resp.text, url)
            if not article:
                return None
            if not miner.is_company_confirmed(article, ticker, company_name, short_name or company_name, [ticker,short_name or ticker]):
                return None
            import re
            # An incidental mention in a market roundup is not company-specific news.
            from urllib.parse import urlparse
            official_host=(urlparse(website).hostname or '').removeprefix('www.') if website else ''
            host=(urlparse(url).hostname or '').removeprefix('www.')
            official=bool(official_host and (host==official_host or host.endswith('.'+official_host)))
            if not official and not headline_matches(article['title'],ticker,company_name,short_name):
                return None
            published = article.get('published_date', '')
            # Do not label articles with an unknown or future date as recent news.
            import pandas as pd
            date = pd.to_datetime(published, errors='coerce', utc=True)
            now = pd.Timestamp.now(tz='UTC')
            if pd.isna(date) or date > now or (now - date).days > 90:
                return None
            title=' '.join(article['title'].split()[:25])
            if len(article['title'].split())>25:title+='…'
            from urllib.parse import urlparse
            return {'title': title, 'url': url, 'source': urlparse(url).hostname+' / arminer',
                         'published_date': published, 'summary': 'Đọc nguồn gốc để kiểm tra diễn biến và bối cảnh; chưa suy luận tác động đến định giá.',
                         'company_confirmed': True,'official_issuer':official}
        except requests.RequestException:
            return None
        except (ValueError,KeyError,TypeError):
            return None
    with ThreadPoolExecutor(max_workers=4) as pool:rows=[r for r in pool.map(extract,links) if r]
    import pandas as pd
    return sorted(rows,key=lambda n:pd.to_datetime(n['published_date'],utc=True),reverse=True)[:6]


def mine_pdf(content, keywords, filename):
    import pymupdf
    dictionary = module('arminer.core.dictionary').Dictionary(name='StockLens Evidence')
    terms = list(dict.fromkeys(k.strip().lower() for k in keywords.split(',') if k.strip()))[:20]
    if not terms or any(len(k) > 80 for k in terms):
        raise ValueError('Nhập 1-20 từ khóa, mỗi từ khóa tối đa 80 ký tự.')
    dictionary.add_category('investment', keywords=[{'keyword': k, 'language': 'vi'} for k in terms])
    matcher = module('arminer.mining.matcher').GenericFuzzyMatcher(dictionary)
    snippets=module('arminer.mining.snippet_extractor').SnippetExtractor(context_chars=120)
    with pymupdf.open(stream=content, filetype='pdf') as pdf:
        if pdf.is_encrypted:
            raise ValueError('PDF có mật khẩu; hãy dùng bản đã mở khóa.')
        if pdf.page_count > 500:
            raise ValueError('PDF vượt giới hạn 500 trang.')
        findings, text_pages, all_matches, total_words = [], 0, [], 0
        for page_no, page in enumerate(pdf):
            text = page.get_text()
            total_words += len(text.split())
            if len(text.strip()) >= 30:
                text_pages += 1
            matches=matcher.search(text,use_fuzzy=False)
            all_matches.extend(matches)
            from company_identity import norm
            toc=any(t in norm(text[:1500]) for t in ['muc luc','table of contents'])
            for match in matches:
                pos = match['position']
                snippet=' '.join(snippets.extract_snippet(text,pos,len(match['keyword_canonical'])).split())
                score=(3 if page_no>=8 else 0)+(2 if len(snippet.split())>=25 else 0)+(1 if '.' in snippet else 0)-(8 if toc else 0)
                score-=2 if sum(c.isdigit() for c in snippet)>len(snippet)*.12 else 0
                findings.append({'keyword':match['keyword_canonical'],'page':page_no+1,'snippet':snippet,'context_rank':score})
                if len(findings)>100:findings=sorted(findings,key=lambda f:f['context_rank'],reverse=True)[:80]
        findings=sorted(findings,key=lambda f:(-f['context_rank'],f['page']))[:80]
        usable=text_pages>=max(1,pdf.page_count*.25)
        metrics=module('arminer.mining.metrics').MetricsCalculator().calculate(all_matches,total_words) if usable else None
        return {'filename': filename[:160], 'sha256': hashlib.sha256(content).hexdigest(),
                'pages': pdf.page_count, 'text_pages': text_pages, 'findings': findings,
                'total_words':total_words,'metrics':metrics,'keywords':terms,
                'metrics_status':'TEXT_MINED' if text_pages==pdf.page_count else 'PARTIAL_TEXT' if usable else 'OCR_REQUIRED',
                'findings_truncated':len(all_matches)>len(findings),
                'normalization_method':'Tổng lượt khớp / số token tách khoảng trắng × 10.000; toàn bộ lớp văn bản, không chỉ 80 trích đoạn lưu.',
                'method': 'arminer exact keyword matching; có trang và trích đoạn để kiểm tra',
                'warning': f'{pdf.page_count-text_pages}/{pdf.page_count} trang không đủ lớp văn bản; trang ảnh cần OCR nếu muốn khai phá.' if text_pages < pdf.page_count else '',
                'uploaded_at': datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(timespec='seconds')}
