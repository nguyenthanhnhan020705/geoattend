# GeoAttend Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Phương thức thực hiện chờ người dùng chọn; chưa phân công agent hoặc viết mã sản phẩm.

**Goal:** Chạy được ứng dụng cùng nguồn, database PostGIS, một Admin và luồng cấp/đăng nhập/đổi/đặt lại mật khẩu User.

**Architecture:** FastAPI phục vụ trang HTML/CSS/JS và API. Psycopg pool kết nối schema `geoattend`; phiên đăng nhập lưu database và dùng cookie. Phase 1 chỉ xây nền tảng và tài khoản; nghiệp vụ chấm công được triển khai từ Phase 2.

**Tech Stack:** Python 3.13, FastAPI, Uvicorn, Psycopg 3/pool, Argon2id, PostgreSQL/PostGIS, Pytest, HTTPX; pip/venv trên Windows.

**Spec:** [Thiết kế MVP đã duyệt](../specs/2026-10-14-geoattend-mvp-design.md), nhất là mục 2–4, 8–11. [BRD](../../../README.md): FR-01, FR-16–18; AC-01 phần xác thực, AC-17–19. Phần lịch sử trong AC-01 thuộc phase sau.

**Trạng thái:** kế hoạch đã lập, chờ duyệt và chọn cách thực hiện. Không coi các bước kiểm thử trong tài liệu là đã chạy.

## Global Constraints

- Một Admin chỉ quản lý; mọi tài khoản tạo qua API có vai trò `USER`.
- Username trim/lowercase, 3–50 ký tự, `[a-z0-9._-]`; mật khẩu 8–128 ký tự, không trim; họ tên giữ tiếng Việt.
- Chỉ lưu Argon2id hash mật khẩu; không có đăng ký công khai, Google login hoặc mật khẩu trong log/Git.
- Cookie `geoattend_session`: HttpOnly, SameSite=Lax, Path=/, Secure trên HTTPS; hạn tuyệt đối 12 giờ.
- API mutation cần CSRF và kiểm tra nguồn; login JSON, từ chối Origin khác khi được gửi.
- Đổi/reset mật khẩu thu hồi mọi phiên của tài khoản bị tác động; User dùng mật khẩu được cấp ngay, không bắt buộc đổi lần đầu.
- Sau 5 lần đăng nhập sai/tên tài khoản chuẩn hóa trong 5 phút, từ chối tiếp với 429 đến khi cửa sổ giảm dưới 5; không khóa vĩnh viễn.
- Schema `geoattend` không mở qua API Supabase; quyền runtime và migration riêng; browser chỉ gọi FastAPI.
- Trạng thái/ngày/GPS/Geofence tuân thủ spec, nhưng API chấm công, bản đồ và maintenance nghiệp vụ chưa nằm trong Phase 1.

## Review Focus

1. Reset/đổi mật khẩu đồng thời login: không để phiên dựa trên mật khẩu cũ sống sót sau commit — Task 4–5.
2. Cookie hết hạn/revoked/inactive và CSRF khác phiên: từ chối ngay tại Backend — Task 4.
3. Username khác hoa/thường/space và role client giả mạo: không trùng tài khoản hoặc nâng quyền — Task 3, 5.
4. Migration/bootstrap chạy lại hoặc đồng thời: không mất dữ liệu, không tạo Admin thứ hai — Task 2–3.
5. Database lỗi và nội dung họ tên giống HTML: giữ thông tin mật khẩu khỏi phản hồi/log, hiển thị tên bằng text — Task 1, 6.

## Môi trường, phụ thuộc và giao diện chung

Hiện repo chỉ có tài liệu. Đã đọc môi trường: Python 3.13.3; không tìm thấy `uv`/`docker` qua `Get-Command`. Không yêu cầu Docker để viết/chạy unit tests; integration cần database PostGIS riêng do người dùng cung cấp hoặc chuẩn bị trong bước thực hiện.

