# Tài liệu GeoAttend

Bắt đầu từ [tổng hợp toàn dự án](PROJECT_OVERVIEW.md) để nắm mục tiêu, kiến trúc, chức năng và tiến độ; [README dự án](../README.md) hướng dẫn cài đặt nhanh. Mỗi phase có một file phân tích riêng. Kế hoạch và báo cáo gốc vẫn nằm trong [archive](archive/README.md) để đối chiếu.

## Tổng hợp, phân tích theo phase và mở rộng

| Tài liệu | Nội dung |
| --- | --- |
| [PROJECT_OVERVIEW](PROJECT_OVERVIEW.md) | Tổng hợp toàn bộ dự án: phạm vi, vai trò, kiến trúc, dữ liệu, nghiệp vụ, các phase và phần còn lại |
| [Phase 0](phases/PHASE_0_PHAN_TICH_NGHIEP_VU_VA_THIET_KE.md) | Phân tích nghiệp vụ và thiết kế |
| [Phase 1](phases/PHASE_1_NEN_TANG_DATABASE_VA_TAI_KHOAN.md) | Nền tảng, database, xác thực và tài khoản |
| [Phase 2](phases/PHASE_2_REMOTE_PHIEN_LAM_VIEC_VA_LICH_SU.md) | Remote, phiên làm việc, lịch sử và tự đóng ngày |
| [Phase 3](phases/PHASE_3_OFFICE_GEOFENCE_VA_GPS.md) | Office, GPS, Geofence và thời hạn vị trí |
| [Phase 4](phases/PHASE_4_NGHI_TRUA_XIN_NGHI_VA_LUONG_THEO_CA.md) | Nghỉ trưa, nghỉ và luồng làm việc theo ca |
| [Phase 5](phases/PHASE_5_DASHBOARD_VA_BAN_DO_ADMIN.md) | Dashboard và bản đồ Admin |
| [Phase 6](phases/PHASE_6_KIEM_THU_VAN_HANH_VA_PILOT.md) | Kiểm thử tổng thể, vận hành và pilot |
| [Chức năng bổ sung](features/README.md) | Các điều chỉnh đã triển khai và quy ước tài liệu cho chức năng mới |
| [Hướng phát triển](FUTURE_DEVELOPMENT.md) | Ý tưởng sau MVP, chưa cam kết triển khai |

Các file phase mô tả mục tiêu, phạm vi, phân tích/triển khai, mã nguồn liên quan, kiểm chứng và giới hạn. Số test ở từng mốc là snapshot của toàn suite, không cộng các mốc thành tổng số test.

## Sử dụng và phát triển

| Tài liệu | Nội dung |
| --- | --- |
| [USAGE](USAGE.md) | Thao tác User/Admin, chấm công theo ca, bản đồ và xử lý lỗi thường gặp |
| [DEVELOPMENT](DEVELOPMENT.md) | Cài đặt, cấu hình, tài khoản quản trị, chạy web/worker và kiểm thử |
| [REQUIREMENTS](REQUIREMENTS.md) | BRD, mã yêu cầu FR/BR/AC/NFR; có phần lịch sử được ghi rõ |
| [ROADMAP](ROADMAP.md) | Phần đã hoàn thành và công việc còn lại |
| [ACCOUNT_RULES](ACCOUNT_RULES.md) | Quyền và vòng đời tài khoản |
| [STATE_TRANSITIONS](STATE_TRANSITIONS.md) | Trạng thái, khóa ngày, thời gian và chống thao tác trùng |
| [ADMIN_HISTORY](ADMIN_HISTORY.md) | Xem/xóa lịch sử nhân viên, điều kiện và giới hạn |

## Kiểm chứng và vận hành

| Tài liệu | Nội dung |
| --- | --- |
| [PHASE_6_VERIFICATION](PHASE_6_VERIFICATION.md) | Kết quả kiểm thử đã ghi nhận và giới hạn chưa nghiệm thu |
| [PHASE_6_ACCEPTANCE](PHASE_6_ACCEPTANCE.md) | Ma trận nghiệm thu theo từng yêu cầu |
| [PHASE_6_PERFORMANCE](PHASE_6_PERFORMANCE.md) | Phương pháp và kết quả đo tải local |
| [PHASE_6_OPERATIONS](PHASE_6_OPERATIONS.md) | HTTPS, worker, quyền database, log, backup, restore và rollback |
| [PHASE_6_PILOT](PHASE_6_PILOT.md) | Checklist thiết bị thật và pilot 5 ngày; chưa có kết quả pilot |
| [evidence/phase6](evidence/phase6/) | Số liệu đo tải và diễn tập restore đã khử thông tin nhạy cảm |

Quy tắc hiện hành: Check-out và nghỉ cả ngày khóa ngày; nghỉ sáng cho tiếp tục buổi chiều; Admin được xóa lịch sử theo điều kiện trong ADMIN_HISTORY. Thiết kế cũ cho bắt đầu lại sau Check-out hoặc hủy nghỉ cả ngày đã được thay thế. Số liệu kiểm thử trong báo cáo là kết quả của lần chạy được ghi rõ, không tự cập nhật theo mỗi thay đổi.

## Phân loại file

- Giữ `app/`, `migrations/`, `scripts/`, `tests/`, `deploy/`, các file requirements, lockfile, `pyproject.toml`, `.env.example` và `.gitignore`: phục vụ chạy, phát triển hoặc vận hành dự án.
- Giữ giấy phép trong `app/static/vendor/`: đi kèm thư viện bản đồ đang sử dụng.
- Gom kế hoạch, báo cáo phase cũ, checklist cũ và bàn giao agent vào `docs/archive/`. Chúng có giá trị tra cứu lịch sử nhưng không phải hướng dẫn bắt đầu hiện hành.
- Giữ nguyên các thư mục local đã được Git bỏ qua. Đặc biệt `.env` chứa cấu hình riêng và `.local-tests` có thể chứa cluster PostgreSQL đang dùng.

Đợt sắp xếp tài liệu này chỉ thay đổi Markdown và đường dẫn tài liệu; không sửa mã nguồn, migration, cấu hình chạy hoặc dữ liệu.
