# GeoAttend — Bàn giao Phase 0–4

**Giao diện User sau bàn giao:** thông tin nhân viên đầu trang; ba lựa chọn Office/Remote/Xin nghỉ; form lý do mở khi bấm, lịch sử thu gọn cuối trang và tải theo yêu cầu. Chỉ thay HTML/CSS/JS, không migration; xem [USER_MOBILE_UI](../docs/USER_MOBILE_UI.md).

**Bổ sung sau Phase 4 (15/10/2026):** theo yêu cầu mới, Admin được xem/xóa vĩnh viễn lịch sử từng ngày nhân viên, có xác nhận và chặn ngày đang làm việc/nghỉ trưa. Cần migration 004 và runtime grants tương ứng; xem [ADMIN_HISTORY](../docs/ADMIN_HISTORY.md). Các kết quả Phase 0–4 bên dưới là mốc lịch sử; Dashboard/Onsite vẫn chưa triển khai.

> Dành cho agent tiếp quản: đọc toàn bộ file này trước khi sửa mã. Phase 0–3 đã hoàn thành; Phase 4 đã triển khai theo kế hoạch bên dưới, bằng chứng mới tại [PHASE_4_VERIFICATION](../docs/PHASE_4_VERIFICATION.md). Không cần làm lại các quyết định nghiệp vụ đã duyệt.

**Cập nhật:** 15/10/2026. **Mốc bàn giao ban đầu:** `e52d2dd`, sau bản sửa bản đồ `1d72990`. Phase 4 tiếp tục trên cùng branch/worktree; xem Git log và báo cáo Phase 4 cho các commit/kết quả mới. Số test Phase 1–3 bên dưới là bằng chứng lịch sử.

## 1. Bắt đầu đúng workspace

| Nội dung | Giá trị |
| --- | --- |
| Workspace gốc | `D:\N.ThanhNhan\INTERN\geoattend` |
| Worktree chứa ứng dụng hoàn chỉnh | `D:\N.ThanhNhan\INTERN\geoattend\.worktrees\phase-1` |
| Branch hiện tại | `feat/phase-1-foundation-auth` |
| Tài liệu bàn giao này | `handoff/README.md`, tính từ worktree trên |
| Trạng thái tích hợp | Giữ branch/worktree để phát triển tiếp; không mặc định mã đã merge về main |

```powershell
Set-Location 'D:\N.ThanhNhan\INTERN\geoattend\.worktrees\phase-1'
git status --short
git branch --show-current
git log -5 --oneline
```

Nếu chuyển máy, chuyển đúng branch/commit và các file đã commit; tạo lại `.venv`, cấu hình bí mật riêng. Không sao chép mật khẩu vào tài liệu. Nếu cần worktree khác, tạo từ branch/mốc đã hoàn thành này, không từ main chưa có ứng dụng. Không reset hoặc ghi đè thay đổi đang có của người dùng.

## 2. Tóm tắt dự án và phạm vi

GeoAttend là ứng dụng chấm công Office/Remote có xác minh vị trí Office bằng GIS. FastAPI phục vụ API và HTML/CSS/JavaScript cùng nguồn; PostgreSQL/PostGIS lưu dữ liệu, Supabase đang cung cấp database cho môi trường local. Xác thực là tài khoản/mật khẩu của ứng dụng, không dùng Supabase Auth hoặc Google OAuth.

| Phase | Trạng thái | Kết quả |
| --- | --- | --- |
| 0 | Hoàn thành | BRD, quyết định nghiệp vụ, bảng trạng thái, thiết kế dữ liệu/API/giao diện |
| 1 | Hoàn thành | Nền tảng, migration, đăng nhập, phân quyền, Admin cấp User |
| 2 | Hoàn thành | Remote, Check-out, bắt đầu lại, lịch sử bản thân, tự đóng 20:00 |
| 3 | Hoàn thành | Geofence, Office/GPS, hết hạn vị trí 30 ngày; đã sửa nền bản đồ và chờ vô hạn |
| 4 | Hoàn thành | Nghỉ trưa, nghỉ sáng/cả ngày, hủy nghỉ kết hợp bắt đầu, chuyển Office ↔ Remote; 195 test đạt, review không lỗi chặn |

