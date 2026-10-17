> **Tài liệu lưu trữ:** nội dung và số liệu bên dưới phản ánh thời điểm lập tài liệu. Các hướng dẫn/quy tắc cũ có thể đã được thay thế; xem [tài liệu hiện hành](../README.md) trước khi thực hiện.

# Điều chỉnh Xin nghỉ — 16/10/2026

Yêu cầu: chỉ sửa luồng Xin nghỉ của User. Chọn **BUỔI SÁNG / CẢ NGÀY** trước, sau đó nhập lý do và xác nhận.

- Nghỉ sáng: trạng thái **Đang nghỉ buổi sáng**, hai lựa chọn **TIẾP TỤC BUỔI CHIỀU OFFICE / REMOTE**; Office xác minh GPS, Remote cần lý do như trước. Khi tiếp tục hiện **Đang làm việc**, chỉ có **CHECK-OUT** cuối ngày, không hiện Nghỉ trưa/Check-out sớm. Sau reload vẫn đúng ca, không suy ra ca bằng giờ thiết bị.
- Nghỉ cả ngày: lưu `FULL_DAY_LEAVE` và lý do, `day_finished=true`, không tạo phiên làm việc giả, không cho bắt đầu/hủy nghỉ để làm việc trong ngày. Ngày hôm sau theo giờ Việt Nam mở lại. Giữ nguyên ngoại lệ Admin xóa ngày/reset và replay UUID cũ.
- Thêm cờ trạng thái `morning_leave` từ sự kiện ngày hiện tại; giữ `lunch_taken` đúng nghĩa nghỉ trưa. Backend không yêu cầu lý do Check-out sớm cho phiên buổi chiều sau nghỉ sáng.
- Không đổi migration, Dashboard/Onsite, Admin history/editor, retention GPS 30 ngày, transaction/lock hoặc payload hash. Giữ enum/đường replay của action hủy nghỉ cũ để UUID đã commit vẫn đọc lại được; action mới từ `FULL_DAY_LEAVE` bị chặn.

Ruling: yêu cầu hiện tại thay thế nghiệp vụ cũ cho hủy nghỉ cả ngày và cách hiển thị ca sau nghỉ sáng. Chuyển các test rollback/GPS/revocation của hủy nghỉ sang tiếp tục sau nghỉ sáng để giữ kiểm chứng transaction/GPS/quyền, đồng thời kiểm tra riêng hủy nghỉ cả ngày bị từ chối. Các API chuyển chế độ khác giữ tương thích.

## Kiểm chứng

- RED: 7 failed (chưa có cờ nghỉ sáng/khóa nghỉ cả ngày, UI chưa chọn loại nghỉ trước lý do).
- GREEN: 7 passed, 1 warning trên PostgreSQL 17/PostGIS test local riêng và Edge headless.
- Hồi quy liên quan: **76 passed, 1 warning**, 247.60s. Giữ kiểm tra rollback cả event/GPS, session/revision/cutoff/revocation, retry UUID, layout mobile/desktop, lịch sử và Dashboard.
- Legacy UUID hủy nghỉ đã commit: **1 passed**, 2.54s; fixture dựng payload/hash và kết quả cũ độc lập, replay không thêm phiên/request.
- Review độc lập và review test bổ sung: không có lỗi chặn; khoảng trống legacy replay đã được bổ sung. Ruling: giữ API chuyển chế độ/nghỉ trưa cũ tương thích; chỉ UI sau nghỉ sáng được thu về CHECK-OUT theo yêu cầu, không mở rộng thay đổi ngoài luồng nghỉ.
- Full suite: **267 passed, 1 warning**, **677.18s** (11m17s), log `.local-tests/phase-5/leave-full.log`, hoàn tất 10:36 ngày 16/10/2026 giờ Việt Nam. Tiến trình đã chạy xong trong lúc phiên làm việc tạm dừng vì quota; khi tiếp tục đã đọc lại log đầy đủ và xác nhận không có thay đổi mã sau lúc khởi chạy. Không dùng các số 218/249/259 của các mốc trước làm kết quả lần này.
- `pip check`: No broken requirements found; `git diff --check` đạt, kiểm tra lại sau khi tiếp tục. Cảnh báo duy nhất là upstream Starlette/httpx như baseline. Không có migration/dependency mới; giữ branch/worktree, không merge/push/deploy.

## Cách chạy

Trong `.worktrees/phase-1`:

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Fixture dùng database test `geoattend_test_<uuid>` riêng. Không tạo/xóa dữ liệu thử hoặc migration mới trên Supabase thật. Khi dùng bản mới, khởi động lại web và Ctrl+F5; không cần migration. Chưa push/deploy/pilot hoặc kiểm chứng GPS/HTTPS trên điện thoại thật.
