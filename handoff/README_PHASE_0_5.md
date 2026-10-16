# GeoAttend — Bàn giao Phase 0–5

> **For agentic workers:** Phase 0–5 đã triển khai; kiểm tra Git và báo cáo trước khi sửa mã, không tự chạy lại các task đã hoàn thành. Tuân thủ AGENTS.md và skill bắt buộc. Kế hoạch Task 1–5 bên dưới được giữ làm bằng chứng phạm vi đã thực hiện.

**Cập nhật:** 16/10/2026. **Baseline mã nguồn:** `8dd1af2`, branch `feat/phase-1-foundation-auth`. Đây là tài liệu bàn giao tổng hợp mới; [bàn giao cũ](README.md) giữ chi tiết và bằng chứng lịch sử.

**Goal:** hoàn thiện Dashboard trạng thái nhân viên và Onsite Map cho Admin, tích hợp các chức năng quản lý sẵn có mà bảo toàn Phase 0–4.

**Architecture:** mở rộng ứng dụng FastAPI cùng nguồn hiện có; đọc trạng thái/phiên/sự kiện từ PostgreSQL/PostGIS, tái sử dụng đối soát 20:00, quyền Admin, lịch sử và bản đồ. Không tạo hệ thống chấm công hoặc nguồn trạng thái thứ hai.

**Tech Stack:** Python 3.13, FastAPI/Pydantic, Psycopg, PostgreSQL/PostGIS, HTML/CSS/JavaScript, Leaflet và nền MapLibre/OpenFreeMap hiện có, pytest/Playwright.

**Spec:** [BRD](../README.md) FR-10–13, FR-15, BR-06/07, AC-01/07/08/15/16; [roadmap](../docs/ROADMAP.md) mục Phase 5; [thiết kế MVP](../docs/superpowers/specs/2026-10-14-geoattend-mvp-design.md) mục 8–9. Các bổ sung được người dùng xác nhận ở mục 3 dưới đây được ưu tiên hơn mô tả cũ.

## 0. Kết quả Phase 5 hiện hành — 16/10/2026

Phase 5 hoàn thành trong worktree/branch nêu bên dưới: API Dashboard/Onsite, trang `/admin/dashboard`, liên kết quản lý/lịch sử/văn phòng và refresh 30 giây. Tái sử dụng lịch sử/xóa ngày và editor sẵn có, không đổi migration hoặc UI User. Login Admin vẫn đến `/admin/users`, có link Dashboard.

Commit theo task: `ae5765d` (snapshot), `39339f6` (Onsite/retention), `2f339d3` (UI/map), `4c80dbc` (refresh/hồi quy); commit Task 5 chứa báo cáo/tài liệu, xem Git log. Baseline `8dd1af2` là mốc trước Phase 5, không phải yêu cầu reset.

Full suite mới **249 passed, 1 warning** trong **406.93s**, kết thúc khoảng 09:10 ngày 16/10/2026 giờ Việt Nam; 218 là baseline lịch sử. Review độc lập không có Critical/Important. Xem [PHASE_5_VERIFICATION](../docs/PHASE_5_VERIFICATION.md), [MANUAL_TEST_PHASE_5](../docs/MANUAL_TEST_PHASE_5.md) cho lệnh, các lượt RED/GREEN, bằng chứng, lỗi baseline đã gặp và giới hạn.

Minor có điều kiện: nếu browser khôi phục nguyên document từ back/forward cache, cần tải lại trang để tiếp tục refresh; Back thực tế trên Edge với header no-store đã tải lại và hoạt động đúng. Chưa chứng nhận hành vi cache trên browser khác, GPS điện thoại/HTTPS thật, hiệu năng 95% ≤2 giây hoặc pilot. Phase 6 chưa thực hiện. Không merge/push/deploy, không chạy migration hoặc tạo/xóa dữ liệu thử trên Supabase thật trong Phase 5.

