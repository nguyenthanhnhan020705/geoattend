# Admin xem và xóa vĩnh viễn lịch sử nhân viên

Yêu cầu bổ sung được người dùng xác nhận ngày 15/10/2026: Admin được xem và xóa vĩnh viễn lịch sử cá nhân nhân viên. Quyền xóa này thay thế giới hạn không xóa lịch sử trong thiết kế MVP ban đầu; User vẫn chỉ xem lịch sử bản thân.

## Sử dụng

1. Admin vào **Quản lý nhân viên**, chọn **Lịch sử** ở đúng nhân viên.
2. Chọn khoảng ngày, bấm **Xem lịch sử**; danh sách phân trang 20 ngày. Không chọn ngày thì dùng 7 ngày gần nhất.
3. Chọn **Xóa ngày này**. Kiểm tra tên nhân viên, tài khoản và ngày; nhập chính xác tên tài khoản rồi chọn **Xóa vĩnh viễn**.

Thao tác xóa toàn bộ phiên, sự kiện, lý do và GPS của ngày đã chọn trong database ứng dụng; không xóa tài khoản hay ngày/nhân viên khác. Không có thùng rác hoặc khôi phục trong ứng dụng. Ngày đang Office/Remote/nghỉ trưa hoặc có phiên mở bị chặn; nhân viên cần Check-out và Admin tải lại trước khi xóa.

Lịch sử đã xóa biến mất ở cả Admin và nhân viên. Nếu xóa lịch sử hôm nay, trạng thái về chưa bắt đầu với revision mới; nhân viên có thể bắt đầu lại trước 20:00. Màn hình cũ bị từ chối. Database chỉ giữ dấu kỹ thuật ngày/revision và UUID/hash thao tác đã xử lý để chặn retry khôi phục dữ liệu đã xóa; không giữ lý do, sự kiện, phiên, GPS hoặc kết quả replay cũ trong các dấu đó. Đây không phải bản lưu để phục hồi lịch sử.

Quyền xem áp dụng cả nhân viên bị khóa; GPS hết hạn vẫn bị che theo chính sách 30 ngày. Tài khoản Admin được kiểm tra lại dưới khóa và session phải còn hiệu lực; User/khách không truy cập các endpoint mới.

## Cài đặt

Cần migration **004_history_deletion.sql**, bổ sung hai cột đánh dấu kỹ thuật. Công cụ migrate đồng thời cấp quyền DELETE ba bảng con attendance cho runtime role; không cấp quyền xóa tài khoản. Không sửa migration cũ.

```powershell
cd D:\N.ThanhNhan\INTERN\geoattend\.worktrees\phase-1
.\.venv\Scripts\python.exe -m scripts.local_run migrate
```

Khởi động lại web và maintenance nếu đang chạy bằng phiên bản cũ, sau đó Ctrl+F5 trên trình duyệt. Migration không tự xóa lịch sử. Việc xóa chỉ xảy ra khi Admin gửi thao tác xác nhận.

## API và tính nhất quán

- `GET /api/admin/users/{id}/history?from=YYYY-MM-DD&to=YYYY-MM-DD&page=1&page_size=20`: cùng cấu trúc lịch sử cá nhân, chỉ Admin.
- `DELETE /api/admin/users/{id}/history/{day_id}` với JSON `expected_revision`, `confirm_username`, CSRF và Origin cùng nguồn.
- Profile lock theo thứ tự UUID, dùng chung khóa nhân viên với attendance/maintenance. Kiểm tra revision ngăn xóa thay đổi mới; retry cùng phiên bản xóa trả thành công mà không xóa phiên mới. UUID của attendance đã xóa trả `HISTORY_DELETED`.
- Mọi bước xóa/tombstone cùng transaction; lỗi database rollback cả phiên, event, GPS và replay. Không xóa bản sao lưu ngoài database ứng dụng; chính sách backup production thuộc Phase 6.

## Kiểm chứng

Test API/database: `tests/integration/test_admin_history.py`; browser: `tests/integration/test_admin_history_browser.py`. Chỉ dùng database PostgreSQL/PostGIS test riêng, không tạo hoặc xóa dữ liệu thử trên Supabase thật.

Đã quan sát RED do endpoint/nút chưa có, rồi GREEN tập trung 14 test gồm migration và browser 360px/desktop. Kiểm tra role/CSRF, target khác, xác nhận sai, revision cũ, inactive/retention, rollback, Admin session bị thu hồi khi chờ khóa, retry mất phản hồi, migration lặp và runtime role hạn chế. Các ca bổ sung kiểm tra ngày khác giữ nguyên, hai request xóa hoặc xóa vs bắt đầu phiên mới.

Trước sửa review, toàn suite **208 passed, 1 warning** trong 218.18 giây. Review độc lập tìm hai điểm Important trong dọn request: còn giữ thời điểm thao tác cũ và request trước migration 003 không có result_work_date bị bỏ sót. Hai test mới quan sát RED, sửa xong toàn nhóm API/browser/migration **19 passed** trong 33.90 giây. Request cũ được đối chiếu qua event/session trước khi xóa, các timestamp thao tác bị thay bằng thời điểm xóa. Không còn Important chưa xử lý; toàn suite sau sửa **210 passed, 1 warning** trong 239.24 giây. Warning upstream Starlette/httpx có sẵn; `pip check` và `git diff --check` không lỗi.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.local-tests/admin-history/final -o cache_dir=.local-tests/admin-history/cache
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Migration 004 đã áp dụng thành công bằng `scripts.local_run migrate` trên database ứng dụng đang cấu hình, chỉ cập nhật schema/quyền; không tạo/xóa dữ liệu chấm công thử trên Supabase thật. Cần khởi động lại tiến trình web đang chạy phiên bản cũ và Ctrl+F5 để dùng endpoint/giao diện mới.

Giới hạn review: kiểm chứng database ứng dụng và browser Edge tại 360px/desktop; không tuyên bố xóa dữ liệu ngoài database như backup/WAL/log/export, chứng nhận pháp lý, hiệu năng production hoặc mọi trình duyệt/công nghệ hỗ trợ tiếp cận. Giữ nguyên Minor timeline trùng timestamp đã ghi ở Phase 4; thay đổi này không sửa thứ tự hiển thị đó. Không merge/push/deploy production trong tác vụ này.
