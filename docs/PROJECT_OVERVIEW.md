# GeoAttend — Tổng hợp toàn dự án

## 1. Mục tiêu và phạm vi

GeoAttend là ứng dụng WebGIS ghi nhận trạng thái làm việc Office/Remote, nghỉ trưa, nghỉ sáng/cả ngày và kết thúc ngày. MVP phục vụ một công ty, một văn phòng, một nhóm khoảng 10 nhân viên và một Admin quản lý.

Hệ thống xác minh vị trí khi bắt đầu Office, giúp Admin theo dõi trạng thái và tra cứu lịch sử. Không theo dõi GPS liên tục, không tính lương hoặc đánh giá năng suất theo giờ làm việc. Remote/nghỉ không cần phê duyệt. Yêu cầu chi tiết có mã FR/BR/AC/NFR tại [REQUIREMENTS](REQUIREMENTS.md).

## 2. Vai trò và chức năng

| Vai trò | Chức năng |
| --- | --- |
| User | Đăng nhập, đổi mật khẩu, Office/Remote, nghỉ trưa, xin nghỉ, Check-out và xem lịch sử bản thân |
| Admin | Cấp/reset tài khoản User, Dashboard, bản đồ Onsite, cấu hình văn phòng/Geofence, xem và xóa lịch sử từng ngày theo điều kiện |
| Người vận hành | Thiết lập/khôi phục Admin, migration, chạy web/maintenance, backup và khôi phục |

Admin không chấm công cá nhân. Không có đăng ký công khai hoặc đăng nhập Google trong MVP. Xem [ACCOUNT_RULES](ACCOUNT_RULES.md) và [hướng dẫn sử dụng](USAGE.md).

## 3. Kiến trúc

```text
Trình duyệt User/Admin
  → FastAPI: trang HTML/CSS/JavaScript và API cùng nguồn
    → Psycopg connection pool → PostgreSQL/PostGIS (schema geoattend)
Maintenance độc lập → đối soát ngày, dọn phiên xác thực và GPS hết hạn
```

- Python 3.13, FastAPI/Uvicorn; JavaScript thuần, Leaflet/MapLibre cho bản đồ.
- Database ứng dụng dùng PostgreSQL/PostGIS; cấu hình hiện có sử dụng Supabase. Trình duyệt gọi Backend, không kết nối trực tiếp database.
- Xác thực bằng cookie phiên lưu tại database; mật khẩu Argon2id, token phiên chỉ lưu hash. API thay đổi dữ liệu kiểm tra quyền, CSRF và nguồn yêu cầu.
- Migration SQL đánh số và checksum; tài khoản database runtime tách khỏi tài khoản migration.
- Web và maintenance là hai tiến trình. Production có mẫu Caddy HTTPS và systemd trong `deploy/`.

## 4. Dữ liệu và tính nhất quán

| Nhóm | Bảng |
| --- | --- |
| Tài khoản/xác thực | `profiles`, `auth_sessions`, `auth_attempts` |
| Văn phòng | `office` |
| Chấm công | `attendance_days`, `work_sessions`, `attendance_events` |
| Vị trí có thời hạn | `office_locations` |
| Chống gửi trùng | `attendance_requests` |

`schema_migrations` ghi phiên bản schema. Mỗi User có trạng thái theo ngày Việt Nam. Các thao tác khóa profile, kiểm tra ngày/revision và ghi phiên/sự kiện/trạng thái trong cùng transaction. `request_id` cho phép gửi lại an toàn khi mất phản hồi; cùng mã nhưng khác nội dung bị từ chối.

## 5. Luồng nghiệp vụ hiện hành

- Chưa bắt đầu: chọn Office có GPS, Remote có lý do hoặc xin nghỉ có lý do.
- Ca đầu: nghỉ trưa hoặc Check-out sớm có lý do. Nghỉ trưa đóng phiên; tiếp tục Office/Remote tạo phiên mới.
- Nghỉ sáng: khi quay lại chọn tiếp tục buổi chiều Office/Remote, không chờ một mốc giờ chiều cố định. Sau nghỉ sáng/nghỉ trưa, UI chỉ hiện Check-out cuối ngày.
- Mọi Check-out và nghỉ cả ngày khóa ngày; ngày hôm sau mở lại. Admin xóa lịch sử hôm nay hợp lệ là ngoại lệ đưa ngày về chưa bắt đầu với revision mới.
- Từ đúng 20:00 giờ Việt Nam, không tạo/tiếp tục/chuyển phiên. Phiên còn mở được hệ thống đóng; nghỉ trưa chỉ ghi kết thúc ngày, không cộng thêm thời gian làm việc.
- Office chấp nhận điểm trong hoặc trên ranh giới bằng `ST_Covers`, không vùng đệm, không chặn chỉ vì sai số GPS lớn. Tọa độ/accuracy hết hạn sau 30 ngày; lịch sử và kết quả xác minh được giữ.

