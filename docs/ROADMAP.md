# GeoAttend — Tiến độ MVP

Phạm vi MVP: một công ty, một văn phòng, một Admin và khoảng 10 nhân viên. Mã chức năng đã triển khai; nghiệm thu môi trường thật và pilot vẫn còn mở.

Tổng hợp toàn bộ nội dung tại [PROJECT_OVERVIEW](PROJECT_OVERVIEW.md). Đọc phân tích riêng: [Phase 0](phases/PHASE_0_PHAN_TICH_NGHIEP_VU_VA_THIET_KE.md), [Phase 1](phases/PHASE_1_NEN_TANG_DATABASE_VA_TAI_KHOAN.md), [Phase 2](phases/PHASE_2_REMOTE_PHIEN_LAM_VIEC_VA_LICH_SU.md), [Phase 3](phases/PHASE_3_OFFICE_GEOFENCE_VA_GPS.md), [Phase 4](phases/PHASE_4_NGHI_TRUA_XIN_NGHI_VA_LUONG_THEO_CA.md), [Phase 5](phases/PHASE_5_DASHBOARD_VA_BAN_DO_ADMIN.md), [Phase 6](phases/PHASE_6_KIEM_THU_VAN_HANH_VA_PILOT.md).

| Phase | Nội dung | Trạng thái |
| --- | --- | --- |
| 0 | Phân tích nghiệp vụ, kiến trúc, dữ liệu và API | Đã hoàn thành thiết kế; một số quy tắc đã được cập nhật sau đó |
| 1 | Database, đăng nhập, phân quyền và quản lý tài khoản | Đã triển khai |
| 2 | Remote, phiên làm việc, lịch sử cá nhân và tự đóng lúc 20:00 | Đã triển khai |
| 3 | Geofence, Office và thời hạn GPS 30 ngày | Đã triển khai |
| 4 | Nghỉ trưa, nghỉ sáng/cả ngày và luồng làm việc theo ca | Đã triển khai theo quy tắc hiện hành |
| 5 | Dashboard, bản đồ Onsite và lịch sử Admin | Đã triển khai |
| 6 | Kiểm thử tổng thể, triển khai và pilot | Hoàn tất phần local/chuẩn bị; chưa hoàn tất toàn phase |

## Quy tắc hiện hành

- Mọi Check-out kết thúc ngày; Check-out ca đầu cần lý do. Sau nghỉ trưa/nghỉ sáng không bắt buộc lý do sớm.
- Nghỉ cả ngày khóa ngày; nghỉ sáng cho tiếp tục buổi chiều Office/Remote trước 20:00.
- Admin được xóa lịch sử ngày đã dừng làm việc sau xác nhận. Xóa hôm nay đưa ngày về chưa bắt đầu với revision mới.
- API chuyển trực tiếp Office/Remote giữ tương thích; UI theo ca không có nút chuyển trực tiếp khi đang làm việc.

Chi tiết tại [STATE_TRANSITIONS](STATE_TRANSITIONS.md), [ACCOUNT_RULES](ACCOUNT_RULES.md) và [ADMIN_HISTORY](ADMIN_HISTORY.md).

## Bằng chứng và phần còn lại

[Báo cáo Phase 6](PHASE_6_VERIFICATION.md) ghi nhận 290 ca kiểm thử đạt và một cảnh báo thư viện. [Đo tải local](PHASE_6_PERFORMANCE.md) và [diễn tập restore](evidence/phase6/restore.json) đã có bằng chứng. Các kết quả local không thay cho nghiệm thu trên môi trường triển khai.

Cần hoàn thành:

1. Chọn và triển khai môi trường HTTPS, database, worker và người phụ trách vận hành.
2. Kiểm tra GPS, Geofence và luồng User/Admin trên thiết bị thật, bao gồm Android/iPhone.
3. Xác minh log, giám sát, backup/restore, tự đóng ngày và thời hạn GPS trên môi trường đích.
4. Đo ít nhất 95% yêu cầu API backend hoàn tất trong tối đa 2 giây trên cấu hình đích.
5. Pilot khoảng 10 User trong 5 ngày làm việc, tổng hợp phản hồi và nghiệm thu.

Theo dõi bằng [ma trận AC/NFR](PHASE_6_ACCEPTANCE.md), [runbook vận hành](PHASE_6_OPERATIONS.md) và [checklist pilot](PHASE_6_PILOT.md). Còn một giới hạn trình bày Timeline: các sự kiện trùng timestamp có thể sắp theo UUID khác thứ tự nhân quả; dữ liệu phiên/trạng thái được kiểm thử riêng.

## Sau MVP

PWA, thông báo, xuất báo cáo, AI/RAG, QR, nhiều văn phòng/phòng ban và ứng dụng mobile thuộc định hướng sau MVP. Tính lương và đánh giá năng suất nằm ngoài phạm vi MVP.

Các định hướng được phân tích tại [FUTURE_DEVELOPMENT](FUTURE_DEVELOPMENT.md); những bổ sung đã triển khai tại [features](features/README.md).

Kế hoạch và số liệu từng giai đoạn được giữ trong [archive](archive/README.md); [roadmap cũ](archive/ROADMAP.md) chỉ dùng để tra cứu lịch sử.
