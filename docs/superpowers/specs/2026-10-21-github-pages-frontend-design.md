# GeoAttend: giao diện GitHub Pages và API độc lập

Trạng thái: người dùng đã duyệt thiết kế; chưa triển khai.

## Mục tiêu đã xác nhận

Người dùng muốn giao diện GeoAttend hiện tại được xuất bản trên GitHub Pages, dùng địa chỉ `github.io`, không mua tên miền. Hiện chưa có backend công khai. Những lần cập nhật `main` phải có thể tự xuất bản lại giao diện tại cùng địa chỉ. Địa chỉ dự kiến là `https://nguyenthanhnhan020705.github.io/geoattend/`; chỉ xác nhận hoạt động sau khi Pages deploy thành công.

Giữ nghiệp vụ, dữ liệu PostgreSQL/PostGIS và tài khoản hiện có. Không chuyển nghiệp vụ sang Supabase Auth/Edge Functions trong phạm vi này. Không mặc định tạo dịch vụ trả phí hoặc chọn nhà cung cấp backend thay người dùng.

## Các phương án và lựa chọn đề xuất

1. **GitHub Pages + FastAPI độc lập, phiên bearer cho giao diện khác origin:** tái sử dụng nghiệp vụ/backend; cần thêm lớp gọi API và xác thực không phụ thuộc cookie bên thứ ba. Đây là phương án đề xuất cho địa chỉ `github.io`.
2. GitHub Pages + cookie khác site: phải thay SameSite và CORS; trình duyệt vẫn có thể chặn cookie bên thứ ba. Không chọn làm nền tảng đăng nhập cho phương án này.
3. GitHub Pages + viết lại backend bằng dịch vụ Supabase: thay đổi xác thực, quyền, transaction và maintenance trên diện rộng. Nằm ngoài phạm vi tách giao diện.

## Kiến trúc

```text
Trình duyệt → GitHub Pages: HTML/CSS/JavaScript
           → HTTPS FastAPI API độc lập → PostgreSQL/PostGIS
Maintenance độc lập                   → PostgreSQL/PostGIS
GitHub Actions: main → build artifact tĩnh → GitHub Pages
```

Backend chưa có địa chỉ triển khai. Mã giao diện hỗ trợ cấu hình API công khai khi build; không giả lập một backend đang chạy. Trước khi cấu hình API, trang đăng nhập hiển thị thông báo dịch vụ chưa được kết nối và khóa gửi thông tin đăng nhập. Không coi việc Pages mở được là ứng dụng đã sẵn sàng chấm công.

## Xuất bản và đường dẫn

- Thêm công cụ build bằng Python, dùng lại nguồn trong `app/static/`; không duy trì hai bản giao diện viết tay.
- Tạo artifact riêng chỉ gồm HTML/CSS/JS, ảnh và thư viện bản đồ cần thiết. Không xuất `.env`, database, migration, Python source, test, tài liệu nội bộ hoặc backup.
- Tạo các trang dạng thư mục có `index.html` tương ứng với login, user, account, admin/users, admin/dashboard, admin/office và các trang báo cáo tuần. Tạo trang gốc dẫn tới login.
- Chuẩn hóa điều hướng, CSS, module JS, ảnh và thư viện theo base path `/geoattend/`. Tải lại trực tiếp trang con phải hoạt động, không dựa vào rewrite của FastAPI.
- Cấu hình công khai chỉ chứa base path, API origin HTTPS và phiên bản build. Không đưa DSN, mật khẩu hoặc token quản trị vào artifact.
- Workflow chạy khi push `main` và khi gọi thủ công; build/kiểm tra trước, deploy artifact sau. Giới hạn quyền workflow ở checkout, Pages và OIDC cần thiết.

## Kết nối API và phiên đăng nhập

