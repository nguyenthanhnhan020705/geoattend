# GeoAttend — Bàn giao Phase 6

**Trạng thái: phần local/chuẩn bị hoàn tất kiểm chứng; môi trường thật/pilot chưa thực hiện, toàn Phase 6 còn mở.** Làm trong `.worktrees/phase-1`, branch `feat/phase-1-foundation-auth`. Không reset, merge/push/deploy hoặc chạy test trên Supabase thật. Phase 0–5 đã hoàn thành, không triển khai lại.

## Tài liệu hiện hành

1. [Báo cáo và task status](../docs/PHASE_6_VERIFICATION.md), [kế hoạch chi tiết](../docs/superpowers/plans/2026-10-16-phase-6-readiness.md).
2. [Ma trận 19 AC/5 NFR](../docs/PHASE_6_ACCEPTANCE.md), [hiệu năng](../docs/PHASE_6_PERFORMANCE.md).
3. [Runbook HTTPS/secret/quyền DB/worker/log/backup/restore/release/rollback](../docs/PHASE_6_OPERATIONS.md).
4. [Thiết bị thật, phiếu duyệt đích và pilot khoảng 10 User/5 ngày](../docs/PHASE_6_PILOT.md).
5. Hợp đồng nghiệp vụ: LEAVE_FLOW_VERIFICATION, EARLY_CHECKOUT_VERIFICATION, mục 3 bàn giao Phase 0–5. Các mô tả cũ cho Check-in lại/hủy nghỉ cả ngày đã bị thay thế.

## Đã kiểm chứng trong lần tiếp quản

Baseline mới **267 passed, 1 warning, 693.88s**, không sao chép số test lịch sử. Lifecycle Dashboard bfcache probe đỏ–xanh; không hồi sinh polling khi đã 403. Timeline trùng cả hai timestamp có thể sắp UUID đảo thứ tự, chỉ trình bày; probe giữ sự kiện/phiên/trạng thái đúng, Minor còn mở.

Tải thật HTTP loopback/PostGIS, 10 User + Admin và lịch sử tổng hợp: trước tối ưu c20 dài chỉ **93.51% ≤2s** (FAIL). Gom truy vấn Dashboard để giảm giữ khóa, giữ khóa/recheck/retention. Lượt cuối sau sửa review/collector **3651 request, đủ mẫu, 0 lỗi**; c1/c10/c20 **100% ≤2s**, p95 c20 **606.620ms**, max **1405.177ms**. Chỉ chứng minh local; chưa hiệu năng đích. [Số liệu cuối](../docs/evidence/phase6/load-final.json); giữ cả các lượt FAIL/trung gian trong PERFORMANCE.

Restore diễn tập pg_dump/pg_restore thật vào DB UUID riêng, GPS-free và legacy-with-gps: API che quá hạn trước purge, maintenance idempotent, giữ lịch sử/xác minh/tombstone, quyền runtime/checksum; kiểm tra thu hồi session phục hồi trước mở dịch vụ. Backup chuẩn loại dữ liệu bảng GPS, giữ 7 bản ngày mã hóa; sau restore không phục hồi Marker GPS cũ, không tạo điểm giả. Owner dữ liệu/vận hành phải tiếp nhận policy và kiểm tra backup/PITR provider.

Full suite cuối sau sửa review **290 passed, 1 warning, 0 skipped, 586.58s**, exit0; `pip check`, `git diff --check` và kiểm tra diff từ baseline đều đạt, không đổi migration/dependency. Warning upstream Starlette/httpx. Review ba Important đã sửa: proxy log request khi 502, timing unhandled 500 trước body, thiếu diễn tập xóa sau backup. Không có vòng review độc lập thứ hai; test focused và full suite xác minh bản sửa. Không lấy baseline hoặc lượt focused làm kết quả cuối.

## Kiểm thử local an toàn

Cluster test có sẵn `.local-tests/phase-3/pgdata`, PostgreSQL17/PostGIS port 55440, không initdb/xóa cluster. Xác minh pg_isready/PID sở hữu trước thao tác. Fixture chỉ tạo/drop `geoattend_test_<uuid>`; helper restore còn chặn host không loopback/DB không prefix test. Không đọc/in `.env` hoặc chạy launcher ứng dụng để tạo dữ liệu test.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m pip check
git diff --check
```

Đo tải dài chạy riêng theo PERFORMANCE, không cạnh tranh full suite/browser. Không nới assertion 95% để xanh. Giữ kết quả FAIL trước sửa; không coi c1/c10 hoặc local là chứng nhận production. Probe proxy là test mới opt-in: đặt `GEOATTEND_CADDY_BINARY` trỏ tới binary Caddy 2.11.7 local đã xác minh checksum từ release chính thức; thiếu biến này test mới sẽ ghi skip, không phải bằng chứng log proxy đạt. Lượt cuối được cấu hình binary nên phải có kết quả thực tế, không skip.

## Việc còn chờ quyền/điều kiện

Chưa có host/domain/DB/chi phí được duyệt, người trực vận hành/owner dữ liệu/người giữ khóa backup hoặc danh sách người tham gia. Điền phiếu PILOT khi có đích cụ thể rồi xin duyệt tác động: release/DSN/quyền/migration, dữ liệu, chi phí, backup/rollback và xác minh. Không xin quyền chung không rõ đích.

Chưa chạy Caddy/systemd trên host thật; chưa HTTPS/GPS điện thoại thật, bfcache thực đa browser, đo API cấu hình đích, backup mã hóa/retention job/provider logging hoặc pilot 5 ngày. Không mô phỏng thành bằng chứng thật. **Không đánh dấu toàn Phase 6 hoàn thành.**
