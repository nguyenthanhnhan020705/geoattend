# GitHub Pages Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Xuất bản giao diện GeoAttend tại GitHub Pages, tự cập nhật từ main và hỗ trợ API FastAPI khác origin khi backend được cấu hình.

**Architecture:** Build một artifact tĩnh từ app/static với base path /geoattend/. Giữ cookie cùng origin và thêm bearer opt-in cho Pages, dùng chung bảng phiên và nghiệp vụ. GitHub Actions xuất bản artifact; chưa có API thì khóa đăng nhập với thông báo rõ ràng.

**Tech Stack:** Python 3.13, FastAPI/Starlette, JavaScript ES modules, PostgreSQL/PostGIS, pytest, Playwright, GitHub Actions/Pages.

**Spec:** [Thiết kế đã duyệt](../specs/2026-10-21-github-pages-frontend-design.md).

## Global Constraints

- Frontend dự kiến: https://nguyenthanhnhan020705.github.io/geoattend/; origin CORS chính xác https://nguyenthanhnhan020705.github.io.
- Không tạo nhà cung cấp backend, dịch vụ trả phí, migration trên database ứng dụng hoặc thay hệ tài khoản.
- Không dùng cookie bên thứ ba làm điều kiện đăng nhập Pages; không đưa token vào URL, log, localStorage hoặc artifact.
- Dùng sessionStorage theo API origin/base path; thời hạn phiên hiện hành 43200 giây, database chỉ lưu hash token.
- Không thay nghiệp vụ/revision/UUID retry/GPS retention, không sửa migration đã áp dụng hoặc thêm dependency sản phẩm khi thư viện hiện có đáp ứng.
- Mã nguồn cùng origin vẫn phục vụ được bằng FastAPI. HTML Pages công khai không chứa dữ liệu nhân viên; quyền được kiểm tra tại API.
- Chỉ xác nhận link hoạt động sau deploy thành công; chỉ xác nhận sử dụng đầu cuối sau khi có API HTTPS, database và maintenance.

## Review Focus

- API origin/base path sai hoặc chứa thông tin đăng nhập: từ chối build, không gửi mật khẩu sang địa chỉ ngoài cấu hình (Task 1, 3).
- Bearer lỗi đi kèm cookie hợp lệ: trả 401, không đổi ngầm tài khoản (Task 2).
- sessionStorage không truy cập được, token hết hạn hoặc mạng chập chờn: thông báo rõ, không xóa UUID chưa xác nhận (Task 3, 5).
- PDF bị chặn popup hoặc lỗi quyền: không mở tab trắng vĩnh viễn, vẫn có thao tác tải có xác thực (Task 4).
- Reload trang con, import module và CSS image dưới /geoattend/: không 404 hoặc trỏ về gốc domain (Task 1, 5).

## File Structure

- `scripts/build_pages.py`: build artifact, rewrite đường dẫn HTML theo bảng route và sinh config/CSP công khai.
- `app/static/js/runtime-config.js`: cấu hình mặc định cùng origin; bản sinh trong artifact chọn Pages.
- `app/static/js/transport.js`: URL, bearer storage và fetch; không phụ thuộc DOM.
- `app/static/js/page-session.js`: guard vai trò trước khi kích hoạt trang, redirect theo base path.
- `app/static/js/api.js`: wrapper JSON/CSRF/error, dùng transport; giữ các export hiện hành.
- `app/config.py`, `app/auth/routes.py`, `app/auth/dependencies.py`, `app/main.py`: cấu hình frontend origin, bearer và CORS opt-in.
- `app/static/js/reports-api.js`, `admin-export.js`, `login.js`, `account.js`, `user.js`, `admin-users.js`, `admin-office.js`, `admin-dashboard.js`, `user-weekly-reports.js`, `admin-weekly-reports.js`, `report-home.js`: đưa request/điều hướng/khởi tạo vào transport và guard.
- `.github/workflows/pages.yml`, `docs/GITHUB_PAGES.md`: xuất bản và hướng dẫn nối API sau này.
- Test mới: `tests/test_pages_build.py`, `tests/integration/test_pages_auth.py`, `tests/integration/test_pages_frontend.py`, `tests/integration/test_pages_files.py`; thêm fixture static/API riêng tại `tests/pages_fixtures.py`.

