"""Evidence bundle and conservative adapter to X10's existing FA/TA engine."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
import re
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from integration import BOT, clean, module

TZ = ZoneInfo('Asia/Ho_Chi_Minh')
CONFIG = json.loads((BOT / 'strategy_config.json').read_text(encoding='utf-8'))
LABELS = {'BUY': 'Đạt điều kiện sàng lọc', 'WATCH': 'Tiếp tục theo dõi',
          'DATA_REVIEW': 'Chưa đủ dữ liệu để kết luận', 'HOLD': 'Theo dõi vị thế', 'EXIT': 'Cảnh báo rủi ro'}

# Exact, statement-qualified aliases; do not collapse gross sales with net sales,
# or group net profit with profit attributable to the parent company's owners.
VCI_ALIASES = {
    'income_statement': {
        'net_sales':'revenue', 'sales':'gross_revenue', 'gross_profit':'gross_profit',
        'cost_of_sales':'cogs', 'interest_expenses':'interest_expense',
        'net_accounting_profit_loss_before_tax':'profit_before_tax',
        'net_profit_loss_after_tax':'net_income',
        'attributable_to_parent_company':'net_income_parent',
        'eps_basic_vnd':'eps',
    },
    'balance_sheet': {
        'total_assets':'total_assets', 'owners_equity':'equity', 'liabilities':'total_liabilities',
        'cash_and_cash_equivalents':'cash_and_cash_equivalents', 'current_assets':'current_assets',
        'current_liabilities':'current_liabilities', 'short_term_borrowings':'short_term_borrowings',
        'long_term_borrowings':'long_term_borrowings',
        'minority_interests':'non_controlling_equity','minority_interest':'non_controlling_equity',
        'total_liabilities':'total_liabilities',
    },
    'cash_flow': {
        'net_cash_inflows_outflows_from_operating_activities':'operating_cash_flow',
        'net_cash_from_operating_activities':'operating_cash_flow',
        'depreciation_and_amortization':'depreciation_and_amortization',
        'purchases_of_fixed_assets_and_other_long_term_assets':'capex',
    },
}


def normalize_financial_frame(frame, ticker, statement, period):
    periods = [c for c in frame if re.fullmatch(r'\d{4}([- /]?Q[1-4])?', str(c), re.I)]
    if not periods or 'item_id' not in frame:
        raise ValueError('Unsupported financial schema')
    rows=[]
    for index, row in frame.reset_index(drop=True).iterrows():
        raw=str(row['item_id'])
        code=VCI_ALIASES[statement].get(raw,f'raw_vci:{statement}:{raw}:{index}')
        name=str(row.get('item') or raw)
        for column in periods:
            value=pd.to_numeric(row.get(column),errors='coerce')
            if pd.notna(value) and np.isfinite(value):
                rows.append({'ticker':ticker,'statement':statement,'report_period':str(column),
                    'period_type':'annual' if period=='year' else 'quarterly','published_date':None,
                    'item_code':code,'raw_item_code':raw,'item_name':name,'value':float(value),
                    'unit':'VND/share' if code=='eps' else 'VND','source':'vnstock VCI',
                    'fetched_at':datetime.now(TZ).isoformat(timespec='seconds'),
                    'period_end':str(column)[:4]+('-12-31' if 'Q' not in str(column) else {1:'-03-31',2:'-06-30',3:'-09-30',4:'-12-31'}[int(str(column)[-1])])})
    return rows


def ticker_of(value):
    value = str(value).strip().upper()
    if not re.fullmatch(r'[A-Z][A-Z0-9]{1,9}', value):
        raise ValueError('Mã cổ phiếu phải gồm 2-10 ký tự chữ/số, ví dụ FPT, VCB, SSI.')
    return value


def annual_wide(rows):
    if rows.empty:
        return pd.DataFrame()
    data = rows.copy()
    data['period_end'] = data['report_period'].map(lambda p: str(p)[:4] + '-12-31')
    data['value'] = pd.to_numeric(data['value'], errors='coerce')
    result=data.pivot_table(index=['ticker', 'period_end'], columns='item_code', values='value', aggfunc='first').reset_index()
    # An explicit accounting estimate, never relabel operating profit as EBIT.
    if 'ebit' not in result and {'profit_before_tax','interest_expense'} <= set(result):
        result['ebit']=result['profit_before_tax']+result['interest_expense'].abs()
    if 'is_ebitda' not in result and {'ebit','depreciation_and_amortization'} <= set(result):
        result['is_ebitda']=result['ebit']+result['depreciation_and_amortization']
    return result


def finance_rows(ticker, period):
    """VCI financials in VND. KBS is excluded after a verified period mismatch."""
    from vnstock import Finance
    scraper = module('vn_stock_scraper_complete')
    diagnostics = [{'module':'financials','source':'KBS','status':'EXCLUDED_PERIOD_MISMATCH',
                    'detail':'FPT Head year 2025 carried 2022 values during integration QA; no automatic relabelling.'}]
    for source in ('VCI',):
        rows = []
        try:
            scraper.wait_for_community_slot()
            finance = Finance(source=source, symbol=ticker, period=period, get_all=True)
            for statement in ('income_statement', 'balance_sheet', 'cash_flow'):
                try:
                    scraper.wait_for_community_slot()
                    frame = getattr(finance, statement)()
                    if not isinstance(frame, pd.DataFrame) or frame.empty:
                        continue
                    normalized=normalize_financial_frame(frame,ticker,statement,period)
                    rows.extend(normalized)
                    diagnostics.append({'module':statement,'source':source,'status':'OK','rows':len(normalized)})
                except Exception as exc:
                    diagnostics.append({'module': statement, 'source': source, 'status': type(exc).__name__})
        except Exception as exc:
            diagnostics.append({'module': 'financials', 'source': source, 'status': type(exc).__name__})
        if rows:
            return pd.DataFrame(rows), diagnostics
    return pd.DataFrame(), diagnostics


def normalize_prices(prices):
    data = prices.copy()
    if data.empty:
        return data
    for field in ('open', 'high', 'low', 'close', 'volume'):
        data[field] = pd.to_numeric(data[field], errors='coerce')
    valid = ((data['close'] > 0) & (data['volume'] >= 0)
             & (data['low'] <= data[['open', 'close']].min(axis=1))
             & (data['high'] >= data[['open', 'close']].max(axis=1)))
    data = data.loc[valid].drop_duplicates(['ticker', 'date'], keep='last').sort_values('date')
    data['adjusted_close'] = pd.to_numeric(data.get('adjusted_close', data['close']), errors='coerce')
    # DNSE and the vnstock fallback supply adjusted price history in the X10 adapter.
    data['analysis_ready'] = data['adjusted_close'].notna()
    data['trading_value'] = data['close'] * data['volume']
    return data


def evaluate(company, prices, benchmark, annual, now=None):
    engine = module('strategy_engine')
    now = now or datetime.now(TZ)
    prices, benchmark = normalize_prices(prices), normalize_prices(benchmark)
    warnings = []
    if prices.empty:
        return {'ticker': company['ticker'], 'final_action': 'DATA_REVIEW', 'fa_coverage': 0,
                'decision_reason': 'Không có chuỗi giá hợp lệ.'}, ['Không lấy được giá lịch sử.']
    fa = engine.build_signal_fa(pd.DataFrame([company]), annual_wide(annual), CONFIG)
    ta = engine.build_ta(prices, benchmark, CONFIG)
    if ta.empty:
        return {'ticker': company['ticker'], 'final_action': 'DATA_REVIEW'}, ['Chuỗi giá không đủ để phân tích.']
    signal = engine.combine(fa, ta, CONFIG).iloc[0].to_dict()
    latest = pd.Timestamp(prices['date'].iloc[-1]).date()
    age = (now.date() - latest).days
    if age > 7 or age < 0:
        warnings.append(f'Giá thuộc phiên {latest}; cần kiểm tra độ mới trước khi quyết định.')
    if signal.get('fa_status') != 'READY':
        warnings.append('Báo cáo tài chính chưa đủ độ phủ; không phát kết luận đạt điều kiện đầu tư.')
    if annual.empty:
        warnings.append('Chưa lấy được báo cáo tài chính năm.')
    else:
        latest_year = pd.to_numeric(annual['report_period'].astype(str).str[:4], errors='coerce').max()
        if latest_year < now.year - 2 or latest_year >= now.year:
            warnings.append('Kỳ tài chính năm cần kiểm tra: dữ liệu quá cũ hoặc năm chưa kết thúc.')
        wide=annual_wide(annual)
        for _,row in wide.iterrows():
            assets,liabilities,equity=(row.get(k,np.nan) for k in ('total_assets','total_liabilities','equity'))
            if all(pd.notna(v) for v in (assets,liabilities,equity)) and assets>0:
                if abs(assets-liabilities-equity)/assets>.01:
                    warnings.append('Bảng cân đối chưa khớp tài sản = nợ phải trả + vốn chủ; cần đối chiếu nguồn.')
                    break
    if benchmark.empty:
        warnings.append('Thiếu VN-Index để so sánh sức mạnh tương đối và xu hướng thị trường.')
    if warnings:
        signal['original_screen_action'] = signal['final_action']
        signal['final_action'] = 'DATA_REVIEW'
    signal['universe_rank'] = None
    signal['ranking_note'] = 'Phân tích một mã; chưa xếp hạng Top 30 toàn thị trường.'
    signal['action_label'] = LABELS.get(signal['final_action'], signal['final_action'])
    signal['liquidity_note'] = 'Giá trị giao dịch ước tính bằng giá đóng cửa × khối lượng; không phải giá trị khớp lệnh thực.'
    signal['accounting_note'] = 'LNST hợp nhất dùng cho ROE/ROA, biên lợi nhuận và tăng trưởng; LNST thuộc cổ đông công ty mẹ hiển thị riêng. EBIT ước tính = LNTT + |chi phí lãi vay|.'
    return clean(signal), warnings


def fetch_bundle(ticker, progress=lambda message: None):
    ticker = ticker_of(ticker)
    scraper = module('vn_stock_scraper_complete')
    from database import archive, comparison
    cached=archive(ticker)
    now = datetime.now(TZ)
    start = now - timedelta(days=850)
    def get_prices(symbol):
        try:
            return scraper.fetch_ta_daily_range(symbol,start,now)
        except Exception as exc:
            return pd.DataFrame(),[{'source':'live price','ticker':symbol,'status':type(exc).__name__}]
    progress('Lấy giá cổ phiếu và VN-Index từ bộ thu thập X10…')
    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(get_prices, ticker)
        benchmark, benchmark_diag = get_prices('VNINDEX')
        prices, price_diag = future.result()
    if prices.empty:
        prices=cached.get('price_daily',pd.DataFrame())
        price_diag.append({'source':'X10 SQLite','status':'ARCHIVE_FALLBACK'})
    if benchmark.empty:
        benchmark=cached.get('benchmark_daily',pd.DataFrame())
    if prices.empty:
        raise ValueError('Không lấy được giá của mã này. Kiểm tra mã và kết nối nguồn dữ liệu.')
    progress('Lấy thông tin doanh nghiệp và báo cáo tài chính…')
    try:
        company, meta_diag = scraper.fetch_metadata(ticker)
    except Exception as exc:
        company={'ticker':ticker}
        meta_diag=[{'source':'metadata','status':type(exc).__name__}]
    company={**cached.get('company',{}),**{k:v for k,v in company.items() if v is not None}}
    try:
        from company_adapter import fetch
        details=fetch(ticker)
        company.update({k:v for k,v in details.items() if v is not None})
        meta_diag.append({'source':'VCI overview','status':'NORMALIZED_DUPLICATE_COLUMNS'})
    except Exception as exc:
        meta_diag.append({'source':'VCI overview','status':type(exc).__name__})
    if not company.get('company_name'):
        company['company_name'] = ticker
    annual, fa_diag = finance_rows(ticker, 'year')
    quarterly, fq_diag = finance_rows(ticker, 'quarter')
    from financial_adapter import miner_rows
    try:
        miner_financials=miner_rows(ticker)
    except Exception:
        miner_financials=pd.DataFrame()
    miner_conflicts=comparison(annual,miner_financials)
    conflicts=comparison(annual,cached.get('financial_annual',pd.DataFrame()))
    archive_finance=False
    if annual.empty:
        annual=cached.get('financial_annual',pd.DataFrame())
        if annual.empty: annual=miner_financials
        archive_finance=not annual.empty
    if quarterly.empty:
        quarterly=cached.get('financial_quarterly',pd.DataFrame())
    progress('Tính điểm FA/TA, kiểm tra độ phủ và ngày dữ liệu…')
    signal, warnings = evaluate(company, prices, benchmark, annual, now)
    if archive_finance:
        signal['final_action']='DATA_REVIEW'
        signal['action_label']='Cần đối chiếu BCTC lưu trữ'
        warnings.append('BCTC lấy từ SQLite lưu trữ; chưa đối chiếu kỳ và định nghĩa lợi nhuận với VCI. Không dùng để kết luận đầu tư.')
    if conflicts:
        warnings.append('Đã phát hiện chênh lệch BCTC trong SQLite; sử dụng VCI và giữ riêng số liệu lưu trữ để truy vết.')
    bank='ngân hàng' in str(company.get('industry','')).lower() or 'ngân hàng' in str(company.get('sector','')).lower()
    if bank:
        signal['final_action']='DATA_REVIEW'
        signal['action_label']='Ngân hàng: cần đánh giá chuyên ngành'
        for key in ('debt_equity','current_ratio','net_debt_ebitda','fa_score','unified_score'):
            signal[key]=None
        warnings.append('Không áp dụng FA doanh nghiệp thường cho ngân hàng. Cần NIM, nợ xấu, bao phủ nợ xấu và CAR trước khi kết luận.')
    prices = normalize_prices(prices)
    diagnostics = clean(price_diag + benchmark_diag + meta_diag + fa_diag + fq_diag)
    sources = [
        {'name': str(prices['source'].iloc[-1])+' - dữ liệu giá', 'url': 'https://www.dnse.com.vn/', 'as_of': str(prices['date'].iloc[-1])},
        {'name': 'VCI qua Vnstock - báo cáo tài chính', 'url': 'https://trading.vietcap.com.vn/',
         'as_of': str(annual['report_period'].max()) if not annual.empty else 'Chưa có'},
    ]
    progress('Tra cứu báo cáo thường niên trong catalog Miner…')
    from mining import reports_for, latest_news
    try:
        reports = reports_for(ticker)
    except Exception as exc:
        reports = []
        warnings.append('Catalog báo cáo chưa sẵn sàng: ' + type(exc).__name__)
    progress('Khai thác tin doanh nghiệp có nguồn từ Miner…')
    try:
        news = latest_news(ticker, company.get('company_name') or ticker)
    except Exception as exc:
        news = []
        warnings.append('Nguồn tin chưa sẵn sàng: ' + type(exc).__name__)
    if not news:
        warnings.append('Chưa xác minh được tin doanh nghiệp gần đây; không suy diễn tác động tin tức.')
    bundle=clean({'ticker': ticker, 'company': company, 'signal': signal,
                  'created_at': now.isoformat(timespec='seconds'), 'price_unit': 'VND/cổ phiếu',
                  'prices': prices.tail(420).to_dict('records'), 'benchmark': normalize_prices(benchmark).tail(420).to_dict('records'),
                  'annual': annual.to_dict('records'), 'quarterly': quarterly.to_dict('records'),
                  'news': news, 'reports': reports, 'mining': [], 'warnings': warnings,
                  'diagnostics': diagnostics, 'sources': sources, 'methodology': CONFIG,
                  'database_audit':{'path':str(cached and 'dtata  full toping/analysis_data/stocks_analysis.sqlite' or ''),'read_only':True,'conflicts':conflicts,'archive_finance':archive_finance}})
    bundle['miner_financial_audit']={'rows':clean(miner_financials.to_dict('records')),'conflicts':miner_conflicts,
        'note':'BCTC Miner dùng đối chiếu lịch sử; không tự bổ sung số liệu năm/quý hiện tại bằng dự đoán.'}
    from research import enrich
    return enrich(bundle)
