# Phase 6 — Kiểm chứng và sổ thực hiện

Phase 6 **chưa hoàn thành toàn bộ**; phần local/chuẩn bị đang xác minh lại sau review, còn các cổng môi trường thật/pilot. Bắt đầu 16/10/2026 trong `.worktrees/phase-1`, branch `feat/phase-1-foundation-auth`, HEAD `8d96052`, Git sạch. Không reset về `2472785`; không triển khai lại Phase 0–5. Không có AGENTS.md trên đĩa tại root/worktree; áp dụng chỉ dẫn AGENTS trong yêu cầu người dùng.

## Kế hoạch và trạng thái

[Kế hoạch chi tiết](superpowers/plans/2026-10-16-phase-6-readiness.md), [ma trận AC/NFR](PHASE_6_ACCEPTANCE.md).

| Task | Trạng thái | Bằng chứng |
| --- | --- | --- |
| 1 — Baseline/ma trận | Hoàn tất local | 19 AC + 5 NFR; baseline 267 passed, 1 warning, 693.88s |
| 2 — Hồi quy/Minor | Hoàn tất local | Lifecycle RED 1 fail/1 pass → refresh GREEN 7 pass; probe timeline 1 pass; chờ cache thực đa browser |
| 3 — Hiệu năng | Hoàn tất local | Lượt cuối sau review 3651 request/đủ mẫu, 0 lỗi, cả c1/c10/c20 100%≤2s; p95 c20 606.620ms; tải đích pending |
| 4 — Vận hành/restore/log | Hoàn tất chuẩn bị/local | Guard RED → GREEN; 12 test timing/log/restore đạt; mẫu triển khai chưa chạy trên host đích |
| 5 — Bàn giao/checklist | Full suite đạt; chờ review cuối | 286 passed/1 warning; checklist/phiếu duyệt đích/roadmap/handoff sẵn sàng; cổng T/P chưa chạy |

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
- Timeline: ép UUID cố định và timestamp trùng; JUnit `.local-tests/phase-6/timeline.xml` ghi `LUNCH_START,WORK_END,WORK_START`. API không mất sự kiện, phiên đã đóng và resume/Checkout đúng; probe **1 passed, 12.45s**. Đây là Minor trình bày: không có thứ tự nhân quả đáng tin giữa UUID khi cả hai timestamp bằng nhau, có thể gặp nhiều sự kiện ghép (không chỉ lunch). Không thay schema/đoán ưu tiên event_type vì có thể đảo các thao tác thực khác. Giữ event IDs/thời gian/replay, owner biết giới hạn khi xem timeline; không chứng nhận thứ tự đẹp cho trường hợp này.
- Load smoke đầu: 3 lỗi 401 do clock login đã cố định nhưng dependency giữ imported utc_now thực; session hết hạn theo giờ thật buổi tối. Đồng bộ cả hai clock trong harness, không sửa xác thực sản phẩm. Lượt smoke-02 c1/c10 đạt; c20 **173 request, 0 lỗi, 94.21965% ≤2s**, assertion đúng ngưỡng nên báo FAIL. Chưa kết luận nguyên nhân cho tới đo endpoint và lượt chạy riêng.
- Restore lượt đầu: TypeError do TestClient.delete không nhận json; dùng request('DELETE',...) như helper hiện có. Đây là lỗi harness, chưa tác động database đích thật.
- Tải dài trước tối ưu (rounds=10): mỗi mức **1217 request**; c1 100%, p95 128.283ms; c10 99.096%, p95 1058.781ms; c20 93.509%, p95 2171.957ms, 0 lỗi HTTP. Log load-measure-01 giữ nguyên. Dashboard giữ khóa toàn bộ profile trong nhiều truy vấn/User. Test query bound RED `(6,24)` khi 1→10 User chưa có ngày; gom truy vấn ngày/phiên/xác minh và chỉ gọi reconcile cho User có ngày quá cutoff, giữ nguyên khóa/recheck/clock và bộ đọc retention. Cần GREEN hồi quy và đo lại riêng sau sửa.
- GREEN sau tối ưu: nhóm query/Dashboard/Onsite/unit/restore **35 passed, 1 warning, 103.17s**. Tải riêng `load-measure-02` **3 passed, 164.10s**: mỗi mức 1217 request; c1 100%/p95 108.394ms, c10 100%/579.407ms, c20 99.91783%/806.608ms; 0 lỗi, max c20 2009.836ms. Đạt ngưỡng local, vẫn 1 request >2s; không chứng nhận production. Chi tiết [PERFORMANCE](PHASE_6_PERFORMANCE.md).

