# StockLens - Investment Opportunity Research

Ứng dụng giữa kỳ phân tích cơ hội đầu tư cổ phiếu Việt Nam, tích hợp X10, Annual Report Miner, report_engine và HoHa. PDF A4 đầy đủ 8 trang hoặc tóm tắt 4 trang: kỹ thuật, VN-Index, tài chính, định giá có đầu vào, sự kiện, kịch bản và nguồn kiểm chứng.

## Chạy trên Windows

Clone repository, mở PowerShell ở thư mục này:

```powershell
cd stocklens
.\setup.ps1
.\start.ps1
```

Mở http://127.0.0.1:8787. Python >= 3.10, môi trường dùng chung `$HOME\.venv`. PDF dùng Edge hoặc Chromium qua Playwright. Không cần API AI trả phí. Khóa Vnstock nếu nguồn yêu cầu được người dùng cấu hình ngoài Git; không đưa khóa vào chat/commit.

Demo dữ liệu thật đã lưu:

```powershell
& "$HOME\.venv\Scripts\Activate.ps1"
python run.py --restore-evidence output/FPT-evidence.json
```

Mở http://127.0.0.1:8787/?job=verified-fpt. Giá/BCTC giữ ngày trong bằng chứng; bản lưu quá cũ bị chặn kết luận. Nút Phân tích lấy dữ liệu mới.

## Dữ liệu và giới hạn

- Database X10 gốc lớn hơn giới hạn tệp GitHub nên không commit. Có thể đặt bản người dùng sở hữu tại `dtata  full toping/analysis_data/stocks_analysis.sqlite` (hai dấu cách sau dtata). App chỉ đọc; thiếu database vẫn dùng nguồn online, catalog và dữ liệu Miner được đóng kèm. Không khởi động pipeline/bot cũ.
- `stocklens/output/` có PDF FPT, VCB và JSON bằng chứng thực; không phải dữ liệu trực tiếp cho mọi thời điểm.
- FPT đã đối chiếu một số công bố gốc. Các mã khác có thể thiếu kiểm chứng BCTC hoặc chỉ tiêu ngành. Không dùng số giả để lấp khoảng trống; chưa có giá mục tiêu/backtest cá nhân.
- Tài liệu thiết kế, giấy phép và thay đổi: [stocklens/README.md](stocklens/README.md), [cập nhật PDF](stocklens/docs/CAP_NHAT_PDF.md), [ghi nhận bên thứ ba](stocklens/THIRD_PARTY_NOTICES.md).

## Kiểm thử

```powershell
cd stocklens
& "$HOME\.venv\Scripts\Activate.ps1"
python -m unittest discover -s tests -v
python verify_reports.py
```

Kiểm thử database được bỏ qua khi chưa cung cấp archive tùy chọn. Các tệp môi trường, credentials, lịch sử riêng và cache không nằm trong repository.
