# Weekly PDF Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task in this session. Steps use checkbox (`- [ ]`) syntax for tracking. No parallel agents are needed for implementation; task interfaces depend on each other.

**Goal:** User nộp/thay một PDF mỗi tuần trong hạn; Admin xem/tải, User nhận đúng nhắc Chủ nhật và thông báo tuần trước chưa nộp.

**Architecture:** Module `app/reports/` riêng dùng cookie session, CSRF/Origin và Psycopg hiện có. PDF lưu cùng metadata trong PostgreSQL, profile lock trước report lock; request đọc có giới hạn trước khi mở transaction ghi. Trang User/Admin riêng và module nhắc hạn nhỏ dùng chung; không thêm PDF vào snapshot chấm công.

**Tech Stack:** Python 3.13, FastAPI, PostgreSQL/PostGIS, Psycopg, HTML/CSS/JavaScript thuần, pytest, Playwright/Edge. Không thêm dependency hoặc dịch vụ lưu file.

**Spec:** [WEEKLY_REPORTS.md](../../features/WEEKLY_REPORTS.md), người dùng duyệt ngày 18/10/2026 bằng yêu cầu “triển khai nhé”, sau đó giới hạn thay đổi chính ở chức năng báo cáo, giữ nguyên nghiệp vụ các phần cũ. Triển khai inline trong worktree hiện tại.

## Global Constraints

- Làm tại `.worktrees/phase-1`, branch `feat/phase-1-foundation-auth`; baseline đặc tả `a24f3df`. Giữ thay đổi sẵn có, không reset/clean.
- Một PDF/User/tuần từ thứ Hai đến Chủ nhật theo giờ Việt Nam; khóa tuần cũ từ đúng 00:00 thứ Hai kế tiếp, gồm thay thế. Không phụ thuộc cutoff chấm công 20:00.
- Tối đa **10 MB = 10.000.000 byte**; chỉ `.pdf`, `application/pdf`, nhận diện header/kết thúc PDF; đây không phải bộ quét mã độc.
- Chủ nhật chưa nộp: **BẠN CÒN 1 NGÀY ĐỂ NỘP BÁO CÁO NHÉ!!**
- Tuần liền trước chưa nộp: **TUẦN VỪA RỒI BẠN CHƯA NỘP BÁO CÁO. HÃY TRÌNH BÀY NỘI DUNG ĐÓ GỘP VỚI TUẦN NÀY NHÉ!**
- Không truy thu trước tuần chứa `max(profiles.created_at, schema_migrations.applied_at của 005)`; không suy đoán nội dung PDF đã gộp.
- User chỉ đọc/ghi bản thân, Admin chỉ đọc báo cáo User; session phải còn hợp lệ dưới khóa; CSRF/Origin cho upload, không PDF/storage browser hoặc log nhạy cảm.
- Migration mới `005_weekly_reports.sql`; checksum 001–004 và dependency giữ nguyên. Chỉ test DB riêng; không chạy launcher `.env`, migration thật, push/merge/deploy.
- Giữ PDF hiện hành qua các tuần; thay thế không giữ bản cũ trong app. Backup cũ vẫn có thể chứa bản đã thay theo retention backup hiện hành.
- Kiểm chứng local không hoàn tất HTTPS/thiết bị/GPS/hiệu năng đích/pilot Phase 6.

## Review Focus

1. Upload chờ khóa qua nửa đêm Chủ nhật không được lọt vào tuần cũ; Task 2 kiểm tra clock và session sau lock.
2. PDF tiếng Việt, tên file có dấu nháy/CRLF/đường dẫn không tạo XSS/header injection; Task 3 kiểm tra sanitization và Content-Disposition.
3. Timeout rồi retry sau khi tuần đã khóa không được ghi mới/khôi phục bản cũ; Task 2 kiểm tra replay gần nhất và stale revision.
4. User tạo mới hoặc bật chức năng vào giữa tuần không nhận thiếu báo cáo trước đó; Task 1/2 kiểm tra mốc áp dụng, kể cả sau restore.
5. Tab đang mở qua đổi tuần hoặc session/account đổi trong tab không gửi lại file dưới danh tính/tuần khác; Task 4 kiểm tra trạng thái, UUID và payload được giữ trong bộ nhớ.

