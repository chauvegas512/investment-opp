# StockLens - Phân tích cơ hội đầu tư cổ phiếu

Ứng dụng giữa kỳ tích hợp X10, SQLite archive, Annual Report Miner, report_engine và HoHa. Nhập mã cổ phiếu Việt Nam, phân tích bằng dữ liệu thật, xem bằng chứng và xuất PDF A4 đầy đủ 8 trang hoặc tóm tắt 4 trang.

## Chạy trên Windows

Giữ các thư mục runtime cùng cấp với `stocklens` như cấu trúc repository. Python >= 3.10, môi trường dùng chung `$HOME\.venv`.

```powershell
cd stocklens
.\setup.ps1
.\start.ps1
```

Mở http://127.0.0.1:8787, API tại `/api/docs`. Xuất PDF dùng Edge; nếu không có Edge, dùng Chromium của Playwright. Không cần API AI trả phí.

Demo từ dữ liệu thật đã lưu:

```powershell
& "$HOME\.venv\Scripts\Activate.ps1"
python run.py --restore-evidence output/FPT-evidence.json
```

Mở http://127.0.0.1:8787/?job=verified-fpt. Bản lưu giữ nguyên ngày dữ liệu; quá cũ thì bị chặn kết luận. Nút Phân tích lấy dữ liệu mới.

Khóa Vnstock nếu nguồn yêu cầu có thể đặt trong biến môi trường `VNSTOCK_API_KEY` hoặc `.env` do người dùng tạo ở thư mục cha. Không đưa khóa vào Git/chat. Ứng dụng không gọi `setup_api_key` hoặc ghi khóa; `--stdin-key` nhận khóa qua nhập ẩn và giữ trong bộ nhớ.

## Phạm vi sản phẩm

- OHLCV, MA20/50/200, RSI(14), MACD(12,26,9), ATR(14), khối lượng, vùng giá tham khảo; VN-Index so cùng ngày.
- BCTC năm/quý, tăng trưởng đúng kỳ, lợi nhuận hợp nhất và mẹ tách riêng, chất lượng dòng tiền, tỷ số định giá khi đủ đầu vào.
- Tin có nguồn, ngày công bố/sự kiện, trạng thái kiểm chứng và điều kiện theo dõi.
- Catalog Miner và khai thác PDF người dùng tải lên theo từ khóa/trang/SHA-256; PDF scan chưa có OCR tự động.
- PDF có tóm tắt, kỹ thuật, thị trường, tài chính, định giá, sự kiện, kịch bản, kế hoạch theo dõi và nguồn bấm được. Người dùng chọn thời hạn, phong cách, độ chi tiết, tiêu đề và bật/tắt phần tin/bằng chứng.
- SQLite riêng trong `data/` lưu lịch sử phân tích; không commit lịch sử riêng. RAM giới hạn 30 phiên, 2 tác vụ đồng thời, TTL 6 giờ.

## Chính xác dữ liệu và giới hạn

FA/TA kế thừa engine X10; tổng điểm mặc định 20% FA hiệu dụng + 80% TA. Điểm là bộ lọc nghiên cứu, chưa phải xác suất lợi nhuận. Kiểm tra ngày giá, kỳ tài chính, độ phủ và ngành trước khi kết luận. Ngân hàng không áp dụng FA chung; chỉ tiêu ngành chưa kiểm chứng được ghi rõ.

VCI là nguồn BCTC hiện tại. KBS bị loại do phát hiện lệch kỳ; không gán lại năm bằng suy đoán. Dữ liệu SQLite/Miner được giữ riêng để đối chiếu, không trộn định nghĩa. Giá chuẩn hóa VND/cổ phiếu; benchmark là điểm. Cuối kỳ kế toán không thay ngày công bố.

Database X10 tùy chọn tại `dtata  full toping/analysis_data/stocks_analysis.sqlite` (hai dấu cách sau dtata) được mở chỉ đọc. File gốc vượt giới hạn GitHub nên không commit; thiếu archive vẫn có luồng online. Không chạy lại pipeline/bot cũ.

Không dùng số 0 hoặc dữ liệu giả thay chỗ thiếu. P/E/P/B chỉ là tỷ số tham khảo khi đủ đầu vào; chưa có tập doanh nghiệp so sánh, DCF, giá mục tiêu hoặc hiệu quả backtest một mã đã chứng minh. Công bố gốc đã đối chiếu cho một số dữ kiện FPT; không coi mọi mã đã được kiểm chứng tương tự.

## Kiểm thử và hồ sơ

```powershell
python -m unittest discover -s tests -v
python verify_reports.py
```

`verify_ui.py` kiểm tra server localhost đang chạy. Các fixture tổng hợp chỉ dùng trong test, không nằm trong luồng dữ liệu thật. PDF/JSON mẫu trong `output/` giữ ngày dữ liệu.

Xem [cập nhật PDF](docs/CAP_NHAT_PDF.md), [bàn giao](docs/BAN_GIAO.md), [thiết kế hệ thống](docs/BAO_CAO_HE_THONG.md) và [ghi nhận nguồn](THIRD_PARTY_NOTICES.md). Điền thông tin thành viên, lớp và giảng viên theo thông tin thật của nhóm trước khi nộp.

Thiết kế PDF 8 module theo X10 + Annual Miner: [PDF_8_MODULES.md](docs/PDF_8_MODULES.md).