## Task 1: Build artifact và cấu hình public

**Interfaces:** `build_pages(output: Path, *, base_path: str, api_origin: str, version: str, allow_loopback: bool=False) -> None`; module sinh export `runtimeConfig = {mode, basePath, apiOrigin, version}`. mode mặc định nguồn là `same-origin`; artifact là `pages`. Chỉ test local bật allow_loopback, workflow không bật.

- [x] Viết `test_pages_build.py`: build `/geoattend/` và `/`, assert tồn tại root/login/user/account/admin/users/admin/dashboard/admin/office/user/weekly-reports/admin/weekly-reports `index.html`; asset nội bộ resolve tồn tại; output không có `.env`, Python, SQL, docs hoặc dữ liệu local. Kiểm tra CSS URL và module tương đối.
- [x] Thêm assertions: API HTTPS có path/userinfo/query/fragment hoặc scheme lạ bị ValueError; base path chứa `..`, query, dấu quote bị từ chối; API rỗng được phép. Vị trí output không được là repo root, nguồn hoặc thư mục cha nguồn. Không xóa đệ quy output người dùng truyền vào.
- [x] Chạy `python -m pytest tests/test_pages_build.py -q`, xác nhận RED do thiếu builder.
- [x] Implement builder/CLI `python -m scripts.build_pages --output ... --base-path /geoattend/ --api-origin ... --version ...`. Chỉ copy allowlist assets, tạo `.nojekyll`; HTML dùng route có trailing slash trong artifact, nguồn same-origin giữ route hiện hành. CSP meta đặt trước resource, `connect-src` giới hạn API/map, `object-src 'none'`, `base-uri 'none'`, không script inline. Referrer policy no-referrer. Không thêm frame-ancestors vào meta vì không có hiệu lực.
- [x] Chạy lại test đạt rồi commit `feat: build GitHub Pages frontend artifact`.

## Task 2: Backend bearer và CORS opt-in

**Interfaces:** thêm Settings `frontend_origin: str=''`, env `GEOATTEND_FRONTEND_ORIGIN`. Origin rỗng tắt bearer; nonempty validate HTTPS (loopback HTTP cho test/local). `POST /api/auth/token` nhận LoginInput, trả account_response + `access_token`, `token_type='Bearer'`, `expires_at`; không set cookie. `/api/auth/login` giữ hợp đồng cũ.

- [x] Viết test_pages_auth: token endpoint tắt mặc định; bật thì login trả token và DB hash khác token, không Set-Cookie; cookie login không có access_token. Bearer /me, logout với CSRF, đổi/reset mật khẩu, khóa account, hết hạn/thu hồi, sai role và bearer malformed được kiểm tra thật với database riêng.
- [x] Thêm test bearer sai + cookie hợp lệ trả 401; token login chỉ chấp nhận Origin frontend chính xác và JSON; cookie request cross-site vẫn bị từ chối; thiếu/sai CSRF bị từ chối. Không lộ secret trong lỗi hoặc log.
- [x] Test preflight từ frontend được chấp nhận cho Authorization/X-CSRF-Token/X-Report-Filename/Content-Type và GET/POST/PUT/DELETE; origin lạ không có allow-origin; lỗi 401/403/422 có CORS đúng. Không bật wildcard hoặc allow-credentials cho bearer.
- [x] Chạy `python -m pytest tests/integration/test_pages_auth.py -q` xác nhận RED.
- [x] Implement token route qua login() hiện hành; get_auth_context ưu tiên header Authorization nếu xuất hiện, không fallback khi malformed; lưu `request.state.auth_transport`. validate_origin nhận context chế độ bearer để nới đúng origin opt-in; giữ CSRF trên mọi thao tác thay đổi. CORS bọc ngoài stack lỗi FastAPI khi frontend_origin được cấu hình; app factory và timing vẫn hoạt động.
- [x] Chạy test mới cùng `tests/test_config.py tests/test_auth_api.py tests/test_accounts_api.py tests/test_health.py tests/test_phase6_load.py`; đạt rồi commit `feat: support explicit cross-origin bearer sessions`.

