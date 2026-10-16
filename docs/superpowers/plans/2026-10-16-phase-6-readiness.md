# Phase 6 Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** kiểm chứng MVP hiện hành trên môi trường riêng, chuẩn bị vận hành và các cổng nghiệm thu môi trường thật.

**Architecture:** giữ FastAPI/PostGIS và worker hiện có. Bổ sung kiểm thử, công cụ đo tải/diễn tập riêng và cấu hình triển khai mẫu; không đổi mô hình chấm công.

**Tech Stack:** Python 3.13, PostgreSQL 17/PostGIS, pytest, Playwright/Edge, Uvicorn, PostgreSQL client utilities, Caddy/systemd mẫu.

**Spec:** yêu cầu Phase 6 ngày 16/10/2026; `docs/LEAVE_FLOW_VERIFICATION.md`, `docs/EARLY_CHECKOUT_VERIFICATION.md`, hợp đồng mục 3 `handoff/README_PHASE_0_5.md`; BRD AC-01–19/NFR-01–05.

## Global Constraints

- Chỉ `.worktrees/phase-1`; HEAD khởi điểm `8d96052`, branch `feat/phase-1-foundation-auth`, working tree sạch.
- Giữ khóa ngày sau mọi Check-out/nghỉ cả ngày; ca từ server, cutoff đúng 20:00 Việt Nam, Admin không chấm công.
- Giữ profile lock/transaction/recheck/replay cũ/tombstone, ST_Covers, không buffer/accuracy gate, GPS đúng 30 ngày.
- Không sửa migration đã áp dụng, không nới/bỏ test cũ, không dùng Supabase thật cho test.
- Không push/merge/deploy/pilot hoặc tác động đích thật khi chưa có quyền riêng.
- Người dùng đã ủy quyền tự lập kế hoạch và thực hiện local/test; không lặp lại approval kỹ thuật thường lệ của skill.

## Review Focus

- Restore khôi phục GPS quá hạn hoặc lịch sử đã bị Admin xóa: cô lập, purge và đối soát xóa trước mở dịch vụ.
- Dashboard phục hồi document cache sau pagehide: refresh hoạt động lại, không hồi sinh polling sau 403.
- Sự kiện cùng timestamp: xác định tác động hiển thị, không đổi thứ tự nghiệp vụ dựa trên UUID.
- Tải Dashboard khóa toàn bộ profile cạnh tranh thao tác User: đo đồng thời đọc/ghi và tỷ lệ lỗi.
- Log HTTP/exception có query/token/GPS hoặc DSN: không thu thập body/query, kiểm tra trường hợp lỗi.

### Task 1: Baseline và ma trận nghiệm thu

**Files:** `docs/PHASE_6_ACCEPTANCE.md`, kế hoạch này.
**Interfaces:** test fixture tạo/drop database `geoattend_test_<uuid>` ở cluster local 55440; ma trận cung cấp test/gap/gate cho các task sau.

- [ ] Đọc tài liệu theo thứ tự, kiểm tra Git/worktree và xác minh cluster test, không đọc `.env`.
- [ ] Chạy full suite baseline, lưu log `.local-tests/phase-6/baseline.log`; Expected: ghi số thực tế và mọi lỗi, không mặc định 267.
- [ ] Lập đủ 19 AC và 5 NFR với test hiện có, môi trường, tiêu chí và phần cần bằng chứng thật.
- [ ] Kiểm tra đủ ID bằng script/assertion và `git diff --check`; commit tài liệu.

### Task 2: Hồi quy và Minor

**Files:** `tests/integration/test_admin_dashboard_refresh.py`, `app/static/js/admin-dashboard.js`, `tests/integration/test_phase6_readiness.py`, báo cáo Phase 6.
**Interfaces:** dùng API/clock/fixtures hiện có; không đổi payload hoặc migration.

- [ ] Test `pagehide` rồi `pageshow(persisted=true)` phải tải snapshot mới và duy trì đúng một timer; test 403 không phục hồi polling. Chạy RED trước sửa JS.
- [ ] Sửa lifecycle tối thiểu, chạy GREEN cùng toàn nhóm refresh.
- [ ] Probe timeline bằng ID cố định có thứ tự ngược và timestamp trùng; ghi mức ảnh hưởng, giữ tương thích nếu chỉ presentation và không có thứ tự tổng quát an toàn.
- [ ] Rà soát test quyền/GIS/concurrency/retry/cutoff/ngày mới/retention; bổ sung ca thiếu có ý nghĩa. Commit task khi focused xanh.

### Task 3: Đo tải backend

