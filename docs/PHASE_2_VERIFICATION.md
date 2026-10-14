# GeoAttend — Kiểm chứng Phase 2

**Kết quả cuối:** 85/85 kiểm thử đạt sau review độc lập và một lượt sửa. Migration 003 đã áp dụng trên Supabase; web và maintenance đã chạy với tài khoản database riêng. Tài khoản thực còn 1 ADMIN/1 USER, chưa có dữ liệu chấm công thử trên Supabase.

Phạm vi: Remote, Check-out, bắt đầu lại, lịch sử bản thân, đối soát 20:00 và maintenance độc lập. Office và thao tác nghỉ thuộc Phase 3–4; nghiệp vụ theo thiết kế MVP đã duyệt.

## Kiểm thử

- Baseline Phase 1: 46/46. Lần đầu 45 đạt/1 lỗi do quyền ghi thư mục tạm Windows; đổi đường dẫn basetemp/cache riêng khắc phục, không bỏ qua kiểm thử.
- API: 13 ca thất bại khi endpoint chưa tồn tại, sau triển khai đều đạt. Bao gồm lý do bắt buộc, input thừa, quyền/CSRF, revision, gửi lại UUID, lịch sử cá nhân và rollback toàn bộ khi ghi sự kiện lỗi.
- Thời gian và đồng thời: trước/đúng/sau 20:00 Việt Nam; yêu cầu chờ khóa qua 20:00; đóng bù ngày cũ; replay sau cutoff; nghỉ trưa/nghỉ; cùng UUID chỉ một phiên; UUID khác cùng revision chỉ một thành công; Check-out và maintenance chỉ một kết thúc.
- Browser Edge headless 360px: Remote → tải lại → Check-out → bắt đầu lại → lịch sử. Lý do chứa HTML được hiển thị bằng text, không gọi GPS, không tràn ngang và không lỗi JavaScript. Server đã commit nhưng mất phản hồi: retry giữ nguyên UUID/payload và không tạo phiên thứ hai.
- Launcher: mật khẩu có dấu nháy/backslash/khoảng trắng giữ nguyên; runtime/admin được tách; tiến trình web không thừa hưởng bí mật quản trị.
- Thu hồi phiên trong lúc action chờ khóa: test ban đầu nhận 200, sau sửa nhận 401. Maintenance chờ khóa không cản đặt lại mật khẩu. Role runtime hạn chế chạy được Remote, lịch sử, Check-out và maintenance.
- Review phát hiện hai lỗi Important. Ngày cũ chưa commit bị retry sang ngày mới: thêm `expected_work_date` trong payload/hash, test start và checkout ngày cũ đều bị 409, UUID đã commit vẫn replay qua ngày. Launcher migrate bỏ DSN runtime: test thật ban đầu thiếu quyền schema, sau sửa cấp quyền cho role lấy từ `SELECT current_user`, hỗ trợ username pooler khác tên role SQL.
- Toàn bộ suite cuối: **85 passed, 1 warning trong 66.21 giây**, PostgreSQL 17/PostGIS riêng trên localhost và Edge. `pip check`: không lỗi phụ thuộc. `git diff --check`: không lỗi whitespace. Warning upstream Starlette TestClient/HTTPX được giữ nguyên.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55439/postgres'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.local-tests/phase-2/tmp-final -o cache_dir=.local-tests/phase-2/cache
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

## Review và quyết định

Review độc lập: agent `phase2_final_review`, GPT-6-astra, chỉ đọc; không truy cập Supabase/bí mật. Base `3d5a5b7`, head trước sửa `ed7f4a2`. Không Critical, hai Important đã sửa bằng regression trước code; không gọi review lần hai.

1. Tiếp tục trong linked worktree và phương pháp inline đã chọn. Không merge/push; nếu sai, thay đổi local có thể hoàn nguyên.
2. Bash không có; ghi checklist/ledger bằng PowerShell thay helper Bash, vẫn lưu RED/GREEN/commit. Chi phí: khác cách ghi chứng cứ.
3. Người dùng đã ủy quyền tự code/test; thiết kế đã duyệt là nguồn quyết định, không xin lại quyền phạm vi. Chi phí nếu sai: sửa lựa chọn triển khai local.
4. Migration 003 thêm bốn cột kết quả thao tác và index ngày đến hạn để replay nguyên kết quả cũ. Không lưu payload/GPS. Chi phí: schema có thêm metadata; migration cũ giữ nguyên.
5. Kiểm tra lại phiên xác thực dưới khóa profile. Chi phí: thêm SELECT, đổi lại yêu cầu đã thu hồi không được ghi chấm công.
6. Đóng bù được commit trước khi trả lỗi xung đột action; lỗi SQL vẫn rollback toàn bộ action. Chi phí: thao tác bị từ chối vẫn có thể kích hoạt đối soát ngày quá hạn, đúng thiết kế.
7. Bổ sung `expected_work_date` bắt buộc để ràng buộc ý định với ngày đang hiển thị. UUID đã commit được replay trước kiểm tra ngày. Chi phí: client cũ thiếu trường phải tải lại; không đổi quy tắc nghiệp vụ.
8. Migration nhận cả DSN quản trị/runtime, xác định role thực qua kết nối runtime thay vì đoán từ username pooler. Web/maintenance vẫn chỉ nhận runtime. Chi phí: thêm một kết nối khi migrate và yêu cầu runtime tồn tại trước đó.
9. Các mục reviewer không đánh giá: Office/GPS/nghỉ/Admin dashboard giữ ở Phase 3–5; provisioning worker production/uptime/benchmark giữ ở Phase 6; Supabase được root kiểm tra riêng. Chi phí: chưa tuyên bố MVP/pilot hoàn thành.

**Minor hoãn:** test browser Phase 2 hiện yêu cầu Edge, chưa tuân theo fallback `GEOATTEND_BROWSER_CHANNEL=chromium` của test Phase 1. Bộ suite này đã chạy trên Windows có Edge; máy không có Edge cần bổ sung hỗ trợ fallback trước chạy đầy đủ.

## Chạy thực và giới hạn

- Launcher kết nối Supabase bằng `geoattend_runtime` và `postgres`, TLS được xác nhận. Migration 003 thành công; đủ ba phiên bản migration, số tài khoản giữ nguyên.
- Web `/api/health` trả 200 và database ok; `/login` trả 200; attendance chưa đăng nhập trả 401. OpenAPI yêu cầu `expected_work_date`, xác nhận tiến trình chạy mã mới.
- Maintenance đã chạy một lần và đang chạy mỗi phút trong phiên Terminal do công cụ quản lý. Dọn một phiên đăng nhập đã hết hiệu lực; không sửa tài khoản hay tạo chấm công thực để kiểm thử.
- Khởi động nền Windows bằng Start-Process bị công cụ từ chối `blocked by policy`; đã chạy thành công bằng các phiên Terminal được quản lý, không cần người dùng làm bước thay thế.
- Máy phải bật để worker chạy mỗi phút. Khi tắt máy, lần chạy lại/API đọc xử lý bù với mốc nghiệp vụ 20:00. Production cần worker liên tục.
- Không tuyên bố pilot, HTTPS/GPS hay ngưỡng 95% API ≤2s đã đạt: thuộc các phase sau.
- PostgreSQL thử nghiệm đã dừng sau kiểm chứng. Xóa workspace ghi chú `.superpowers/sdd/2026-10-14-phase-2-remote-attendance` bị kiểm soát tự động từ chối `blocked by policy`; giữ lại thư mục đã được Git ignore, không thử vượt kiểm soát. Branch và worktree được giữ để tiếp tục phát triển.