- Giữ chế độ cookie HttpOnly hiện hành cho giao diện cùng origin trên FastAPI; không thay response login cũ thành response chứa token.
- Thêm endpoint đăng nhập bearer riêng, bật qua cấu hình dành cho frontend độc lập. Vẫn dùng kiểm tra mật khẩu, giới hạn thử sai và bảng phiên hiện có; không thay hash mật khẩu hoặc tạo hệ tài khoản thứ hai.
- Token ngẫu nhiên cùng thời hạn phiên hiện hành; database chỉ lưu hash. Response đăng nhập bearer chứa access token, thời điểm hết hạn và thông tin tài khoản. Không ghi token/mật khẩu vào URL hoặc log.
- Giao diện Pages gửi `Authorization: Bearer ...` và không dựa vào cookie backend. Token lưu trong `sessionStorage` theo API origin/base path để tải lại trang trong cùng tab; không lưu mật khẩu hoặc dùng `localStorage`. Đóng tab kết thúc việc lưu token phía trình duyệt; logout phải thu hồi phiên trên server rồi xóa token và dữ liệu pending trong tab.
- Token trong sessionStorage có thể bị JavaScript cùng origin đọc khi có XSS. Giữ render dữ liệu người dùng bằng text, không bổ sung script bên thứ ba; artifact Pages có CSP phù hợp qua meta và referrer policy. Cookie HttpOnly vẫn là chế độ cho bản cùng origin.
- Backend chỉ cho CORS với origin chính xác `https://nguyenthanhnhan020705.github.io`, không dùng wildcard. Cho phép đúng method/header cần thiết, gồm Authorization, X-CSRF-Token và X-Report-Filename. API origin và frontend origin là hai cấu hình tách biệt; path `/geoattend/` không phải thành phần origin.
- Các thao tác thay đổi dữ liệu vẫn kiểm tra CSRF và Origin. Chỉ cho phép cross-site request từ frontend origin được cấu hình ở chế độ bearer; không nới kiểm tra cookie hiện hành. Request có header bearer sai không được rơi về cookie để đăng nhập nhầm tài khoản.
- Backend luôn kiểm tra quyền User/Admin, hết hạn/thu hồi phiên và khóa tài khoản. Trang HTML công khai trên Pages không chứa dữ liệu nhân viên; frontend xác minh vai trò trước khi hiển thị nội dung, còn API là nơi quyết định quyền truy cập.

## Báo cáo PDF, Excel và chức năng hiện có

- Gom URL và transport API để các request JSON, upload PDF, download Excel đều dùng cùng API origin và token.
- Link PDF hiện mở endpoint trực tiếp phải đổi sang fetch có xác thực, lấy Blob rồi mở hoặc tải. Không chuyển token vào query string. Thu hồi object URL khi không còn dùng; xử lý trình duyệt chặn popup và giữ thao tác tải dự phòng.
- Giữ nguyên UUID retry, revision, giới hạn PDF, timeout và quyền đọc báo cáo. Mất mạng không được xóa token hoặc đổi UUID như thể server đã từ chối.
- Bản đồ lấy cấu hình và dữ liệu qua API; GPS chỉ thu khi thao tác Office. Không đưa GPS vào storage, URL, log hay artifact Pages.

## Kiểm chứng

1. Build artifact: không có bí mật; mọi trang con, asset và module hoạt động dưới `/geoattend/`; chưa cấu hình API thì không gửi mật khẩu.
2. API: cookie cũ tiếp tục đạt; bearer đăng nhập/đăng xuất/hết hạn/thu hồi phiên; sai Origin/CORS/CSRF bị từ chối; không chấp nhận bearer lỗi bằng cookie hợp lệ.
3. Trình duyệt: chạy static server và API trên hai origin khác nhau, không dùng cookie cho Pages; đăng nhập, reload, phân quyền, Office/Remote, báo cáo PDF và Excel trên mobile/desktop.
4. Chạy regression phù hợp sau thay đổi auth; giữ kiểm tra transaction/GIS, migration và maintenance hiện có. Không dùng database ứng dụng cho test.
5. Sau xuất bản thật: kiểm tra URL Pages, tải trang con và phiên bản build. Chỉ xác nhận người khác dùng được khi API HTTPS, database, migration và maintenance đã sẵn sàng và kiểm thử đầu cuối đạt.

## Các bước cần điều kiện bên ngoài

Repository cần quyền bật Pages và chạy Actions. Backend vẫn cần tài khoản/máy chủ được người dùng chọn để chạy FastAPI và maintenance, cùng cấu hình database riêng. Chuẩn bị mã và workflow không đồng nghĩa đã tạo backend hoặc chấp nhận chi phí. Không chạy FastAPI lâu dài trong GitHub Actions để thay hosting.
