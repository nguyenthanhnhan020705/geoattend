# Điều chỉnh luồng User: Check-out và xin nghỉ

**Trạng thái:** đã triển khai theo yêu cầu ngày 16/10/2026. Liên quan [Phase 2](../phases/PHASE_2_REMOTE_PHIEN_LAM_VIEC_VA_LICH_SU.md) và [Phase 4](../phases/PHASE_4_NGHI_TRUA_XIN_NGHI_VA_LUONG_THEO_CA.md).

## Yêu cầu và quy tắc

| Tình huống | Hành vi hiện tại |
| --- | --- |
| Đang làm ca đầu | UI hiện Nghỉ trưa và Check-out sớm |
| Check-out sớm | Phải nhập lý do 1–1000 ký tự sau trim và xác nhận; kết thúc ngày |
| Nghỉ trưa | Chọn tiếp tục Office/Remote; tạo phiên mới |
| Xin nghỉ | Chọn buổi sáng/cả ngày trước, sau đó nhập lý do và xác nhận |
| Nghỉ sáng | Có hai lựa chọn tiếp tục buổi chiều Office/Remote trước 20:00; Office xác minh GPS, Remote cần lý do |
| Sau nghỉ trưa/nghỉ sáng | UI chỉ hiện Check-out cuối ngày; không bắt lý do sớm |
| Đã Check-out hoặc nghỉ cả ngày | `day_finished=true`, không có action mới; ngày Việt Nam mới mở lại |

Đây là thay đổi so với quyền bắt đầu lại sau Check-out và hủy nghỉ cả ngày trong thiết kế ban đầu. Admin xóa lịch sử hôm nay hợp lệ vẫn là ngoại lệ đưa ngày về chưa bắt đầu; cùng UUID đã commit vẫn replay được.

## Thiết kế và ảnh hưởng

- Backend dùng trạng thái/sự kiện thực để trả `lunch_taken`, `morning_leave`, `day_finished`; không suy ra ca từ giờ trên thiết bị.
- Lý do Check-out được lưu ở phiên và sự kiện kết thúc; hiển thị như văn bản trong lịch sử.
- UI mở form lý do theo thao tác, có xác nhận và giữ bản nháp khi đóng/mở form.
- Giữ transaction, khóa profile, mốc 20:00, expected date/revision và hash payload để retry cũ hoạt động.
- Không đổi migration. API switch/nghỉ trưa cũ giữ tương thích; thay đổi UI không đồng nghĩa xóa các API đó.
- Action hủy nghỉ cả ngày mới bị chặn; kết quả của UUID hủy nghỉ đã commit ở bản cũ vẫn đọc lại được.

## Kiểm chứng

`test_daily_action_ui.py` và `test_leave_day_flow.py` kiểm tra lý do, reload, khóa ngày, ngày mới, UI và legacy replay. Các nhóm race/retention/quyền kiểm tra các bất biến được giữ.

Báo cáo lịch sử: [Check-out sớm](../archive/EARLY_CHECKOUT_VERIFICATION.md) ghi mốc toàn suite 259 test đạt; [luồng nghỉ](../archive/LEAVE_FLOW_VERIFICATION.md) ghi mốc 267 test đạt. Không cộng hai con số này. Kết quả tổng thể sau đó ở [Phase 6](../phases/PHASE_6_KIEM_THU_VAN_HANH_VA_PILOT.md).

Hướng dẫn sử dụng tại [USAGE](../USAGE.md), hợp đồng trạng thái tại [STATE_TRANSITIONS](../STATE_TRANSITIONS.md).
