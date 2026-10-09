# Cập nhật PDF và kiểm chứng dữ liệu - 09/10/2026

Báo cáo A4 đầy đủ 8 trang, bản tóm tắt 4 trang. Người dùng chọn thời hạn nghiên cứu, phong cách theo dõi, tiêu đề và các phần tin/bằng chứng. Lựa chọn trình bày không tự thay trọng số hay khuyến nghị.

## Nội dung mới

- Tóm tắt có luận điểm, rủi ro và điều kiện mất hiệu lực.
- Nến, MA20/50/200, RSI Wilder(14), MACD EMA(12,26,9), ATR Wilder(14), hỗ trợ/kháng cự từ 20 phiên trước.
- Lợi suất và điều kiện PDF lấy trực tiếp từ X10: mốc 3/6/12 tháng lịch và ngày chung cổ phiếu/VN-Index; chênh lệch theo điểm phần trăm.
- Tài chính năm/quý, tăng trưởng đúng kỳ trước, độc lập phạm vi lợi nhuận hợp nhất và cổ đông mẹ.
- P/E tham khảo từ vốn hóa/LNST mẹ 4 quý liên tiếp; P/B từ vốn hóa/vốn thuộc cổ đông mẹ. Không xuất giá mục tiêu bằng P/E giả định.
- Sự kiện phân biệt ngày công bố/ngày xảy ra, dữ kiện/suy luận và việc cần theo dõi.
- Kết luận tổng hợp điều kiện X10, luận điểm, rủi ro và mất hiệu lực; nguồn bấm được, dữ liệu còn thiếu và trạng thái kiểm chứng.

## Các lỗi dữ liệu đã xử lý

1. VCI overview có các cột `issue_share` trùng tên: chọn ứng viên khớp vốn hóa/giá; không chọn tùy tiện khi không xác định được.
2. FPT chuyển cơ sở hợp nhất FPT Telecom từ 01/01/2026: chặn YoY doanh thu/LNST hợp nhất thô giữa hai cơ sở. Giữ riêng tăng trưởng so sánh điều chỉnh do doanh nghiệp công bố.
3. Số cổ phiếu FPT sau phát hành đối chiếu công bố ngày 25/09/2026. Vốn hóa dùng giá chốt báo cáo nhân số cổ phiếu; EPS năm nguồn không được dùng ngầm để tạo giá mục tiêu sau phát hành.
4. Tổng Q1+Q2 doanh thu, LNST hợp nhất, LNST mẹ và OCF của FPT khớp BCTC bán niên soát xét. Đối chiếu PDF scan bằng đọc trực quan; SHA-256, URL, trang và ngày kiểm chứng lưu trong `resources/verified_disclosures.json`.
5. Bổ sung ánh xạ các mã ngân hàng cho tổng nợ, lợi ích không kiểm soát và OCF; trình bày thu nhập lãi thuần/tổng thu nhập hoạt động thay chỉ tiêu doanh thu/gộp doanh nghiệp thông thường.
6. Ngân hàng không áp dụng FA chung/current ratio/nợ vay-vốn chủ/OCF-LNST. NIM, NPL, bao phủ nợ xấu, CAR còn chưa kiểm chứng thì giữ trạng thái cần đánh giá chuyên ngành.

## Kiểm tra

`python -m unittest discover -s tests -v`: kiểm tra chỉ báo bằng chuỗi chuẩn, benchmark cùng ngày, dữ liệu thiếu/cũ, cổ phiếu trùng cột, vốn mẹ và lợi nhuận TTM, trích số trang PDF và xuất PDF thực.

`python verify_reports.py`: FPT và VCB từ dữ liệu thật đã lưu; mỗi mã bản đầy đủ 8 trang, tóm tắt 4 trang; kiểm tra chân trang, số trang, văn bản và các đối chiếu FPT. Không dùng dữ liệu kiểm thử làm số liệu doanh nghiệp.

`python verify_ui.py`: kiểm tra giao diện đang chạy trên localhost, tuỳ chọn PDF, mobile và lỗi đầu vào.

Các công bố gốc chưa kiểm chứng cho mọi mã; tập doanh nghiệp so sánh/DCF/EV-EBITDA/OCR chưa đầy đủ. Các giá trị chưa có không được thay bằng 0 hoặc giả định ngầm. PDF mẫu giữ nguyên ngày dữ liệu, không phải số liệu trực tiếp tại lần mở file sau này.

Cấu trúc và phương pháp bản 8 module theo thiết kế mới: [PDF_8_MODULES.md](PDF_8_MODULES.md).
