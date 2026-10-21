> **Tài liệu lưu trữ:** nội dung và số liệu bên dưới phản ánh thời điểm lập tài liệu. Các hướng dẫn/quy tắc cũ có thể đã được thay thế; xem [tài liệu hiện hành](../README.md) trước khi thực hiện.

# Điều chỉnh CHECK-OUT SỚM — 16/10/2026

Yêu cầu người dùng sau Phase 5: CHECK-OUT SỚM kết thúc ngày làm việc, không CHECK-IN lại; bổ sung lý do bắt buộc khi Check-out sớm.

Thiết kế: mọi `CHECKED_OUT` có `day_finished=true`, `allowed_actions=[]`; ngày hôm sau theo giờ Việt Nam mở lại. Khi chưa có `LUNCH_START`, CHECK_OUT mới cần lý do 1–1000 ký tự sau trim. Check-out sau nghỉ trưa không bắt buộc lý do. Lý do được lưu trong `work_sessions.end_reason` và sự kiện `WORK_END.reason`, hiển thị qua lịch sử hiện có bằng văn bản an toàn. Dùng lại transaction/profile lock, hash/UUID, pending retry và form lý do; không đổi schema/migration.

Kế hoạch thực hiện: viết kiểm thử API/browser đỏ → sửa điều kiện khóa và form lý do → hồi quy toàn bộ → review độc lập → commit. Ruling: yêu cầu mới thay thế quyền bắt đầu lại sau Check-out sớm trong tài liệu/test cũ; chuyển ca kiểm thử GPS lại sang nghỉ trưa/tiếp tục và runtime maintenance sang ngày mới, giữ các kiểm tra persistence/GPS/lock/retention. Ngoại lệ Admin xóa ngày hôm nay/reset và replay UUID đã commit vẫn giữ nguyên.

## Bằng chứng

- RED khóa ngày: 4 failed, 2 passed (Office/Remote Check-out sớm chưa khóa, UI vẫn hiện Check-in); các ca sau nghỉ trưa đã xanh.
- RED lý do: 3 failed, 3 passed (API chấp nhận thiếu lý do và UI chưa có form); chuỗi rỗng/trắng/quá dài đã được schema từ chối.
- GREEN bước đầu: `test_daily_action_ui.py`: 15 passed, 1 warning. Sau đó tăng kiểm tra browser: đóng/mở giữ bản nháp, không gửi khi trắng, mất phản hồi/reload/retry giữ payload, lý do HTML hiển thị như văn bản, không có GPS khi Check-out.
- Lượt focused đầu có hai lỗi browser do thay nhầm nhãn nút trong test; đã sửa đúng CHECK-IN ban đầu và TIẾP TỤC sau nghỉ trưa. Không sửa hành vi sản phẩm để né lỗi test.
- Kiểm thử legacy UUID không có lý do: 1 passed; race xóa ngày/Check-in: 2 passed. Ruling: khi yêu cầu Check-in lấy lock trước xóa, trả `DAY_FINISHED`; khi xóa lấy lock trước, trả `STALE_REVISION`. Cả hai thứ tự đều xóa thành công và không có phiên mở; kỳ vọng cũ chỉ `STALE_REVISION` đã được thay bằng các bất biến này.
- Review độc lập (gồm các test bổ sung): không có lỗi chặn; đề xuất thêm ca legacy replay đã thực hiện và đạt.
- Full suite lần đầu: **255 passed, 3 failed, 1 warning**, 455.57s. Lỗi gồm kỳ vọng cũ trong `test_delete_races_with_restart_or_delete[False]` và hai viewport của `test_account_first_reason_panels_and_lazy_history`. Đã cập nhật thao tác nhập lý do/xác nhận cho layout, giữ và tăng kiểm tra focus/không gửi khi mới mở form; sửa bất biến race như trên. Không bỏ test hoặc nới điều kiện sản phẩm.
- Full suite cuối: **259 passed, 1 warning**, **469.07s**, `PYTEST_EXIT=0`; log local `.local-tests/phase-5/early-checkout-full-02.log`. Cảnh báo upstream Starlette/httpx như baseline. Bao gồm API/PostGIS, browser Office/Remote, Dashboard/Onsite, Admin delete/reset, race/lock/cutoff, retention và UUID cũ/mới.
- `pip check`: **No broken requirements found**; `git diff --check` đạt. Không thay migration hoặc dependency. Giữ branch/worktree hiện tại theo yêu cầu; không merge/push/deploy.

## Cách chạy

Trong `.worktrees/phase-1`, dùng PostgreSQL 17/PostGIS **test local riêng**, không dùng database Supabase thật:

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Fixture tạo/xóa database `geoattend_test_<uuid>` riêng. Không chạy migration mới hoặc ghi dữ liệu thử lên database thật; không merge/push/deploy. Khi chạy bản mới: khởi động lại web rồi Ctrl+F5; không cần migration. Chưa kiểm chứng GPS/HTTPS trên điện thoại thật hoặc pilot; các giới hạn Phase 5 khác vẫn giữ nguyên.
