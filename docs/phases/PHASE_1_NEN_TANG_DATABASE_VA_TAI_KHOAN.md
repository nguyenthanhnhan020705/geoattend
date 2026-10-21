# Phase 1 — Nền tảng, database và tài khoản

**Trạng thái:** đã triển khai. Phụ thuộc [Phase 0](PHASE_0_PHAN_TICH_NGHIEP_VU_VA_THIET_KE.md). Phạm vi chính: FR-01, FR-16–18; AC-01 phần xác thực và AC-17–19.

## Mục tiêu

Chạy được FastAPI cùng giao diện, kết nối PostGIS, khởi tạo một Admin và hoàn chỉnh luồng cấp/đăng nhập/đổi/đặt lại mật khẩu User.

## Phân tích và triển khai

- Cấu hình môi trường, connection pool, health API, trang đăng nhập và trang được bảo vệ theo vai trò.
- Migration SQL có checksum và khóa khi chạy; runtime role tách migration role. Nền tảng schema chấm công được tạo sẵn để dùng ở phase sau.
- Username chuẩn hóa và duy nhất; mật khẩu Argon2id; database chỉ cho một Admin.
- Phiên đăng nhập 12 giờ, token ngẫu nhiên chỉ lưu hash, cookie HttpOnly/SameSite và Secure khi HTTPS.
- Kiểm tra CSRF/Origin cho thao tác ghi; giới hạn thử sai dùng dữ liệu chung tại database.
- Đổi/reset mật khẩu thu hồi toàn bộ phiên của tài khoản; khóa profile ngăn login đồng thời giữ phiên dựa trên mật khẩu cũ.
- Admin cấp User, reset mật khẩu; User dùng ngay mật khẩu được cấp, có thể tự đổi sau.

## Mã nguồn và dữ liệu

`app/main.py`, `app/config.py`, `app/db/`, `app/auth/`, `app/accounts/`, các trang tài khoản và `scripts/bootstrap_admin.py`, `scripts/recover_admin.py`, `scripts/migrate.py`. Migration nền tảng: `001_identity.sql`, `002_attendance.sql`; các migration sau là phần bổ sung.

API xác thực dưới prefix `/api/auth` gồm `/login`, `/me`, `/logout`, `/change-password`; quản lý User tại `/api/admin/users` và reset-password theo User. Chi tiết quy tắc tại [ACCOUNT_RULES](../ACCOUNT_RULES.md).

## Kiểm chứng

Các nhóm test xác thực/tài khoản, migration, constraints, bootstrap, race và browser kiểm tra quyền, session hết hạn/thu hồi, CSRF, trùng username và giữ lịch sử khi đổi mật khẩu. Báo cáo lịch sử: [PHASE_1_VERIFICATION](../archive/PHASE_1_VERIFICATION.md); kế hoạch: [Phase 1](../archive/superpowers/plans/2026-10-14-phase-1-foundation-auth.md).

## Đầu ra và bước tiếp

Admin cấp User → User đăng nhập → đổi/reset mật khẩu → đăng nhập lại. Chấm công Remote được triển khai ở [Phase 2](PHASE_2_REMOTE_PHIEN_LAM_VIEC_VA_LICH_SU.md). Cách thiết lập trên máy mới tại [DEVELOPMENT](../DEVELOPMENT.md).
