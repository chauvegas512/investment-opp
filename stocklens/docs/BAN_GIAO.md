# Bản bàn giao StockLens

## Vận hành

Chạy `stocklens/start.ps1`, mở http://127.0.0.1:8787. Chọn cổ phiếu, đợi phân tích, đọc các tab, chỉnh tiêu đề và tải PDF. API ở `/api/docs`. Muốn trình diễn ngay dữ liệu FPT thực đã đối chiếu: `python run.py --restore-evidence output/FPT-evidence.json` trong môi trường `$HOME/.venv`.

## Phần đã tích hợp

- `dtata  full toping/analysis_data/stocks_analysis.sqlite`: đọc danh sách mã, doanh nghiệp, giá, chỉ số VN-Index và BCTC. Kết nối `mode=ro`, không khởi động pipeline cũ hoặc ghi vào database gốc.
- Giá ưu tiên nguồn mới; nếu nguồn lỗi dùng bản lưu và kiểm tra độ mới. Tài chính ưu tiên VCI; BCTC SQLite được đối chiếu riêng. Nếu chỉ có tài chính lưu trữ thì yêu cầu kiểm tra lại trước kết luận.
- X10: chiến lược FA/TA, kiểm tra độ phủ và chỉ báo. Không gán backtest danh mục cũ cho một mã đang phân tích.
- Miner: catalog, lọc tin đúng doanh nghiệp, khai thác PDF người dùng với số trang và SHA-256.
- `financial_adapter.py` đọc Parquet BCTC có sẵn trong Miner theo ticker; ánh xạ mã chỉ tiêu chính xác sang cấu trúc chung và giữ nguồn file/sheet. Lưu riêng trong bằng chứng để đối chiếu, ưu tiên VCI cho kỳ mới. Đã sửa current ratio của Miner thành tài sản ngắn hạn / nợ ngắn hạn và bỏ token dự phòng nhúng trong financial.py.
- `report_engine.schema` và `report_engine.charts`: hợp đồng dữ liệu và biểu đồ tài chính. Template A4 StockLens đầy đủ 10 trang hoặc tóm tắt 4 trang, bổ sung nến/RSI/MACD/ATR, VN-Index cùng ngày, tài chính năm/quý, định giá theo đầu vào, sự kiện, kịch bản, theo dõi và nguồn.
- HoHa: giữ bản trình chiếu tại `/api/jobs/{id}/slides`.
- Database StockLens riêng `data/stocklens.sqlite` lưu lịch sử phân tích; có thể mở lại sau khi khởi động. Không lưu API key trong database.

## Định giá và phạm vi

P/E tham khảo dùng vốn hóa theo giá chốt và số cổ phiếu có kiểm tra nguồn, chia LNST mẹ bốn quý liên tiếp. P/B dùng vốn thuộc cổ đông mẹ sau khi trừ lợi ích không kiểm soát. EPS năm nguồn giữ riêng với EPS TTM quy đổi; không tạo giá mục tiêu từ P/E giả định. Ngân hàng ẩn FA chung và các chỉ số không phù hợp; cần thêm NIM, NPL, bao phủ nợ xấu và CAR. Chi tiết sửa cơ sở hợp nhất/cổ phiếu/dòng tiền FPT: `CAP_NHAT_PDF.md`.

Chưa tích hợp OCR, dự báo lợi nhuận, AI trả phí, tải/đọc tự động mọi tài liệu catalog, peer valuation cùng thời điểm hoặc backtest ngoài mẫu. Những phần này không được giả lập trong sản phẩm.

## Hồ sơ nộp bài

- `output/StockLens-FPT.pdf`: báo cáo mẫu từ dữ liệu thật.
- `output/FPT-evidence.json`: dữ liệu, nguồn, kỳ, chênh lệch và phương pháp để kiểm tra.
- `output/FPT-source-verification.json`: đối chiếu doanh thu/LNST hợp nhất năm 2025 với báo cáo chính thức FPT.
- `docs/BAO_CAO_HE_THONG.md`: kiến trúc và kịch bản bảo vệ; bổ sung tên nhóm, lớp, giảng viên theo thông tin thực.

Giữ các thư mục nguồn cùng cấp vì ứng dụng dùng các module gốc. Không nộp `.env`, cache môi trường Python hoặc token trong bản sao nguyên repo. Chạy trên localhost; đây là ứng dụng phục vụ bài giữa kỳ, chưa triển khai dịch vụ nhiều người dùng.
