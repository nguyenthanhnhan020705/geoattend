# Phase 0 — Phân tích nghiệp vụ và thiết kế

**Trạng thái:** đã hoàn thành thiết kế. Đây là bản phân tích tổng hợp, có ghi các quyết định đã được thay thế sau triển khai.

## Mục tiêu và phạm vi

Chốt MVP trước khi viết mã: một công ty/văn phòng, User/Admin, Office/Remote, nghỉ, lịch sử và bản đồ. Xác định các yêu cầu FR/BR/AC/NFR, chính sách GPS, thời gian và các tiêu chí nghiệm thu.

## Phân tích và quyết định

- Admin chỉ quản lý, không chấm công; Admin cấp tài khoản User, không đăng ký công khai.
- Office cần GPS/Geofence, Remote/nghỉ cần lý do. Check-out không lấy GPS.
- Ngày làm việc theo giờ Việt Nam; mốc tự đóng 20:00 cố định.
- GPS giữ 30 ngày; chỉ lưu vị trí khi bắt đầu Office, không theo dõi liên tục.
- Chọn FastAPI phục vụ trang và API cùng nguồn; PostgreSQL/PostGIS, cookie session, Argon2id, Psycopg, migration SQL và maintenance độc lập.
- Tách trạng thái ngày, phiên làm việc, sự kiện, vị trí và mã yêu cầu để hỗ trợ lịch sử, retention và gửi lại an toàn.

## Đầu ra

[BRD](../REQUIREMENTS.md), [quy tắc tài khoản](../ACCOUNT_RULES.md), [bảng trạng thái](../STATE_TRANSITIONS.md), thiết kế dữ liệu/API/UI và lộ trình Phase 1–6.

## Những điều chỉnh sau thiết kế

Thiết kế ban đầu cho bắt đầu lại sau Check-out, hủy nghỉ cả ngày và chưa có quyền xóa lịch sử. Quy tắc hiện hành đã thay thế: Check-out/nghỉ cả ngày khóa ngày; Admin được xóa ngày theo điều kiện. Các thay đổi được tổng hợp trong [features](../features/README.md); không triển khai lại nghiệp vụ cũ.

## Kiểm chứng và chuyển tiếp

Phase 0 được nghiệm thu bằng quyết định thiết kế, không phải kết quả chạy phần mềm. [Phase 1](PHASE_1_NEN_TANG_DATABASE_VA_TAI_KHOAN.md) triển khai nền tảng và tài khoản từ thiết kế này.

Nguồn lịch sử: [thiết kế MVP đầy đủ](../archive/superpowers/specs/2026-10-14-geoattend-mvp-design.md).