Phase 5 (Dashboard/Onsite/lịch sử nhân viên cho Admin) và Phase 6 (production/pilot) chưa triển khai và không thuộc đợt bàn giao triển khai Phase 4. Không tự thêm tính lương, duyệt nghỉ, nhiều văn phòng, đăng ký công khai, QR hay theo dõi GPS liên tục.

## 3. Các quy tắc đã chốt — phải giữ nguyên

- Một Admin được khởi tạo khi thiết lập. Admin tạo/cấp tài khoản User, đặt lại mật khẩu; chỉ quản lý, không chấm công. User có thể đổi mật khẩu, không bắt buộc đổi lần đầu; không khôi phục qua email.
- Múi giờ nghiệp vụ `Asia/Ho_Chi_Minh` (UTC+07:00). Backend quyết định thời gian; không tin thời gian thiết bị. Từ đúng 20:00 đến hết ngày không bắt đầu/tiếp tục/chuyển chế độ làm việc.
- Tối đa một phiên đang mở cho mỗi User. Ngày mới bắt đầu `NOT_STARTED` nếu chưa có sự kiện; giữ lịch sử ngày trước.
- Lúc 20:00, Office/Remote còn mở được hệ thống đóng, ghi nguồn `SYSTEM`. Phân biệt mốc nghiệp vụ 20:00 với `recorded_at` lúc thực thi; không trình bày là giờ nhân viên thực sự kết thúc. Khi worker dừng, lần chạy lại/API phải xử lý bù.
- Office lấy GPS một lần tại mỗi lần bắt đầu/tiếp tục/chuyển vào Office. Backend kiểm tra PostGIS `ST_Covers`: chấp nhận trong và trên ranh giới, không vùng đệm. Accuracy được lưu, không dùng làm ngưỡng từ chối. Thất bại giữ trạng thái cũ, không tự chuyển Remote.
- Remote phải có lý do; Remote, nghỉ và Check-out không lấy GPS. Check-out không cần còn trong Geofence.
- Xóa tọa độ và accuracy sau 30 ngày từ lúc ghi nhận; giữ phiên, sự kiện và kết quả xác minh. API che GPS hết hạn ngay cả khi maintenance chưa purge.
- Phiên, sự kiện, trạng thái và kết quả idempotency phải ghi trong cùng transaction. Lỗi ghi dữ liệu rollback toàn bộ thao tác.
- Giữ `request_id` UUID, `expected_revision`, `expected_work_date`; cùng UUID/cùng payload trả kết quả cũ, khác payload bị từ chối. Màn hình cũ không được ghi đè trạng thái mới.
- Thời gian/quyền/session cần kiểm tra lại sau khi chờ khóa, đặc biệt qua 20:00, qua ngày, logout/reset mật khẩu hoặc khóa tài khoản.

## 4. Phase 0 — kết quả đã thực hiện

- Chuẩn hóa BRD, chốt các TBD về GPS, ranh giới, nghỉ, cutoff, hủy nghỉ và chuyển chế độ.
- Duyệt bảng chuyển trạng thái và nguyên tắc đồng thời/idempotency.
- Duyệt mô hình dữ liệu tách tài khoản, auth session, trạng thái ngày, phiên làm việc, sự kiện, GPS và replay request.
- Chốt kiến trúc FastAPI cùng nguồn, PostgreSQL/PostGIS, giao diện web và phân quyền User/Admin.
- Chốt mục tiêu pilot khoảng 10 User trong 5 ngày làm việc, ít nhất 95% API xử lý Backend trong 2 giây (không tính GPS). Đây là tiêu chí tương lai, chưa phải kết quả đo đã đạt.

Nguồn: [BRD](../README.md), [bảng trạng thái](../docs/STATE_TRANSITIONS.md), [thiết kế MVP đã duyệt](../docs/superpowers/specs/2026-10-14-geoattend-mvp-design.md).

## 5. Phase 1 — kết quả đã thực hiện

- Dựng FastAPI, health endpoint, static UI, cấu hình môi trường và lockfile dependency.
- Migration/checksum, runtime role tách migration role; hỗ trợ PostGIS tại schema `public` hoặc `extensions` trên Supabase.
- Bootstrap Admin chạy lại không tạo thêm Admin; User do Admin tạo, không tự seed tài khoản thực.
- Đăng nhập/đăng xuất, cookie session, CSRF, giới hạn đăng nhập, kiểm tra quyền Backend; đổi/reset mật khẩu thu hồi session liên quan.
- UI đăng nhập, tài khoản cá nhân, danh sách/tạo/reset/khóa User.
- Launcher `scripts.local_run` đọc `.env`, truyền DSN phù hợp cho từng tiến trình; không đưa bí mật quản trị vào web runtime.

