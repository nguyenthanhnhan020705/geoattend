# Phase 3 — Office và Geofence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Admin lưu vùng văn phòng; User Check-in Office qua GPS, Check-out không GPS; vị trí hết hạn được che và xóa sau 30 ngày.

**Architecture:** Giữ FastAPI, Psycopg và schema hiện tại. PostGIS xác minh Polygon/Point tại Backend; tất cả function được định danh theo schema extension thực tế để chạy trên local/public và Supabase/extensions. Leaflet được phục vụ local, tile nền lấy từ cấu hình; dữ liệu Geofence không phụ thuộc tile.

**Tech Stack:** Python 3.13, FastAPI/Psycopg, PostgreSQL 17/PostGIS, Leaflet 1.9.4, HTML/CSS/JS, Pytest/Playwright.

**Spec:** `docs/superpowers/specs/2026-10-14-geoattend-mvp-design.md` §§4–9, `docs/STATE_TRANSITIONS.md`, Phase 3 của `docs/ROADMAP.md`.

**Authorization and execution:** Người dùng đã duyệt thiết kế và ủy quyền tự code/test; yêu cầu thực hiện Phase 3 tiếp tục inline execution đã chọn. Không thêm quy tắc nghiệp vụ cần quyết định mới. Tiếp tục linked worktree `.worktrees/phase-1`; không merge/push. Test trên PostgreSQL riêng port 55440; không tạo Geofence/tài khoản/chấm công thử trên Supabase thực. Chỉ yêu cầu người dùng thao tác khi công cụ không làm được.

## Global Constraints

- Admin sửa văn phòng, User không truy cập API/trang quản trị. Profile/session được kiểm tra lại dưới khóa; CSRF/Origin dùng cơ chế hiện tại.
- GeoJSON chỉ geometry Polygon, EPSG:4326, tọa độ hữu hạn trong giới hạn, ring đóng, 4–1001 điểm mỗi ring, tối đa 10 rings và 2000 điểm tổng để giới hạn input. Không tự sửa Polygon tự cắt/rỗng/diện tích 0; kiểm tra PostGIS.
- Geofence trống chưa cấu hình: Office 409, Remote vẫn hoạt động. Revision chống ghi đè; thay đổi vùng không tính lại phiên đã mở.
- START_OFFICE chỉ từ NOT_STARTED/CHECKED_OUT trong Phase 3; dùng GPS mới mỗi lần bắt đầu. Trong/ranh giới chấp nhận bằng ST_Covers; ngoài vùng403. Lỗi giữ nguyên trạng thái, không tự chuyển Remote.
- Office và sửa Geofence được tuần tự hóa bằng row lock; recheck đồng hồ/phiên sau chờ khóa văn phòng, không vượt 20:00. START_OFFICE ghi phiên, sự kiện verified=true, office_revision và GPS trong cùng transaction.
- Request hash Remote/Check-out giữ tương thích Phase 2 khi thêm field GPS. Không lưu tọa độ trong request record, log hoặc response replay. Office retry giữ payload trong bộ nhớ tab; không ghi GPS vào sessionStorage/localStorage. Reload đọc trạng thái mới.
- GPS expires_at = recorded_at + 30 ngày tuyệt đối. API che tọa độ/accuracy từ đúng expires_at dù worker chưa chạy. Worker đặt point/accuracy null, giữ session/event/verified/purged_at; chạy lặp an toàn.
- Leaflet script/style local có license; CSP chỉ nới cho trang bản đồ và đúng origin tile cấu hình. Attribution luôn hiển thị. Tile lỗi không ngăn lưu Polygon. Không đưa token/DSN ra frontend.

## Task 1: API văn phòng và PostGIS

**Files:** create `app/gis/{__init__,schemas,service,routes}.py`, `tests/integration/test_office.py`; modify `app/main.py`.

**Interfaces:** `OfficeInput(name,address,geom,expected_revision)`; `get_office(conn)` trả name/address/geom/revision (chưa có revision0); `save_office(conn,body,context)` khóa profile Admin, advisory singleton rồi cập nhật Polygon. `extension_schema(conn)` trả identifier PostGIS; `verify_office(conn,latitude,longitude)` khóa row FOR SHARE, trả office_revision/id hoặc ApiError. `GET/PUT /api/admin/office` chỉ Admin, GET gồm map tile config.