## 1. Workspace và cách tiếp quản

```powershell
Set-Location 'D:\N.ThanhNhan\INTERN\geoattend\.worktrees\phase-1'
git status --short
git branch --show-current
git log -5 --oneline
```

- Chỉ triển khai trong `.worktrees/phase-1`; không làm trên bản root/main thiếu mã ứng dụng. Giữ các thay đổi chưa commit của người dùng nếu có.
- Baseline nêu trên là mốc bàn giao, không phải yêu cầu reset về commit này. Nếu Git đã tiến thêm, đọc diff/log trước khi tiếp tục.
- Không merge, push, triển khai production hoặc khởi chạy pilot trong Phase 5 này.
- Không đọc/in bí mật `.env` vào chat/log/commit. Máy mới tạo môi trường từ `.env.example` và hướng dẫn DEVELOPMENT.

## 2. Kết quả Phase 0–4

| Phase | Đã thực hiện | Bằng chứng lịch sử |
| --- | --- | --- |
| 0 — Nghiệp vụ/thiết kế | Chốt vai trò, GPS/Geofence, trạng thái, thời gian, dữ liệu, API, UI và tiêu chí pilot. | [Thiết kế đã duyệt](../docs/superpowers/specs/2026-10-14-geoattend-mvp-design.md), [STATE_TRANSITIONS](../docs/STATE_TRANSITIONS.md). |
| 1 — Nền tảng/xác thực | FastAPI, migration/checksum, runtime role, bootstrap một Admin, đăng nhập/đăng xuất, cookie/CSRF, phân quyền, tạo User, đổi/reset mật khẩu và thu hồi session. | 46 test; [báo cáo](../docs/PHASE_1_VERIFICATION.md). |
| 2 — Remote/ngày làm việc | Remote có lý do, Check-out, trạng thái/revision, lịch sử cá nhân, UUID chống lặp, transaction/lock, tự đóng 20:00 và worker chạy bù. | 85 test; [báo cáo](../docs/PHASE_2_VERIFICATION.md). |
| 3 — Office/GIS | Editor Polygon/vùng loại trừ, Office lấy GPS và ST_Covers, lưu vị trí riêng, retention 30 ngày; sửa nền bản đồ, giữ bản nháp và timeout API. | 119 test ban đầu; 122 sau sửa bản đồ; [báo cáo](../docs/PHASE_3_VERIFICATION.md), [MAP_RECOVERY](../docs/MAP_RECOVERY.md). |
| 4 — Nghỉ/tiếp tục/chuyển chế độ | Nghỉ trưa, tiếp tục Office/Remote, nghỉ sáng/cả ngày, hủy nghỉ kết hợp bắt đầu, API chuyển Office ↔ Remote nguyên tử, retry và kiểm thử đồng thời. | 195 test; [báo cáo](../docs/PHASE_4_VERIFICATION.md). |
| Bổ sung đã hoàn thành | Admin xem/xóa vĩnh viễn lịch sử từng ngày; UI User gọn cho điện thoại; thao tác theo ca và khóa sau Check-out cuối ngày. | 210 → 213 → **218 test đạt** ở lần xác minh gần nhất; xem mục 3. |

Các số test là kết quả đã chạy tại từng mốc, không phải lời khẳng định vừa chạy lại khi viết tài liệu. Lần gần nhất: **218 passed, 1 warning**, cảnh báo upstream Starlette/httpx; `pip check` và `git diff --check` đạt. Ở mốc baseline này Phase 5 chưa triển khai; kết quả Phase 5 mới ở mục 0. Phase 6 production/pilot chưa thực hiện. Chưa chứng nhận GPS trên điện thoại thật/HTTPS production.

### Các commit cần biết

