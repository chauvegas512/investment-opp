"""Báo cáo nghiên cứu A4: dữ kiện, điều kiện đánh giá và nguồn có thể truy vết."""
from datetime import date,datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import threading
from jinja2 import Environment,FileSystemLoader,select_autoescape
from integration import module
from research import enrich
from research_v2 import values_for

LOCK=threading.Lock();HERE=Path(__file__).parent

def render(bundle,title,include_news=True,include_mining=True,horizon='medium',risk='balanced',depth='full',include_images=True):
    bundle=enrich(bundle)
    from reports import fmt,financial_table
    import deep_charts
    from report_modules import build
    from company_images import for_company
    images=for_company(bundle['ticker'],inline=True) if include_images else []
    schema=module('report_engine.schema');charts=module('report_engine.charts')
    periods=sorted({str(r['report_period']) for r in bundle['annual']})[-4:]
    values={p:values_for(bundle['annual'],p) for p in periods}
    bank=bundle['research']['quality']['bank']
    finance_keys=[('Thu nhập lãi thuần','net_interest_income'),('LNST hợp nhất','net_income')] if bank else [('Doanh thu','revenue'),('LNST hợp nhất','net_income')]
    fundamental=schema.Fundamentals(periods=periods,
        metrics={label:[values[p].get(key)/1e9 if values[p].get(key) is not None else None for p in periods] for label,key in finance_keys},
        units={label:'tỷ VND' for label,key in finance_keys},chart_keys=[label for label,key in finance_keys])
    r=bundle['research']
    modules=build(bundle,include_mining)
    with LOCK:
        visuals={'technical':deep_charts.strategy_price(r['technical']),'health':deep_charts.health(modules['health_trend']),
                 'relative':deep_charts.relative(bundle.get('x10_context',{}),bundle['ticker']),'finance':charts.fundamentals_chart(fundamental)}
    qperiods=sorted({str(r['report_period']) for r in bundle.get('quarterly',[])})[-4:]
    qvalues={p:values_for(bundle['quarterly'],p) for p in qperiods}
    qtable=[['Chỉ tiêu (tỷ VND)',*qperiods]]
    for key,label in [('net_interest_income','Thu nhập lãi thuần') if bank else ('revenue','Doanh thu thuần'),('net_income','LNST hợp nhất'),('net_income_parent','LNST cổ đông mẹ'),('operating_cash_flow','Dòng tiền kinh doanh')]:
        qtable.append([label,*[fmt(qvalues[p][key]/1e9) if qvalues[p].get(key) is not None else 'Chưa có' for p in qperiods]])
    sections=list(range(1,9)) if depth=='full' else [1,2,3,8]
    env=Environment(loader=FileSystemLoader(HERE/'templates'),autoescape=select_autoescape(['html']))
    env.filters['fmt']=fmt;env.filters['pct']=lambda v:fmt(v*100)+'%' if v is not None else 'Chưa có'
    env.filters['bn']=lambda v:fmt(v/1e9) if v is not None else 'Chưa có'
    horizons={'short':('Ngắn hạn / 1-3 tháng','Ưu tiên giá, khối lượng và xác nhận thị trường; kỳ tài chính là điều kiện nền.'),
        'medium':('Trung hạn / 3-12 tháng','Kết hợp xu hướng với lợi nhuận mẹ, dòng tiền và khả năng thực hiện sự kiện kinh doanh.'),
        'long':('Dài hạn / trên 12 tháng','Ưu tiên chất lượng tăng trưởng và dòng tiền nhiều kỳ; điểm X10 thiên về kỹ thuật chưa đủ làm luận điểm dài hạn.')}
    risks={'cautious':('Thận trọng','Ưu tiên xử lý các khoảng trống dữ liệu và đợi nhiều nguồn xác nhận trước khi nâng mức tin cậy.'),
        'balanced':('Cân bằng','Đánh giá đồng thời tài chính, định giá và kỹ thuật; không nâng kết luận từ một chỉ báo riêng.'),
        'active':('Chủ động','Theo dõi tín hiệu mỗi phiên; tốc độ cập nhật không thay thế yêu cầu kiểm chứng dữ liệu.')}
    return env.get_template('research.html').render(b=bundle,s=bundle['signal'],c=bundle['company'],r=r,v=visuals,title=title,
        sections=sections,total=len(sections),annual_table=financial_table(bundle),quarter_table=qtable,m=modules,x=bundle.get('x10_context',{}),
        news=bundle.get('news',[]) if include_news else [],mining=bundle.get('mining',[]) if include_mining else [],
        horizon=horizons[horizon],risk=risks[risk],generated_at=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%Y-%m-%d %H:%M'),
        f=bundle.get('issuer_disclosures',{}),images=images,
        logo=next((i for i in images if i['role']=='logo'),None),photos=[i for i in images if i['role']=='company'],
        event_image=next((i for i in images if i['role']=='event'),None))
