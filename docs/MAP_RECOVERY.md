# Khắc phục nền bản đồ và trạng thái chờ

Ngày kiểm tra: 15/10/2026.

## Cách sử dụng

1. Mở `http://127.0.0.1:8000`, đăng nhập Admin và nhấn **Ctrl+F5** để tải giao diện mới.
2. Vào **Văn phòng**. Kéo/thu phóng đến vị trí cần cấu hình. Nếu cần, nhập một cặp vĩ độ/kinh độ rồi chọn **Thêm đỉnh** để đưa bản đồ đến vị trí đó.
3. Chọn **Vẽ vùng**, bấm ít nhất ba đỉnh bao quanh văn phòng. Nút này hỏi xác nhận nếu đang có vùng trong trình chỉnh sửa.
4. Điền tên và địa chỉ, chọn **Xem trước**, sau đó **Lưu vùng văn phòng**. Có thể kéo các đỉnh hoặc sửa tọa độ trước khi lưu.

Nếu nền không tải được, chọn **Tải lại bản đồ**; bản nháp được giữ. Nếu API quá thời gian chờ, giao diện báo lỗi sau 15 giây và mở lại thao tác. Nếu lỗi xảy ra lúc lưu, chọn **Tải lại bản đã lưu** để kiểm tra kết quả trước khi lưu tiếp.

## Nguyên nhân và thay đổi

- DNS của `tile.openstreetmap.org` thất bại trên máy kiểm tra; Edge báo `ERR_NAME_NOT_RESOLVED`, gây nền xám. Kết nối cơ sở dữ liệu vẫn hoạt động.
- Yêu cầu API trước đây không có giới hạn chờ; khi mạng treo, trình chỉnh sửa có thể giữ trạng thái đang tải vô thời hạn. Giới hạn mới bao gồm cả lúc đọc phản hồi; lỗi mạng không được coi là kết quả xác định để giữ UUID thử lại của chấm công.
- Nền mặc định chuyển sang [OpenFreeMap](https://openfreemap.org/quick_start/), giữ Leaflet để chỉnh Polygon. MapLibre GL 5.6.2 và Leaflet binding 0.1.4 được phục vụ local, kèm giấy phép trong `app/static/vendor`. Credits OpenFreeMap/OpenMapTiles/OpenStreetMap hiển thị trên bản đồ.
- CSP chỉ cho nền truy cập origin cấu hình. Có thể tiếp tục dùng raster; xem [DEVELOPMENT](DEVELOPMENT.md).

## Kiểm chứng

- Đã tái hiện kiểm thử thất bại trước bản sửa cho yêu cầu treo và nút vẽ vùng.
- Edge qua mạng thật tải nền OpenFreeMap thành công, ảnh `.local-tests/map-fix/real-map.png` hiển thị đường phố và địa danh TP.HCM.
- Kiểm thử trình duyệt tự động kiểm tra hết chờ, vẽ và lưu Polygon bằng bấm chuột, credits sau tải lại, giữ các đỉnh trong bản nháp.
- Toàn bộ suite: **122 passed**, 1 cảnh báo deprecation có sẵn của Starlette/httpx, 189,76 giây. Kiểm thử tập trung sau bổ sung kiểm tra giữ bản nháp và cấu hình launcher: **8 passed**. Tất cả chạy trên PostgreSQL/PostGIS riêng ở port 55440.
- Sau khởi động lại, `/api/health` báo `database: ok`; trang đăng nhập và thư viện bản đồ trả HTTP 200. Không tạo dữ liệu thử trên Supabase thật.

Nguồn bản đồ cần Internet và trình duyệt hỗ trợ WebGL. Khi nguồn nền mất kết nối, vẫn có thể chỉnh vùng bằng tọa độ; nút tải lại không bảo đảm khắc phục sự cố của nhà cung cấp.
