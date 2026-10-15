# GeoAttend — Kiểm thử thủ công Phase 3

Mở `http://127.0.0.1:8000/login` trên máy chạy ứng dụng. Dùng cửa sổ thường cho Admin, cửa sổ ẩn danh cho User. Kiểm thử Office trước 20:00 giờ Việt Nam; không đổi giờ Windows hay sửa trực tiếp database để vượt mốc này.

## Admin cấu hình vùng thực tế

1. Đăng nhập Admin, chọn **Văn phòng** hoặc mở `/admin/office`.
2. Nhập tên và địa chỉ văn phòng.
3. Di chuyển bản đồ đến văn phòng; bấm để thêm ít nhất ba đỉnh bao quanh khu vực. Có thể dùng ô vĩ độ/kinh độ để thêm hoặc sửa đỉnh, kéo đỉnh trên bản đồ hoặc xóa đỉnh trong danh sách.
4. Nếu cần vùng loại trừ bên trong, thêm một đường biên loại trừ với ít nhất ba đỉnh. Backend từ chối Polygon tự cắt, không có diện tích hoặc vùng loại trừ không hợp lệ.
5. Bấm **Xem trước**, kiểm tra vùng rồi bấm **Lưu vùng văn phòng**. Phiên bản tăng sau khi lưu; tải lại trang vẫn giữ vùng.
6. Mở cùng trang trong hai tab Admin, sửa và lưu tab thứ nhất. Lưu tab thứ hai phải báo vùng đã thay đổi và giữ bản nháp. **Tải lại bản đã lưu** có xác nhận bỏ bản nháp.

Bản đồ nền dùng OpenStreetMap mặc định, có thể thay bằng `GEOATTEND_MAP_TILE_URL`/`GEOATTEND_MAP_ATTRIBUTION`. Nếu nền không tải được, các đỉnh và Polygon vẫn chỉnh/lưu được bằng tọa độ. Bản đồ mặc định chỉ là vị trí xem ban đầu; hệ thống không tự tạo Geofence thật.

## User Check-in Office

| Thao tác | Kết quả mong đợi |
| --- | --- |
| Chưa cấu hình vùng, bấm Office | Báo Admin chưa cấu hình; trạng thái giữ nguyên. |
| Trong vùng, bấm Check-in Office và cấp quyền GPS | “Đang làm tại văn phòng”, có một phiên Office và lịch sử GPS đã xác minh. |
| Trên ranh giới vùng | Được chấp nhận; bộ test tự động đã kiểm tra bằng tọa độ chính xác. |
| Ngoài vùng | Bị từ chối, không mở phiên và không tự chuyển Remote. |
| Từ chối quyền vị trí hoặc GPS timeout | Báo lỗi có hướng dẫn thử lại; Remote vẫn là lựa chọn thủ công có lý do. |
| GPS báo sai số lớn nhưng điểm nằm trong vùng | Vẫn chấp nhận; độ chính xác được ghi để tra cứu. |
| Tải lại khi đang Office | Giữ phiên đang mở. |
| Check-out | Đóng phiên, không hỏi GPS. |
| Bắt đầu Office lại sau Check-out | Xin vị trí mới và xác minh theo vùng hiện tại. |
| Mất phản hồi khi server đã ghi | “Gửi lại thao tác” dùng cùng UUID/payload trong tab, không tạo thêm phiên. GPS không lưu vào sessionStorage/localStorage. |
| Sau 20:00 | Không mở phiên; phiên còn mở tự đóng với nguồn hệ thống. |

Thay đổi Geofence chỉ áp dụng cho lần xác minh tiếp theo, giữ revision/kết quả của phiên cũ. User không sửa được vùng hoặc truy cập trang/API Admin.

## GPS hết hạn

Tọa độ/độ chính xác có thời hạn 30 ngày tuyệt đối từ lúc ghi nhận. Từ đúng thời điểm hết hạn, API che dữ liệu ngay dù maintenance chưa chạy. Worker đặt tọa độ/độ chính xác thành null, giữ lịch sử và kết quả xác minh. Giao diện hiển thị “Dữ liệu vị trí đã hết hạn lưu”. Bộ test dùng đồng hồ kiểm soát để kiểm tra mốc 30 ngày; không cần chờ 30 ngày thực hoặc sửa dữ liệu Supabase.

## Chạy lại sau khi mở máy

```powershell
cd D:\N.ThanhNhan\INTERN\geoattend\.worktrees\phase-1
.\.venv\Scripts\python.exe -m scripts.local_run serve
```

Terminal PowerShell thứ hai:

```powershell
cd D:\N.ThanhNhan\INTERN\geoattend\.worktrees\phase-1
.\.venv\Scripts\python.exe -m scripts.local_run maintenance
```

Giữ hai Terminal mở. Với localhost trên máy tính, trình duyệt có thể xin GPS; cần cấp cả quyền vị trí của Windows và trình duyệt. Kiểm thử điện thoại qua môi trường triển khai HTTPS thuộc Phase 6. Không gửi mật khẩu hoặc tọa độ cá nhân vào báo lỗi công khai.
