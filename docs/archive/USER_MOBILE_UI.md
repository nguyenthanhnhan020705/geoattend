> **Tài liệu lưu trữ:** nội dung và số liệu bên dưới phản ánh thời điểm lập tài liệu. Các hướng dẫn/quy tắc cũ có thể đã được thay thế; xem [tài liệu hiện hành](../README.md) trước khi thực hiện.

# Giao diện User ưu tiên điện thoại

Theo yêu cầu 15/10/2026, trang User được bố trí một cột: thông tin nhân viên/tài khoản đầu tiên, trạng thái và chọn phiên ở giữa, lịch sử cá nhân cuối trang.

Cập nhật Xin nghỉ 16/10/2026: chọn BUỔI SÁNG/CẢ NGÀY rồi nhập lý do và xác nhận. Nghỉ sáng hiện “Đang nghỉ buổi sáng”, hai nút TIẾP TỤC BUỔI CHIỀU OFFICE/REMOTE; sau tiếp tục hiện “Đang làm việc” và chỉ CHECK-OUT cuối ngày. Nghỉ cả ngày khóa ngày, không hủy nghỉ để làm tiếp. `morning_leave` được lấy từ sự kiện ngày hiện tại, giữ đúng sau reload; CHECK-OUT sau nghỉ sáng không yêu cầu lý do sớm. Xem [LEAVE_FLOW_VERIFICATION](LEAVE_FLOW_VERIFICATION.md).

- Khi chưa vào ca: ba lựa chọn **CHECK-IN OFFICE**, **CHECK-IN REMOTE**, **XIN NGHỈ**. Khi đang làm trước nghỉ trưa, chỉ hiện **NGHỈ TRƯA / CHECK-OUT SỚM**. Đang nghỉ trưa chỉ có hai lựa chọn **TIẾP TỤC OFFICE / TIẾP TỤC REMOTE**. Khi đã tiếp tục làm việc, chỉ hiện **CHECK-OUT** cuối ngày. Các form/nhóm thao tác khác được ẩn theo giai đoạn; không còn nút chuyển trực tiếp chế độ khi đang làm việc trên giao diện User.
- Remote và Xin nghỉ mở khung nhập lý do nhỏ ngay dưới các lựa chọn; chỉ một khung xuất hiện tại một thời điểm. Mở/đóng khung không ghi chấm công. Khung được đóng sau khi xác nhận thao tác thành công; chuyển khung/đóng vẫn giữ bản nháp chưa gửi. Có nút đóng, quản lý focus và aria-expanded.
- CHECK-OUT SỚM mở cùng khung lý do: bắt buộc 1–1000 ký tự sau trim, có thông báo kết thúc ngày và nút xác nhận. Backend kiểm tra trong transaction sau replay/kiểm tra trạng thái; thiếu lý do không đóng phiên hoặc tăng revision. Lưu lý do vào phiên và sự kiện kết thúc; lịch sử User/Admin đọc lại được. CHECK-OUT sau nghỉ trưa vẫn không yêu cầu lý do. Xem [kiểm chứng điều chỉnh](EARLY_CHECKOUT_VERIFICATION.md).
- Office vẫn chỉ xin GPS khi bấm thao tác Office. Cấu trúc pending/UUID không đổi; GPS vẫn không vào storage. Theo yêu cầu 16/10/2026, mọi CHECK-OUT, kể cả CHECK-OUT SỚM, kết thúc ngày và khóa đến ngày hôm sau ở cả API lẫn UI. API chuyển trực tiếp cũ còn được giữ tương thích, nhưng không xuất hiện trong luồng giao diện mới.
- Tiến trình nghỉ trưa được suy ra từ sự kiện `LUNCH_START`, không dựa vào giờ thiết bị hoặc storage. `day_finished=true` cho mọi trạng thái `CHECKED_OUT`; action mới với ngày/revision hiện hành trước cutoff bị 409 `DAY_FINISHED`. Retry UUID đã commit vẫn trả kết quả cũ. Ngày mới theo giờ Việt Nam tự reset; ngoại lệ Admin xóa ngày hôm nay/reset vẫn giữ nguyên. Không cần migration; khởi động lại web rồi Ctrl+F5 sau lần điều chỉnh này.
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

Để dùng bản điều chỉnh theo ca và khóa ngày, khởi động lại web bằng `scripts.local_run serve`, rồi **Ctrl+F5** trên `/user`. Không cần migration. Báo cáo 213 test ở trên là mốc bố cục mobile trước khi bổ sung luồng theo ca; kết quả mới được cập nhật dưới đây.

## Kiểm chứng luồng theo ca và khóa ngày

`tests/integration/test_daily_action_ui.py` kiểm tra bốn tổ hợp Office/Remote trước và sau nghỉ, reload ở từng trạng thái, CHECK-OUT cuối ngày và khóa sau reload, API từ chối bắt đầu lại, replay UUID và reset ngày mới. 5 test đầu quan sát RED rồi GREEN; test khóa ngày quan sát RED trước bổ sung kiểm tra Backend. Các test browser cũ được cập nhật theo tên nút mới và việc bỏ thao tác chuyển chế độ trực tiếp khỏi UI; kiểm thử API chuyển chế độ vẫn được giữ.

Kết quả: nhóm API/browser liên quan **22 passed** trong 72.17 giây; toàn suite **218 passed, 1 warning** trong 190.21 giây. Warning upstream Starlette/httpx có sẵn; `pip check`/`git diff --check` không lỗi. Không tạo/xóa dữ liệu thử trên Supabase thật.

Review độc lập không có Critical/Important; góp ý Minor về thông báo nhầm là nhân viên tự Check-out khi hệ thống đóng lúc 20:00 đã được sửa sang “Ngày làm việc đã kết thúc”. API chuyển chế độ cũ và quyền Admin xóa ngày/reset trạng thái được giữ theo phạm vi đã duyệt, không bị thay bởi điều chỉnh UI này.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.local-tests/daily-actions/full -o cache_dir=.local-tests/daily-actions/cache-admin
```
