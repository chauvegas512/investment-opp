# Ghi nhận dự án nguồn

StockLens dùng adapter để gọi các module gốc, giữ thông báo bản quyền. Bản Miner tại máy được sửa công thức current ratio và bỏ token HF dự phòng nhúng trong module financial.py; chi tiết trong docs/BAN_GIAO.md.

- **X10 Investment Lab**: thư mục `../taikhoanx10_bot_tele-main/taikhoanx10_bot_tele-main`; tái sử dụng thu thập dữ liệu và engine FA/TA. Bản nguồn hiện có không chứa LICENSE; trước khi phát hành công khai, nhóm cần xác nhận quyền sử dụng/phân phối. Bản tích hợp hiện dùng nguồn tại máy người dùng.
- **vn-annual-report-miner**, tác giả Trương Minh Quân; MIT; nguồn được đề bài giới thiệu: https://github.com/Tumiqa/vn-annual-report-miner. Giấy phép nằm ở thư mục gốc dự án Miner.
- **HoHa Slide/PDF Core**, Apache-2.0; giữ LICENSE, NOTICE, MODIFICATIONS.md và THIRD_PARTY_NOTICES.md trong thư mục nguồn. StockLens dùng PresentationDNA và renderer; không chạy toàn bộ ứng dụng Presenton.
- **Vnstock/Vnai** dùng theo điều kiện của nhà cung cấp và phiên bản cài đặt. Dữ liệu doanh nghiệp có nguồn riêng, không đồng nghĩa được quyền phân phối lại không giới hạn.
- **report_engine** và bộ dữ liệu **dtata  full toping**: do người dùng cung cấp; sử dụng schema/biểu đồ và SQLite ở chế độ chỉ đọc.

StockLens không phải bản phát hành chính thức của các dự án nguồn. Khi di chuyển hoặc đóng gói, giữ các thư mục nguồn và giấy phép tương ứng, loại bỏ `.env`, cache, dữ liệu cá nhân và `node_modules`.

- **find_images.py**: script do người dùng cung cấp, được tích hợp để tìm ảnh theo query; sửa logging ngoại lệ để không lộ URL xác thực.
- **Logo/ảnh FPT và Vietcombank**: nguồn và URL gốc, SHA-256, ngày đối chiếu được ghi tại `resources/company_images.json`. Logo thuộc chủ sở hữu nhãn hiệu. Ảnh được dùng minh họa và liên kết nguồn; không tuyên bố giấy phép tự do.
