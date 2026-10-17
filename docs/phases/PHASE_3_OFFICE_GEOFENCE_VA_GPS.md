# Phase 3 — Office, Geofence và GPS

**Trạng thái:** đã triển khai và kiểm thử local. Phụ thuộc [Phase 2](PHASE_2_REMOTE_PHIEN_LAM_VIEC_VA_LICH_SU.md). Phạm vi chính: FR-02, FR-08 phần Office, FR-14 và chính sách vị trí NFR-02.

## Mục tiêu

Cho Admin cấu hình vùng văn phòng và User bắt đầu Office khi vị trí hợp lệ, đồng thời kiểm soát việc thu thập/lưu/xóa GPS.

## Phân tích và triển khai

- Văn phòng lưu Polygon EPSG:4326, hỗ trợ vùng loại trừ; kiểm tra hợp lệ, không rỗng/tự cắt, có diện tích. Revision ngăn ghi đè cấu hình mới.
- User bấm Office mới gọi `getCurrentPosition`; không dùng theo dõi liên tục. Tọa độ không lưu vào localStorage/sessionStorage.
- Backend tạo Point theo thứ tự longitude/latitude và dùng `ST_Covers`, chấp nhận cả ranh giới. Không vùng đệm; accuracy lớn không tự làm thao tác thất bại.
- Chưa cấu hình, ngoài vùng hoặc GPS lỗi thì giữ trạng thái trước đó; không tự chuyển Remote.
- Giữ khóa vùng khi xác minh, lưu đúng revision của Geofence tại phiên Office. Thay vùng không tính lại phiên cũ.
- GPS được lưu riêng tại `office_locations`; API che tọa độ/accuracy ngay khi đủ 30 ngày, worker xóa giá trị vật lý sau đó. Giữ lịch sử và kết quả xác minh.
- Check-out không lấy GPS, kể cả khi nhân viên ở ngoài vùng.

## Mã nguồn và giao diện

`app/gis/`, tích hợp `app/attendance/service.py`, trang `admin-office.html`, `admin-office.js`, `office-map-background.js` và luồng Office trong `user.js`.

API quản trị `GET/PUT /api/admin/office`; Office dùng chung `POST /api/attendance/actions`. Admin vẽ/sửa đỉnh, xem trước rồi lưu. Khả năng phục hồi nền bản đồ được bổ sung sau đó, xem [UI và bản đồ](../features/UI_AND_MAP.md).

## Kiểm chứng và giới hạn

Test GIS kiểm tra trong/ngoài/trên biên, vùng loại trừ, sai thứ tự tọa độ, input không hợp lệ và cập nhật vùng đồng thời. Test retention kiểm tra trước/đúng/sau 30 ngày và worker chạy lại. Browser kiểm tra quyền GPS giả lập, retry, không lưu GPS và giữ bản nháp.

Báo cáo lịch sử: [PHASE_3_VERIFICATION](../archive/PHASE_3_VERIFICATION.md), [khôi phục bản đồ](../archive/MAP_RECOVERY.md); mốc toàn suite lần lượt 119 và 122 test đạt. GPS trên điện thoại thật/HTTPS đích thuộc [Phase 6](PHASE_6_KIEM_THU_VAN_HANH_VA_PILOT.md), chưa được thay bằng kết quả giả lập.

Đầu ra: Admin lưu vùng → User vào Office hợp lệ → xem phiên có xác minh. [Phase 4](PHASE_4_NGHI_TRUA_XIN_NGHI_VA_LUONG_THEO_CA.md) dùng lại xác minh này khi tiếp tục hoặc chuyển chế độ.