| Commit | Nội dung |
| --- | --- |
| `d1c57d9` | Hồi quy và bàn giao Phase 4 (các task trước đó nằm trong Git log). |
| `effce0e` | Admin xem và xóa vĩnh viễn lịch sử nhân viên; migration 004. |
| `161f724` | UI User dành cho điện thoại, lịch sử tải khi mở. |
| `8dd1af2` | Hiển thị thao tác theo nghỉ trưa và khóa sau Check-out cuối ngày. |

## 3. Hợp đồng đã chốt — phải bảo toàn

### Tài khoản, thời gian và an toàn ghi dữ liệu

- Admin chỉ quản lý, không chấm công, không có Marker và không tính vào tổng nhân viên. User do Admin cấp; không tự đăng ký, không Google/Supabase Auth.
- Backend quyết định thời gian theo `Asia/Ho_Chi_Minh` (UTC+07:00). Từ đúng 20:00 không bắt đầu/tiếp tục/chuyển chế độ. Ngày mới tính theo giờ Việt Nam.
- Worker/API đối soát phiên còn mở tại 20:00 và chạy bù khi dừng. Nguồn đóng `SYSTEM`, phân biệt thời điểm nghiệp vụ và `recorded_at`; không gọi 20:00 là giờ nhân viên thực sự kết thúc.
- Tối đa một phiên mở/User. Giữ transaction, profile lock trước day/session lock, kiểm tra lại quyền/session/thời gian sau khi chờ khóa.
- Giữ `request_id`, `expected_revision`, `expected_work_date`, replay UUID cùng payload, từ chối UUID khác payload và tab cũ. Không đổi hash payload cũ hoặc phá pending retry.

### GPS và GIS

- Office lấy GPS một lần mỗi lần bắt đầu/tiếp tục/chuyển vào Office; `ST_Covers` chấp nhận trong/trên ranh giới, không buffer; accuracy được lưu nhưng không dùng để từ chối.
- Remote/nghỉ/Check-out không lấy GPS. Office lỗi giữ trạng thái cũ, không tự chuyển Remote.
- GPS Office chỉ giữ trong bộ nhớ tab khi retry, không ghi storage. Tọa độ/accuracy hết hạn đúng 30 ngày; API che ngay cả khi worker chưa purge.
- Onsite là **vị trí Check-in đã xác minh**, không phải vị trí trực tiếp hay bằng chứng người đó vẫn đang ở văn phòng. Không theo dõi GPS liên tục.

### UI User và khóa cuối ngày — quy tắc mới nhất

1. Thông tin nhân viên ở đầu; ba lựa chọn CHECK-IN OFFICE / CHECK-IN REMOTE / XIN NGHỈ. Chỉ mở lý do khi chọn Remote/nghỉ.
2. Đang làm trước nghỉ trưa: chỉ **NGHỈ TRƯA** và **CHECK-OUT SỚM**.
3. Đang nghỉ trưa: chỉ **TIẾP TỤC OFFICE** và **TIẾP TỤC REMOTE**; Remote vẫn cần lý do, Office xác minh GPS lại.
4. Sau tiếp tục: chỉ **CHECK-OUT**. Sau Check-out cuối ngày khóa đến ngày hôm sau, kể cả reload hoặc gọi API mới.
5. Backend xác định khóa bằng `CHECKED_OUT` và có sự kiện `LUNCH_START` trong ngày; trả `lunch_taken`, `day_finished`. Không suy ra ca bằng giờ trên đồng hồ.
6. Check-out sớm trước nghỉ trưa vẫn cho bắt đầu lại trước 20:00. API chuyển trực tiếp Office/Remote cũ còn được giữ tương thích; UI hiện tại không hiển thị các nút đó khi đang làm. Không tự xóa API hoặc đưa nút cũ trở lại.
7. Lịch sử cá nhân ở cuối, thu gọn, chỉ tải khi mở; phản hồi cũ không được ghi đè lịch sử mới.

Chi tiết: [USER_MOBILE_UI](../docs/USER_MOBILE_UI.md), [STATE_TRANSITIONS mục 6](../docs/STATE_TRANSITIONS.md).

