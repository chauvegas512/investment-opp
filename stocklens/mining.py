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
    return clean([{k: row.get(k) for k in ('record_id', 'ticker', 'year', 'file_name', 'source', 'status', 'file_size_mb')}
                  for row in rows if row.get('ticker', '').upper() == ticker])


def latest_news(ticker, company_name):
    miner = module('arminer.data.news_scraper')
    # Limited number of verified articles rather than crawling every news portal.
    links = miner.CafeFScraper.get_article_links(ticker, max_links=6)
    import requests
    rows = []
    for url in links[:6]:
        try:
            resp = requests.get(url, timeout=12, headers={'User-Agent': 'Mozilla/5.0'})
            resp.raise_for_status()
            article = miner.UniversalNewsExtractor.extract_from_html(resp.text, url)
            if not article:
                continue
            if not miner.is_company_confirmed(article, ticker, company_name, company_name, [ticker]):
                continue
            import re
            # An incidental mention in a market roundup is not company-specific news.
            if not re.search(r'(?<![A-Z0-9])'+re.escape(ticker)+r'(?![A-Z0-9])',article['title'],re.I) and company_name.casefold() not in article['title'].casefold():
                continue
            published = article.get('published_date', '')
            # Do not label articles with an unknown or future date as recent news.
            import pandas as pd
            date = pd.to_datetime(published, errors='coerce', utc=True)
            now = pd.Timestamp.now(tz='UTC')
            if pd.isna(date) or date > now or (now - date).days > 90:
                continue
            if any(row['url']==url for row in rows):continue
            title=' '.join(article['title'].split()[:25])
            if len(article['title'].split())>25:title+='…'
            rows.append({'title': title, 'url': url, 'source': 'CafeF / arminer',
                         'published_date': published, 'summary': 'Đọc nguồn gốc để kiểm tra diễn biến và bối cảnh; chưa suy luận tác động đến định giá.',
                         'company_confirmed': True})
        except requests.RequestException:
            continue
    return rows[:4]


def mine_pdf(content, keywords, filename):
    import pymupdf
    dictionary = module('arminer.core.dictionary').Dictionary(name='StockLens Evidence')
    terms = list(dict.fromkeys(k.strip().lower() for k in keywords.split(',') if k.strip()))[:20]
    if not terms or any(len(k) > 80 for k in terms):
        raise ValueError('Nhập 1-20 từ khóa, mỗi từ khóa tối đa 80 ký tự.')
    dictionary.add_category('investment', keywords=[{'keyword': k, 'language': 'vi'} for k in terms])
    matcher = module('arminer.mining.matcher').GenericFuzzyMatcher(dictionary)
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
            for match in matches:
                if len(findings) >= 80:continue
                pos = match['position']
                findings.append({'keyword': match['keyword_canonical'], 'page': page_no + 1,
                                 'snippet': ' '.join(text[max(0, pos-100):pos+240].split())})
        metrics=module('arminer.mining.metrics').MetricsCalculator().calculate(all_matches,total_words)
        return {'filename': filename[:160], 'sha256': hashlib.sha256(content).hexdigest(),
                'pages': pdf.page_count, 'text_pages': text_pages, 'findings': findings,
                'total_words':total_words,'metrics':metrics,'keywords':terms,
                'findings_truncated':len(all_matches)>len(findings),
                'normalization_method':'Tổng lượt khớp / số token tách khoảng trắng × 10.000; toàn bộ lớp văn bản, không chỉ 80 trích đoạn lưu.',
                'method': 'arminer exact keyword matching; có trang và trích đoạn để kiểm tra',
                'warning': f'{pdf.page_count-text_pages}/{pdf.page_count} trang không đủ lớp văn bản; trang ảnh cần OCR nếu muốn khai phá.' if text_pages < pdf.page_count else '',
                'uploaded_at': datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(timespec='seconds')}