Bằng chứng lịch sử: **46 kiểm thử đạt**. [Kế hoạch](../docs/superpowers/plans/2026-10-14-phase-1-foundation-auth.md), [báo cáo](../docs/PHASE_1_VERIFICATION.md).

## 6. Phase 2 — kết quả đã thực hiện

- `START_REMOTE`, `CHECK_OUT`, bắt đầu lại sau Check-out trước 20:00; lý do Remote bắt buộc.
- API trạng thái, `allowed_actions`, lịch sử bản thân theo ngày và phân trang; User không đọc được người khác.
- Profile lock, revision, work date và UUID chống thao tác lặp/đồng thời; rollback khi ghi sự kiện lỗi.
- Tự đóng 20:00, chạy bù ngày cũ, tách thời điểm nghiệp vụ/thời điểm ghi nhận; worker maintenance độc lập.
- UI Remote/Check-out/lịch sử. Remote giữ payload chưa biết kết quả trong `sessionStorage` để thử lại cùng UUID.

Bằng chứng lịch sử: **85 kiểm thử đạt**. [Kế hoạch](../docs/superpowers/plans/2026-10-14-phase-2-remote-attendance.md), [báo cáo](../docs/PHASE_2_VERIFICATION.md), [kiểm thử tay](../docs/MANUAL_TEST_PHASE_2.md).

## 7. Phase 3 — kết quả đã thực hiện

- Admin `/admin/office` xem, vẽ/chỉnh Polygon, vùng loại trừ, kéo/sửa/xóa đỉnh, xem trước và lưu với revision. Backend kiểm tra Polygon và quyền; không tự chọn Geofence thực tế.
- User `START_OFFICE` lấy GPS, Backend xác minh, tạo phiên và lưu vị trí tách riêng; có lỗi rõ khi chưa cấu hình/ngoài vùng/từ chối GPS.
- Payload Office có GPS chỉ giữ trong bộ nhớ tab để thử lại, không lưu vào storage. Hash của thao tác Remote cũ vẫn tương thích sau khi thêm trường GPS.
- Maintenance purge vị trí hết hạn; lịch sử vẫn giữ kết quả xác minh.
- Sửa sau Phase 3: nguồn OSM raster cũ lỗi DNS trên máy kiểm tra. Nền mặc định chuyển OpenFreeMap qua MapLibre + Leaflet; thư viện/giấy phép lưu local, credits đầy đủ, CSP giới hạn origin.
- Thêm **Vẽ vùng**, **Tải lại bản đồ** giữ bản nháp; tọa độ đầu tiên đưa bản đồ đến điểm nhập. API có timeout 15 giây gồm đọc body; lỗi mạng/timeout không bị coi là kết quả xác định của thao tác chấm công.

Bằng chứng: Phase 3 ban đầu **119 kiểm thử đạt**; sau sửa bản đồ **122 passed, 1 warning** upstream Starlette/httpx. Edge qua mạng thật hiển thị đường phố TP.HCM. GPS trong test được giả lập; chưa chứng nhận GPS trên điện thoại thật hoặc triển khai HTTPS production.

[Kế hoạch](../docs/superpowers/plans/2026-10-15-phase-3-office-geofence.md), [báo cáo](../docs/PHASE_3_VERIFICATION.md), [kiểm thử tay](../docs/MANUAL_TEST_PHASE_3.md), [sửa bản đồ](../docs/MAP_RECOVERY.md).

## 8. Vị trí mã nguồn và hợp đồng hiện tại

Tất cả đường dẫn sau tính từ worktree ứng dụng.

