# Kiểm tra trước khi đưa lên main — 21/10/2026

## Phạm vi

Tích hợp lịch sử phát triển và các thay đổi local vào `main`: chấm công/GIS, tài khoản, Dashboard, báo cáo tuần PDF, xuất Excel, giao diện, migration, công cụ vận hành và tài liệu. Không đưa `.env`, virtualenv, database, backup hoặc artifact local lên GitHub. Chưa triển khai lên máy chủ thật.

## Kết quả xác minh

- Chạy toàn bộ 335 test trên PostgreSQL 17/PostGIS local riêng, Edge headless và Caddy thật: **333 passed, 2 failed, 1 warning**, 446,51 giây. Hai lỗi thuộc cùng ca restore có hai chính sách backup: dữ liệu ngày tạo tài khoản/kích hoạt báo cáo lấy ngày thật trong khi clock nghiệp vụ cố định 14/10/2026.
- Sửa riêng dữ liệu của ca restore: cố định `profiles.created_at` và `schema_migrations.applied_at` trong database test theo clock nghiệp vụ. Không sửa logic production, migration hoặc bỏ assertion.
- Chạy lại toàn bộ `tests/integration/test_phase6_restore.py` sau sửa: **3 passed, 1 warning**, 11,65 giây. Ca này xác minh cả PDF, checksum migration, dữ liệu GPS hết hạn, tombstone, thu hồi phiên và quyền runtime sau restore.
- `python -m pip check`: **No broken requirements found**. `git diff --check` đạt.
- Cảnh báo hiện có: Starlette deprecation về `httpx` trong TestClient.

Kết quả bao phủ 335 ca qua lượt toàn bộ và lượt chạy lại nhóm restore; chưa chạy lại một lượt toàn bộ sau sửa dữ liệu test. Database ứng dụng không được migrate hoặc tạo dữ liệu thử trong lần kiểm tra này.

## Trước khi deploy

Thực hiện [runbook vận hành](PHASE_6_OPERATIONS.md), cấu hình bí mật ngoài Git, domain/HTTPS, migration (gồm 005), quyền runtime, web và maintenance. Kiểm tra thiết bị/GPS thật, backup/restore trên môi trường đích và [pilot](PHASE_6_PILOT.md) còn cần thực hiện. GitHub Pages không chạy backend Python của ứng dụng.