**Files:** `scripts/phase6_load.py`, `tests/test_phase6_load.py`, `tests/integration/test_phase6_load.py`, `docs/PHASE_6_PERFORMANCE.md`.
**Interfaces:** đo ASGI từ request vào đến response body cuối bằng perf_counter, không body/query/secret; dữ liệu tổng hợp DB riêng, 10 User + Admin, tải bằng HTTP loopback.

- [ ] RED kiểm tra thống kê nearest-rank p50/p95/p99, tỷ lệ ≤2000ms tính cả lỗi và endpoint template không chứa UUID/query; rồi code GREEN.
- [ ] Harness tự tạo DB local riêng, migration và user tổng hợp, chạy web độc lập, warmup tách riêng; không dùng launcher `.env`.
- [ ] Đo concurrency 1/10/20, request đọc status/history/dashboard/onsite và ghi Office/Remote/nghỉ/checkout/replay; ghi số lượng, latency, error, CPU/RAM/version/cấu hình và giới hạn.
- [ ] Đạt local khi ≥95% mẫu hoàn tất ≤2s và không lỗi ngoài kỳ vọng; môi trường đích vẫn pending. Commit.

### Task 4: Vận hành, backup/restore và log

**Files:** `deploy/`, `scripts/phase6_restore_drill.py`, `tests/integration/test_phase6_restore.py`, `docs/PHASE_6_OPERATIONS.md`.
**Interfaces:** dùng `scripts.maintenance.run_once`, `apply_migrations/grant_runtime`, pg_dump/pg_restore; runtime/migration role tách biệt.

- [ ] Diễn tập dump/restore vào DB riêng với GPS hết hạn/chưa hết hạn và tombstone; kiểm tra API che trước purge, maintenance purge trước readiness, phiên/lịch sử/checksum/quyền còn đúng.
- [ ] Kiểm tra log và HTTP lỗi không lộ sentinel mật khẩu/token/GPS/DSN; sửa RED/GREEN nếu gặp rò rỉ.
- [ ] Chuẩn bị HTTPS same-origin, cookie Secure, private bind/proxy trust, worker độc lập/restart, health/log/alert, secret và quyền DB, migration/rollback.
- [ ] Chốt chính sách backup mẫu: mã hóa, 7 bản ngày, purge tự động, không archive kéo dài; owner vận hành và owner dữ liệu phải được chỉ định trước go-live; restore phải đối soát dữ liệu xóa sau backup.
- [ ] Chạy diễn tập thật bằng PostgreSQL tools local và lưu kết quả đã khử nhạy cảm; commit.

### Task 5: Thiết bị thật/pilot và bàn giao

**Files:** `docs/PHASE_6_PILOT.md`, `docs/PHASE_6_VERIFICATION.md`, `handoff/README_PHASE_6.md`, README/ROADMAP/DEVELOPMENT/tổng kết.
**Interfaces:** nhận bằng chứng Task 1–4; không biến mô phỏng/browser headless thành thực nghiệm thiết bị.

- [ ] Checklist điện thoại/máy tính, HTTPS/GPS permission, mạng yếu/mất phản hồi/retry, cutoff và Dashboard; mẫu kết quả bỏ trống có chủ ý khi chưa chạy.
- [ ] Pilot khoảng 10 User/5 ngày làm việc: vai trò, lịch, phản hồi ẩn danh, số đo API/GPS aggregate, tiêu chí dừng/đạt và owner ký.
- [ ] Chuẩn bị phiếu duyệt đích triển khai: host/domain/DB, diff/migration, dữ liệu, chi phí cần báo giá, backup/rollback/xác minh; chưa xin tác động khi chưa có đích cụ thể.
- [ ] Full suite cuối, pip check, diff --check; Expected: báo đúng số pass/fail/warning, lưu log và giới hạn.
- [ ] Review độc lập toàn diff theo executing-plans; sửa finding quan trọng bằng RED/GREEN; cập nhật trạng thái và commit. Phase 6 vẫn chưa hoàn tất nếu thiếu HTTPS/thiết bị thật/tải đích/pilot.

## Trạng thái thực hiện

Task 1–4 hoàn tất local/chuẩn bị; Task 5 checklist/handoff đã soạn, đang full suite/review cuối. Kết quả/commit và các quyết định phát sinh ghi trong `docs/PHASE_6_VERIFICATION.md`; scratch ledger ở `.superpowers/sdd/2026-10-16-phase-6-readiness/progress.md`. Toàn Phase 6 còn mở các cổng HTTPS/thiết bị thật/tải đích/pilot.
