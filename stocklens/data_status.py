"""Trạng thái từng phần: dữ liệu có, chưa công bố/nguồn thiếu, chưa xác minh, không áp dụng."""
from datetime import datetime
from zoneinfo import ZoneInfo
def build(b):
    q=b.get('research',{}).get('quality',{});c=b.get('company',{});docs=b.get('annual_insights',[]);news=b.get('news',[])
    now=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'));price=b.get('signal',{}).get('signal_date')
    rows=[{'key':'prices','label':'Giá chốt phiên','status':'AVAILABLE' if price else 'MISSING','detail':price or 'Nguồn chưa có giá hợp lệ'},
        {'key':'financials','label':'BCTC năm / quý','status':'AVAILABLE' if q.get('latest_annual') and q.get('latest_quarter') else 'SOURCE_INCOMPLETE','detail':f"{q.get('latest_annual') or 'chưa có'} / {q.get('latest_quarter') or 'chưa có'}; kỳ mới chỉ dùng khi nguồn đã cung cấp"},
        {'key':'annual_report','label':'Khai phá BCTN','status':'OCR_REQUIRED' if docs and any(d.get('metrics_status')=='OCR_REQUIRED' for d in docs) else 'PARTIAL_TEXT' if docs and any(d.get('metrics_status')=='PARTIAL_TEXT' for d in docs) else 'AVAILABLE' if docs and any(d.get('metrics') is not None for d in docs) else 'OCR_REQUIRED' if docs else 'SOURCE_UNAVAILABLE','detail':f"{len(docs)} báo cáo đã xử lý; {sum(d.get('text_pages',0) for d in docs)}/{sum(d.get('pages',0) for d in docs)} trang có văn bản; {len(b.get('reports',[]))} mục catalog"},
        {'key':'news','label':'Bản tin doanh nghiệp','status':'AVAILABLE' if news else 'NO_RECENT_VERIFIED_NEWS','detail':f'{len(news)} bài có nguồn và ngày; không có bài không có nghĩa doanh nghiệp không hoạt động'},
        {'key':'publication','label':'Ngày công bố BCTC','status':'SOURCE_NOT_PROVIDED' if any(not r.get('published_date') for r in b.get('annual',[])) else 'AVAILABLE','detail':'VCI không trả ngày công bố cho một số dòng; không dùng cuối kỳ thay ngày công bố'},
        {'key':'sector','label':'Chỉ tiêu chuyên ngành','status':'NEEDS_ISSUER_VERIFICATION' if q.get('bank') else 'AVAILABLE_COMPONENTS','detail':'NIM/NPL/bao phủ/CAR cần công bố ngân hàng đúng kỳ' if q.get('bank') else 'Chỉ tính khi tử/mẫu và định nghĩa phù hợp ngành'}]
    return {'checked_at':now.isoformat(timespec='seconds'),'datasets':rows,'price_date':price,'financial_fetched_at':max((r.get('fetched_at','') for r in b.get('annual',[])),default='')}
