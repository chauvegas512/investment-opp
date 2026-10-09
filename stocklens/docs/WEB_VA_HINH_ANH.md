# Web mới và ảnh minh họa doanh nghiệp

Web thống nhất với PDF bằng bảng màu tím/lime/hồng/cyan, sidebar, hero cổ phiếu, KPI cards, biểu đồ đổi cửa sổ, bảng điều kiện X10 và Report Studio. Dữ liệu giao diện lấy từ job thật; không dùng số minh họa trong HTML mẫu. Trang chủ có thể mở bản FPT đã lưu và ghi rõ ngày dữ liệu; nút Phân tích cập nhật nguồn thật.

`static/app.js` và `app.css` cung cấp giao diện responsive, tab tài chính/định giá/tin/BCTN/nguồn, chọn nhóm từ khóa, upload PDF và tùy chỉnh báo cáo. Biểu đồ đổi cửa sổ 21/63/126/252 phiên hiển thị; lợi suất và điều kiện X10 vẫn lấy theo mốc lịch từ engine.

`find_images.py` được tích hợp từ script người dùng cung cấp. Hàm `search_images` hỗ trợ Google/Serper/Brave và Bing fallback. Ngoại lệ tìm ảnh chỉ ghi tên lớp lỗi để tránh URL chứa key xuất hiện trong log. Key được người vận hành cấu hình qua môi trường; bản mã không có key. Khóa được dùng trong lượt tìm ảnh này qua nhập ẩn, chỉ ở RAM của tiến trình, không ghi `.env` hoặc commit.

Kết quả tìm ảnh là ứng viên. Các ảnh FPT/VCB dùng trong bản này được đối chiếu với website chính thức trước khi chọn. Registry `resources/company_images.json` giữ URL gốc, trang nguồn, SHA-256, ngày đối chiếu và vai trò logo/company/event. File ảnh lưu dưới `static/company-images/`, phục vụ web và nhúng offline vào PDF. Không tự gán ảnh của doanh nghiệp khác khi mã chưa có ảnh được kiểm chứng.

PDF có logo trên bìa, ảnh doanh nghiệp và ảnh sự kiện phù hợp. Checkbox Hình ảnh bật/tắt phần này, không thay dữ liệu hay điểm. Ảnh có liên kết nguồn; chỉ minh họa, không là bằng chứng tài chính. Logo/ảnh thuộc chủ sở hữu nguồn; không tuyên bố giấy phép sử dụng tự do.

Kiểm tra:

- `verify_redesign.py`: tab, đổi cửa sổ biểu đồ, ảnh/logo, ẩn ảnh trong báo cáo, chọn nhóm từ khóa, mobile 390/320px, không lỗi JavaScript.
- `verify_reports.py`: PDF FPT/VCB 8 trang và tóm tắt 4 trang, không tràn chân trang.
- Tests ảnh: provenance/local paths, ảnh nhúng offline, mã không xác định không nhận nhầm logo, parser metadata không hợp lệ.