Chọn dependency trực tiếp, đối chiếu bản phát hành công khai trên PyPI (không khẳng định đây là các phiên bản mới nhất): [fastapi 0.143.0](https://pypi.org/project/fastapi/0.143.0/), [uvicorn 0.53.0](https://pypi.org/project/uvicorn/0.53.0/), [psycopg 3.3.6](https://pypi.org/project/psycopg/3.3.6/), [psycopg-pool 3.3.3](https://pypi.org/project/psycopg-pool/3.3.3/), [argon2-cffi 25.1.0](https://pypi.org/project/argon2-cffi/25.1.0/), [pytest 9.1.1](https://pypi.org/project/pytest/9.1.1/), [httpx 0.28.1](https://pypi.org/project/httpx/0.28.1/). Task 1 kiểm chứng cài đặt với Python hiện tại và lưu toàn bộ dependency đã resolve vào lockfile; nếu có bất tương thích, sửa pin và ghi kết quả trước chuyển task.

`requirements.txt`: FastAPI/Uvicorn, `psycopg[binary]`, psycopg-pool, argon2-cffi với pin trên. `requirements-dev.txt` thêm Pytest/HTTPX và tham chiếu runtime. Lockfiles tách runtime/dev; sinh trong venv sạch, không ghi package bên ngoài dự án.

Cấu hình qua environment, `.env.example` chỉ minh họa; không tự đọc `.env` nếu chưa có cơ chế nạp rõ. Các biến: `GEOATTEND_DATABASE_URL`, `GEOATTEND_MIGRATION_DATABASE_URL`, `GEOATTEND_TEST_DATABASE_URL`, `GEOATTEND_ORIGIN`, `GEOATTEND_SECURE_COOKIES`. Origin chỉ scheme/host/port, mặc định local `http://127.0.0.1:8000`; yêu cầu Secure khi origin HTTPS. Không in DSN. `SESSION_TTL_SECONDS=43200` là hằng số.

Giao diện dùng chung:

- `Settings.from_env() -> Settings`: config bất biến, kiểm tra origin/DSN; không mở kết nối tại import.
- `create_app(settings: Settings | None = None, pool: ConnectionPool | None = None) -> FastAPI`: injection pool để kiểm thử; lifespan quản lý pool do app tạo, không đóng pool được truyền từ ngoài.
- `transaction(pool: ConnectionPool) -> ContextManager[Connection[dict]]`: connection dict-row, transaction commit/rollback.
- `utc_now() -> datetime`: timezone-aware UTC; có thể override trong kiểm thử.
- `ApiError(status_code: int, code: str, message: str)`: serializer `{code,message}`, 422 không đưa lại input password trong lỗi validation.
- `Account`: dataclass nội bộ `id: UUID, username: str, full_name: str, role: Literal['USER','ADMIN'], is_active: bool`; không chứa password hash.
- `AuthContext`: dataclass `account: Account, session_id: UUID, csrf_token: str`; không trả session_id/raw token qua API.
- `get_auth_context(request: Request) -> AuthContext`, `require_admin(request: Request) -> AuthContext`, `require_user(request: Request) -> AuthContext`: dependency đồng bộ.

Lệnh test dùng `.\.venv\Scripts\python.exe -m pytest ...`. Marker `integration` là PostGIS thật; gọi `-m integration` thiếu cấu hình phải lỗi rõ ràng, không skip rồi báo đạt. Unit/API test với fake dependency chạy không cần kết nối mạng. Không reset schema/database sử dụng thực tế.

## Task 1: Ứng dụng cùng nguồn và kiểm tra sức khỏe

**Files:** tạo `requirements.txt`, `requirements-dev.txt`, `requirements.lock.txt`, `requirements-dev.lock.txt`, `pyproject.toml`, `.gitignore`, `.env.example`, `app/__init__.py`, `app/main.py`, `app/config.py`, `app/errors.py`, `app/clock.py`, `app/db/__init__.py`, `app/db/pool.py`, `app/static/login.html`, `tests/conftest.py`, `tests/test_health.py`, `tests/test_config.py`.

**Interfaces:** tạo Settings/create_app/transaction/utc_now/ApiError như trên; `/api/health` trả `{status:'ok',database:'ok'}` với 200 hoặc `{code:'DATABASE_UNAVAILABLE',message:'Cơ sở dữ liệu chưa sẵn sàng.'}` với 503; `/login` phục vụ HTML. `app = create_app()` không kết nối database cho đến lifespan. API routes đăng ký trước static mount.

- [ ] Tạo venv bằng `python -m venv .venv`, pin dependency và cấu hình pytest/pythonpath tại `pyproject.toml`; cài dependencies trong venv để chạy test. Cài runtime trước bằng `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, lưu `pip freeze` vào `requirements.lock.txt`; sau đó cài dev và lưu `requirements-dev.lock.txt`. Chỉ sinh lockfiles sau cài đặt thành công; `python -m pip check` phải không báo bất tương thích.
- [ ] Viết test sau và test database exception trả 503 không chứa DSN; config origin HTTPS buộc Secure cookie. Fake pool đã được tạo trong fixture, không dùng database thật.

```python
def test_health_ready(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'database': 'ok'}
```

- [ ] Chạy `.\.venv\Scripts\python.exe -m pytest tests/test_health.py tests/test_config.py -q`; xác nhận FAIL vì chưa có app/route trước triển khai.
- [ ] Triển khai interface và health query `SELECT 1`, static trang login tối thiểu; mapping lỗi không lộ secrets, không ghi request body auth vào log. Cấu hình sample không chứa password thật.
- [ ] Chạy lại test trên, `pip check`, và test `/login` trả HTML còn `/api/unknown` trả lỗi API, không bị static trả trang login.
- [ ] Lưu bằng chứng kết quả; commit riêng Task 1 nếu môi trường Git cho phép, không đưa bí mật/venv vào commit.

## Task 2: Migration schema và nền tảng dữ liệu

**Files:** tạo `migrations/001_identity.sql`, `migrations/002_attendance.sql`, `app/db/migrations.py`, `scripts/__init__.py`, `scripts/migrate.py`, `tests/integration/conftest.py`, `tests/integration/test_migrations.py`, `tests/integration/test_constraints.py`.

**Interfaces:** `apply_migrations(conn: Connection[dict], directory: Path) -> list[str]`, ghi phiên bản/checksum trong `geoattend.schema_migrations`; lệnh `python -m scripts.migrate` dùng migration DSN, dừng nếu thiếu. Dùng transaction và database advisory lock cho migration, checksum file đã chạy thay đổi phải báo lỗi.

- [ ] Viết tests migration trên database test mới: chạy tạo đủ 9 bảng theo spec mục 4; chạy lại trả `[]`, dữ liệu fixture vẫn còn; sửa checksum đã ghi bị từ chối; migration lỗi không ghi phiên bản thành công. Schema test riêng được tạo bằng admin test DSN, runtime test dùng quyền hạn chế; fixture dừng nếu test DSN thiếu hoặc trùng DSN app/migration, chỉ dọn đúng schema do fixture tạo.
- [ ] Chạy `.\.venv\Scripts\python.exe -m pytest tests/integration/test_migrations.py tests/integration/test_constraints.py -q -m integration`; FAIL trước migration khi đã có database test, không coi lỗi cấu hình là RED của test nghiệp vụ.
- [ ] Tạo 001: schema riêng, profiles/auth_sessions/auth_attempts; UUID/time/check role; unique username chuẩn hóa, partial unique `(role) WHERE role='ADMIN'`. FK không cascade xóa lịch sử. Cho runtime SELECT/INSERT/UPDATE cần thiết và DELETE với auth/session cleanup, không DDL.
- [ ] Tạo 002: office/attendance_days/work_sessions/attendance_events/office_locations/attendance_requests với trường, FK, indexes trong spec. Bật PostGIS bằng migration role; extension schema lấy từ cấu hình kết nối kiểm chứng (public hoặc extensions), SQL gọi đúng schema. Cố định một office bằng singleton unique expression; Polygon có thể null trước cấu hình, có geom thì phải valid/non-empty/area>0. Point EPSG:4326. Session một phiên mở/ngày, end>=start; accuracy>=0 khi có; location một/session; không có end_location/end_accuracy. Phiên request IDs và kết quả sự kiện theo spec, không lưu payload GPS.
- [ ] Thêm test `test_database_rejects_second_admin`: insert Admin thứ hai gây unique violation; `test_duplicate_normalized_username_rejected`: `nhan` và biến thể không được ghi thành hai tài khoản. Test tất cả bảng tạo được, FKs phiên/sự kiện hoạt động và runtime không ALTER schema.
- [ ] Chạy lại migration/constraint tests và `python -m scripts.migrate` trên database local/test được chỉ định; schema được tạo và lần hai không tạo lại. Commit riêng migration/tests sau khi đạt.

## Task 3: Mật khẩu và khởi tạo/khôi phục Admin

**Files:** tạo `app/auth/__init__.py`, `app/auth/models.py`, `app/auth/passwords.py`, `app/accounts/__init__.py`, `app/accounts/repository.py`, `app/accounts/bootstrap.py`, `scripts/bootstrap_admin.py`, `scripts/recover_admin.py`, `tests/test_passwords.py`, `tests/integration/test_bootstrap.py`.

**Interfaces:** `normalize_username(value: str) -> str`; `validate_password(value: str) -> str`; `hash_password(value: str) -> str`; `verify_password(encoded: str, value: str) -> bool`; `create_initial_admin(conn, username: str, full_name: str, password: str) -> Account`; `recover_admin(conn, new_password: str) -> None`. Repository nội bộ: `get_account_by_username(conn, username: str, for_update: bool = False) -> dict | None`, `get_account_by_id(conn, account_id: UUID, for_update: bool = False) -> dict | None`; dict nội bộ có hash, không dùng làm API response.

- [ ] Viết test normalization/giới hạn bằng parametrization; mật khẩu có space được giữ nguyên; hash khác mật khẩu gốc, `$argon2id$`, verify đúng/sai không ném exception ra API. Ví dụ:

```python
def test_password_preserves_spaces():
    encoded = hash_password(' Pass1234 ')
    assert verify_password(encoded, ' Pass1234 ')
    assert not verify_password(encoded, 'Pass1234')
```

- [ ] Chạy `.\.venv\Scripts\python.exe -m pytest tests/test_passwords.py -q`; FAIL chưa có hàm; sau đó triển khai Argon2id với argon2-cffi, không log password/hash.
- [ ] Viết integration tests bootstrap chạy lại giữ mật khẩu/hồ sơ Admin cũ, bootstrap đồng thời chỉ một thành công; recover chỉ đổi Admin và thu hồi auth_sessions, không tạo User/Admin mới. Chạy test để thấy FAIL trước bổ sung bootstrap.
- [ ] Triển khai lệnh `python -m scripts.bootstrap_admin` và `python -m scripts.recover_admin`: lấy username/full_name qua prompt, password qua `getpass` và xác nhận lại; dùng quyền quản trị/migration DSN, không lấy password qua command-line argument. Bootstrap lock và unique index; nếu Admin tồn tại báo dừng, không update. Recover yêu cầu xác nhận tài khoản Admin đang khôi phục, không in bí mật.
- [ ] Chạy password/bootstrap tests; CLI test stdin/getpass mock bảo đảm chạy lại và input password sai không đổi dữ liệu. Commit Task 3 sau đạt.

## Task 4: Phiên đăng nhập, CSRF, giới hạn thử sai và quyền

**Files:** tạo `app/auth/repository.py`, `app/auth/service.py`, `app/auth/dependencies.py`, `app/auth/schemas.py`, `app/auth/routes.py`, `tests/test_auth_api.py`, `tests/integration/test_auth_sessions.py`, `tests/integration/test_auth_races.py`; sửa `app/main.py`, `tests/conftest.py`.

**Interfaces:** `login(conn, username: str, password: str, now: datetime) -> LoginResult`; dataclass `LoginResult(account: Account, raw_token: str, csrf_token: str, expires_at: datetime)` nội bộ. `resolve_session(conn, raw_token: str, now: datetime) -> AuthContext`; `revoke_session(conn, session_id: UUID, now: datetime) -> None`; `validate_origin(request: Request, origin: str) -> None`; `validate_csrf(request: Request, context: AuthContext) -> None`. `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout` theo spec.

- [ ] Viết tests login đúng trả Account/CSRF và cookie; response không có raw token ngoài cookie, không có hash; lỗi unknown/wrong/inactive trả cùng 401 code/message. Hạn phiên đúng 12h, cookie HttpOnly/SameSite/Path và Secure theo origin. `/me` không cookie/hết hạn/revoked trả 401; Admin/User nhận role đúng.
- [ ] Chạy `.\.venv\Scripts\python.exe -m pytest tests/test_auth_api.py -q`; FAIL thiếu routes; triển khai route/schema/dependency và serializer không phản chiếu password khi 422.
- [ ] Viết integration test 5 lần sai ghi auth_attempts, lần 6 trả 429; đúng cửa sổ 5 phút giảm số lần, đăng nhập lại được; không đổi trạng thái is_active. Nhiều app instances dùng cùng database phải dùng cùng giới hạn. Sai login vẫn commit auth_attempts dù route trả 401; giới hạn dùng advisory lock theo username chuẩn hóa để các yêu cầu đồng thời không vượt ngưỡng.
- [ ] Triển khai token `secrets.token_urlsafe(32)`, database chỉ lưu SHA-256 token và csrf ngẫu nhiên; lookup kiểm tra account active, expiry, revoked. Dùng constant-time CSRF compare, Origin đúng cấu hình với mutation. Login chỉ JSON, Origin khác bị 403. Không bật CORS rộng; mọi response auth `Cache-Control: no-store`.
- [ ] Viết test CSRF thiếu/sai/thuộc phiên khác 403, logout cùng Origin/CSRF thành công làm phiên cũ không truy cập lại. `require_admin` từ User và `require_user` từ Admin đều 403. Resolve/expire/revoke dùng clock injection.
- [ ] Viết race test dùng hai connection và đồng bộ barrier: login lấy khóa profile trước verify/tạo session; change/reset (Task 5) lấy cùng khóa, update hash/revoke trong transaction. Bất kỳ login bằng mật khẩu cũ đã verify trước reset phải có session bị revoke sau reset commit; không giữ transaction đọc trước rồi insert sau reset. Test đầy đủ sau Task 5, Task 4 định nghĩa giao diện khóa này.
- [ ] Chạy auth API/session tests và kiểm tra log caplog không có password/DSN/token. Thêm `prune_auth_data(conn, now: datetime) -> tuple[int, int]` trong `app/auth/repository.py`: xóa lần thử sai đủ 5 phút, phiên revoked/hết hạn; test không xóa phiên còn hiệu lực. Gọi dọn theo nhu cầu khi xác thực, maintenance tổng thể từ Phase 2. Commit Task 4 sau đạt các test đã triển khai; race suite chạy lại ở Task 5.

## Task 5: Admin cấp/reset tài khoản và đổi mật khẩu cá nhân

**Files:** tạo `app/accounts/service.py`, `app/accounts/schemas.py`, `app/accounts/routes.py`, `tests/test_accounts_api.py`, `tests/integration/test_accounts.py`; sửa `app/accounts/repository.py`, `app/auth/routes.py`, `app/auth/service.py`, `app/main.py`, `tests/integration/test_auth_races.py`.

**Interfaces:** `create_user(conn, username: str, full_name: str, password: str) -> Account`; `list_users(conn) -> list[Account]`; `reset_user_password(conn, account_id: UUID, new_password: str, now: datetime) -> None`; `change_password(conn, account_id: UUID, current_password: str, new_password: str, now: datetime) -> None`. Tự đổi/đặt lại lấy khóa profile, update/revoke cùng transaction như Task 4. API schema `extra='forbid'`, không nhận role/id từ client create.

- [ ] Viết API tests: Admin create trả 201 `{id,username,full_name,role:'USER'}`; GET list trả `{items:[...]}`, chỉ User, không hash; trùng normalized username trả 409; extra role ADMIN trả 422; User 403, anonymous 401. Missing CSRF 403 không tạo bản ghi. Họ tên trim dài 1–200 ký tự, giữ Unicode.
- [ ] Chạy `.\.venv\Scripts\python.exe -m pytest tests/test_accounts_api.py -q`; FAIL route/service chưa có; triển khai `GET/POST /api/admin/users`, `POST /api/admin/users/{id}/reset-password`, `POST /api/auth/change-password`.
- [ ] Test reset User: 204, mọi phiên User bị revoke, Admin vẫn dùng được phiên cũ, old password 401, new password thành công và không buộc đổi. Target Admin bị từ chối; id không tồn tại 404. User không reset tài khoản khác.
- [ ] Test tự đổi: mật khẩu hiện tại sai 401 không đổi hash/revoke; new password sai giới hạn 422; thành công 204, mọi phiên kể cả hiện tại revoked, cookie xóa, mật khẩu cũ 401/new thành công. Identity/role/full_name và lịch sử fixture không đổi; không chặn lần đăng nhập đầu.
- [ ] Chạy integration tests create/reset/change/races: nhiều create username tương đương chỉ một thành công; hai reset/change đồng thời không bỏ sót session cũ, không lộ unique violation thô. Ghi sự kiện chấm công fixture trước đổi/reset và xác nhận số dòng/nội dung không đổi.
- [ ] Chạy `.\.venv\Scripts\python.exe -m pytest tests/test_accounts_api.py tests/integration/test_accounts.py tests/integration/test_auth_races.py -q`; đạt trước commit Task 5.

## Task 6: Giao diện tài khoản và hướng dẫn chạy

**Files:** tạo `app/static/user.html`, `app/static/admin-users.html`, `app/static/account.html`, `app/static/css/app.css`, `app/static/js/api.js`, `app/static/js/login.js`, `app/static/js/user.js`, `app/static/js/admin-users.js`, `app/static/js/account.js`, `docs/DEVELOPMENT.md`, `tests/test_pages.py`; sửa `app/static/login.html`, `app/main.py`, `README.md`, `.env.example`.

**Interfaces:** trang `/login`, `/user`, `/admin/users`, `/account`; static `/static/...`. `api.js`: `loadAccount() -> Promise<AccountResponse>`, `apiFetch(path, options) -> Promise<unknown>` gửi cookie cùng nguồn/CSRF cho mutation, ánh xạ code/message; CSRF nằm memory, không localStorage. `AccountResponse` là `{id,username,full_name,role,csrf_token}` như `/me`. Sau login role ADMIN đến `/admin/users`, USER đến `/user`.

- [ ] Viết tests `/login` 200, `/user` chưa login redirect `/login`, `/admin/users` từ User 403, từ Admin 200; `/account` cho cả hai. Kiểm tra trình duyệt `name_is_displayed_as_text` dùng họ tên `<img src=x onerror=alert(1)>` và xác nhận DOM khi kiểm tra trình duyệt hiển thị text, không tạo img hay chạy script. Backend không chèn tên vào HTML bằng string interpolation.
- [ ] Chạy `.\.venv\Scripts\python.exe -m pytest tests/test_pages.py -q`; FAIL trước thêm pages; triển khai HTML/CSS/JS với form login, create/reset User, change-password và logout. Không dựng Dashboard/attendance giả; trang User Phase 1 chỉ hiển thị thông tin đăng nhập và điều hướng tài khoản, ghi rõ chức năng chấm công triển khai ở phase sau trong tài liệu phát triển.
- [ ] Kiểm tra tay luồng Admin tạo `nhan` → User login ngay → User đổi mật khẩu/logout → Admin reset → User login mới; hai phiên khác nhau đều bị thu hồi sau đổi/reset. Form lỗi giữ tên/họ tên, xóa password sau success, khóa nút trong pending và dùng textContent cho tên/message. Lỗi mạng không báo success hoặc mất dữ liệu đã nhập không nhạy cảm.
- [ ] Kiểm tra chiều rộng 360px và desktop: form không tràn ngang, password input autocomplete phù hợp; người dùng bàn phím thao tác được, label/focus/error rõ. Không gọi geolocation trong Phase 1.
- [ ] Viết DEVELOPMENT với lệnh venv/cài lockfiles, export env PowerShell, migrate, bootstrap/recover, Uvicorn, unit và integration tests. Nêu database local/test riêng, roles runtime/migration và schema không exposed. Không in DSN/password mẫu thật; hướng dẫn localhost HTTP và HTTPS Secure cookie.
- [ ] Chạy `.\.venv\Scripts\python.exe -m pytest -q` với test database được cấu hình, `.\.venv\Scripts\python.exe -m pip check`, `git diff --check`; đọc output toàn bộ. Nếu không có integration DB, báo số unit tests đã chạy và phần chưa kiểm chứng, không đánh dấu Phase 1 hoàn thành.
- [ ] Commit thay đổi Task 6 sau checks đạt; cập nhật roadmap với kết quả thực tế, không đánh dấu chấm công/lịch sử/bản đồ hoàn thành.

## Đầu ra và bàn giao Phase 1

Ứng dụng chạy local trên một địa chỉ; migration tạo schema trên môi trường mới; một Admin cấp/reset tài khoản User; User login và đổi mật khẩu tùy chọn. API kiểm tra quyền/CSRF và database giữ hash/phiên đúng thiết kế. Có hướng dẫn dựng lại, kết quả unit/integration và kiểm tra giao diện.

Phase 2 bắt đầu sau khi nghiệm thu nền tảng/tài khoản; không có task hiện tại triển khai Office/Remote, trạng thái chấm công, lịch sử nghiệp vụ hoặc bản đồ.

**Cách thực hiện đề xuất:** trực tiếp trong phiên hiện tại, lần lượt Task 1–6 vì các task phụ thuộc chặt vào migration/interface xác thực. Có thể chọn nhiều agent nếu người dùng yêu cầu. Bản kế hoạch cần được duyệt trước triển khai theo writing-plans; không coi phê duyệt thiết kế Phase 0 là đã duyệt kế hoạch mới này.
