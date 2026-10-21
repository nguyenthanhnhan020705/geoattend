# Bổ sung giao diện User và phục hồi bản đồ

**Trạng thái:** đã triển khai và kiểm thử trình duyệt local; nghiệm thu điện thoại/HTTPS đích thuộc [Phase 6](../phases/PHASE_6_KIEM_THU_VAN_HANH_VA_PILOT.md).

## Giao diện User ưu tiên điện thoại

Mục tiêu là giảm số form xuất hiện cùng lúc và giúp nhân viên tập trung vào thao tác đang cần.

- Thông tin nhân viên ở đầu, trạng thái/thao tác theo ca ở giữa, lịch sử cá nhân thu gọn cuối trang.
- Chọn Remote hoặc Xin nghỉ mới hiện phần nhập lý do. Lịch sử chỉ tải khi người dùng mở.
- Giữ bản nháp, trạng thái đang gửi và focus; tên/lý do dùng text để tránh thực thi HTML.
- Phản hồi lịch sử cũ không ghi đè lượt tải mới khi đóng/mở hoặc đổi bộ lọc.
- Dùng lại hợp đồng GPS/retry/UUID; không thay đổi schema hoặc quyền.

Mã liên quan: `app/static/user.html`, `css/app.css`, `js/user.js`. Kiểm chứng: `test_user_mobile_layout.py` và các test luồng User. [Báo cáo UI lịch sử](../archive/USER_MOBILE_UI.md) có các mốc kiểm thử, không thay cho chứng nhận mọi điện thoại.

## Nền bản đồ và editor văn phòng

Mục tiêu là giữ khả năng thao tác khi nguồn bản đồ hoặc API gặp lỗi mạng, đồng thời cho Admin vẽ vùng trực tiếp.

- Leaflet quản lý editor; nền vector mặc định dùng OpenFreeMap qua MapLibre. Có cấu hình raster và attribution.
- Admin bấm Vẽ vùng, chọn các đỉnh, xem trước rồi lưu; có thể sửa bằng tọa độ.
- API có giới hạn chờ; khi lỗi tải, mở lại thao tác. Khi lưu bị timeout, cần tải bản đã lưu để biết kết quả.
- Tải lại bản đồ giữ bản nháp; nguồn nền lỗi không chặn danh sách/lịch sử và thao tác chỉnh tọa độ.
- Giữ thư viện và giấy phép tại `app/static/vendor/`; nguồn nền cần Internet, vector cần WebGL.

Mã liên quan: `admin-office.js`, `office-map-background.js`, `api.js` và cấu hình map trong `app/config.py`. Test: `test_office_map_recovery.py`, `test_office_browser.py`, test cấu hình. [Báo cáo bản đồ](../archive/MAP_RECOVERY.md) lưu nguyên nhân và bằng chứng tại thời điểm sửa.

Các bổ sung này không làm thay đổi quy tắc Geofence/GPS ở [Phase 3](../phases/PHASE_3_OFFICE_GEOFENCE_VA_GPS.md). Cách sử dụng tại [USAGE](../USAGE.md), cấu hình tại [DEVELOPMENT](../DEVELOPMENT.md).
