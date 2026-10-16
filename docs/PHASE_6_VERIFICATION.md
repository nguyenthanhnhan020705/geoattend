# Phase 6 — Kiểm chứng và sổ thực hiện

Phase 6 **đang thực hiện**, chưa nghiệm thu môi trường thật/pilot. Bắt đầu 16/10/2026 trong `.worktrees/phase-1`, branch `feat/phase-1-foundation-auth`, HEAD `8d96052`, Git sạch. Không reset về `2472785`; không triển khai lại Phase 0–5. Không có AGENTS.md trên đĩa tại root/worktree; áp dụng chỉ dẫn AGENTS trong yêu cầu người dùng.

## Kế hoạch và trạng thái

[Kế hoạch chi tiết](superpowers/plans/2026-10-16-phase-6-readiness.md), [ma trận AC/NFR](PHASE_6_ACCEPTANCE.md).

| Task | Trạng thái | Bằng chứng |
| --- | --- | --- |
| 1 — Baseline/ma trận | Hoàn tất local | 19 AC + 5 NFR; baseline 267 passed, 1 warning, 693.88s |
| 2 — Hồi quy/Minor | Đang hoàn thiện | Lifecycle RED 1 fail/1 pass → refresh GREEN 7 pass; probe timeline 1 pass |
| 3 — Hiệu năng | Đang đo | Unit timing/statistics RED → GREEN 4 pass; burst c20 chưa đạt, phải báo cả kết quả này |
| 4 — Vận hành/restore/log | Đang thực hiện | Guard DB test RED 5 fail → GREEN 5 pass; diễn tập đang chạy |
| 5 — Bàn giao/checklist | Chưa hoàn tất | Thiết bị thật/HTTPS đích/tải đích/pilot đều chưa chạy |

## Baseline mới

Cluster PostgreSQL17/PostGIS test có sẵn `.local-tests/phase-3/pgdata`, chỉ loopback `127.0.0.1:55440`. Kiểm tra pg_ctl không có server; khởi động lại bằng quyền nâng được người dùng duyệt sau lỗi restricted token trong sandbox. Không initdb, không xóa cluster, không dùng `.env`/Supabase. Fixture tạo/drop riêng `geoattend_test_<uuid>`.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
./.venv/Scripts/python.exe -m pytest -q --basetemp=.local-tests/phase-6/baseline -o cache_dir=.local-tests/phase-6/cache
```

Kết quả thực tế **267 passed, 1 warning, 693.88s**; log `.local-tests/phase-6/baseline.log`. Warning upstream Starlette/httpx. Baseline khởi chạy trước khi thêm test/mã Phase 6; các lượt probe sau dùng DB UUID khác. Đây là kết quả local, không phải production hoặc thiết bị thật.

## Quyết định thực hiện

- Yêu cầu ủy quyền lập kế hoạch và tự làm local/test được ưu tiên hơn các bước hỏi lại design/plan kỹ thuật thường lệ của skill. Dùng using-superpowers, writing-plans, executing-plans, TDD, systematic-debugging và verification-before-completion; review cuối theo requesting-code-review.
- Các task đo/probe độc lập được chạy trong lúc baseline chậm, DB riêng. Mẫu tải nghiệm thu cuối phải chạy riêng sau baseline; báo cả lượt burst có cạnh tranh tài nguyên.
- Mô tả hủy nghỉ cả ngày/bắt đầu lại sau Checkout trong STATE_TRANSITIONS/thiết kế cũ chỉ là lịch sử đã bị thay thế; không khôi phục code nghiệp vụ cũ.
- Thời gian nghiệp vụ của load test cố định 09:00 Việt Nam để không làm thao tác từ sau cutoff trên máy chạy buổi tối; API/database/GIS/transaction/HTTP thật, đo perf_counter thật, không có delay giả. Phải nêu giới hạn này khi bàn giao.

## Nhật ký lỗi kiểm thử mới

- Probe bfcache: RED snapshot không đổi 09:00 → 10:00 sau pageshow; pagehide đặt stopped nhưng thiếu pageshow. Sửa lifecycle có kiểm tra persisted, không bỏ trạng thái dừng vì 403; cả nhóm refresh **7 passed, 1 warning, 115.36s**. Đây là lifecycle tổng hợp trên Edge, chưa chứng nhận cache thực đa browser.
- Timeline: ép UUID cố định và timestamp trùng cho WORK_END/LUNCH_START; API không mất sự kiện, phiên đã đóng và resume/Checkout đúng. Cần ghi thứ tự cụ thể từ JUnit probe; không thay schema chỉ để xử lý trình bày.
- Load smoke đầu: 3 lỗi 401 do clock login đã cố định nhưng dependency giữ imported utc_now thực; session hết hạn theo giờ thật buổi tối. Đồng bộ cả hai clock trong harness, không sửa xác thực sản phẩm. Lượt smoke-02 c1/c10 đạt; c20 **173 request, 0 lỗi, 94.21965% ≤2s**, assertion đúng ngưỡng nên báo FAIL. Chưa kết luận nguyên nhân cho tới đo endpoint và lượt chạy riêng.
- Restore lượt đầu: TypeError do TestClient.delete không nhận json; dùng request('DELETE',...) như helper hiện có. Đây là lỗi harness, chưa tác động database đích thật.

## Các cổng còn mở

HTTPS đích, thiết bị thật/GPS thực, đo tải trên cấu hình đích, người vận hành/owner dữ liệu và pilot khoảng 10 người/5 ngày làm việc cần quyền/điều kiện cụ thể. Không ghi completed cho toàn Phase 6 khi các cổng này còn mở.