### Admin lịch sử — đã có, không triển khai lại

- `GET /api/admin/users/{account_id}/history`; `DELETE /api/admin/users/{account_id}/history/{day_id}`.
- Có lọc ngày/phân trang, xác nhận nhập đúng username và revision; chặn xóa ngày đang làm hoặc nghỉ trưa/phiên còn mở.
- Xóa vĩnh viễn phiên, sự kiện, lý do, GPS ngày được chọn; giữ tài khoản và ngày khác. Giữ tối thiểu tombstone UUID/hash và revision để chặn replay/tab cũ phục hồi dữ liệu.
- Xóa ngày hôm nay reset về `NOT_STARTED`; đây là ngoại lệ quản trị đã được chấp thuận đối với khóa cuối ngày. Không bỏ ngoại lệ hay tombstone.
- Migration `004_history_deletion.sql` đã áp dụng trên database ứng dụng ở máy bàn giao; máy khác vẫn kiểm tra migration. Không sửa migration 001–004 đã có checksum.

Chi tiết: [ADMIN_HISTORY](../docs/ADMIN_HISTORY.md). Tái sử dụng dialog `admin-history.js` khi liên kết từ Dashboard/Marker.

## 4. Tài liệu và bản đồ mã nguồn cần đọc

Đọc theo thứ tự: tài liệu này → [ROADMAP](../docs/ROADMAP.md) Phase 5 → [BRD](../README.md) các yêu cầu nêu ở đầu → thiết kế MVP mục 8–9 → STATE_TRANSITIONS → USER_MOBILE_UI → ADMIN_HISTORY → [DEVELOPMENT](../docs/DEVELOPMENT.md) → MAP_RECOVERY. Báo cáo Phase 1–4 dùng tra cứu hồi quy, không phải danh sách việc cần làm lại.

| Vị trí | Vai trò |
| --- | --- |
| `app/main.py` | Gắn router, protected page, no-store và CSP; CSP bản đồ hiện chỉ áp dụng `/admin/office`. |
| `app/auth/dependencies.py` | Quyền Admin/User, context session và CSRF; phải dùng cho API mới. |
| `app/attendance/service.py` | `reconcile_locked`, `snapshot`, `read_history`, transaction/lock; không gọi public User status bằng tài khoản Admin. |
| `app/accounts/history_service.py`, `routes.py` | Lịch sử/xóa của Admin, bảo vệ target và session. |
| `app/gis/service.py` | `get_office`, `save_office`, `get_location`, xác minh và retention; PostGIS có thể ở `public` hoặc `extensions`. |
| `app/static/admin-office.html`, `js/admin-office.js` | Đã có tên/địa chỉ/Geofence và kiểm tra revision. |
| `app/static/js/office-map-background.js`, `vendor/` | Nền map và thư viện local/credits; kiểm tra đường dẫn thực trước sửa. |
| `app/static/js/admin-history.js` | Dialog lịch sử; đọc interface thực trước tích hợp. |
| `app/static/js/api.js`, `login.js` | CSRF/timeout và điều hướng đăng nhập hiện tại. |
| `tests/db_fixtures.py`, `tests/conftest.py`, `tests/browser_attendance.py` | Database test cô lập, clock/GPS giả lập và helper browser. |
| `tests/integration/test_daily_action_ui.py`, `test_user_mobile_layout.py` | Hồi quy UI User và khóa cuối ngày. |
| `migrations/`, `app/db/migrations.py` (`grant_runtime`) | Schema và quyền tối thiểu; chỉ thêm migration kế tiếp nếu thật sự cần. |

## 5. Phạm vi và hợp đồng Phase 5

### Phải hoàn thành