API chuyển trực tiếp Office/Remote còn được giữ tương thích, UI hiện hành đi theo ca. Quy tắc chính xác tại [STATE_TRANSITIONS](STATE_TRANSITIONS.md).

## 6. Phân tích theo phase

| Phase | Nội dung | Trạng thái |
| --- | --- | --- |
| [0](phases/PHASE_0_PHAN_TICH_NGHIEP_VU_VA_THIET_KE.md) | Chốt phạm vi, nghiệp vụ, kiến trúc và dữ liệu | Hoàn thành thiết kế; đã có điều chỉnh nghiệp vụ sau đó |
| [1](phases/PHASE_1_NEN_TANG_DATABASE_VA_TAI_KHOAN.md) | Nền tảng, database, xác thực và tài khoản | Đã triển khai |
| [2](phases/PHASE_2_REMOTE_PHIEN_LAM_VIEC_VA_LICH_SU.md) | Remote, trạng thái ngày, lịch sử và mốc 20:00 | Đã triển khai |
| [3](phases/PHASE_3_OFFICE_GEOFENCE_VA_GPS.md) | Office, Geofence và thời hạn GPS | Đã triển khai |
| [4](phases/PHASE_4_NGHI_TRUA_XIN_NGHI_VA_LUONG_THEO_CA.md) | Nghỉ trưa, nghỉ và làm việc theo ca | Đã triển khai theo các điều chỉnh hiện hành |
| [5](phases/PHASE_5_DASHBOARD_VA_BAN_DO_ADMIN.md) | Dashboard và bản đồ Admin | Đã triển khai |
| [6](phases/PHASE_6_KIEM_THU_VAN_HANH_VA_PILOT.md) | Kiểm thử tổng thể, vận hành và pilot | Đã kiểm chứng local/chuẩn bị; chưa hoàn tất môi trường thật/pilot |

Các bổ sung được ghi riêng tại [features](features/README.md): lịch sử Admin, UI theo ca, khóa ngày và khôi phục bản đồ. Các đề xuất chưa triển khai ở [FUTURE_DEVELOPMENT](FUTURE_DEVELOPMENT.md).

## 7. Kiểm chứng và giới hạn

Báo cáo Phase 6 ghi nhận 290 test đạt, một cảnh báo thư viện. Lượt chạy lại trước push ngày 17/10/2026 cũng đạt **290 passed, 1 warning**, 416,67 giây; log local `.local-tests/phase-6/github-publish-tests.log`. Đây là kết quả tại các mốc chạy đó; lần tổ chức tài liệu này không chạy lại bộ kiểm thử ứng dụng.

Đo tải local đã ghi 3.651 request, đủ mẫu, 0 lỗi và 100% trong 2 giây ở lượt cuối; đã diễn tập backup/restore trên database test riêng. Chi tiết tại [báo cáo](PHASE_6_VERIFICATION.md), [hiệu năng](PHASE_6_PERFORMANCE.md) và [ma trận nghiệm thu](PHASE_6_ACCEPTANCE.md).

Còn thiếu HTTPS trên máy chủ đích, GPS/thiết bị thật, xác minh vận hành/hiệu năng đích và pilot khoảng 10 người trong 5 ngày làm việc. Timeline có thể sắp các sự kiện trùng timestamp theo UUID khác thứ tự nhân quả; đây là giới hạn trình bày đã ghi nhận.

## 8. Cách tiếp tục dự án

- Chạy/cấu hình/kiểm thử: [DEVELOPMENT](DEVELOPMENT.md).
- Hướng dẫn User/Admin: [USAGE](USAGE.md).
- Tiến độ và việc còn lại: [ROADMAP](ROADMAP.md).
- Triển khai/backup/restore: [PHASE_6_OPERATIONS](PHASE_6_OPERATIONS.md).
- Thiết bị thật và pilot: [PHASE_6_PILOT](PHASE_6_PILOT.md).
- Kế hoạch và số liệu cũ: [archive](archive/README.md), chỉ dùng theo bối cảnh lịch sử.

Khi bổ sung chức năng: tạo tài liệu riêng theo hướng dẫn trong [features](features/README.md), rồi cập nhật mục chức năng, phase liên quan và tiến độ tại đây. Không đánh dấu hoàn thành chỉ vì đã có bản thiết kế.
