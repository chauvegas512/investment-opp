"""Structured investment report -> HoHa layouts -> Chromium PDF, in memory."""
from __future__ import annotations
import html
import math
from pathlib import Path

from integration import module


def fmt(value, digits=1):
    if value is None:
        return 'Chưa có'
    try:
        return f'{float(value):,.{digits}f}' if math.isfinite(float(value)) else 'Chưa có'
    except (TypeError, ValueError):
        return str(value)


def price_chart(prices, width=1080, height=360):
    rows = [r for r in prices[-250:] if r.get('close') is not None]
    if len(rows) < 2:
        return '<p>Chưa đủ dữ liệu vẽ biểu đồ.</p>'
    values = [float(r['close']) for r in rows]
    lo, hi = min(values), max(values)
    pad = max((hi - lo) * .1, 1)
    lo, hi = lo-pad, hi+pad
    left, top, cw, ch = 95, 20, width-130, height-70
    points = ' '.join(f'{left+i*cw/(len(values)-1):.1f},{top+ch-(v-lo)*ch/(hi-lo):.1f}' for i, v in enumerate(values))
    grid = ''
    for i in range(5):
        y = top+i*ch/4
        value = hi-i*(hi-lo)/4
        grid += f'<line x1="{left}" x2="{left+cw}" y1="{y}" y2="{y}" stroke="#dae5ea"/><text x="{left-10}" y="{y+5}" text-anchor="end" fill="#526678" font-size="14">{fmt(value,0)}</text>'
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Giá đóng cửa, đơn vị VND mỗi cổ phiếu" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-height:330px;font-family:Arial">{grid}<polyline points="{points}" fill="none" stroke="#087e8b" stroke-width="3"/><text x="{left}" y="{height-12}" font-size="14" fill="#526678">{html.escape(str(rows[0]["date"])[:10])}</text><text x="{left+cw}" y="{height-12}" text-anchor="end" font-size="14" fill="#526678">{html.escape(str(rows[-1]["date"])[:10])}</text></svg>'


def financial_table(bundle):
    from research_v2 import values_for
    rows = bundle.get('annual', [])
    periods = sorted({r['report_period'] for r in rows}, reverse=True)[:4]
    codes = [('revenue','Doanh thu thuần'), ('net_income','LNST hợp nhất'), ('net_income_parent','LNST cổ đông công ty mẹ'), ('gross_profit','Lợi nhuận gộp'),
             ('total_assets','Tổng tài sản'), ('equity','Vốn chủ sở hữu'), ('total_liabilities','Nợ phải trả'),
             ('operating_cash_flow','Dòng tiền kinh doanh')]
    if bundle.get('research',{}).get('quality',{}).get('bank'):
        codes[0]=('net_interest_income','Thu nhập lãi thuần');codes[3]=('total_operating_income','Tổng thu nhập hoạt động')
    lookup = {(p,k):v for p in periods for k,v in values_for(rows,p).items() if v is not None}
    table = [['Chỉ tiêu (tỷ đồng)', *periods]]
    for code, name in codes:
        table.append([name, *[fmt(lookup[(p, code)]/1e9) if (p, code) in lookup else 'Chưa có' for p in periods]])
    return table


def table_html(rows):
    return '<table><thead><tr>' + ''.join('<th>'+html.escape(str(c))+'</th>' for c in rows[0]) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in row)+'</tr>' for row in rows[1:]) + '</tbody></table>'