- Tổng số và danh sách **tất cả tài khoản USER**, gồm chưa bắt đầu; không loại âm thầm tài khoản bị khóa khỏi tổng số. Có thể hiện trạng thái tài khoản riêng, nhưng không trộn vào trạng thái chấm công.
- Bảy trạng thái: `NOT_STARTED`, `WORKING_OFFICE`, `WORKING_REMOTE`, `LUNCH_BREAK`, `MORNING_LEAVE`, `FULL_DAY_LEAVE`, `CHECKED_OUT`. Hai loại nghỉ tách riêng; số lượng khớp danh sách và tổng User.
- API Admin theo thiết kế: `GET /api/admin/dashboard`, `GET /api/admin/onsite`; snapshot có `as_of`, `work_date`. Trạng thái hôm nay phải đối soát đúng 20:00/ngày mới khi worker chưa chạy.
- Onsite chỉ từ trạng thái `WORKING_OFFICE` và **phiên Office đang mở tương ứng** có xác minh; không lấy điểm từ phiên Office cũ sau chuyển ca/chế độ.
- Map hiển thị Geofence, tên Marker; Popup gồm tên, trạng thái, giờ Check-in, xác minh GPS, thao tác xem lịch sử. Hết hạn GPS không trả tọa độ/accuracy, hiển thị “Dữ liệu vị trí đã hết hạn lưu”. Thiếu vị trí không đặt Marker giả tại tâm văn phòng hoặc (0,0).
- Làm mới mỗi **30 giây khi trang hiển thị**, khi quay lại tab và bấm tải lại. Hiện thời điểm snapshot và nhãn dữ liệu cũ khi lỗi mạng. Không lấy GPS khi refresh.
- Dùng lại lịch sử Admin và trang văn phòng. Tên/địa chỉ/Polygon đã có: kiểm chứng FR-15, bổ sung điều hướng; không tạo editor thứ hai. Múi giờ và cutoff cố định, không thêm cài đặt cho phép sửa.

### Quyết định triển khai để tránh mâu thuẫn

- Tạo `app/admin/` cho API tổng hợp, không trộn truy vấn Dashboard vào action ghi chấm công. Các tên file mới ở task dưới là kế hoạch, chưa tồn tại ở baseline.
- Dùng một builder snapshot chung trả tổng số, nhóm trạng thái, nhân viên và dữ liệu Onsite; cả hai API dùng chung builder/hợp đồng. Dashboard có thể nhận kèm dữ liệu Onsite trong cùng phản hồi để số lượng/danh sách/map hiển thị từ cùng snapshot. Endpoint Onsite là projection của cùng mô hình.
- Đối soát bằng cơ chế `reconcile_locked` đã có, khóa profile theo thứ tự ID ổn định trước day/session; không lấy lock Admin/nhân viên với thứ tự tùy ý. Chọn một `as_of` sau khi có các khóa cần thiết và kiểm tra lại session; đọc các thành phần từ cùng snapshot giao dịch. Không gọi `lock_user` cho User bị khóa vì Dashboard vẫn phải liệt kê tài khoản đó.
- Không cần migration cho chức năng đọc nếu schema hiện tại đủ. Nếu phát hiện cần index/schema, thêm migration mới, test trên DB riêng trước; không tự chạy migration mới lên Supabase thật trong lần bàn giao này.
- Các trường response chi tiết phải được ghi rõ bằng schema/test ở Task 1 trước khi UI tiêu thụ; không đổi hợp đồng API Phase 0–4.

### Ngoài phạm vi

Không làm Phase 6, payroll, chấm trễ/về sớm tự động, duyệt nghỉ, QR, theo dõi GPS liên tục, nhiều văn phòng, xuất báo cáo nâng cao, PWA/AI-RAG; không refactor diện rộng hoặc nâng framework để làm Dashboard.

## 6. Phase 5 Implementation Plan — thực hiện tuần tự

### Task 1 — Snapshot Admin và kiểm thử quyền/nhất quán