## Task 3: Transport và guard giao diện

**Interfaces:** transport exports `apiUrl(path)`, `pageUrl(path)`, `requestApi(path, options={})`, `saveSession(token, expiresAt)`, `clearSession()`; page-session exports `requirePageAccount(role=null) -> Promise<Account>`. requestApi trả Response, không tự parse JSON; api.js tiếp tục export apiFetch/loadAccount/bindForm/bindLogout/message.

- [x] Viết browser tests với static/API ở hai origin: chưa cấu hình API thì login disabled và không có request POST; có API thì token login, reload vẫn đăng nhập, không cookie; route User/Admin đúng. Mở trang bảo vệ trực tiếp khi chưa login không được gọi dữ liệu hoặc kích hoạt form trước guard.
- [x] Test sessionStorage bị chặn thông báo rõ và không gọi login; token hết hạn xóa phiên/điều hướng login; lỗi mạng giữ token và UUID pending. API path chỉ nhận `/api/` nội bộ, không cho URL tuyệt đối/protocol-relative override origin. pageUrl chỉ nhận các route ứng dụng trong base path.
- [x] Chạy test_pages_frontend chọn các test trên, xác nhận RED.
- [x] Implement transport, guard, login, wrapper api và mọi module trang. Pages dùng credentials omit + Authorization; same-origin dùng credentials same-origin. CSRF giữ trong RAM từ /me/login. Khóa dữ liệu/trang trước guard; role khác điều hướng trang phù hợp; account page cho cả hai role. Đổi mật khẩu/logout xóa session và pending ứng dụng, không clear toàn bộ storage của origin. Mỗi lần clear dùng đúng namespace app/API.
- [x] Chạy các test trên và regression browser login/account/attendance; đạt rồi commit `feat: connect Pages UI to independent API`.

## Task 4: PDF và Excel qua transport xác thực

**Interfaces:** `reports-api.js` giữ reportLinks/reportDetails/uploadReport; thêm `fetchReportFile(reportId, {admin=false, download=false}={}) -> Promise<Blob>`. Tạo module `app/static/js/file-downloads.js` với `downloadBlob(blob, filename)` và `openPdf(blob)`, dùng bởi reportLinks và admin-export.

- [x] Viết test_pages_files: nộp/thay PDF bằng UUID/revision qua API khác origin; User chỉ đọc PDF của mình, Admin đọc đúng quyền; Excel tải đúng nội dung và ngày lọc. Tất cả request có Authorization, không token trong URL, không navigation thẳng vào API file.
- [x] Test popup bị chặn vẫn có download, 401 clear session, 403/500 hiển thị lỗi và phục hồi nút; object URL được thu hồi khi đóng/đổi nội dung hoặc hết hạn phù hợp, không thu hồi trước browser bắt đầu đọc file. Không coi response HTML/JSON lỗi là file tải thành công.
- [x] Chạy test mới xác nhận RED rồi implement upload dùng requestApi, link PDF có click fetch, quản lý Blob URL và thông báo lỗi cạnh link. Không đổi UUID khi lỗi mạng; admin-export dùng transport và downloadBlob.
- [x] Chạy test_pages_files và test_admin_export_browser/test_weekly_reports_browser cũ; đạt rồi commit `feat: authenticate cross-origin report and export downloads`.

## Task 5: Kiểm chứng đầu cuối và hồi quy

