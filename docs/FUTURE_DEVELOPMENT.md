# Hướng phát triển GeoAttend

**Trạng thái:** định hướng sau MVP từ BRD, chưa phải kế hoạch triển khai đã được duyệt. Các mục dưới đây chưa được coi là chức năng đã hoàn thành.

## Ưu tiên trước khi mở rộng

Hoàn tất [Phase 6](phases/PHASE_6_KIEM_THU_VAN_HANH_VA_PILOT.md): triển khai HTTPS, kiểm tra GPS/thiết bị thật, vận hành/backup, đo hiệu năng đích và pilot khoảng 10 người trong 5 ngày làm việc. Xử lý lỗi cản trở được phát hiện từ quá trình này trước khi chốt phạm vi mở rộng.

## Các hướng đã được nêu trong yêu cầu

| Hướng phát triển | Mục đích | Nội dung cần phân tích trước khi làm |
| --- | --- | --- |
| PWA | Truy cập thuận tiện trên điện thoại | Cài đặt, cache, cập nhật phiên bản, hành vi khi mất mạng và gửi lại thao tác |
| Thông báo | Nhắc/trao đổi thông tin liên quan chấm công | Kênh gửi, thời điểm, quyền nhận và tùy chọn người dùng |
| Báo cáo và xuất Excel/CSV/PDF | Tổng hợp ngày/tuần/tháng | Chỉ số, quyền xem/xuất và giới hạn dữ liệu cá nhân/GPS |
| Audit Log và Correction Request | Truy vết và yêu cầu điều chỉnh | Sự kiện cần lưu, quyền sửa/duyệt và quan hệ với xóa lịch sử |
| Dynamic QR Verification | Bổ sung xác minh tại văn phòng | Cách kết hợp GPS, thời hạn mã và chống sử dụng lại/chia sẻ mã |
| Nhiều văn phòng/phòng ban | Mở rộng phạm vi doanh nghiệp | Mô hình dữ liệu, quyền theo đơn vị, lựa chọn vùng và báo cáo |
| Ứng dụng mobile | Hỗ trợ trải nghiệm ứng dụng riêng | Nền tảng, phân phối, quyền vị trí và tương thích API |
| AI + RAG cho báo cáo | Đọc, tóm tắt báo cáo nhân viên để Admin tra cứu | Dữ liệu đầu vào, quyền truy cập, chi phí, lưu trữ và cách kiểm tra kết quả |

Tính lương và đánh giá năng suất nằm ngoài phạm vi MVP; bảng này không tự bổ sung chúng vào kế hoạch. Chưa có lịch, ngân sách hoặc cam kết thứ tự cho các hướng trên.

## Cách đưa một hướng vào triển khai

Khi chọn một chức năng, tạo một file phân tích tại `docs/features/` theo [quy ước](features/README.md): chốt mục tiêu/phạm vi, ảnh hưởng dữ liệu/API/UI, tiêu chí nghiệm thu và trạng thái. Sau khi có quyết định, cập nhật [tổng hợp dự án](PROJECT_OVERVIEW.md), [roadmap](ROADMAP.md) và tài liệu phase liên quan.

Nguồn phạm vi: mục 12.2 trong [REQUIREMENTS](REQUIREMENTS.md). Các ý tưởng chưa chọn tiếp tục được giữ trong file này để tránh tạo nhiều tài liệu rời chưa có nội dung thực tế.
