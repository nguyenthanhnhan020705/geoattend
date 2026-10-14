# GeoAttend — Chạy và kiểm tra Phase 1

Phase 1 cung cấp đăng nhập, tài khoản cá nhân và Admin cấp/đặt lại tài khoản User. Luồng Office/Remote, lịch sử nghiệp vụ, Dashboard và bản đồ được triển khai ở các phase sau; migration đã chuẩn bị mô hình dữ liệu của MVP.

## 1. Chuẩn bị

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

Migration tạo schema `geoattend`, tìm extension PostGIS hiện có (hỗ trợ schema `public` hoặc `extensions`), hoặc tạo extension mới tại `public` nếu được phép. Tạo đủ 9 bảng, ghi version/checksum và cấp quyền runtime theo user trong DSN ứng dụng. Runtime có DML cần thiết, chỉ DELETE các bảng xác thực cần dọn, không ALTER/CREATE schema. Không dùng cùng database role cho runtime và migration.

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

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Truy cập `http://127.0.0.1:8000/login`, đăng nhập bằng tài khoản đã tạo:

- Admin đến `/admin/users`: cấp User, tải danh sách và đặt lại mật khẩu.
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

## 6. Phạm vi bàn giao

Xem [roadmap](ROADMAP.md) và [kế hoạch Phase 1](superpowers/plans/2026-10-14-phase-1-foundation-auth.md). Các thao tác chấm công và các tác vụ 20:00/GPS 30 ngày thuộc phase kế tiếp; không phải chức năng đã triển khai trong Phase 1. Hạ tầng Supabase/production chưa được tạo hoặc cấu hình tự động bằng lần thực hiện này.