**Files:** `tests/pages_fixtures.py` chạy ThreadingHTTPServer artifact có directory riêng và Uvicorn API trên loopback ports ngẫu nhiên; mỗi test dùng database do test_dsn tạo. Bật bearer đúng origin static, không lấy .env ứng dụng. Dùng hai hostname localhost/127.0.0.1 khi khả thi để kiểm tra cross-site, và assert không có cookie API/không dùng cookie fallback.

- [x] Bổ sung test full flow ở 360px/1280px: login, refresh deep link, Office với browser GPS mock, Remote có lý do, lịch sử, logout; Admin tạo User/cấu hình geofence/dashboard; PDF/Excel từ Task 4. Assert không JS error, không asset 404, không tràn ngang. Clock test và activation/create date phải cùng tuần cố định.
- [x] Kiểm tra CSS/map worker dưới base path và CSP, API offline/timeout, retry cùng UUID khi response mất. Chạy các test Pages mới đến khi đạt, sửa nguyên nhân thay vì bỏ assertion.
- [x] Chạy full suite bằng interpreter có dependency, PostgreSQL/PostGIS test và Caddy thật; `python -m pip check`; `git diff --check`. Nếu dùng venv worktree cũ, chỉ mượn interpreter, cwd vẫn là worktree triển khai và pytest pythonpath='.'; không dùng schema/database ứng dụng.
- [x] Ghi số passed/failed/skipped, giới hạn test cross-site local so với HTTPS thật và bằng chứng trong docs/GITHUB_PAGES.md; commit `test: verify Pages and API separation end to end`.

## Task 6: Workflow, hướng dẫn và xuất bản

**Interfaces:** repo variable `GEOATTEND_API_ORIGIN` (rỗng cho trạng thái chưa kết nối). Workflow `.github/workflows/pages.yml` chạy main/workflow_dispatch, build bằng Python 3.13, base path `/geoattend/`, version github.sha; không cài dependency backend để build HTML.

- [x] Viết workflow build/test artifact trước deploy. Dùng official checkout/setup-python/configure-pages/upload-pages-artifact/deploy-pages, xác minh phiên bản action hiện hành từ tài liệu chính thức trước viết; pin SHA nếu repo có quy ước. Tách quyền build contents:read và deploy pages:write/id-token:write, environment github-pages, concurrency theo Pages; không deploy pull request.
- [x] Cập nhật README và docs/GITHUB_PAGES.md: API origin public config, frontend origin backend, maintenance/migration vận hành độc lập; cách bật Pages source Actions và backend chưa kết nối. Ghi lệnh build/serve local và luồng cập nhật giữ link cũ. Không gọi link dự kiến là link đang chạy.
- [x] Build artifact local và chạy kiểm tra Task 1; kiểm tra workflow chỉ upload output build. Commit `ci: publish GeoAttend frontend with GitHub Pages`.
- [x] Theo quyền đã có trong phiên, tích hợp nhánh triển khai vào main sau kiểm chứng; push main không force. Kiểm tra quyền GitHub CLI/API sẵn có, không in credentials. Bật Pages source Actions qua công cụ được hỗ trợ nếu đủ quyền; thiếu quyền thì báo đúng thao tác cần người dùng thực hiện.
- [x] Theo dõi workflow và GET URL Pages/root/trang con/assets, xác nhận version build. Nếu chưa có API, chỉ kết luận giao diện public + trạng thái chưa kết nối; không tuyên bố chấm công đã dùng được. Không tự tạo tài khoản hosting hoặc dịch vụ trả phí để vượt điều kiện này.

## Execution Handoff

Người dùng đã duyệt thiết kế và yêu cầu triển khai. Thực hiện Native: triển khai trong phiên này bằng executing-plans, kiểm tra giao diện giữa các task và review cuối. Các task phụ thuộc transport/config/auth, nên làm tuần tự thuận tiện hơn chia nhiều implementer. Nếu muốn reviewer hoặc triển khai bằng subagent, áp dụng đúng lựa chọn của người dùng và skill, không tự mở nhiều agent trước đó.
