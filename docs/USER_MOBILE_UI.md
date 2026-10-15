# Giao diện User ưu tiên điện thoại

Theo yêu cầu 15/10/2026, trang User được bố trí một cột: thông tin nhân viên/tài khoản đầu tiên, trạng thái và chọn phiên ở giữa, lịch sử cá nhân cuối trang.

- Ba lựa chọn chính: **CHECK-IN OFFICE**, **CHECK-IN REMOTE**, **XIN NGHỈ**. Các thao tác không được server cho phép bị vô hiệu hóa. Office vẫn hiển thị tên tương ứng khi tiếp tục/hủy nghỉ/chuyển chế độ để thể hiện rõ thao tác sắp thực hiện.
- Remote và Xin nghỉ mở khung nhập lý do nhỏ ngay dưới các lựa chọn; chỉ một khung xuất hiện tại một thời điểm. Mở/đóng khung không ghi chấm công. Khung được đóng sau khi xác nhận thao tác thành công; chuyển khung/đóng vẫn giữ bản nháp chưa gửi. Có nút đóng, quản lý focus và aria-expanded.
- Office vẫn chỉ xin GPS khi bấm thao tác Office. Nghỉ trưa, Check-out, chuyển chế độ, hủy nghỉ và retry giữ nguyên quy tắc Backend. Cấu trúc pending/UUID không đổi; GPS vẫn không vào storage.
- **Lịch sử cá nhân** mặc định thu gọn, bấm để mở hoặc thu lại. Không gọi API lịch sử khi đang đóng; khi mở hoặc làm mới lúc đang mở sẽ lấy dữ liệu mới. Phản hồi lỗi/thành công cũ bị bỏ qua khi đã đóng hoặc có lượt tải mới, tránh ghi đè snapshot mới.
- CSS dành riêng cho trang User; bố cục Admin và chức năng xóa lịch sử không thay đổi. Không có migration, không tạo/xóa dữ liệu thử trên Supabase thật.

## Kiểm chứng

- Test bố cục mới quan sát RED trước khi triển khai; GREEN 2 ca viewport 360px/1280px. Kiểm tra thứ tự tài khoản/lịch sử, ba lựa chọn, form ẩn mặc định, focus, giữ bản nháp, không gửi action khi chỉ mở form, history lazy load và không tràn ngang.
- Nhóm browser liên quan đạt 17 ca trước sửa race, bao gồm retry mất phản hồi/timeout/reload, GPS, nghỉ, chuyển chế độ, lịch sử Admin và tài khoản.
- Test mở–đóng nhanh với phản hồi lịch sử cũ bị giữ đã quan sát RED, sau đó sửa bằng generation counter; nhóm bố cục đạt 3/3 test trong 14.82 giây.
- Review độc lập không phát hiện Critical/Important; góp ý Minor về phản hồi lịch sử cũ đã được tái hiện và sửa bằng test ở trên. Backend/live Supabase không thuộc lượt review giao diện; hồi quy chạy trên database test riêng. Minor UUID ordering của Phase 4 giữ nguyên ngoài phạm vi.
- Toàn suite sau sửa: **213 passed, 1 warning** trong 237.69 giây. `pip check` và `git diff --check` không lỗi. Warning upstream Starlette/httpx có sẵn. Database test PostgreSQL/PostGIS local riêng; ảnh kiểm tra ở `.local-tests/user-mobile/artifacts/user-360.png` và `user-1280.png`.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.local-tests/user-mobile/full -o cache_dir=.local-tests/user-mobile/cache
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Để dùng giao diện mới, nhấn **Ctrl+F5** trên trang `/user`; không cần migrate hoặc khởi động lại Backend vì chỉ thay HTML/CSS/JS.