def slide_html(bundle, title='Báo cáo phân tích cơ hội đầu tư', include_news=True, include_mining=True):
    renderer = module('services.smart_layout_renderer')
    dna_module = module('services.presentation_dna')
    dna = dna_module.PresentationDNA(name='StockLens Investment Research', subject=bundle['ticker'],
        font_family='Arial', layouts=['cover','editorial','comparison','diagram','source_visual'],
        palette=dna_module.DesignPalette(canvas='#FFFFFF', ink='#173244', accent='#087E8B', muted='#F0F6F7'))
    signal, company = bundle['signal'], bundle['company']
    records = []
    def add(heading, lines, role='content'):
        records.append({'title': heading, 'content_markdown': '\n'.join(lines), 'role': role,
                        'takeaway': '', 'visual_form': 'title' if role=='title' else 'editorial'})
    add(bundle['ticker']+' | '+title, [company.get('company_name') or bundle['ticker'],
        'STOCKLENS / BÀI GIỮA KỲ', 'Dữ liệu, phương pháp và bằng chứng có thể kiểm tra.',
        'Ngày tạo: '+bundle['created_at'][:10]], 'title')
    add('01 / Kết quả sàng lọc', [
        signal.get('action_label') or 'Chưa đủ dữ liệu để kết luận',
        'Điểm tổng hợp: '+fmt(signal.get('unified_score'))+'/100; FA: '+fmt(signal.get('fa_score'))+'; TA: '+fmt(signal.get('ta_score')),
        'Độ phủ FA: '+fmt((signal.get('fa_coverage') or 0)*100)+'%; phiên giá: '+str(signal.get('signal_date') or 'Chưa có'),
        'Điểm = 20% FA hiệu dụng + 80% kỹ thuật. Đây là bộ lọc nghiên cứu, không phải dự báo lợi nhuận.',
        signal.get('ranking_note', ''),
        *(bundle.get('warnings', [])[:3])])
    # Charts/tables remain structured and are rendered on dedicated evidence pages.
    records.append({'custom_title':'02 / Giá và dữ liệu giao dịch', 'custom_html': price_chart(bundle.get('prices', [])) +
        '<p>Giá đóng cửa, VND/cổ phiếu. Biểu đồ tối đa 250 phiên gần nhất.</p><p>Giá trị giao dịch ước tính = đóng cửa × khối lượng. Chuỗi giá có thể đã điều chỉnh sự kiện doanh nghiệp.</p>'})
    ta = [('Giá đóng cửa / VND', 'close'), ('MA20 / VND','ma20'), ('MA50 / VND','ma50'), ('MA200 / VND','ma200'), ('Khối lượng / cổ phiếu','volume'), ('Khối lượng / TB20','volume_ratio')]
    add('03 / Bằng chứng kỹ thuật', [name+': '+fmt(signal.get(key),0 if key not in ('volume_ratio',) else 2) for name,key in ta] +
        ['Động lượng 3 / 6 / 12 tháng: '+ ' / '.join(fmt(signal.get(k)*100)+'%' if signal.get(k) is not None else 'Chưa có' for k in ('return_3m','return_6m','return_12m'))])
    records.append({'custom_title':'04 / Báo cáo tài chính doanh nghiệp', 'custom_html':table_html(financial_table(bundle)) +
        '<p>LNST hợp nhất và LNST thuộc cổ đông công ty mẹ được tách riêng. Ô thiếu giữ nguyên “Chưa có”; cuối kỳ không phải ngày công bố.</p>'})
    add('05 / Chất lượng, tăng trưởng và an toàn', [
        'ROE: '+(fmt(signal['roe']*100)+'%' if signal.get('roe') is not None else 'Chưa có'),
        'ROA: '+(fmt(signal['roa']*100)+'%' if signal.get('roa') is not None else 'Chưa có'),
        'Biên lợi nhuận: '+(fmt(signal['profit_margin']*100)+'%' if signal.get('profit_margin') is not None else 'Chưa có'),
        'Tăng trưởng lợi nhuận năm: '+(fmt(signal['profit_growth']*100)+'%' if signal.get('profit_growth') is not None else 'Chưa có'),
        'Nợ vay / vốn chủ: '+fmt(signal.get('debt_equity'),2)+'; thanh toán hiện hành: '+fmt(signal.get('current_ratio'),2),
        'Điều kiện loại trừ: '+str(signal.get('hard_reject_reason') or 'Chưa ghi nhận; cần kiểm tra độ phủ.'),
        'ROE, ROA và biên lợi nhuận sử dụng LNST hợp nhất. EBIT ước tính = LNTT + |chi phí lãi vay|.'])
    if include_news:
        news = bundle.get('news', [])
        for i in range(0, max(1,len(news)), 2):
            subset = news[i:i+2]
            body = ''.join('<article><h3>'+html.escape(n['title'])+'</h3><p>'+html.escape(n.get('summary',''))+'</p><p>'+html.escape(n.get('published_date',''))+' · '+html.escape(n['source'])+'</p><a href="'+html.escape(n['url'], quote=True)+'">'+html.escape(n['url'])+'</a></article>' for n in subset)
            records.append({'custom_title':'06 / Tin tức doanh nghiệp đã xác minh', 'custom_html': body or '<p>Chưa lấy được bài viết có ngày và danh tính doanh nghiệp phù hợp. Không tạo tin tức thay thế.</p>'})
    if include_mining:
        mined = bundle.get('mining', [])
        if not mined:
            add('07 / Báo cáo thường niên và bằng chứng', [
                'Catalog Miner tìm thấy '+str(len(bundle.get('reports',[])))+' báo cáo cho mã '+bundle['ticker']+'.',
                'Danh mục này chưa đồng nghĩa với việc đã tải và phân tích nội dung báo cáo.',
                'Tải PDF ở giao diện StockLens để khai thác từ khóa, trích đoạn và số trang.'])
        for document in mined:
            findings = document.get('findings', [])[:12]
            for i in range(0,max(1,len(findings)),3):
                body = '<p>'+html.escape(document['filename'])+' · SHA-256: '+html.escape(document['sha256'])+'</p>'
                body += ''.join('<article><h3>Trang '+str(f['page'])+' · '+html.escape(f['keyword'])+'</h3><p>'+html.escape(f['snippet'])+'</p></article>' for f in findings[i:i+3])
                body += '<p>'+html.escape(document.get('warning',''))+'</p>'
                records.append({'custom_title':'07 / Khai thác văn bản báo cáo', 'custom_html':body})
    add('08 / Cơ hội, rủi ro và điều kiện theo dõi', [
        'Xu hướng: '+('Giá > MA50 > MA200.' if signal.get('trend_pass') else 'Chưa đạt điều kiện giá > MA50 > MA200.'),
        'Động lượng: '+('Lợi suất 3, 6 và 12 tháng cùng dương.' if signal.get('momentum_pass') else 'Chưa xác nhận động lượng dương trên cả ba kỳ.'),
        'Thị trường: '+('VN-Index trên MA chế độ thị trường.' if signal.get('market_bull') else 'VN-Index chưa xác nhận trạng thái hỗ trợ hoặc thiếu dữ liệu.'),
        'Không biến số lượt xuất hiện từ khóa thành đánh giá tích cực/tiêu cực của doanh nghiệp.',
        'Cần kiểm tra dòng tiền kinh doanh, đòn bẩy, sự kiện doanh nghiệp và báo cáo mới nhất trước khi sử dụng kết quả.',
        'Phân tích thực hiện tại thời điểm tạo báo cáo; không phải bằng chứng hiệu quả backtest.'])
    add('09 / Phương pháp và tính tái lập', [
        'FA kế thừa X10: chất lượng 40%, tăng trưởng 25%, định giá 20%, an toàn 15%.',
        'FA hiệu dụng = 50 + (FA - 50) × độ phủ. Điều kiện loại trừ đưa FA hiệu dụng về 0.',
        'TA: động lượng 30, sức mạnh tương đối 25, xu hướng 25, breakout 15, khối lượng 5 điểm.',
        'Ngưỡng sàng lọc 60/100; thanh khoản ước tính tối thiểu 2 tỷ VND/phiên; thị trường hỗ trợ.',
        'StockLens bổ sung chặn kết luận khi FA không đủ độ phủ, giá quá cũ hoặc kỳ tài chính không phù hợp.',
        'Không có xếp hạng toàn thị trường, giá mục tiêu hay cam kết lợi nhuận trong phân tích một mã.'])
    source_lines = [s['name']+' | kỳ dữ liệu: '+s['as_of']+' | '+s['url'] for s in bundle['sources']]
    source_lines += ['X10: strategy_engine.py và vn_stock_scraper_complete.py.',
                     'vn-annual-report-miner: catalog, news_scraper và GenericFuzzyMatcher.',
                     'HoHa Slide/PDF Core: PresentationDNA và smart_layout_renderer.',
                     'PDF xuất bằng Chromium, không cần API AI trả phí.']
    add('10 / Nguồn và ghi nhận phần mềm', source_lines)
    for i in range(0,len(bundle.get('warnings', [])),5):
        add('Phụ lục / Chất lượng dữ liệu', bundle['warnings'][i:i+5])
    pages = []
    total = len(records)
    for index, record in enumerate(records):
        if 'custom_html' in record:
            page = '<section class="evidence"><div class="eyebrow">STOCKLENS / '+html.escape(bundle['ticker'])+'</div><h1>'+html.escape(record['custom_title'])+'</h1>'+record['custom_html']+f'<footer>{index+1} / {total} · '+html.escape(bundle['created_at'][:10])+'</footer></section>'
        else:
            role = record['role']
            rendered = renderer.render_code_slide(record,dna,[],index,total,role=role)
            if rendered is None:
                rendered = renderer.render_code_fallback_slide(record,dna,[],index,total,role=role)
            page = rendered['html']
        pages.append('<div class="report-page">'+page+'</div>')
    css = '''@page{size:1280px 720px;margin:0}*{box-sizing:border-box}html,body{margin:0;padding:0;font-family:Arial,sans-serif;color:#173244;background:white}.report-page{width:1280px;height:720px;break-after:page;position:relative}.report-page:last-child{break-after:auto}.evidence{width:1280px;height:720px;padding:50px 64px;position:relative;background:white}.eyebrow{font-size:14px;color:#087e8b;letter-spacing:2px}h1{font-size:34px;margin:20px 0 28px}h3{font-size:20px;margin:8px 0}p{font-size:18px;line-height:1.45}table{width:100%;border-collapse:collapse;font-size:16px}td,th{padding:10px;border-bottom:1px solid #d9e5e9;text-align:right}td:first-child,th:first-child{text-align:left}th{background:#e8f3f4}article{padding:10px 0;border-bottom:1px solid #dae5ea}article p{font-size:17px;margin:8px 0}a{color:#087e8b;overflow-wrap:anywhere;font-size:14px}footer{position:absolute;bottom:30px;left:64px;color:#526678;font-size:13px}'''
    return '<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>'+html.escape(bundle['ticker']+' - StockLens')+'</title><style>'+css+'</style></head><body>'+''.join(pages)+'</body></html>'


def report_html(bundle, title='Báo cáo phân tích cơ hội đầu tư', include_news=True, include_mining=True, horizon='medium', risk='balanced', depth='full',include_images=True):
    from research_report import render
    return render(bundle,title,include_news,include_mining,horizon,risk,depth,include_images)


def pdf_bytes(markup):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        # Reuse the installed Edge browser; Chromium is the portable fallback.
        try:
            browser = pw.chromium.launch(channel='msedge', headless=True)
        except Exception:
            browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={'width':1280,'height':720})
            page.set_content(markup, wait_until='load')
            page.evaluate('document.fonts.ready')
            return page.pdf(print_background=True, prefer_css_page_size=True)
        finally:
            browser.close()