**Files:** tạo `app/admin/__init__.py`, `schemas.py`, `service.py`, `routes.py`; sửa `app/main.py`; tạo `tests/integration/test_admin_dashboard.py`.

**Interfaces:** builder nội bộ `build_snapshot(conn, context) -> dict` trả `as_of`, `work_date`, `total_users`, `counts`, `items`, `onsite`. Mỗi employee có ID, username, full_name, is_active, status và thông tin phiên hiện tại cần hiển thị. `counts` chứa đủ bảy key kể cả 0. Hai route nêu ở mục 5 dùng cùng builder; schema được cố định bằng test trong task này.

- [x] Viết test quyền: anonymous 401, User 403, Admin 200; không lộ hash/session/token.
- [x] Viết test đủ bảy trạng thái, USER chưa có attendance_day, tài khoản bị khóa, không tính Admin; `sum(counts.values()) == total_users == len(items)`; từng nhóm khớp danh sách.
- [x] Viết test trước/đúng/sau 20:00, qua ngày, worker dừng, hủy nghỉ và ngày bị Admin xóa; đọc lặp không tạo sự kiện SYSTEM trùng.
- [x] Chạy test xác nhận đỏ vì endpoint chưa có; triển khai snapshot/route với quyền, transaction và thứ tự lock đã nêu; test đồng thời với action/xóa lịch sử, session bị thu hồi khi chờ lock.
- [x] Chạy `.\.venv\Scripts\python.exe -m pytest tests/integration/test_admin_dashboard.py -q` với DSN test riêng; đạt toàn bộ mới commit task.

### Task 2 — Dữ liệu Onsite và bảo vệ GPS

**Files:** mở rộng `app/admin/schemas.py`, `service.py`, `routes.py`; tạo `tests/integration/test_admin_onsite.py`; tái sử dụng GIS hiện có.

**Interfaces:** `GET /api/admin/onsite` trả thời điểm/ngày snapshot, danh sách Office và thông tin vị trí `available`/`expired`/không có; available mới có tọa độ/accuracy. Đầu ra Onsite kèm Dashboard dùng cùng quy tắc. Văn phòng đọc từ `get_office(conn)` qua API hiện có hoặc thành phần snapshot dùng chung.

- [x] Viết test Office đã xác minh được lấy đúng từ phiên mở; resume Office dùng điểm mới, không điểm ca trước; rời Onsite sau lunch/Remote/checkout khi refresh.
- [x] Viết test GPS trước/đúng/sau hạn 30 ngày khi chưa purge; không lộ tọa độ/accuracy hết hạn; thiếu location không dùng tọa độ thay thế; giữ kết quả xác minh.
- [x] Viết test chưa cấu hình Geofence, sửa Geofence không sửa điểm lịch sử, PostGIS schema được fixture hỗ trợ, và quyền tương tự Task 1.
- [x] Chạy test đỏ; bổ sung truy vấn/serialization tối thiểu, không lưu bản sao GPS vào bảng/cache khác.
- [x] Chạy hai file test Admin mới; đạt toàn bộ mới commit task.

### Task 3 — Dashboard và Onsite Map

**Files:** tạo `app/static/admin-dashboard.html`, `app/static/js/admin-dashboard.js`; sửa `app/main.py`, CSS và điều hướng Admin/login liên quan; tái sử dụng nền map và dialog lịch sử. Tạo `tests/integration/test_admin_dashboard_browser.py`.

**Interfaces:** trang bảo vệ `/admin/dashboard`; tiêu thụ schema Task 1–2. Lịch sử dùng endpoint/dialog sẵn có; văn phòng liên kết `/admin/office`. Không thay trang/chấm công User.

