# Giao diện GeoAttend trên GitHub Pages

## Phạm vi

Giao diện được build từ `app/static/`, xuất bản dưới `/geoattend/` bằng workflow `Publish GeoAttend frontend`. Địa chỉ dự kiến: `https://nguyenthanhnhan020705.github.io/geoattend/`. Chỉ coi link đang hoạt động sau khi workflow deploy thành công và kiểm tra HTTP thực tế. Trạng thái triển khai được báo trong lần bàn giao, không suy ra từ địa chỉ dự kiến.

Hiện chưa có backend HTTPS công khai được cấu hình. Khi biến `GEOATTEND_API_ORIGIN` chưa có giá trị, Pages hiển thị **“Dịch vụ chưa được kết nối. Vui lòng liên hệ Admin.”**, khóa nhập/gửi tài khoản và không gọi API đăng nhập. Có giao diện public chưa có nghĩa mọi người đã đăng nhập/chấm công được.

## Bật và cập nhật Pages

1. Trong repository, vào **Settings → Pages → Source → GitHub Actions** (có thể thiết lập bằng GitHub API với quyền quản trị).
2. Push bản đã kiểm thử lên `main`, hoặc chạy workflow thủ công trong **Actions**.
3. Build dùng Python 3.13 và thư viện chuẩn, không đọc `.env` và không cần cài dependency backend. Workflow kiểm tra artifact trước khi upload; chỉ `_site` được xuất bản.
4. Deploy thành công giữ nguyên địa chỉ Pages. Mỗi lần push `main` sẽ chạy lại. Biến repository thay đổi không tự sinh commit: cần chạy workflow thủ công hoặc push bản mới.

Artifact chỉ chứa trang HTML, CSS/JS, ảnh, font và giấy phép thư viện được allowlist. Không xuất Python backend, test, migration, database, backup, `.env` hoặc tài liệu nội bộ. Các trang Admin trên Pages là HTML công khai không có dữ liệu; API mới quyết định quyền đọc/ghi, frontend chỉ điều hướng theo tài khoản.

## Kết nối backend khi có nơi chạy

Không bắt buộc một nhà cung cấp hosting cụ thể. Cần máy chủ chạy FastAPI và tiến trình maintenance độc lập, kết nối PostgreSQL/PostGIS, migration hiện hành và quyền runtime theo [runbook](PHASE_6_OPERATIONS.md).

Backend cấu hình ngoài Git:

```text
GEOATTEND_ORIGIN=https://<địa-chỉ-backend-thực-tế>
GEOATTEND_SECURE_COOKIES=true
GEOATTEND_FRONTEND_ORIGIN=https://nguyenthanhnhan020705.github.io
GEOATTEND_DATABASE_URL=<kết-nối-runtime-riêng>
```

`GEOATTEND_ORIGIN` là origin backend, không phải URL Pages. `GEOATTEND_FRONTEND_ORIGIN` không chứa `/geoattend/` hoặc dấu `/` cuối. Không gửi DSN/mật khẩu vào chat hay đưa vào GitHub Pages. `.env.example` để frontend origin rỗng; chỉ bật bearer cho backend được chọn.

Sau khi backend đã sẵn sàng, vào **Settings → Secrets and variables → Actions → Variables**, đặt repository variable **`GEOATTEND_API_ORIGIN`** bằng HTTPS origin backend, không có path, query hoặc thông tin đăng nhập. Biến này là địa chỉ public, không phải secret hay chuỗi kết nối database. Chạy lại Pages workflow. Chưa có API thì để rỗng, không nhập địa chỉ phỏng đoán.

Tạo/cấp tài khoản qua Admin; không có đăng ký công khai. Sau khi kết nối, kiểm tra đăng nhập/đăng xuất, User/Admin, GPS thật qua HTTPS, Remote, geofence, PDF và Excel trước khi gửi dùng chính thức. Maintenance phải chạy để kết thúc ngày/dọn dữ liệu hết hạn; không dùng GitHub Actions làm tiến trình web hoặc maintenance thường trực.

## Phiên và tải file