| File/thư mục | Trách nhiệm |
| --- | --- |
| `app/main.py`, `app/config.py` | Khởi tạo ứng dụng, cấu hình, security headers/CSP |
| `app/auth/`, `app/accounts/` | Xác thực, phân quyền, quản lý tài khoản |
| `app/attendance/schemas.py` | `ActionInput`, START_REMOTE/OFFICE, CHECK_OUT và action nghỉ/hủy/chuyển Phase 4 |
| `app/attendance/service.py` | `act`, `snapshot`, `history`, `reconcile_locked`, `maintain`; lock, replay, transaction |
| `app/attendance/routes.py` | GET status/history, POST actions; chỉ User |
| `app/gis/` | Cấu hình/xác minh Office, lưu vị trí, retention; đọc lại tên hàm thực trước sửa |
| `app/clock.py` | Nguồn giờ có thể giả lập trong test |
| `app/static/user.html`, `app/static/js/user.js` | Màn hình chấm công, pending retry, hiển thị lịch sử |
| `app/static/js/api.js` | CSRF, fetch/timeout, lỗi và xác thực phía UI |
| `app/static/admin-office.html`, `app/static/js/admin-office.js` | Editor Geofence |
| `app/static/js/office-map-background.js` | Nền map độc lập với khả năng chỉnh/lưu vùng |
| `migrations/001_identity.sql` | Schema ban đầu, đã có trạng thái/sự kiện nghỉ |
| `migrations/002_attendance.sql`, `003_attendance_replay.sql` | Bổ sung phục vụ chấm công và kết quả replay |
| `scripts/local_run.py`, `scripts/maintenance.py` | Chạy local, worker |
| `tests/db_fixtures.py`, `tests/conftest.py` | Database test tách biệt, fixture API |
| `tests/integration/` | Hồi quy attendance, race, Office/GPS, retention, browser |

API hiện có: `GET /api/attendance/status`, `POST /api/attendance/actions`, `GET /api/attendance/history`; Admin `GET/PUT /api/admin/office`. Xem `/docs`/OpenAPI và route auth/accounts để lấy hợp đồng đầy đủ.

Request chấm công dùng `request_id`, `expected_revision`, `expected_work_date`, `action`; Remote có `reason`; Office có `latitude`, `longitude`, `accuracy_m`. Reason được trim, độ dài 1–1000. Response thao tác có `event_ids`, `session_id`, `work_date`, `status`, `revision`. `allowed_actions` phải khớp Backend, không chỉ ẩn/hiện nút theo suy đoán ở UI.

**Chú ý:** schema đã khai báo đủ trạng thái/event nghỉ, đối soát `LUNCH_BREAK` lúc 20:00 và replay nhiều event. Phase 4 dùng lại các phần này, không cần migration mới. Không sửa migration đã áp dụng: checksum được kiểm tra. Nếu cần schema mới, thêm migration số tiếp theo.

`history` trả cả `sessions` và `events`; UI dùng chung timeline hiện có. Phase 4 mở rộng phân loại Office cho START, CANCEL_LEAVE_START và SWITCH: hash bao gồm GPS, pending chỉ giữ bộ nhớ tab, không storage. Hash action cũ được giữ. Nghỉ dùng tên action `MORNING_LEAVE`/`FULL_DAY_LEAVE` theo kế hoạch này, không dùng tên đề xuất cũ `LEAVE_MORNING`/`LEAVE_FULL_DAY`.

## 9. Chạy local và kiểm thử

### 9.1. Mỗi lần bật máy

Trong worktree, `.env` đã có cấu hình Supabase riêng trên máy hiện tại. Không cần mở pgAdmin hay bootstrap lại Admin. Máy mới tham khảo `.env.example`, [DEVELOPMENT](../docs/DEVELOPMENT.md) để tạo môi trường; bí mật không có trong Git.

Terminal 1:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_run serve
```

Terminal 2:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_run maintenance
```

Mở `http://127.0.0.1:8000/login`. Maintenance cần chạy liên tục nếu muốn xử lý đúng lúc 20:00; máy tắt thì lần chạy lại xử lý bù. Chỉ chạy một web server port 8000 và một worker. Lỗi Windows 10048 thường do đã có server; kiểm tra tiến trình/cổng trước khi khởi chạy thêm, không tắt tiến trình không rõ nguồn.

Khi có migration mới: `.\.venv\Scripts\python.exe -m scripts.local_run migrate`. Dọn một lần: `.\.venv\Scripts\python.exe -m scripts.local_run maintenance --once`. Không tạo lại role/Admin mỗi ngày. Lỗi “Cơ sở dữ liệu chưa sẵn sàng” cần kiểm tra `/api/health`, cấu hình/kết nối trước khi sửa dữ liệu.

### 9.2. Bộ kiểm thử

