"""Điều kiện nghiên cứu rút từ dữ kiện đã lưu, không tạo dự báo hoặc xác suất."""
def build(b):
    r=b['research'];t=r['technical'].get('latest',{});m=r['metrics'];s=b['signal'];f=b.get('issuer_disclosures',{})
    def price(k):
        value=t.get(k)
        return f'{value:,.0f} VND' if value is not None else 'chưa đủ dữ liệu'
    business=(f"Doanh thu năm {m['year']} tăng {m['revenue_growth']*100:.1f}%, LNST hợp nhất tăng {m['profit_growth']*100:.1f}%."
              if m.get('revenue_growth') is not None and m.get('profit_growth') is not None else 'Thiếu kỳ liền trước để xác nhận tăng trưởng năm.')
    if r['quality']['bank'] and m.get('profit_growth') is not None:business=f"LNST hợp nhất năm {m['year']} tăng {m['profit_growth']*100:.1f}%; chưa đủ chỉ tiêu chuyên ngành để đánh giá chất lượng tín dụng."
    opportunities=[business,'Giá trị đầu tư cần được xác nhận bằng tăng trưởng lợi nhuận mẹ, dòng tiền và định giá có cùng cơ sở cổ phiếu.']
    if f.get('comparable_growth'):
        g=f['comparable_growth'];opportunities.insert(0,f"H1/2026: doanh nghiệp công bố doanh thu +{g['revenue_yoy']*100:.1f}% và LNST mẹ +{g['parent_profit_yoy']*100:.1f}% trên cơ sở so sánh điều chỉnh.")
    risks=[]
    if f.get('half_year',{}).get('operating_cash_flow',0)<0:
        risks.append('Dòng tiền kinh doanh bán niên âm dù lợi nhuận dương; cần theo dõi công nợ và giải phóng vốn lưu động ở kỳ tiếp theo.')
    if not s.get('trend_pass'):risks.append('Xu hướng X10 chưa đạt giá > MA50 > MA200; hồi phục ngắn hạn chưa đủ xác nhận xu hướng dài hơn.')
    if not s.get('market_bull'):risks.append('VN-Index chưa xác nhận điều kiện thị trường hỗ trợ hoặc thiếu benchmark phù hợp.')
    if f.get('basis_change'):risks.append('Phương pháp hợp nhất đổi từ 2026; doanh thu và LNST hợp nhất khác cơ sở có thể tạo tăng trưởng sai nếu so trực tiếp.')
    if r['quality']['bank']:risks.insert(0,'Thiếu bộ chỉ tiêu ngân hàng đã kiểm chứng; chưa đủ bằng chứng kết luận về chất lượng tín dụng hoặc an toàn vốn.')
    risks.append('Chưa có tập định giá doanh nghiệp tương đồng cùng ngày; P/E và P/B chỉ là tỷ số tham khảo.')
    observations=r['technical'].get('interpretations',[])[:2]
    scenarios=[
        {'name':'Cải thiện','trigger':f"Giá vượt kháng cự {price('resistance20')} và giữ trên MA50 {price('ma50')}; KL > TB20 phiên trước; VN-Index xác nhận hỗ trợ.",'response':'Cập nhật tín hiệu kỹ thuật. Chỉ nâng luận điểm khi lợi nhuận mẹ và dòng tiền kỳ mới cũng xác nhận.','invalidate':'Phá vỡ thất bại, giá quay dưới vùng vừa vượt hoặc kết quả kinh doanh không xác nhận.'},
        {'name':'Tiếp diễn / chưa xác nhận','trigger':f"Giá trong vùng {price('support20')} – {price('resistance20')}; các điều kiện xu hướng chưa đồng thuận.",'response':'Giữ trạng thái quan sát, kiểm tra báo cáo mới và biến động giá; không coi tin hợp tác là doanh thu chắc chắn.','invalidate':'Vượt hoặc thủng vùng tham khảo với xác nhận khối lượng; có công bố tài chính làm đổi luận điểm.'},
        {'name':'Suy yếu','trigger':f"Đóng cửa dưới hỗ trợ {price('support20')} cùng KL tăng, hoặc dòng tiền/lợi nhuận mẹ kỳ mới xấu hơn bằng chứng hiện có.",'response':'Hạ mức tin cậy của luận điểm hồi phục, rà lại dữ liệu và rủi ro. Đây là điều kiện nghiên cứu, chưa phải lệnh giao dịch.','invalidate':'Giá lấy lại vùng mất với xác nhận khối lượng và kết quả tài chính cải thiện.'}]
    watch=[{'when':'Mỗi phiên','check':'Giá, MA20/50/200, RSI, MACD, hỗ trợ/kháng cự và KL/TB20 trước phiên.','rule':'Tính lại ngưỡng theo cửa sổ mới; không giữ cố định mức trong PDF.'},
        {'when':'Khi có BCTC mới','check':'LNST mẹ, doanh thu cùng cơ sở, OCF và công nợ; đối chiếu ngày công bố.','rule':'Phân biệt quý độc lập/lũy kế trước khi cộng TTM; cập nhật số cổ phiếu sau phát hành.'},
        {'when':'Khi có công bố sự kiện','check':'Ngày sự kiện, hợp đồng, đơn hàng, thời gian triển khai, thu nhập bất thường.','rule':'Tách dữ kiện công bố với suy luận; chưa có giá trị hợp đồng thì không cộng vào EPS.'},
        {'when':'Trước khi sử dụng kết quả','check':'Ngày giá, ngày cổ phiếu, kỳ lợi nhuận, coverage và bộ chỉ tiêu ngành.','rule':'Dừng kết luận nếu giá quá cũ, sai kỳ, thiếu dữ liệu trọng yếu hoặc bằng chứng không khớp.'}]
    return {'opportunities':opportunities[:3],'risks':risks[:5],'observations':observations,'scenarios':scenarios,'watch':watch,
        'invalidation':'Luận điểm mất hiệu lực nếu dữ kiện nền bị sửa, BCTC mới phủ nhận tăng trưởng/dòng tiền, hoặc điều kiện kỹ thuật đã nêu không giữ được. Khi đó cần chạy lại phân tích.'}