- [x] Tests RED: chưa login401, User403, Admin chưa cấu hình revision0; lưu và đọc lại Polygon; stale revision409 không ghi đè; CSRF403; rỗng/tự cắt/zero area/NaN/out-of-range/non-Polygon422; đồng thời hai lần lưu revision0 chỉ một thành công; hỗ trợ extension schema extensions.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/integration/test_office.py -q -o cache_dir=.local-tests/phase-3/cache`; Expected FAIL endpoint absent.
- [x] Implement schema validation and schema-qualified PostGIS, parameterized SQL, Admin row/session revalidation and advisory singleton. No default real office is inserted.
- [x] Run same command; Expected PASS. Commit `feat: add admin office geofence API`.

## Task 2: Office attendance và GPS retention

**Files:** modify `app/attendance/{schemas,service}.py`, `scripts/maintenance.py`; create `app/gis/retention.py`, `tests/integration/test_office_attendance.py`, `test_location_retention.py`.

**Interfaces:** START_OFFICE fields latitude/longitude/accuracy_m required and finite; GPS forbidden on Remote/checkout. Existing expected_work_date/revision/UUID unchanged. History session has location available/expired metadata; result replay still IDs/status only. `purge_locations(conn,now)` returns number purged; maintenance invokes in separate transaction after reconciliation/auth pruning.

- [x] Tests RED: inside/boundary accepted, outside403 unchanged; accuracy huge accepted; invalidGPS422; unconfigured409; checkout withoutGPS; restart newverification; geometry revision retained; GPS insertfailure rolls back session/event/request; stale and sameUUID not duplicate; differentGPS sameUUID409. Test old Remote canonical hash replay.
- [x] Retention tests RED: just-before expiry shows coords; exactly expiry hides coords even beforepurge; expired replay never exposes GPS; purge removespoint+accuracy but keeps verified/session/event; repeat returns0; runtime role can purge; extensions schema functions work.
- [x] Deadline race: hold office row lock, startOffice waits, move clock to20:00, release; no session. Concurrent geofence update/start serializes, each records the revision actually verified.
- [x] Run files, confirm failing behavior, implement minimal changes. Preserve canonical Phase2 hashes by excluding newGPS fields for nonOffice.
- [x] Run tests; Expected PASS. Commit `feat: verify office attendance and expire location data`.

## Task 3: Admin map và User Office flow

**Files:** create `app/static/admin-office.html`, `app/static/js/admin-office.js`, vendor Leaflet files/license; modify user HTML/JS/CSS, Admin navigation, Settings/local launcher, main CSP/page routes; create `tests/integration/test_office_browser.py` and config tests.

**Interfaces:** Admin edits vertices by map click, drag, delete and coordinate inputs, previews before explicit save, preserves draft on errors, reload explicit on409. StartOffice button confirms getCurrentPosition (not watchPosition), disable while locating/submitting; denial/timeout shows actionable message and leaves manualRemote available. Checkout never callsGPS. Office pending remains memory-only; reason and position displayed safely. History marks available or expiredGPS.

- [x] Browser RED: Admin saves Polygon and reloads, Userinside check-in, reload preservesOffice, checkout noGPS, newstart requestsGPS again; outside/denied unchanged, no automaticRemote. Mobile360px, noXSS/JSerrors. Map tilefailure doesnotprevent vertex editing/save. Draft survives saveerror; concurrent adminrevision conflict reloads only after confirmation.
- [x] Config tests RED: tileURL/attribution loaded from env including local_run; invalid protocol/credentials rejected; default no secrets. CSP authorizes only configuredtileorigin on officepage.
- [x] Vendor Leaflet1.9.4 with license, implement UI and page route `/admin/office`. Keep main UI conventions; vertex form also usable if tile unavailable.
- [x] Run browser/config/page tests; Expected PASS. Commit `feat: add office map editor and GPS check-in UI`.

## Task 4: Review, verification và chạy thực

**Files:** update ROADMAP, DEVELOPMENT, manual checklist, .env.example; create PHASE_3_VERIFICATION.

- [x] Run full Pytest with privatePostGIS/Edge; pipcheck, gitdiffcheck. Record exact count/commands/warnings and artifact paths. No false claim on real GPS precision or HTTPS device test.
- [x] One fresh-context whole-change review required by executing-plans; fix Critical/Important in one TDD pass, record Minor separately. Review focus below.
- [x] Verify real Supabase extension schema and runtime permissions, apply migration only if additive migration needed. Stop only verified project web/worker and restart with local_run; health200/login200/newroutes401. Do not insert actual office coordinates automatically.
- [x] Commit all changes, preserve branch/worktree. Stop private PG cluster; preserve logs if cleanup policy prevents removal.

## Pre-flight / rulings

- Task1→2: verify_office takes shared row lock, Admin save takes exclusive row; profile always first, no Admin/user profile cross-lock. Recheck time after officewait. Task2→3: only Office addsGPS; retry storage must never persistGPS. Task2→4: existing runtime UPDATE rights cover retention; no DDL needed unless tests expose missing constraints. No interface conflict.
- Continue existing approved architecture and inline method under explicit user autonomy; no redundant design approval. Cost if wrong: local implementation can be changed.
- Native PowerShell/Python maintain briefs, checklist and RED/GREEN ledger because Bash unavailable. Cost: different bookkeeping format.
- Tests use same live code in existing worktree, but hosted runtime processes stay on old imports until final restart; use privateDB for all mutations. Cost: live static assets can update before restart, so handoff asks browser reload.
- Office retry GPS stays in memory only; reload fetches committed status, never persists rawcoords for replay. Cost: unconfirmed Office request cannot be resent with its originalcoordinates after reload; reattempt requires freshGPS and currentrevision.

## Review Focus

GIS schema public vs extensions; longitude/latitude order; invalid/self-intersecting polygons; rowlock wait crosses20:00 or sessionrevocation; requesthash compatibility with Phase2; expiredGPS leakage through status/history/replay/storage; frontend GPS denial and ambiguous retries; map failure/draft conflict; CSP/attribution; runtime permissions; no test mutations on hosted Supabase.

## References

- https://postgis.net/docs/ST_Covers.html
- https://postgis.net/docs/ST_IsValid.html
- https://leafletjs.com/reference.html