## Vận hành, dữ liệu và kiểm tra log

Lượt `ops-final`: **12 passed, 1 warning, 16.30s**. Gồm 4 test timing/statistics/app metrics, 1 test subprocess nạp logging.json thật, 5 guard test DSN, 2 diễn tập restore. `SafeFormatter` không đưa message/traceback của uvicorn/psycopg ra log; sentinel mật khẩu/token/GPS/query không xuất hiện. Cấu hình web tắt Uvicorn access log, Caddy không bật access log, worker mẫu cũng nạp formatter. Chưa audit DB/proxy/APM/backup log trên provider thật.

Diễn tập pg_dump/pg_restore custom thật ở DB UUID riêng: GPS-free chuẩn và legacy-with-gps. Cả hai giữ checksum 001–004, runtime không CREATE schema/DELETE profiles, lịch sử/xác minh và tombstone; replay dữ liệu đã xóa trả HISTORY_DELETED. Legacy giữ GPS chưa hết hạn, che GPS hết hạn trước worker và purge đúng một bản ghi; lần hai 0. GPS-free không khôi phục bất kỳ dữ liệu bảng office_locations (cả GPS còn hạn), mọi phiên/xác minh vẫn còn, không Marker giả. Thu hồi toàn bộ session phục hồi rồi kiểm tra 401 và login mới thành công. [Kết quả tổng hợp](evidence/phase6/restore.json).

[Runbook](PHASE_6_OPERATIONS.md) và `deploy/` chuẩn bị HTTPS same-origin/cookie Secure, proxy trust loopback, role/secret riêng, release/rollback, worker/health/log/alert, backup GPS-free mã hóa mỗi ngày giữ 7 bản/7 ngày, restore purge/đối soát xóa/thu hồi session trước mở public. Chưa có host Linux/Caddy/systemd/secret store hoặc job backup/retention thật, chưa validate trên host đích. RPO24h/RTO4h là mục tiêu đề xuất cho owner duyệt, không phải SLA đã chứng minh.

## Xác minh cuối

