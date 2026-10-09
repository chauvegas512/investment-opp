# PDF 8 module theo X10 + Annual Miner

Thiết kế lấy bảng màu tím, lime, hồng, cyan, nền lavender và card có viền/đổ bóng từ HTML tham chiếu người dùng. Các giá, điểm và tín hiệu mẫu trong HTML không được dùng làm dữ liệu doanh nghiệp.

| Trang | Module | Dữ liệu và phương pháp |
|---|---|---|
| 01 | Investment Snapshot | Ticker, công ty, giá, R3/6/12 tháng lịch, FA/TA/unified, final_action và decision_reason X10 |
| 02 | Market & Technical Analysis | Giá/MA/volume; năm điều kiện momentum, relative strength, trend, breakout, volume; benchmark cùng mốc lịch theo engine |
| 03 | Financial Performance | BCTC năm/quý VCI, nguồn X10/Miner giữ riêng để đối chiếu; tăng trưởng đúng kỳ, OCF và kiểm tra cơ sở hợp nhất |
| 04 | Financial Health | quality/growth/value/safety của X10; ROE/ROA và tỷ số có đủ thành phần; ngân hàng không áp dụng FA chung |
| 05 | Annual Report Insights | Annual Miner exact matcher + MetricsCalculator: frequency, diversity, frequency/total_words × 10.000, snippet và số trang |
| 06 | Relative Valuation | P/E/P/B tham khảo hiện tại; X10 median_pe_ttm và peer_count từ snapshot archive, biểu đồ so đúng ngày archive |
| 07 | News & Corporate Events | Tin lọc ngày/danh tính/trùng URL; tổng hợp điều kiện từ dữ kiện, corporate_actions chỉ đọc; AI chưa kết nối thì ghi rõ |
| 08 | Investment Conclusion | Luận điểm, rủi ro, điều kiện X10, tỷ số định giá, bảng nguồn/kỳ/trạng thái và mã băm config chiến lược |

## Adapter phương pháp

`report_modules.py` chuẩn hóa các module, không thay quy tắc engine. Điều kiện chiến lược lấy trực tiếp từ signal; RSI/MACD/ATR bổ sung không cộng điểm TA. Lợi suất chiến lược là tháng lịch với ngày chung cổ phiếu/VN-Index theo `aligned_calendar_return`, khác phép minh họa 21/63/126/252 phiên ở bản PDF trước.

`x10_context.py` chuyển phương pháp `stock_data_api.industry_valuation` thành truy vấn SQLite chỉ đọc: sector trước, nếu dưới 5 bản ghi thì chuyển industry; P/E nguồn dương hoặc vốn hóa/LNST TTM, chỉ nhận (0,200]. Mẫu có thể chứa chính mã phân tích. Lưu toàn bộ mẫu, ngày và cách tính trong evidence. Không gọi API/server/bot cũ.

Snapshot archive cũ hơn phiên giá PDF: chỉ so P/E cổ phiếu lưu trữ với median cùng ngày archive. Không lấy trung vị cũ làm định giá ngành tại phiên mới; không đưa P/E display vào FA hoặc tạo giá mục tiêu.

`annual_insights.py` tự tải BCTN từ nguồn đã nhận diện trong `resources/annual_sources.json` và khai phá. Hiện có nguồn FPT 2025. Mã khác có thể tải PDF ở giao diện. Số lượt khớp tính toàn bộ văn bản, không chỉ 80 đoạn được lưu; total_words là số token tách bằng khoảng trắng. Trang không có lớp văn bản không được tính như đã OCR. Bản khai phá cũ thiếu tổng đếm thì phải chạy lại, không suy từ số snippet.

Các nhận xét định lượng được tạo từ số liệu/điều kiện; không cần viết nhận định tay. Công bố nguồn đã kiểm chứng và trạng thái chưa kiểm chứng vẫn được giữ tách biệt. Tần suất từ khóa không là sentiment hay điểm ESG.

## Kiểm tra

- Unit tests: engine flags, giá/benchmark, snapshot P/E fallback/outlier, chỉ số tần suất vượt giới hạn snippet, missing/N/A và PDF thật.
- `verify_reports.py`: FPT và VCB, mỗi mã 8 trang đầy đủ hoặc 4 trang tóm tắt, kiểm tra tràn chân trang và dữ kiện FPT.
- `verify_ui.py`: tuỳ chọn báo cáo, desktop/mobile và lỗi JavaScript.

FPT có BCTN thật và công bố đã đối chiếu; VCB minh họa trường hợp chưa có BCTN khai phá/tin đã kiểm chứng và thiếu bộ chỉ tiêu ngành. Không sinh số liệu lấp khoảng trống.
