# Phase 4 — Nghỉ trưa, nghỉ và luồng theo ca

**Trạng thái:** đã triển khai; áp dụng các điều chỉnh User sau Phase 5. Phụ thuộc [Phase 2](PHASE_2_REMOTE_PHIEN_LAM_VIEC_VA_LICH_SU.md) và [Phase 3](PHASE_3_OFFICE_GEOFENCE_VA_GPS.md). Phạm vi chính: FR-04–07 và các luồng hỗn hợp Office/Remote.

## Mục tiêu

Ghi nhận trọn ngày làm việc gồm nhiều phiên, nghỉ và tiếp tục, bảo đảm thất bại không đóng nhầm phiên hoặc làm mất lịch sử.

## Phân tích và triển khai

| Thao tác | Tác động |
| --- | --- |
| Nghỉ trưa | Đóng phiên hiện tại và ghi `LUNCH_BREAK` trong cùng giao dịch |
| Tiếp tục Office/Remote | Tạo phiên mới; Office xác minh GPS lại, Remote cần lý do |
| Nghỉ sáng | Lưu sự kiện/lý do, không tạo phiên; khi quay lại cho tiếp tục trước 20:00 |
| Nghỉ cả ngày | Lưu sự kiện/lý do, không tạo phiên và khóa ngày theo quy tắc hiện hành |
| API chuyển trực tiếp Office/Remote | Kiểm tra điều kiện đích trước khi đóng phiên cũ và tạo phiên mới nguyên tử |
| Nghỉ trưa qua 20:00 | Ghi `DAY_END`, chuyển Check-out, không kéo dài phiên trước nghỉ |

Mọi chuyển đổi áp dụng khóa profile, transaction, revision/ngày và request UUID có sẵn. Lỗi xác minh hoặc ghi dữ liệu giữ nguyên trạng thái/phiên cũ. Ngày mới độc lập với ngày trước.

## Quy tắc User sau điều chỉnh

UI hiện hành đi theo ca: ca đầu có Nghỉ trưa/Check-out sớm; nghỉ trưa hoặc nghỉ sáng có hai lựa chọn tiếp tục; sau tiếp tục chỉ Check-out cuối ngày. Mọi Check-out và nghỉ cả ngày khóa ngày. API chuyển trực tiếp còn giữ tương thích nhưng UI không có nút chuyển khi đang làm.

Hủy nghỉ cả ngày để làm tiếp từng có trong phase này; hiện chỉ giữ replay UUID lịch sử, chặn action mới. Chi tiết tại [USER_FLOW](../features/USER_FLOW.md) và [STATE_TRANSITIONS](../STATE_TRANSITIONS.md).

## Mã nguồn và kiểm chứng

Mở rộng `app/attendance/service.py`, `schemas.py`, `app/static/user.html`, `user.js`; phase này không thêm migration. Test chính: `test_attendance_breaks.py`, `test_attendance_leave.py`, `test_attendance_switch.py`, `test_phase4_regression.py`, `test_phase4_browser.py` và các test điều chỉnh sau đó.

Kiểm tra các tổ hợp Office/Remote hai ca, nghỉ sáng/cả ngày, rollback, switch đồng thời, mốc 20:00, session bị thu hồi khi chờ khóa và retry qua reload. [Báo cáo lịch sử](../archive/PHASE_4_VERIFICATION.md) ghi **195 test toàn suite đạt** tại mốc Phase 4; kết quả sau điều chỉnh nằm trong tài liệu chức năng bổ sung.

Đầu ra là trạng thái và lịch sử đủ để [Phase 5](PHASE_5_DASHBOARD_VA_BAN_DO_ADMIN.md) tổng hợp lên Dashboard/Onsite. Giới hạn Timeline trùng timestamp vẫn được ghi nhận trong [Phase 6](PHASE_6_KIEM_THU_VAN_HANH_VA_PILOT.md).