Ngày 16/10/2026, log `.local-tests/phase-6/full-final-01.log`: **286 passed, 1 warning, 499.47s**, exit code **0**; gồm 267 ca baseline và 19 ca thêm, không bỏ/nới test cũ. Bao gồm API/database/PostGIS, quyền, transaction/race, retry/replay legacy/tombstone, cutoff/ngày mới, retention, UI User/Admin, Dashboard/Onsite, đo tải smoke và restore thật hai chính sách. Warning duy nhất là upstream Starlette/httpx như baseline.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
# Không đặt GEOATTEND_LOAD_ROUNDS cho full suite smoke mặc định.
./.venv/Scripts/python.exe -m pytest -q --basetemp=.local-tests/phase-6/full-final-01 -o cache_dir=.local-tests/phase-6/cache-final
./.venv/Scripts/python.exe -m pip check
git diff --check
git diff 8d96052 --check
```

Checks sau full suite lúc **22:23 Việt Nam**: `pip check` → **No broken requirements found**; cả hai diff check đạt; migration 001–004 và dependency/lockfiles không đổi. JSON load/restore đã khử nhạy cảm trong docs/evidence/phase6; các log/DB/dump/ảnh test chỉ ở thư mục ignored, không commit dữ liệu người dùng/bí mật. Đọc `.env`/DSN thật không cần cho công việc này và không thực hiện.

Sandbox Windows lỗi tạo process 1909 trong giai đoạn review/checks; process pytest đã khởi chạy vẫn hoàn tất. Lệnh kiểm tra mới dùng quyền nâng được duyệt; không đổi account/credential hoặc hạ cấu hình sandbox. Không có tác động Supabase thật, deploy, merge/push hoặc gửi thông báo cho người khác.

Commit theo task: `0eb1d06` baseline/ma trận; `aae1200` lifecycle/Minor; `f2614b8` đo/tối ưu/timing; `efc6e0e` runbook/log/restore; `6016369` thiết bị/pilot/handoff. Commit bằng chứng cuối theo Git log sau review.

## Review độc lập và lượt sửa cuối

Reviewer đọc range `8d96052..6016369`, không sửa code/Git/DB. Không Critical, có ba Important được kiểm chứng và xử lý trong một lượt sửa:

1. Caddy error logger độc lập access log có thể ghi query/header khi upstream 502. Tải Caddy **2.11.7** Windows chính thức vào `.local-tests`, xác minh **SHA512** theo file checksum release trước khi chạy; không cài service. Probe HTTP loopback với upstream socket không listen đã RED vì TOKEN/GPS/PASSWORD_SENTINEL lọt log; cấu hình global default `exclude http.log.error` → GREEN **1 passed, 0.43s**. Python SafeFormatter không được dùng để che lỗ hổng proxy này; target/provider vẫn cần audit.
2. Timing đặt trong add_middleware đứng bên trong ServerErrorMiddleware, ghi sớm khi unhandled 500. Test trên stack ứng dụng thật với final send trễ 20ms đã RED thứ tự metric→start→body. Đưa wrapper ra ngoài toàn bộ stack qua subclass FastAPI giữ interface/state; GREEN thứ tự start→body→metric, đúng một mẫu 500 có gồm thời gian send trễ. Nhóm timing/log/health **9 passed, 1 warning, 2.73s**.
3. Restore ban đầu chỉ xóa trước dump, chưa chứng minh xóa sau backup. Bổ sung dump trước → xóa source qua Admin API → restore cô lập thấy dữ liệu sống lại → đối soát account/ngày trong sổ xóa và revision/username mới nhất qua API → không còn history/session/event/GPS, replay HISTORY_DELETED. Nhóm restore **3 passed, 1 warning, 15.35s**. Runbook dừng gate nếu ngày active/không có sổ xóa, không ép trạng thái để xóa.

Trong lượt đo lại phát hiện một `/api/auth/me` warmup hoàn tất sau lúc clear collector (1218 thay vì 1217 ở c10); không dùng lượt đó làm số liệu cuối. Đã thêm collector chọn request ngay tại đầu bằng header riêng của harness, đếm request gửi độc lập, chờ callback cuối và assert không có warmup/mất mẫu. Unit RED thiếu collector → GREEN **7 passed, 1 warning, 3.17s** cho timing/log. Lượt `load-final-verified` **3 passed, 83.97s**: cả ba mức 1217 gửi/1217 mẫu, 0 thiếu/thừa, 0 lỗi, 100% ≤2s; p95 c20 **606.620ms**, max **1405.177ms**. [JSON cuối](evidence/phase6/load-final.json). Đang chạy lại full suite; 286 trước review giữ là lịch sử.

## Các cổng còn mở — phần môi trường thật

HTTPS đích, thiết bị thật/GPS thực, đo tải trên cấu hình đích, người vận hành/owner dữ liệu và pilot khoảng 10 người/5 ngày làm việc cần quyền/điều kiện cụ thể. Không ghi completed cho toàn Phase 6 khi các cổng này còn mở.
