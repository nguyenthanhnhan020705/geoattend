# Phase 5 — Dashboard và bản đồ Admin

**Trạng thái:** đã triển khai. Phụ thuộc dữ liệu chấm công Phase 1–4. Phạm vi chính: FR-10 phần Admin, FR-11–13 và FR-15.

## Mục tiêu

Cho Admin xem một bức tranh nhất quán về nhân viên hôm nay, vị trí Office đã xác minh và lịch sử, đồng thời dùng lại các màn hình quản lý đã có.

## Phân tích và triển khai

- Snapshot trả tổng số, bảy nhóm trạng thái và danh sách User, gồm chưa bắt đầu và tài khoản inactive; loại Admin khỏi thống kê chấm công.
- Dùng chung khóa profile với các thao tác ghi; đối soát ngày quá 20:00 trước khi trả snapshot, có `as_of` và `work_date`.
- Onsite chỉ lấy vị trí của phiên Office đang mở đã xác minh; GPS thiếu/hết hạn không tạo Marker giả. Vị trí biểu thị Check-in, không phải theo dõi trực tiếp.
- Marker có tên, Popup có trạng thái/giờ Check-in/xác minh và nút lịch sử.
- Trang dùng lại dialog lịch sử/xóa ngày và editor văn phòng. Quyền xóa lịch sử là bổ sung có trước, không tạo một chức năng xóa thứ hai.
- Refresh sau 30 giây khi tab hiển thị, khi quay lại tab hoặc tải tay; phản hồi cũ không ghi đè snapshot mới. Lỗi mạng giữ dữ liệu có nhãn cũ; lỗi bản đồ không chặn danh sách.

## Mã nguồn và API

`app/admin/service.py`, `routes.py`, `schemas.py`, `admin-dashboard.html`, `admin-dashboard.js`; dùng lại `admin-history.js` và `office-map-background.js`.

API `GET /api/admin/dashboard`, `GET /api/admin/onsite`. Trang `/admin/dashboard`; Admin đăng nhập vẫn tới `/admin/users` và có liên kết Dashboard. Không thêm migration ở Phase 5.

## Kiểm chứng và đầu ra

Test kiểm tra tổng/danh sách/bảy trạng thái, quyền, snapshot khi thay đổi đồng thời, retention, Marker rời Onsite, XSS, layout và refresh. [Báo cáo Phase 5](../archive/PHASE_5_VERIFICATION.md) ghi **249 test toàn suite đạt** tại mốc đó; đây không phải số test hiện tại.

Phase 6 đã bổ sung xử lý khôi phục trang từ browser cache và tối ưu truy vấn snapshot. Vẫn cần kiểm tra browser/thiết bị thực và hiệu năng trên môi trường đích. Xem [Phase 6](PHASE_6_KIEM_THU_VAN_HANH_VA_PILOT.md); [ADMIN_HISTORY](../ADMIN_HISTORY.md) mô tả quyền lịch sử.

Bổ sung độc lập ngày 18/10/2026: [báo cáo tuần PDF](../features/WEEKLY_REPORTS.md) có trang Admin xem/tải và liên kết cạnh Dashboard. Không thêm dữ liệu PDF vào snapshot/truy vấn Dashboard hoặc thay nghiệp vụ Onsite/lịch sử chấm công. Chức năng mới dùng migration 005 riêng, đã kiểm chứng local cùng toàn suite 318 test đạt; đây không phải thay đổi migration của Phase 5 lịch sử và chưa áp dụng vào database ứng dụng.
