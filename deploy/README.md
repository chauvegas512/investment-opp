# StockLens trên VPS và Vercel

Frontend production: https://stocklens-investment.vercel.app. Backend dự kiến: https://stocklens.160.22.107.152.sslip.io. Frontend chỉ hoàn chỉnh khi HTTPS backend và rewrite `/api/health` hoạt động. Không đặt khóa API trong frontend.

## VPS Ubuntu: Python, systemd và Caddy

Triển khai đang dùng Python native vì VPS không kết nối được Docker Hub. `vps_native.sh` cài môi trường Python riêng cho service, Chromium và font Noto; chạy Uvicorn bằng tài khoản `stocklens`, chỉ nghe `127.0.0.1:8787`. Caddy phục vụ HTTPS ở cổng 80/443. Chỉ dùng một worker vì hàng đợi tác vụ được quản lý trong RAM. Hai tác vụ phân tích/refresh và một PDF được xử lý đồng thời tối đa.

Source nằm trong `/opt/stocklens/releases/<timestamp>`; `/opt/stocklens/current` trỏ đến release đang chạy. Lịch sử, cache ảnh và tài liệu nằm tại `/opt/stocklens/shared/data`. SQLite X10 tùy chọn nằm tại `/opt/stocklens/shared/archive/stocks_analysis.sqlite`, được mở chỉ đọc. Không chạy bot hoặc pipeline X10 cũ.

Các helper SSH xác minh fingerprint trước khi xác thực. Fingerprint hiện tại đã được người dùng xác nhận sau khi VPS cài lại; phải xác minh qua nhà cung cấp nếu nó thay đổi. Mật khẩu chỉ nhập qua `getpass`, không truyền trong arguments hay ghi file. `ssh_maintenance.py --image-key` nhận Serper qua `getpass`; `vps_native.sh` mã hóa bằng `systemd-creds`, service đọc credential trong RAM lúc khởi động. Không ghi khóa vào Git hay frontend.

VPS cần lấy được các gói trong `stocklens/requirements.txt`. Nếu mirror không cung cấp SDK Vnstock, `pack_runtime_wheels.py` đóng gói bản Python thuần đã cài hợp lệ trên máy triển khai; `ssh_maintenance.py --wheels` tải riêng lên VPS. `deploy/tmp/wheels` bị loại khỏi Git, không phân phối SDK trong source công khai. Sau khi source release được tải lên, chạy `ssh_maintenance.py --script deploy/vps_native.sh --image-key`. Script cần quyền root, hostname trỏ tới VPS và kết nối TCP 80/443 công khai để cấp chứng chỉ.

Quản trị: `systemctl status stocklens caddy`, `journalctl -u stocklens`, `systemctl restart stocklens`. Khóa mã hóa gắn với máy chủ; khi chuyển máy cần nhập lại qua `getpass`. Sao lưu thư mục shared riêng, không commit dữ liệu hoặc credential.

## Frontend Vercel

Chạy `python deploy/build_frontend.py --backend https://<hostname-backend>`, rồi `npx vercel deploy --prod --yes --cwd deploy/vercel`. Project đã tạo là `stocklens-investment`. Có thể triển khai bằng CLI khi GitHub integration của Vercel không có quyền truy cập repo. Thư mục sinh ra và metadata `.vercel` bị loại khỏi Git. Rewrite cùng origin chuyển `/api/*` và `/image-cache/*` tới VPS, hỗ trợ tải PDF lớn mà không đưa nội dung qua serverless function.

## Kiểm tra và giới hạn

`runtime_check.sh` kiểm thử trên Linux và xác minh danh sách mã. `qa_live.sh` lấy dữ liệu thực FPT/TCB/VJC, kiểm tra ảnh, tin/BCTN, bố cục và PDF tám trang bằng Chromium Linux. `qa_persistence.sh` xác minh báo cáo còn mở được sau restart; dùng `--download-qa` để tải artifact riêng về `deploy/tmp/qa` rồi kiểm tra trực quan.

Danh mục hiện có 1.562 mã; đây là phạm vi tra cứu, không đảm bảo mọi doanh nghiệp có đủ BCTN dạng text, tin mới hay tỷ số đặc thù ngành. Tài liệu scan được đánh dấu cần OCR; dữ liệu thiếu không thay bằng số giả. Phải kiểm tra ngày giá và kỳ tài chính trong từng báo cáo.

Nếu Caddy báo ACME connect timeout nhưng INPUT/OUTPUT Ubuntu đều cho phép, kiểm tra firewall nhà cung cấp và định tuyến quốc tế. `check_firewall.sh` và `network_routes.sh` chỉ chẩn đoán, không xóa firewall. Không bỏ xác minh TLS để che lỗi kết nối. Chỉ xác nhận hoàn tất sau khi URL production gọi được API, hiển thị ảnh và tải PDF thành công.

Docker là phương án thay thế qua `compose.yaml` và `Dockerfile`, yêu cầu truy cập Docker Hub; không chạy đồng thời với service native trên cùng cổng.