- Bản cùng origin do FastAPI phục vụ vẫn dùng cookie HttpOnly, SameSite=Lax và CSRF như trước.
- Pages đăng nhập qua `/api/auth/token`, opt-in bằng frontend origin. Phiên ngẫu nhiên có hạn 12 giờ và lưu hash trong database, dùng chung cơ chế thu hồi/đổi mật khẩu hiện có.
- Trình duyệt lưu token trong sessionStorage theo API/base path, gửi bearer trong header và không gửi cookie API. Token không nằm trong URL, localStorage hoặc artifact. Đóng tab kết thúc việc lưu phiên phía trình duyệt; Admin vẫn có thể thu hồi phiên phía server.
- JavaScript cùng origin có thể đọc sessionStorage nếu xảy ra XSS. Giữ CSP, script nội bộ và render dữ liệu dưới dạng text; không thêm script tùy tiện vào frontend.
- CORS chỉ cho origin Pages đã cấu hình. Thao tác ghi vẫn kiểm tra CSRF/Origin; bearer sai không được fallback sang cookie hợp lệ.
- PDF/Excel được fetch với xác thực rồi tạo Blob để xem/tải; popup bị chặn sẽ tải PDF về máy. Không đưa token vào link PDF. Bản cùng origin tiếp tục hỗ trợ link PDF trực tiếp như trước.
- Lỗi mạng không được coi là thao tác thất bại chắc chắn; giữ UUID/revision để gửi lại an toàn. GPS chỉ ở RAM khi retry Office, không được đưa vào storage hoặc log.
- Hết phiên hoặc API trả 401 chỉ xóa token, giữ thao tác chưa xác nhận để đúng tài khoản đăng nhập lại gửi cùng UUID. Đăng xuất/đổi mật khẩu chủ động xóa cả phiên lẫn pending của ứng dụng. Tải PDF có hạn 30 giây bao gồm đọc body; timeout đóng cửa sổ chờ và cho thử lại.

## Kiểm tra local

Giao diện chưa nối API có thể preview không cần database:

```powershell
python -m unittest tests.test_pages_artifact -v
python -m scripts.build_pages --output .local-tests/pages-preview/geoattend --base-path /geoattend/ --version local
python -m http.server 9000 --bind 127.0.0.1 --directory .local-tests/pages-preview
```

Mở `http://127.0.0.1:9000/geoattend/`. Dùng thư mục output mới/rỗng; builder không xóa dữ liệu cũ. API HTTP chỉ được bật qua tham số Python `allow_loopback=True` trong fixture test/local, không có trong CLI deploy.

Các test mới: `test_pages_build.py`, `test_pages_artifact.py`, `integration/test_pages_auth.py`, `integration/test_pages_frontend.py`, `integration/test_pages_files.py`. Fixture dùng static `localhost` và API `127.0.0.1` khác port, database test UUID riêng và Edge headless, không dùng database ứng dụng. Browser test mô phỏng GPS và kiểm tra lỗi mạng; không thay thế kiểm tra thiết bị/GPS thật hoặc API HTTPS production.

## Bằng chứng triển khai

Ngày 21/10/2026, full suite sau sửa review đạt **380 passed, 1 warning, 0 skipped**, **595,64 giây**, exit 0. Gồm API, PostgreSQL/PostGIS, Edge headless ở các kích thước màn hình, Caddy thật, đo tải và backup/restore cô lập. Log local: `.local-tests/pages-full-reviewed.log`. `pip check` không có dependency hỏng; `git diff --check` đạt. Warning duy nhất là Starlette deprecation về httpx TestClient có từ trước.

Lượt full trước sửa review đạt 377 test; các nhóm kiểm tra trong quá trình triển khai có trùng lặp nên không cộng thành số test độc lập. Không chạy migration hoặc tạo dữ liệu thử trên database ứng dụng.

Review độc lập toàn nhánh không tìm thấy Critical; hai Important về mất UUID khi hết phiên và PDF không giới hạn thời gian đã được tái hiện RED rồi sửa, 3 test hồi quy mới GREEN. Tạm hoãn cải thiện nhỏ về thông báo riêng khi JavaScript không tải được (CSP vẫn chặn native form submit); kiểm thử preview PDF thành công chưa có ca riêng, hiện đã kiểm tra tải đúng byte, fallback popup bị chặn và timeout phục hồi. Bộ kiểm tra artifact bằng `python -S -m unittest tests.test_pages_artifact -v` đạt khi không nạp site-packages.