## File Map và hợp đồng chung

| File | Trách nhiệm |
| --- | --- |
| `migrations/005_weekly_reports.sql`, `app/db/migrations.py` | Schema mới và grant runtime hẹp |
| `app/reports/policy.py` | Tuần Việt Nam, giới hạn, tên file/PDF, nguyên văn thông báo |
| `app/reports/service.py` | Đọc trạng thái/list/file, upload nguyên tử, quyền/lock/retry |
| `app/reports/schemas.py`, `app/reports/routes.py`, `app/reports/__init__.py` | Metadata input/output và User/Admin API |
| `app/main.py` | Đăng ký router, protected pages và no-store API mới |
| `app/static/user-weekly-reports.html`, `app/static/admin-weekly-reports.html` | Trang nộp và trang Admin |
| `app/static/js/reports-api.js` | Fetch binary upload; dùng auth/CSRF từ `/api/auth/me`, timeout và API errors |
| `app/static/js/report-notices.js` | Tải/trình bày nhắc hạn dùng chung trên hai trang User |
| `app/static/js/user-weekly-reports.js`, `app/static/js/admin-weekly-reports.js` | Form upload/replacement/retry/history và filter Admin |
| `app/static/user.html`, `app/static/admin-*.html`, `app/static/js/user.js`, `app/static/css/app.css` | Điều hướng và nhắc hạn, responsive theo UI hiện tại |
| `tests/test_weekly_report_policy.py`, `tests/integration/test_weekly_reports*.py` | Policy, DB/API, race và browser |
| `tests/integration/test_migrations.py`, `tests/integration/test_phase6_restore.py`, `tests/test_pages.py` | Mở rộng test schema/runtime/restore/trang có sẵn |
| `docs/features/WEEKLY_REPORTS.md`, overview/index/roadmap/usage/development/Phase 5/operations | Hành vi, cách chạy và bằng chứng thực tế |

Metadata công khai của một báo cáo: `id`, `user_id`, `week_start`, `week_end`, `filename`, `size_bytes`, `first_submitted_at`, `submitted_at`, `revision`; không có bytes/hash/UUID kỹ thuật. Ngày ISO, timestamp ISO có timezone.

API cố định để frontend/backend thống nhất:

- `GET /api/weekly-reports/status` → `{server_time, week_start, week_end, deadline, max_bytes, report, notices:[{code,message,week_start,week_end}]}`.
- `GET /api/weekly-reports?page=1&page_size=20` → `{items,total,page,page_size}`, chỉ báo cáo đã nộp của chính User.
- `PUT /api/weekly-reports/{week_start}?request_id=<uuid>&expected_revision=<int>`: body binary, Content-Type PDF, CSRF; header `X-Report-Filename` chứa tên file encode UTF-8 để tránh tên file xuất hiện trong access log URL. Trả metadata sau ghi/replay, HTTP 200; không nhận User ID.
- `GET /api/weekly-reports/{report_id}/file?download=false` → PDF inline hoặc attachment; chỉ owner.
- `GET /api/admin/weekly-reports?week_start=<Monday>&user_id=<uuid>&page=1&page_size=20` → `{week_start,week_end,items,total,page,page_size}`. Mỗi item gồm User `id,username,full_name,is_active`, `status` (`SUBMITTED`, `PENDING`, `OVERDUE`, `NOT_APPLICABLE`) và `report` hoặc null. Bộ lọc có thể bỏ; mặc định tuần server hiện tại.
- `GET /api/admin/weekly-reports/{report_id}/file?download=false` → PDF của User, chỉ Admin.
- Lỗi dùng `ApiError` sẵn có: 413 `REPORT_TOO_LARGE`, 422 `INVALID_PDF`/`INVALID_WEEK`/`INVALID_INPUT`, 409 `REPORT_WEEK_CLOSED`/`FUTURE_WEEK`/`STALE_REVISION`/`REQUEST_CONFLICT`, 404 `REPORT_NOT_FOUND`; auth dùng mã hiện có.

