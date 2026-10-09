# Tìm ảnh động và bìa giới thiệu doanh nghiệp

Bản trước chỉ nối registry ảnh đã lưu cho FPT/VCB. Hàm tìm kiếm tồn tại nhưng chưa được web gọi cho các ticker khác. Bản này bổ sung tìm ảnh động và cache công khai theo ticker.

- Web tự tìm khi mở kết quả chưa có ảnh, hoặc người dùng bấm **Tìm ảnh**.
- `POST /api/jobs/{id}/images/search` dùng ticker + tên công ty; Serper nếu key đang ở env của server, Bing fallback khi chưa cấu hình provider khác.
- Kết quả được lọc theo tên/nhãn hiệu/domain công ty; không chỉ dựa vào ticker dễ trùng từ thông thường. Ví dụ FRT không nhận ảnh xe Ford.
- Tải ảnh có kiểm tra IP public, giới hạn 5 MB/24 triệu pixel và định dạng raster. Cache nằm trong `data/image-cache`, không commit.
- Kết quả là ứng viên, không tự gắn nhãn đã xác minh. Hệ thống gợi chọn một ảnh ngang đủ độ phân giải cho bìa; người dùng có thể đổi hoặc bỏ chọn. `POST /api/jobs/{id}/images/select` chỉ nhận ID thuộc cache của ticker.
- Chọn/bỏ ảnh áp dụng vào lần xuất PDF kế tiếp. Ảnh đã chọn được nhúng offline, có nguồn và trạng thái.

Khóa Serper không lưu trong code hoặc file do app tạo. Có thể nhận qua `python run.py --stdin-image-key` bằng nhập ẩn, chỉ ở RAM của server. Sau khi tắt server cần cấu hình lại bằng môi trường của người vận hành hoặc nhập ẩn.

Bìa PDF dùng ảnh lớn phủ ngang, lớp nền tối giúp thông tin dễ đọc, logo/ticker, giá và trạng thái. Bên dưới có giới thiệu ngắn từ nguồn doanh nghiệp hoặc hồ sơ/metadata VCI, kèm liên kết nguồn. Không tạo giới thiệu từ ảnh hoặc từ khóa. Giữ 8 module và dữ liệu FA/TA hiện có; `decision_reason` đầy đủ ở trang kết luận.