- [x] Viết browser test thẻ số lượng/danh sách/Marker khớp snapshot, Popup đủ trường, click chi tiết mở đúng lịch sử User, link văn phòng/tài khoản dùng được.
- [x] Viết test tên/lý do có HTML được hiển thị bằng text; không chèn vào `innerHTML` hoặc HTML Popup không escape.
- [x] Chạy đỏ rồi triển khai HTML/JS. Dùng thư viện map local, credits hiện có và CSP chỉ mở origin cần thiết cho trang mới; không làm CSP toàn app rộng hơn tùy ý.
- [x] Khi map tải lỗi, Dashboard/danh sách/lịch sử vẫn dùng được, có thông báo và thử lại; không xóa dữ liệu đã tải. Kiểm tra điện thoại 360px và desktop, không tràn ngang.
- [x] Chạy browser test mới cùng `test_user_mobile_layout.py`, `test_daily_action_ui.py`; đạt mới commit task.

### Task 4 — Refresh, lỗi mạng và hồi quy quản lý

**Files:** mở rộng JS Dashboard và test browser/API Admin; chỉ sửa code chung nếu test chứng minh cần.

**Interfaces:** refresh 30 giây chỉ khi tab visible; visibility/manual refresh dùng cùng loader. Kết quả cũ không ghi đè snapshot mới; hiển thị `as_of` của dữ liệu đang vẽ.

- [x] Test bằng timer/clock có kiểm soát: 30 giây, quay lại tab, tải tay; tab ẩn dừng polling, không tạo nhiều timer hoặc request chồng không kiểm soát.
- [x] Test giữ phản hồi cũ rồi trả sau phản hồi mới; UI phải giữ bản mới. Test timeout/503: giữ snapshot cũ với nhãn cũ, phục hồi bỏ nhãn; 401 quay lại login, 403 không tiếp tục polling trái quyền.
- [x] Test fake geolocation báo lỗi nếu bị gọi khi refresh Dashboard; không được có lời gọi GPS nào.
- [x] Kiểm tra lại trang văn phòng tên/địa chỉ/Polygon/revision và quyền bằng test hiện có; không đổi cutoff/múi giờ. Tái sử dụng test lịch sử/xóa vĩnh viễn, đảm bảo Dashboard phản ánh ngày reset ở lần refresh tiếp theo.
- [x] Chạy test đỏ cho từng hành vi mới, sửa tối thiểu, chạy bộ Admin và test hồi quy liên quan; đạt mới commit task.

### Task 5 — Xác minh và bàn giao Phase 5

**Files:** tạo `docs/PHASE_5_VERIFICATION.md`, `docs/MANUAL_TEST_PHASE_5.md`; cập nhật ROADMAP, DEVELOPMENT, README và tài liệu bàn giao này theo kết quả thực tế.

- [x] Chạy full suite trên DB test riêng, `pip check`, `git diff --check`; ghi lệnh, kết quả, giới hạn và thời điểm chạy.
- [x] Kiểm tra tay/browser Dashboard → Marker → lịch sử → văn phòng; map lỗi mạng; refresh rời Onsite; desktop/mobile. Không dùng dữ liệu thử trên Supabase thật.
- [x] Đối chiếu AC-01 phần Admin, AC-07/08/15/16 và các hợp đồng mục 3. Không bỏ/sửa kỳ vọng test cũ chỉ để suite xanh; nếu xung đột nghiệp vụ thật sự thì báo rõ và hỏi.
- [x] Kiểm tra diff không thay migration cũ, không làm mất kiểm thử cũ, không có secrets; ghi commit và rủi ro còn lại. Commit tài liệu sau khi xác minh đạt; không tự merge/push/deploy.

## 7. Review Focus và điều kiện hoàn thành

Các tình huống bắt buộc đã được phân vào task: qua cutoff/ngày mới khi worker dừng (Task 1); tranh chấp với action/xóa lịch sử và thu hồi session khi chờ lock (Task 1); điểm Office cũ/GPS hết hạn chưa purge (Task 2); tên chứa HTML/map không tải được (Task 3); phản hồi đảo thứ tự/tab ẩn/lỗi mạng (Task 4).