## Preparation trước Task 1

- [ ] Read skills executing-plans/TDD/systematic-debugging/verification as applicable before work. Detect existing linked worktree, inspect clean/dirty changes, available Python/Edge/PostgreSQL client/Caddy and existing local test cluster using read-only checks; never open `.env` or delete `.local-tests`. No dependency install/upgrade when environment already exists.
- [ ] Use `GEOATTEND_TEST_DATABASE_URL` for existing loopback test cluster `127.0.0.1:55440` only after verifying it is the isolated test service; fixture creates own UUID DB. If cluster stopped, reuse existing cluster with appropriate authorization; do not initdb over it. Keep logs/artifacts under `.local-tests/weekly-reports/`.
- [ ] Run a fresh baseline before product edits using the full-suite command from Task 6 with `--basetemp=.local-tests/weekly-reports/baseline` and separate cache. Record actual result; if failures pre-exist, diagnose and report them before attributing changes to reports.

## Task 1: Schema, policy tuần và kiểm tra file

**Files:** Create `migrations/005_weekly_reports.sql`, `app/reports/__init__.py`, `app/reports/policy.py`; modify `app/db/migrations.py`, `tests/integration/test_migrations.py`; create `tests/test_weekly_report_policy.py`.

**Interfaces:** `week_start_for(now: datetime) -> date`, `week_deadline(week_start: date) -> datetime`, `first_required_week(created_at: datetime, enabled_at: datetime) -> date`, `validate_pdf(filename: str, content_type: str, content: bytes) -> str` (sanitized filename or ApiError). Constants `MAX_PDF_BYTES=10_000_000`, `SUNDAY_REMINDER`, `OVERDUE_REMINDER`.

- [ ] Write policy tests `test_vietnam_week_and_deadline` for `2026-10-25T16:59:59Z → 2026-10-19` and `2026-10-25T17:00:00Z → 2026-10-26`, plus year boundary; `test_first_required_week_uses_later_activation`; `test_pdf_limit_and_filename_sanitization` (empty/fake/mime/wrong suffix/exact limit/limit+1/Unicode/path/CRLF).

```python
assert week_start_for(datetime.fromisoformat('2026-10-25T16:59:59+00:00')) == date(2026, 10, 19)
assert week_start_for(datetime.fromisoformat('2026-10-25T17:00:00+00:00')) == date(2026, 10, 26)
assert week_deadline(date(2026, 10, 19)).isoformat() == '2026-10-26T00:00:00+07:00'
assert MAX_PDF_BYTES == 10_000_000
```

- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_weekly_report_policy.py -q -p no:cacheprovider`; expect RED missing module/functions before implementation.
- [ ] Implement policy using aware datetime and fixed Vietnam offset/established clock conventions. Filename strips path/control chars, bounded length, retains `.pdf`; validate bytes begin `%PDF-` and trimmed file ends `%%EOF`, no file execution.
- [ ] Extend migration tests to expect 005, UNIQUE User/week, Monday, byte length/size constraints, runtime SELECT/INSERT/UPDATE and no DELETE. New table UUID PK + profile FK, `week_start`, `filename`, `pdf bytea`, `size_bytes`, `content_sha256`, `first_submitted_at`, `submitted_at`, `revision`, `request_id`, `request_hash`; positive revision and file size. Add unique `(user_id,week_start)` and useful week/User index.
- [ ] Run schema tests RED before adding 005; add SQL/grant and run policy+migration tests GREEN on isolated DB. Never loosen tests for 001–004; update only expected new migration/table.
- [ ] Commit explicit Task 1 files after diff/test checks.

## Task 2: Service, nhắc hạn, upload/replay và quyền

**Files:** Create `app/reports/service.py`, `tests/integration/test_weekly_reports.py`, `tests/integration/test_weekly_reports_races.py`.

**Interfaces:** All accept existing Psycopg conn and AuthContext: `status(conn, context) -> dict`, `list_own(conn, context, page: int, page_size: int) -> dict`, `submit(conn, context, week_start: date, request_id: UUID, expected_revision: int, filename: str, content: bytes) -> dict`, `list_admin(conn, context, week_start: date | None, user_id: UUID | None, page: int, page_size: int) -> dict`, `read_file(conn, context, report_id: UUID, admin: bool=False) -> dict` returning filename+PDF only internally.

- [ ] Write tests with controlled `app.clock.utc_now`, migration activation and User creation dates: first submit/replacement stores exactly one row/current bytes; Sunday before/at midnight reminders; previous week missing exact copy; no retroactive reminder, both notices; pending/overdue/not-applicable roster and inactive historical download. Assert notice messages exactly match Global Constraints.

```python
assert [n['message'] for n in sunday_status['notices']] == [
    'BẠN CÒN 1 NGÀY ĐỂ NỘP BÁO CÁO NHÉ!!'
]
assert monday_status['notices'][0]['message'] == (
    'TUẦN VỪA RỒI BẠN CHƯA NỘP BÁO CÁO. '
    'HÃY TRÌNH BÀY NỘI DUNG ĐÓ GỘP VỚI TUẦN NÀY NHÉ!'
)
assert replaced['id'] == original['id']
assert replaced['revision'] == original['revision'] + 1
```

- [ ] Run new test file, confirm RED missing service; implement parameterized SQL and metadata-only list/status, transaction profile locks, under-lock role/active/session checks. Activation queried from migration ledger; return 503 if migration missing rather than guessing eligibility. Admin locks Admin/target in sorted UUID order consistent with existing services.
- [ ] Add tests invalid week/future/past, submit at 21:00 works, failed replacement rollback, same UUID+payload replay (also after deadline), UUID conflict, old revision, two concurrent submits/replacements; retry older than latest replacement cannot restore prior bytes. Request hash pins week/revision/sanitized filename/content hash.
- [ ] Implement retry check before deadline check only for already committed latest request, after auth; new writes recheck clock/session after profile/report lock and immediately before SQL. First revision 0, subsequent revision exact; do not hold locks during network upload.
- [ ] Add race tests paused on profile lock crossing deadline or password reset/revocation; assert rejection and unchanged bytes/revision. Use independent test DB connections and events with finite timeouts, no sleeps to guess order.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/integration/test_weekly_reports.py tests/integration/test_weekly_reports_races.py -q --basetemp=.local-tests/weekly-reports/service -o cache_dir=.local-tests/weekly-reports/cache`; expect all GREEN. Commit Task 2 files after checks.

## Task 3: Protected API, giới hạn upload và PDF responses

**Files:** Create `app/reports/schemas.py`, `app/reports/routes.py`, `tests/integration/test_weekly_reports_api.py`; modify `app/main.py`, `tests/test_pages.py` (page cases run in Task 4 after HTML exists).

**Interfaces:** API contract in File Map; User router uses `require_user`, Admin router `require_admin`. Async upload stream reader bounds total real bytes then invokes synchronous service in threadpool with a connection acquired there. No multipart dependency, PDF base64 or full body read before size check.

