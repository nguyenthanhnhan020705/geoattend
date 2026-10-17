# GeoAttend — Cài đặt và phát triển

Chạy các lệnh tại thư mục chứa `app/`, `scripts/` và `requirements.lock.txt`. Sau khi clone, đây là thư mục `geoattend`; trên máy phát triển hiện tại là `.worktrees/phase-1`.

Cài nhanh theo [README](../README.md). Thao tác nghiệp vụ xem [USAGE](USAGE.md); quy tắc hiện hành xem [STATE_TRANSITIONS](STATE_TRANSITIONS.md). Triển khai HTTPS, log, backup/restore và worker xem [runbook](PHASE_6_OPERATIONS.md).

## 1. Chuẩn bị

### Chạy local với Supabase đã cấu hình

File `.env` tại thư mục dự án có `SUPABASE_DB_HOST/PORT/NAME/USER/PASSWORD/SSLMODE` và `GEOATTEND_RUNTIME_DB_USER/PASSWORD`. User qua session pooler có dạng `role.projectref`, port 5432. Không gửi mật khẩu vào chat hay commit `.env`.

Không cần nạp biến môi trường thủ công mỗi lần mở Terminal. Launcher local đọc `.env`, escape mật khẩu qua Psycopg và chỉ truyền DSN phù hợp cho tiến trình con:

```powershell
# Chỉ khi cần thiết lập/cập nhật schema: migration bằng tài khoản quản trị.
.\.venv\Scripts\python.exe -m scripts.local_run migrate

# Terminal 1: web/API.
.\.venv\Scripts\python.exe -m scripts.local_run serve

# Terminal 2: maintenance độc lập, mỗi phút.
.\.venv\Scripts\python.exe -m scripts.local_run maintenance

# Maintenance một lần.
.\.venv\Scripts\python.exe -m scripts.local_run maintenance --once
```

Mở `http://127.0.0.1:8000/login`. Khi tắt máy, hai tiến trình dừng; lần sau chạy lại hai lệnh serve/maintenance. Không chạy lại SQL CREATE ROLE hoặc bootstrap Admin. Database mới khởi tạo Admin bằng `local_run bootstrap-admin`.

User bắt đầu Remote có lý do hoặc Office có GPS; mọi Check-out kết thúc ngày, chỉ ngày hôm sau theo giờ Việt Nam mở lại (trừ Admin xóa hôm nay/reset hợp lệ). Xem lịch sử theo ngày. Remote giữ mã thao tác/payload trong sessionStorage để gửi lại; Office giữ payload GPS trong bộ nhớ tab, không lưu vào storage. API chỉ trả lịch sử của chính User; Admin không chấm công. Admin mở `/admin/office` để vẽ và lưu vùng thực tế; chưa cấu hình thì Office bị từ chối.

Maintenance đóng phiên còn mở tại 20:00 giờ Việt Nam và xóa tọa độ/accuracy hết hạn 30 ngày. Nếu máy/tác vụ tắt lúc đó, lần chạy lại xử lý bù; API luôn che GPS hết hạn dù worker chưa chạy. Muốn tác vụ chạy đúng phút khi không ai mở web cần máy chạy maintenance liên tục; production cần worker độc lập. Nghỉ trưa lúc 20:00 chỉ ghi kết thúc ngày, giữ giờ đóng phiên trước nghỉ; nghỉ sáng/cả ngày giữ nguyên trạng thái.

Bản đồ nền mặc định OpenFreeMap (vector), không cần API key; Leaflet, MapLibre và thư viện kết nối được phục vụ local. `GEOATTEND_MAP_BACKGROUND=auto` chọn nền vector mặc định, hoặc raster nếu đã cấu hình URL tile khác. Có thể chọn rõ `vector`/`raster`; nền raster dùng `GEOATTEND_MAP_TILE_URL` (HTTPS, có `{z}/{x}/{y}`) và `GEOATTEND_MAP_ATTRIBUTION`. `GEOATTEND_MAP_STYLE_URL` cấu hình style vector HTTPS; các tài nguyên của style cần cùng origin để phù hợp CSP. Lỗi tải nền không ngăn chỉnh/sửa vùng. GPS chỉ lấy khi User bấm Office; Check-out/Remote không lấy vị trí. Sau khôi phục backup, thực hiện đủ quy trình trong [runbook](PHASE_6_OPERATIONS.md), gồm dọn GPS hết hạn, đối soát lịch sử đã xóa và thu hồi phiên đăng nhập trước khi mở dịch vụ.

- Python 3.13; PostgreSQL có PostGIS và tài khoản migration có quyền tạo schema/extension.
- Một tài khoản database runtime riêng, không phải superuser hoặc owner schema; database thử nghiệm khác database dùng ứng dụng.
- Giao diện và API chạy cùng nguồn. Local dùng HTTP loopback; môi trường triển khai dùng HTTPS.

