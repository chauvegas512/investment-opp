# Kiểm tra dữ liệu StockLens — 09/10/2026

Quy trình thu thập dùng chung cho mọi mã người dùng nhập. Đợt kiểm tra thực tế đã cập nhật 16 mã có trong lịch sử: FPT, HPG, TCB, VJC, MBB, FTS, HVN, FRT, PNJ, PVT, VCB, BSR, SSI, PAN, GVR và ACB. Đây không phải xác nhận đã tải và kiểm chứng toàn bộ thị trường.

- Cả 16 mã đã có giá phiên 09/10, dữ liệu BCTC năm/quý và bản tin có URL, ngày xuất bản, kiểm tra danh tính. Kỳ tài chính mới nhất nguồn cung cấp là năm 2025/quý 2 năm 2026. Không coi cuối kỳ là ngày công bố.
- Đã tải/xử lý BCTN 2025 cho các mã trên, bổ sung riêng FRT từ bản công bố tháng 4/2026 để thay kết quả khai phá năm 2024.
- Dùng catalog, danh tính/ngành ICB, bộ thu thập tin đa nguồn, bộ trích bài, dictionary, exact matcher, metrics và snippet extractor của Annual Miner. Tần suất tính toàn bộ lớp văn bản; trích đoạn ưu tiên nội dung thay mục lục và có số trang.
- Ảnh bìa tìm và chọn ở server; ẩn gallery và nút chọn ảnh trên web. Ảnh tìm kiếm dùng minh họa, có nguồn, không được coi là chứng cứ tài chính.
- Giá khớp lệnh lấy theo yêu cầu, có timestamp và kiểm tra đơn vị nghìn VND. Trong giờ giao dịch cập nhật theo chu kỳ 30 giây; ngoài phiên ghi rõ khớp cuối nguồn. Thanh giá trong ngày trước 15:00 không dùng làm tín hiệu EOD.
- Có API bổ sung dữ liệu bản lưu, giới hạn hai tác vụ đồng thời và trạng thái cập nhật/lỗi. Database X10 gốc chỉ đọc.

## Phần chưa được xác minh đầy đủ

SSI và ACB có bản BCTN scan gần như chỉ chứa lớp chữ ký. Bộ tìm nguồn thay thế đã thử công bố trực tiếp và tìm PDF công khai; báo cáo ghi `OCR_REQUIRED`, không xuất tần suất bằng 0 như kết quả toàn văn. Một số báo cáo khác cũng có trang ảnh; tỷ lệ trang đọc được được công khai. Chưa có OCR tiếng Việt đã được kiểm định trong môi trường này.

NIM, NPL, bao phủ nợ xấu và CAR cần công bố ngân hàng đúng kỳ. Không tự suy ra từ các khoản mục BCTC tổng hợp hoặc áp dụng thang FA chung cho ngân hàng. Ngày công bố BCTC và snapshot định giá nhóm còn phụ thuộc nguồn; thời điểm lưu trữ luôn được ghi rõ.

## Xác minh

44 kiểm thử đã qua trước bước chốt; kiểm tra thực tế TCB/VJC có bản tin, BCTN và ảnh bìa, PDF đúng 8 trang, không tràn phần chân trang; trình duyệt không báo lỗi JavaScript. Tệp kiểm tra: `verify_backfill.py`. Các phép kiểm tra dữ liệu giá, đơn vị, nhận dạng thương hiệu và trích đoạn nằm trong `tests/test_data_pipeline.py`.