Phase 5 chỉ hoàn tất khi API và UI đạt các tiêu chí trên, full suite gồm hồi quy Phase 0–4 đạt, số lượng khớp danh sách, Marker rời Onsite sau đổi trạng thái, User không truy cập API Admin, GPS hết hạn không lộ, cài đặt văn phòng giữ giới hạn đã duyệt. Không tuyên bố đạt pilot hoặc mục tiêu hiệu năng 95% ≤2 giây nếu chưa đo; pilot khoảng 10 người/5 ngày thuộc Phase 6.

Hạn chế đã biết từ trước: timeline của sự kiện có cùng `event_time` và `recorded_at` có thể sắp theo UUID khiến thứ tự hiển thị sự kiện ghép không như mong đợi; trạng thái/transaction/replay vẫn đúng. Không biến việc này thành refactor Phase 4 ngoài phạm vi nếu không chặn Phase 5; báo rõ nếu gặp.

## 8. Chạy web và kiểm thử an toàn

Hai terminal tại worktree:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_run serve
```

```powershell
.\.venv\Scripts\python.exe -m scripts.local_run maintenance
```

Mở `http://127.0.0.1:8000/login`. Chỉ một server port 8000 và một worker; backend đổi cần restart, static đổi cần Ctrl+F5. Không tắt tiến trình không rõ chủ. `/favicon.ico` 404 chỉ thiếu icon, không phải lỗi khởi động.

Trên máy bàn giao có PostgreSQL17/PostGIS test ở port **55440**, cluster `.local-tests/phase-3/pgdata`. Kiểm tra server sẵn sàng trước, không initdb/xóa cluster cũ. DSN sau chỉ dành cho cluster local test đã xác minh:

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.local-tests/phase-5/run-01 -o cache_dir=.local-tests/phase-5/cache
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Fixture tự tạo/drop `geoattend_test_<uuid>`; tuyệt đối không trỏ biến test vào database ứng dụng/Supabase thật. Máy khác dùng DB test riêng được cấu hình phù hợp, không giả định cluster này tồn tại. Đổi tên `run-01` khi cần lần mới; thư mục `.local-tests`, `.venv`, `.env` không được commit.

Không tự tạo tài khoản/chấm công/Geofence thử hoặc xóa dữ liệu trên Supabase thật. Không chạy migration mới trên database thật nếu chưa được cho phép riêng; chuẩn bị migration và chứng minh bằng DB test trước.

## 9. Prompt gửi agent tiếp theo

```text
Đọc .worktrees/phase-1/handoff/README_PHASE_0_5.md và docs/PHASE_5_VERIFICATION.md trước khi sửa mã. Kiểm tra Git thực tế; Phase 0–5 cùng Admin history/UI User/khóa cuối ngày đã hoàn thành. Full suite Phase 5 ngày 16/10/2026: 249 passed, 1 warning; không dùng 218 làm kết quả mới, không reset/làm lại các task cũ.

Làm việc trong .worktrees/phase-1, tuân thủ AGENTS.md/skill bắt buộc và thực hiện đúng yêu cầu mới của người dùng. Giữ hợp đồng mục 3, transaction/lock/idempotency, retention GPS 30 ngày, UI theo ca và khóa ngày. Đọc giới hạn/minor còn lại trong báo cáo; không mặc định đã chứng nhận pilot, GPS điện thoại/HTTPS, bfcache đa browser hoặc mục tiêu hiệu năng.

Không tạo/xóa dữ liệu thử hoặc chạy migration lên Supabase thật nếu chưa được cho phép riêng. Không tự merge/push/deploy/pilot. Phase 6 chỉ thực hiện khi người dùng giao phạm vi cụ thể. Dùng PostgreSQL/PostGIS test riêng; không sửa migration đã áp dụng, không bỏ/nới test cũ. Cuối công việc báo lệnh/kết quả thực tế, commit và giới hạn.
```