Chạy trong thư mục project (worktree Phase 1 nếu đang phát triển bằng worktree):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock.txt
.\.venv\Scripts\python.exe -m pip check
```

Chỉ chạy ứng dụng thì cài `requirements.lock.txt`. Các lockfiles được sinh bằng Python 3.13 trên Windows; kiểm chứng và sinh lại lockfile tương ứng trước dùng platform/Python khác. File yêu cầu trực tiếp nằm ở `requirements.txt` và `requirements-dev.txt`.

## 2. Cấu hình database

Tham khảo `.env.example`. Ứng dụng đọc environment; không tự nạp `.env`.

```powershell
$env:GEOATTEND_DATABASE_URL = 'postgresql://geoattend_runtime:CHANGE_ME@127.0.0.1:5432/geoattend'
$env:GEOATTEND_MIGRATION_DATABASE_URL = 'postgresql://migration:CHANGE_ME@127.0.0.1:5432/geoattend'
$env:GEOATTEND_ORIGIN = 'http://127.0.0.1:8000'
$env:GEOATTEND_SECURE_COOKIES = 'false'
```

`CHANGE_ME` chỉ là placeholder, không phải thông tin đăng nhập được cấp. Dùng DSN thực của môi trường, URL-encode ký tự đặc biệt trong password; không commit DSN hoặc ghi vào log. Nếu dùng Supabase, lấy chuỗi kết nối PostgreSQL dành cho Backend; không dùng khóa frontend để kết nối database.

Runtime role phải tồn tại trước migration. Ví dụ SQL quản trị trên database mới (thay mật khẩu mẫu bằng bí mật của môi trường):

```sql
CREATE ROLE geoattend_runtime LOGIN PASSWORD 'CHANGE_ME';
```

Chạy migration với hai DSN đã cấu hình:

```powershell
.\.venv\Scripts\python.exe -m scripts.migrate
```

Migration tạo schema `geoattend`, tìm extension PostGIS hiện có (hỗ trợ schema `public` hoặc `extensions`), hoặc tạo extension mới tại `public` nếu được phép. Tạo đủ 9 bảng, ghi version/checksum và cấp quyền runtime theo user trong DSN ứng dụng. Runtime có DML cần thiết, quyền DELETE các bảng xác thực cần dọn và ba bảng con chấm công `work_sessions`, `attendance_events`, `office_locations` phục vụ xóa lịch sử; không DELETE `profiles` hoặc ALTER/CREATE schema. Không dùng cùng database role cho runtime và migration.

Schema `geoattend` không được thêm vào danh sách exposed schemas/API dữ liệu Supabase. Frontend không kết nối trực tiếp database. Migration chạy lại không xóa bảng hoặc dữ liệu; thay đổi migration đã áp dụng sẽ bị từ chối theo checksum, thay vào đó thêm file migration mới.

## 3. Khởi tạo và khôi phục Admin

```powershell
.\.venv\Scripts\python.exe -m scripts.bootstrap_admin
```

Nhập tên tài khoản, họ tên và mật khẩu qua prompt. Mật khẩu nhập ẩn; chạy lại không tạo Admin thứ hai hoặc tự thay mật khẩu của Admin hiện có. Tên đăng nhập chuẩn hóa chữ thường, 3–50 ký tự; mật khẩu 8–128 ký tự.

Nếu quên mật khẩu Admin, người vận hành có quyền quản trị môi trường chạy:

```powershell
.\.venv\Scripts\python.exe -m scripts.recover_admin
```

Xác nhận tên Admin, nhập mật khẩu mới; mọi phiên đăng nhập của Admin bị thu hồi. Không có endpoint công khai phục hồi Admin. User quên mật khẩu thì liên hệ Admin đặt lại qua giao diện quản lý.

## 4. Chạy ứng dụng

Dữ liệu xác thực hết hạn có thể dọn bằng `.\.venv\Scripts\python.exe -m scripts.prune_auth`, dùng runtime DSN trong giao dịch riêng. Login chỉ dọn các lần thử sai của tên tài khoản đang đăng nhập, không khóa/xóa phiên của tài khoản khác; session hết hạn/revoked bị từ chối ngay dù chưa được dọn vật lý. Maintenance định kỳ ở Phase 2 đã dùng cùng chức năng dọn này.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Truy cập `http://127.0.0.1:8000/login`, đăng nhập bằng tài khoản đã tạo:

- Admin đến `/admin/users`: cấp User, tải danh sách và đặt lại mật khẩu; chọn **Dashboard** để mở `/admin/dashboard` theo dõi trạng thái/Onsite/lịch sử.
- User đến `/user`: thông tin cá nhân và liên kết đổi mật khẩu.
- Cả hai có `/account`, đổi mật khẩu và đăng xuất.
- `/api/health` kiểm tra database; lỗi không lộ DSN.

Admin cấp thông tin tài khoản cho nhân viên bên ngoài ứng dụng. User được dùng ngay mật khẩu được cấp, không bị buộc đổi lần đầu. Đổi/reset mật khẩu thu hồi toàn bộ phiên của tài khoản bị tác động; mật khẩu cũ không dùng được nữa. Session đăng nhập có hạn tuyệt đối 12 giờ.