- [ ] Write API tests for anonymous/User/Admin/other User permissions; upload CSRF/Origin, expected inputs, safe validation responses; invalid/missing Content-Length cannot bypass streaming limit, binary content preserved, old file kept after all failures.
- [ ] Run API tests RED (404). Add routers, Pydantic types/query validation, bounded streaming and role/session checks; Content-Length oversize rejects early, actual size is authoritative.
- [ ] Add GET inline/attachment tests for Unicode/quote/CRLF filenames and `application/pdf`, `no-store`, `nosniff`, properly encoded disposition; unknown/other User IDs never return bytes. API lists must not return bytes/hash/request IDs; logging tests ensure no filename/content sentinels appear.
- [ ] Register protected page routes `/user/weekly-reports` USER and `/admin/weekly-reports` ADMIN; extend no-store prefix to User report API. Native browser PDF viewer in new tab, no HTML iframe dependency or public file URL.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/integration/test_weekly_reports_api.py tests/test_auth_api.py tests/test_health.py -q --basetemp=.local-tests/weekly-reports/api -o cache_dir=.local-tests/weekly-reports/cache`; expect GREEN. Commit Task 3 files after checks.

## Task 4: Giao diện User, retry file và nhắc hạn

**Files:** Create User page and `reports-api.js`, `report-notices.js`, `user-weekly-reports.js`; modify `user.html`, `user.js`, `css/app.css`; create `tests/integration/test_weekly_reports_browser.py`; extend `tests/test_pages.py`.

**Interfaces:** `reports-api.js` exports `uploadReport(pending) -> Promise<metadata>` where pending pins `accountId,week_start,request_id,expected_revision,filename,file`; `report-notices.js` exports `refreshReportNotices() -> Promise<status>` and `startReportNotices() -> cleanupFunction`. The latter only touches `[data-report-notices]` container, owns timers/listeners, catches errors in its own UI so attendance remains usable.

- [ ] Write browser tests: correct nav order; selecting one PDF, submit and metadata, confirmation cancel/accept replacing; file size error; historical own view/download; exact notices on home and report page, 360px and desktop without horizontal overflow.
- [ ] Run browser tests RED for missing page/link. Build page with current week/deadline, current report, single file input, pending/retry status and paginated history. Render all user text via textContent, download/view links include `rel=noopener` and protected API URL.
- [ ] Implement binary upload fetch with CSRF via `/api/auth/me`, `credentials:same-origin`, size/MIME checks, bounded network timeout; keep File/UUID/revision only in tab memory when result is unknown. Disable new upload while pending; retry same request; no automatic fresh UUID on timeout. After reload read server status first, file must be reselected for a new request.
- [ ] Test ambiguous committed upload followed by retry, two tab stale revision, changed account/session and page crossing Monday while open. On account mismatch clear pending file; closed-week pending allows retry for confirmation but never retargets file to new week. Refresh state before new upload/confirmation; server remains authoritative.
- [ ] Integrate reminder container on home and page; initial load, visible 60-second refresh, focus/visibility/pageshow refresh; schedule next server day boundary from server_time rather than trusting local clock. Failure stays in report notice area and does not block attendance startup/actions. Previous-week notice stays until week rolls per spec.
- [ ] Run User browser tests plus existing mobile/daily-action/leave-flow tests and page auth tests; expect GREEN. Commit Task 4 files after checks.

## Task 5: Giao diện Admin và PDF sau backup/restore

**Files:** Create Admin page and `admin-weekly-reports.js`; modify Admin nav in `admin-users.html`, `admin-office.html`, `admin-dashboard.html`; extend new report browser tests and `tests/integration/test_phase6_restore.py`.

**Interfaces:** Admin list API in File Map; filters use ISO Monday derived from selected date and backend validates canonical Monday. User picker obtains existing Admin users API; no new account management behavior.

- [ ] Add failing browser tests for nav adjacent Dashboard, week/User filters, statuses for submitted/missing/inactive/not-applicable, current replacement reflected after reload; XSS filenames/names stay text; view/download endpoints give exact file; user cannot access page/API.
- [ ] Implement Admin page and filters, pagination with request generation/abort so old response cannot replace new filter results, native PDF new-tab/download links; empty/error/loading states and retry. Include Dashboard link beside report link on each Admin page, match current visual style.
- [ ] Extend isolated pg_dump/pg_restore drill by submitting real synthetic PDF through API first, restoring GPS-free and asserting PDF bytes/hash/metadata and migration activation timestamp survive. Existing tombstone/retention/revocation assertions remain. Update hardcoded migration counts/expected list only where new 005 requires it.
- [ ] Run Admin browser/report API/restore/runtime migration tests GREEN; verify no extra PDF query in attendance Dashboard path. Commit Task 5 files after checks.

## Task 6: Hồi quy, tài liệu và bàn giao kết quả

**Files:** Update spec status and verification section, `docs/features/README.md`, `docs/PROJECT_OVERVIEW.md`, `docs/ROADMAP.md`, `docs/README.md`, `docs/USAGE.md`, `docs/DEVELOPMENT.md`, `docs/phases/PHASE_5_DASHBOARD_VA_BAN_DO_ADMIN.md`, `docs/PHASE_6_OPERATIONS.md`, README feature list if needed. Mark plan checkboxes with observed outcomes.

- [ ] Run focused tests per task once meaningful; then full `./.venv/Scripts/python.exe -m pytest -q --basetemp=.local-tests/weekly-reports/full -o cache_dir=.local-tests/weekly-reports/cache-full` with verified existing Caddy binary configured to avoid silent proxy test skip. Capture real exit/counts/skips/warnings. If tests fail, diagnose rather than weakening assertions; rerun affected checks then full suite when needed.
- [ ] Run `./.venv/Scripts/python.exe -m pip check`, `git diff --check`; compare migration 001–004 and requirements/lockfiles to baseline to verify unchanged. Review auth/stream memory bounds/download headers/clock races and new UI against spec. Apply requesting-code-review skill at completion, within its authorized review workflow.
- [ ] Update docs with exact outcome: implemented vs verified vs pending; new migration application instructions, PDF DB/backup size impact and old versions in backup. Keep historical 290 result labeled historical and Phase 6 target gates pending. Link plan under weekly spec; no archive plan is used as current behavior.
- [ ] Commit only reviewed task files, inspect final Git status/log. Final answer links User/Admin pages and docs, reports real tests and notes application DB still needs authorized 005 migration before the new UI is usable there. No push/deploy/real-DB migration.

## Self-review before handing off

- [x] Spec sections 1–8 map to Tasks 1–6; both exact reminder messages and new cutoff are pinned.
- [x] UI/API routes, field names, service signatures and revision/retry handling agree across tasks.
- [x] Review Focus conditions each have a named owning test step; activation tests explicitly control migration timestamps rather than use wall-clock time accidentally.
- [x] No multipart/new package, unrelated refactor, real-DB command, unresolved placeholder or automatic Phase 6 continuation is included.
- [x] Plan was reviewed against the approved scope before execution; results are recorded below rather than inferred from the plan.

## Sổ thực hiện ngày 18/10/2026

| Phần | Bằng chứng thực tế |
| --- | --- |
| Preparation | Đã xác nhận linked worktree; baseline mới 290 passed, 1 warning, 433,56s. Cluster test có sẵn chạy loopback 55441 do cổng cũ không bind được; không initdb hoặc dùng .env |
| Tasks 1–3 | Thêm policy/schema/API/service riêng; RED trước khi có module/API/005; nhóm backend ban đầu 25 passed, 1 warning, 15,93s |
| Tasks 4–5 | Trang User/Admin và nhắc hạn; browser/pages/restore 10 passed, 1 warning, 34,56s trước review. Ảnh 360px/1280px trong .local-tests/weekly-reports/screenshots đã được xem |
| Review | Một reviewer độc lập chỉ đọc; không Critical, hai Important. Runtime thiếu SELECT mốc migration và file pending còn giữ sau lỗi đổi tuần/tài khoản đều được tái hiện bằng test RED rồi sửa |
| Sau sửa review | 35 passed, 2 warnings, 62,06s; cảnh báo thứ hai là cache ACL Windows, không lỗi test. Lượt full dùng cache mới riêng |
| Task 6 | Full suite 318 passed, 1 warning, 557,59s, không skip, exit 0; Caddy probe chạy thật; pip check và diff check đạt. Bằng chứng và giới hạn đã cập nhật ở tài liệu chức năng |

Rulings: giữ nguyên `user.js`/`app.css` bằng module `report-home.js` và stylesheet `reports.css` mới; dùng Query/Header validation có sẵn thay vì thêm `schemas.py` không cần thiết; tên file ở header thay vì URL để tránh access log; runtime chỉ đọc hai cột migration name/applied_at; commit một thay đổi chức năng hoàn chỉnh sau kiểm chứng thay vì commit các trang chưa nối xong. Những bước/command ở trên là kế hoạch gốc; bảng này và báo cáo chức năng ghi lại cách thực hiện thực tế.
