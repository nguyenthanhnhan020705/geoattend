# Chức năng bổ sung và điều chỉnh

Các tài liệu này mô tả phần bổ sung hoặc thay đổi so với thiết kế MVP ban đầu. Tổng quan và phân chia phase nằm tại [PROJECT_OVERVIEW](../PROJECT_OVERVIEW.md).

| Chức năng/điều chỉnh | Trạng thái | Tài liệu |
| --- | --- | --- |
| Admin xem và xóa lịch sử từng ngày | Đã triển khai, migration 004 | [ADMIN_HISTORY](../ADMIN_HISTORY.md) |
| Check-out sớm có lý do, khóa ngày, xin nghỉ và tiếp tục buổi chiều | Đã triển khai | [USER_FLOW](USER_FLOW.md) |
| UI User ưu tiên điện thoại và khôi phục nền bản đồ | Đã triển khai, còn nghiệm thu thiết bị thật | [UI_AND_MAP](UI_AND_MAP.md) |

ADMIN_HISTORY giữ ở vị trí hiện có để dùng chung cho tài liệu nghiệp vụ, phase và vận hành; không tạo bản sao nội dung trong thư mục này. Dashboard cache/tối ưu snapshot được phân tích trong [Phase 6](../phases/PHASE_6_KIEM_THU_VAN_HANH_VA_PILOT.md).

## Khi có chức năng mới

Chỉ tạo tài liệu riêng khi có nội dung cần phân tích; không dựng hàng loạt file trống cho ý tưởng chưa được chọn. Mỗi tài liệu nên có:

1. Yêu cầu/mục tiêu và lý do bổ sung.
2. Phạm vi, quy tắc nghiệp vụ và phase liên quan.
3. Ảnh hưởng lên giao diện, API, dữ liệu, quyền và migration nếu có.
4. Trạng thái: đề xuất, đã chốt, đang triển khai, đã kiểm chứng hoặc còn giới hạn.
5. Cách sử dụng, tiêu chí nghiệm thu và bằng chứng thực tế.
6. Liên kết tới quy tắc bị thay thế hoặc tài liệu cần cập nhật.

Sau đó cập nhật bảng ở đây, [tổng hợp dự án](../PROJECT_OVERVIEW.md), phase liên quan và [roadmap](../ROADMAP.md). Ý tưởng chưa được phê duyệt chỉ nằm trong [FUTURE_DEVELOPMENT](../FUTURE_DEVELOPMENT.md).