Python 3.13, PostgreSQL/PostGIS riêng, Playwright + Edge hoặc Chromium. Cài môi trường mới bằng `requirements-dev.lock.txt`; không cài lại nếu môi trường hiện có hoạt động.

```powershell
# Placeholder: thay bằng database quản trị TEST riêng, tuyệt đối không Supabase ứng dụng.
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://TEST_USER:TEST_PASSWORD@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.local-tests/phase-4/run-01 -o cache_dir=.local-tests/phase-4/cache
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Đổi `run-01` thành tên mới nếu thư mục cũ lỗi quyền Windows. Fixture tự tạo database `geoattend_test_<uuid>` và dọn database đó; cần quyền CREATEDB/role/extension theo fixture. Không dùng test DSN trùng DSN ứng dụng/migration.

Port 55440 là cluster local test, được khởi động lại cho Phase 4; không giả định đang chạy ở phiên sau hoặc test credential ở ví dụ là tài khoản thật. Kiểm tra `pg_ctl status` trước khi dùng. Có thể dùng PostgreSQL/PostGIS test khác và sửa DSN. Với máy đã có cluster tại `.local-tests/phase-3/pgdata`, xác minh đường dẫn/config/port rồi mới dùng `pg_ctl` của PostgreSQL 17 để start; không initdb hoặc xóa cluster hiện hữu.

Không đưa mật khẩu/DSN đầy đủ vào chat, commit hay log. Không tạo chấm công/Geofence thử trên Supabase thật. `.env`, `.venv`, `.local-tests`, `.superpowers` không nằm trong Git và không được xem là đầu vào bắt buộc trên máy mới.

## 10. Phase 4 Implementation Plan — đã triển khai

> **For agentic workers:** Đã thực hiện inline theo `superpowers:executing-plans`, từng task với test đỏ/xanh. Không làm lại task đã commit; xem [báo cáo](../docs/PHASE_4_VERIFICATION.md) và [checklist tay](../docs/MANUAL_TEST_PHASE_4.md). Giữ nguyên yêu cầu bảo toàn dữ liệu, idempotency và GPS bên dưới.

**Goal:** Hoàn thiện ngày làm việc có nghỉ và chuyển Office/Remote theo nghiệp vụ đã duyệt.

**Architecture:** Mở rộng cùng `POST /api/attendance/actions` và service hiện tại; tái sử dụng profile lock, transaction, replay, GPS service và đối soát 20:00. Giữ lịch sử sự kiện bất biến, bổ sung UI theo `allowed_actions`, không tạo cơ chế chấm công thứ hai.

**Tech Stack:** FastAPI/Pydantic, Psycopg/PostgreSQL/PostGIS, HTML/CSS/JavaScript, pytest/Playwright.

**Spec:** [STATE_TRANSITIONS](../docs/STATE_TRANSITIONS.md), BRD mục 6.4, FR-04–FR-07, AC-04/05/11/13/14 và thiết kế MVP đã duyệt. Quy tắc mục 3 áp dụng cho mọi task. Tên action mới bên dưới là đề xuất kỹ thuật để triển khai, chưa có trong API hiện tại.

### 10.1. Chuyển trạng thái cần bổ sung

| Trạng thái đầu | Thao tác đề xuất | Kết quả và điều kiện |
| --- | --- | --- |
| `WORKING_OFFICE`/`WORKING_REMOTE` | `START_LUNCH` | Đóng phiên tại lúc nghỉ, ghi `WORK_END` và `LUNCH_START`, chuyển `LUNCH_BREAK`; không GPS |
| `LUNCH_BREAK`/`MORNING_LEAVE` | `START_OFFICE` | GPS hợp lệ → phiên Office mới |
| `LUNCH_BREAK`/`MORNING_LEAVE` | `START_REMOTE` | Lý do hợp lệ → phiên Remote mới |
| `NOT_STARTED` | `MORNING_LEAVE` | Lý do bắt buộc → nghỉ sáng, không phiên/GPS |
| `NOT_STARTED` | `FULL_DAY_LEAVE` | Lý do bắt buộc → nghỉ cả ngày, không phiên/GPS |
| `FULL_DAY_LEAVE` | `CANCEL_LEAVE_START_OFFICE` | Xác minh GPS rồi ghi `LEAVE_CANCELLED` và tạo phiên Office trong cùng giao dịch |
| `FULL_DAY_LEAVE` | `CANCEL_LEAVE_START_REMOTE` | Lý do hợp lệ rồi ghi `LEAVE_CANCELLED` và tạo phiên Remote trong cùng giao dịch |
| `WORKING_OFFICE` | `SWITCH_REMOTE` | Kiểm tra lý do rồi đóng Office/mở Remote nguyên tử |
| `WORKING_REMOTE` | `SWITCH_OFFICE` | Xác minh GPS rồi đóng Remote/mở Office nguyên tử |
| `LUNCH_BREAK` lúc 20:00 | Hệ thống | `DAY_END` nguồn SYSTEM → `CHECKED_OUT`, không sửa phiên trước nghỉ trưa |

Không có hủy nghỉ độc lập. Hủy nghỉ hoặc chuyển chế độ thất bại giữ nguyên trạng thái/phiên cũ. Nghỉ sáng/cả ngày chỉ từ `NOT_STARTED`; không tự bắt đầu vào buổi chiều, không chặn theo giờ sáng/chiều. Mọi chuyển trạng thái không được bảng đã duyệt cho phép đều bị từ chối. `MORNING_LEAVE`, `FULL_DAY_LEAVE`, `NOT_STARTED` không tự đổi thành `CHECKED_OUT` lúc 20:00.

### 10.2. Review Focus

1. Gửi lại UUID cũ sau thay đổi schema: kết quả cũ vẫn replay được; không thay hash Remote/Office đã lưu.
2. Đợi khóa qua 20:00 hoặc qua ngày: không tạo phiên/hủy nghỉ/chuyển chế độ trái quy tắc; đối soát ngày cũ vẫn được ghi nhận đúng.
3. GPS/lý do/ghi event thất bại: phiên trước chuyển chế độ và đăng ký nghỉ cả ngày còn nguyên, không có dữ liệu dở dang.
4. Hai tab, worker, reset mật khẩu hoặc khóa tài khoản chạy đồng thời: không trùng phiên/event, không vượt quyền/session đã thu hồi.
5. Mất phản hồi sau commit hoặc tải lại trang: retry không nhân đôi; không lưu GPS vào persistent storage; UI phản ánh kết quả server.

### Task 1 — Nghỉ trưa và tiếp tục làm việc

**Files:** sửa `app/attendance/schemas.py`, `service.py`; tạo `tests/integration/test_attendance_breaks.py`, bổ sung `test_attendance_races.py`.

**Interfaces:** mở rộng `ActionInput`; giữ chữ ký `act(conn,user_id,body,session_id=None)` và `snapshot(conn,user_id,now)`, response hiện tại. `START_LUNCH` không nhận GPS; `START_OFFICE`/`START_REMOTE` dùng cho tiếp tục từ `LUNCH_BREAK`. Một thao tác có thể trả nhiều `event_ids`.

- [x] Viết và chạy test đỏ: nghỉ trưa đóng đúng một phiên, `LUNCH_START` không có phiên mở mới; resume tạo session ID khác; Office resume phải xác minh lại, Remote resume cần lý do; nghỉ khi chưa làm việc bị 409.
- [x] Mở rộng validator/action/allowed_actions; ghi transaction nguyên tử, revision tăng một lần cho mỗi thao tác, lưu đủ event IDs vào replay. Giữ hash cũ cho payload action cũ.
- [x] Kiểm thử `LUNCH_BREAK` trước/đúng/sau 20:00, maintenance lặp và chạy bù: đúng một `DAY_END`, không đổi end_time của phiên trước nghỉ. Kiểm thử chờ khóa qua cutoff và retry UUID đã commit.
- [x] Chạy `.\.venv\Scripts\python.exe -m pytest tests/integration/test_attendance_breaks.py tests/integration/test_attendance_races.py -q`; chỉ commit khi đạt. Kết quả: API nghỉ trưa/resume và đối soát hoạt động độc lập với UI.

### Task 2 — Nghỉ sáng/cả ngày và hủy nghỉ kết hợp bắt đầu

**Files:** sửa `app/attendance/schemas.py`, `service.py`; tạo `tests/integration/test_attendance_leave.py`; dùng lại GIS service, không nhân bản xác minh tọa độ.

**Interfaces:** thêm action theo bảng; lý do nghỉ/Remote trim 1–1000; chỉ action vào Office nhận bộ GPS đầy đủ. `history` phải trả được event nghỉ/hủy nghỉ và trạng thái hiện tại. Không thêm endpoint hủy nghỉ riêng.

- [x] Viết/chạy test đỏ cho nghỉ có/thiếu lý do, input thừa/GPS bị cấm, chỉ nghỉ từ `NOT_STARTED`; bắt đầu sau nghỉ sáng không cần đợi giờ chiều.
- [x] Implement nghỉ và bắt đầu sau nghỉ sáng theo bảng. Nghỉ không tạo `work_sessions`; giữ event đăng ký nghỉ.
- [x] Implement hủy nghỉ kết hợp bắt đầu: chỉ ghi `LEAVE_CANCELLED` khi GPS/lý do đạt; thất bại giữ `FULL_DAY_LEAVE`. Ngày đã hủy phải có trạng thái làm việc và lịch sử đăng ký/hủy để Phase 5 không đếm thành nghỉ cả ngày hiệu lực.
- [x] Thêm test rollback lỗi insert event, hai request cùng revision, logout/reset khi chờ khóa, qua ngày, trước/đúng 20:00. Giữ trạng thái nghỉ nguyên khi đối soát cuối ngày theo spec.
- [x] Chạy `.\.venv\Scripts\python.exe -m pytest tests/integration/test_attendance_leave.py -q`; đạt rồi commit. Không sửa migration cũ; chỉ thêm migration mới nếu chứng minh cần schema/quyền mới.

### Task 3 — Chuyển trực tiếp Office ↔ Remote

**Files:** sửa `app/attendance/schemas.py`, `service.py`; tạo `tests/integration/test_attendance_switch.py`.

**Interfaces:** `SWITCH_REMOTE` chỉ từ `WORKING_OFFICE`, bắt buộc lý do; `SWITCH_OFFICE` chỉ từ `WORKING_REMOTE`, bắt buộc GPS. `act` trả session mới cùng event kết thúc/bắt đầu; dùng cùng một thời điểm chuyển cho end/start.

- [x] Viết/chạy test đỏ: cả hai chiều thành công, cùng chế độ bị từ chối, ngoài vùng/thiếu lý do giữ phiên cũ mở, không tạo event/phiên mới.
- [x] Xác minh điều kiện chế độ đích và kiểm tra lại giờ/session sau chờ khóa trước khi đóng phiên nguồn. Ghi đóng/mở/event/location/replay trong một transaction; giữ lock order hiện có để tránh deadlock với Admin sửa Geofence và maintenance.
- [x] Thêm test lỗi ghi GPS/event rollback toàn bộ, chuyển vs Check-out/worker, hai tab, UUID lặp/khác payload, chờ lock Office qua cutoff và replay payload cũ.
- [x] Chạy `.\.venv\Scripts\python.exe -m pytest tests/integration/test_attendance_switch.py tests/integration/test_office_attendance.py -q`; đạt rồi commit.

### Task 4 — UI, timeline và thử lại thao tác

**Files:** sửa `app/static/user.html`, `app/static/js/user.js`; sửa `service.py:history` nếu thiếu dữ liệu timeline; tạo `tests/integration/test_phase4_browser.py`.

**Interfaces:** UI dựa trên `allowed_actions` và revision/work date do server trả. Các action vào Office dùng cùng cơ chế GPS một lần và pending payload trong bộ nhớ; các action không GPS có thể dùng cơ chế pending hiện có. Không sửa tên/cấu trúc payload pending cũ nếu chưa có kiểm thử tương thích.

- [x] Viết/chạy test browser đỏ cho nút nghỉ trưa/tiếp tục/nghỉ sáng/nghỉ cả ngày/hủy nghỉ/chuyển chế độ, form lý do và timeline tiếng Việt.
- [x] Thêm nút/form theo quyền và trạng thái, khóa nút khi gửi; hiển thị rõ tự đóng hệ thống, đăng ký/hủy nghỉ, từng phiên sáng/chiều. Không tính khoảng nghỉ thành thời gian làm việc.
- [x] Test mất phản hồi sau commit → retry cùng UUID không nhân đôi; timeout mở lại thao tác; refresh trạng thái/lịch sử; GPS không nằm trong `sessionStorage`/`localStorage`; HTML trong lý do hiển thị dạng text.
- [x] Test viewport 360px và desktop, không tràn ngang/JS error. Chạy `.\.venv\Scripts\python.exe -m pytest tests/integration/test_phase4_browser.py -q`; đạt rồi commit.

### Task 5 — Hồi quy, nghiệm thu và bàn giao Phase 4

**Files:** bổ sung test phase 4/race nếu thiếu; tạo `docs/MANUAL_TEST_PHASE_4.md`, `docs/PHASE_4_VERIFICATION.md`; cập nhật `docs/ROADMAP.md`, `docs/DEVELOPMENT.md` và file này.

**Kết quả:** 195 passed, 1 warning upstream; pip check/diff check không lỗi. Review độc lập không có Critical/Important. Minor hoãn: event trùng timestamp có thể hiển thị đảo thứ tự do UUID; phiên/trạng thái/replay vẫn đúng. Không migration mới; không tạo dữ liệu thử trên Supabase thật. Xem báo cáo Phase 4 cho bằng chứng và giới hạn thiết bị/production.

- [x] Kiểm tra đủ tám kịch bản dưới đây, cộng hủy nghỉ cả ngày và chuyển trực tiếp hai chiều; không đánh dấu hoàn thành chỉ vì đã có nút UI.
- [x] Chạy toàn bộ pytest với database test riêng, `pip check`, `git diff --check`; lưu lệnh/kết quả và giới hạn thực tế. 122 là baseline cũ, tổng test mới phải tăng theo thay đổi.
- [x] Review độc lập theo skill áp dụng; sửa lỗi Critical/Important rồi chạy lại kiểm thử liên quan. Không merge/deploy tự động ngoài phạm vi được giao.
- [x] Nếu có migration mới, kiểm thử chạy lại an toàn trên database test/runtime role hạn chế trước khi áp dụng môi trường thực. Không seed dữ liệu thử lên Supabase thật.
- [x] Hoàn thiện checklist tay, báo cáo và commit. Chỉ ghi Phase 4 hoàn thành khi API/DB/UI/worker và tiêu chí dưới đây đều có bằng chứng.

### 10.3. Checklist nghiệm thu

| Kịch bản | Kết quả cần chứng minh |
| --- | --- |
| Office cả ngày | Office → nghỉ trưa → Office → Check-out; hai phiên, hai lần xác minh GPS |
| Remote cả ngày | Remote → nghỉ trưa → Remote → Check-out; mỗi phiên có lý do, không GPS |
| Remote sáng, Office chiều | Resume Office xác minh GPS, giữ phiên Remote sáng |
| Office sáng, Remote chiều | Resume Remote cần lý do, giữ phiên Office sáng |
| Nghỉ sáng, Office chiều | Event nghỉ có lý do; Office khi quay lại có GPS, không khóa giờ chiều |
| Nghỉ sáng, Remote chiều | Event nghỉ có lý do; Remote khi quay lại cần lý do mới |
| Nghỉ cả ngày | Không phiên/GPS; lịch sử có lý do; hủy kết hợp bắt đầu giữ dấu vết |
| Làm việc một phần ngày | Office/Remote → Check-out; có thể bắt đầu lại trước 20:00 |

Ngoài tám luồng: đúng/trễ 20:00; nghỉ trưa qua cutoff; ngày mới; double click/retry/hai tab; sửa Geofence đồng thời; user bị khóa/session thu hồi; GPS thất bại; retention 30 ngày; quyền Admin/User; rollback khi DB lỗi. Dashboard và thống kê nghỉ cho Admin để Phase 5 triển khai từ dữ liệu đúng của Phase 4.

## 11. Lời giao việc cho agent tiếp theo

> Phase 4 đã triển khai; đọc báo cáo kiểm chứng trước khi tiếp tục. Phase tiếp theo là Phase 5 (Dashboard/Onsite/lịch sử nhân viên cho Admin), chưa được triển khai trong đợt này. Kiểm tra branch/worktree và baseline thực tế trước khi sửa; không làm lại Phase 03 hoặc Phase 4 đã commit. Dùng BRD, STATE_TRANSITIONS và thiết kế Phase 0 làm nguồn nghiệp vụ; giữ transaction/idempotency/GPS/privacy. Không thay tài khoản/mật khẩu hay tạo dữ liệu thử trên Supabase thật. GPS thiết bị thật, HTTPS production và pilot thuộc Phase 6.