Trong môi trường HTTPS, đặt `GEOATTEND_ORIGIN` thành nguồn HTTPS chính xác và `GEOATTEND_SECURE_COOKIES=true`. Trình duyệt gọi API cùng nguồn, mutation có CSRF token; không mở CORS rộng để né lỗi Origin. Cookie Secure không gửi trên HTTP thông thường, ngoại trừ cách trình duyệt xử lý loopback.

## 5. Kiểm thử

Kiểm thử không cần database:

```powershell
.\.venv\Scripts\python.exe -m pytest -m 'not integration' -q
```

Kiểm thử integration cần PostgreSQL/PostGIS riêng. Tài khoản test cần CREATEDB, quyền tạo role test và extension; không dùng DSN ứng dụng/migration làm test DSN. Bộ test tạo database `geoattend_test_<uuid>`, chỉ dọn database do nó tạo. Bên trong database tạm, schema được dựng mới theo từng case.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL = 'postgresql://test_admin:CHANGE_ME@127.0.0.1:5432/geoattend_test'
.\.venv\Scripts\python.exe -m pytest -m 'integration and not browser' -q
```

Thiếu/trùng DSN test sẽ báo lỗi, không skip rồi báo thành công. Dùng PostgreSQL local cho bộ integration nếu dịch vụ hosted không cấp CREATEDB/CREATEROLE; cấu hình Supabase thực được kiểm tra riêng khi triển khai.

Kiểm tra browser sử dụng Edge headless trên Windows nếu có, hoặc Chromium do Playwright quản lý:

```powershell
# Chỉ cần lệnh cài browser khi máy không có Edge phù hợp.
.\.venv\Scripts\python.exe -m playwright install chromium
$env:GEOATTEND_BROWSER_CHANNEL = 'chromium'
.\.venv\Scripts\python.exe -m pytest -m browser -q
```

Bộ browser chạy live Uvicorn/database riêng, kiểm tra Admin cấp User, User đổi mật khẩu, Admin reset, logout, hiển thị tên dạng text và không tràn ngang ở 360px. Screenshot lưu trong `.superpowers/sdd/2026-10-14-phase-1-foundation-auth/artifacts/`, không chứa mật khẩu.

Khi có test DSN và browser phù hợp, chạy toàn bộ:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

## 6. Kiểm chứng và trạng thái hiện hành

Full suite gồm cả kiểm tra Caddy. Để chạy ca proxy thay vì skip, đặt `GEOATTEND_CADDY_BINARY` trỏ tới binary Caddy đã xác minh theo [báo cáo Phase 6](PHASE_6_VERIFICATION.md). Diễn tập restore dùng `pg_dump`/`pg_restore` và chỉ chấp nhận database test local. Các binary, database test, `.env` và ảnh/log local không nằm trên GitHub; cần chuẩn bị trên máy mới.

Kết quả kiểm thử, đo tải và giới hạn nằm trong [PHASE_6_VERIFICATION](PHASE_6_VERIFICATION.md), [PHASE_6_PERFORMANCE](PHASE_6_PERFORMANCE.md) và [ma trận nghiệm thu](PHASE_6_ACCEPTANCE.md). Checklist thiết bị thật/pilot tại [PHASE_6_PILOT](PHASE_6_PILOT.md); tiến độ tại [ROADMAP](ROADMAP.md).

## 7. Các hợp đồng cần giữ khi phát triển

- Ghi phiên, sự kiện, trạng thái và mã yêu cầu trong cùng transaction; khóa profile trước các khóa ngày/phiên.
- Action dùng `request_id`, `expected_revision`, `expected_work_date`. Cùng UUID/nội dung trả lại kết quả cũ; màn hình cũ hoặc UUID khác nội dung bị từ chối.
- Retry Office giữ GPS trong bộ nhớ tab; các action không GPS có thể giữ pending trong sessionStorage. Không lưu GPS vào storage/log.
- Check-out và nghỉ cả ngày khóa ngày; action hủy nghỉ cũ chỉ còn phục vụ replay dữ liệu đã commit. API chuyển trực tiếp Office/Remote giữ tương thích, UI theo ca không có nút chuyển trực tiếp khi đang làm việc.
- `GET /api/admin/dashboard` trả số lượng/danh sách/Onsite/văn phòng cùng snapshot; refresh 30 giây khi trang hiển thị. Onsite chỉ dùng vị trí của phiên Office đang mở đã xác minh và còn hạn lưu.
- Chỉnh Geofence không xác minh lại phiên cũ. Các migration 001–004 đã áp dụng phải giữ checksum; thay đổi schema cần migration mới.
- Xóa lịch sử Admin theo [ADMIN_HISTORY](ADMIN_HISTORY.md); giữ dấu revision/UUID để chặn retry phục hồi dữ liệu đã xóa.

Các kế hoạch và số liệu từng phase trước được giữ riêng trong [archive](archive/README.md).
