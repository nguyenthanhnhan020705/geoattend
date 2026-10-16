# Phase 6 — Ma trận nghiệm thu

Ngày bắt đầu 16/10/2026; baseline Git `8d96052`. Đây là ma trận bằng chứng, không phải chứng nhận production. Hợp đồng mới nhất: LEAVE_FLOW_VERIFICATION → EARLY_CHECKOUT_VERIFICATION → handoff mục 3; mô tả cũ cho bắt đầu lại/hủy nghỉ cả ngày đã bị thay thế.

Môi trường **L**: PostgreSQL 17/PostGIS riêng, pytest API/database và Edge headless, clock/GPS điều khiển. **T**: HTTPS đích được duyệt, điện thoại/máy tính thật. **P**: khoảng 10 User, 5 ngày làm việc. Cột bằng chứng nêu file trong `tests/integration/` trừ khi có chỉ dẫn khác. Kết quả chạy mới và lỗi ở [báo cáo](PHASE_6_VERIFICATION.md); bằng chứng Phase 0–5 giữ trong báo cáo cũ.

| ID | Tiêu chí đạt hiện hành | Bằng chứng tự động hiện có | Khoảng trống / môi trường nghiệm thu |
| --- | --- | --- | --- |
| AC-01 | Login đúng quyền; User chỉ trạng thái/lịch sử mình; Admin không chấm công | test_auth_sessions.py, test_auth_races.py, test_attendance.py, test_admin_history.py, ../test_pages.py | L chạy mới; T đăng nhập/session/logout thực |
| AC-02 | ST_Covers trong/trên biên; ngoài/hole bị từ chối; accuracy lớn không chặn; GPS lỗi giữ trạng thái | test_office_attendance.py, test_office.py, test_office_browser.py, test_phase4_browser.py | L GIS thật, GPS giả; T GPS/permission/HTTPS thật, không suy rộng mô phỏng |
| AC-03 | Remote cần lý do, không GPS/phê duyệt; Admin đọc lý do | test_attendance.py, test_attendance_browser.py, test_admin_dashboard.py | L + T Remote khi từ chối quyền vị trí |
| AC-04 | Lunch đóng phiên, resume tạo phiên mới; Office lấy GPS lại, Remote có lý do | test_attendance_breaks.py, test_phase4_browser.py, test_daily_action_ui.py | L + T bốn tổ hợp Office/Remote |
| AC-05 | Chọn loại nghỉ trước lý do; không GPS; nghỉ sáng resume trước 20:00 không chờ giờ chiều | test_attendance_leave.py, test_leave_day_flow.py | L + T chọn buổi/lý do, reload |
| AC-06 | Checkout không GPS, lưu giờ/lý do đầu ca, không đánh giá hiệu suất | test_daily_action_ui.py, test_office_browser.py, test_attendance.py | L + T ngoài vùng/deny GPS vẫn Checkout |
| AC-07 | Bảy nhóm khớp tổng/danh sách USER gồm inactive/chưa bắt đầu; loại Admin | test_admin_dashboard.py, test_admin_dashboard_browser.py | L + T đối soát User thật; refresh 30 giây |
| AC-08 | Onsite đúng phiên mở đã xác minh; Popup/tên, rời Office bỏ Marker | test_admin_onsite.py, test_admin_dashboard_browser.py, test_admin_dashboard_refresh.py | L + T bản đồ/WebGL/nguồn tile và bfcache đa browser |
| AC-09 | Admin lưu Polygon hợp lệ, revision chặn ghi đè | test_office.py, test_office_map_recovery.py | L + T Polygon văn phòng được owner xác nhận |
| AC-10 | Điện thoại/máy tính dùng được; không GPS ngoài Office/không tracking/storage GPS | test_user_mobile_layout.py, test_office_browser.py, test_phase4_browser.py | L viewport 360/1280 chỉ mô phỏng; T checklist thiết bị bắt buộc |
| AC-11 | Đúng 20:00 Việt Nam đóng một lần SYSTEM; lunch không kéo dài phiên; cấm bắt đầu/resume/switch kể cả NOT_STARTED; ngày mới mở | test_attendance_time.py, test_attendance_races.py, test_phase4_regression.py, test_admin_dashboard.py | L clock/lock qua cutoff; T worker độc lập chạy qua cutoff/ngày mới |
| AC-12 | Mọi Checkout khóa ngày; ngày mới mở, UUID cũ replay; Admin reset/tombstone giữ | test_daily_action_ui.py, test_admin_history.py | L + T mất phản hồi/reload/retry; không tạo phiên trùng |
| AC-13 | Full-day khóa ngày, không hủy; morning resume chỉ Checkout cuối ngày UI; legacy replay vẫn đúng | test_leave_day_flow.py, test_attendance_leave.py | L + T ngày mới/reload, không phục hồi nghiệp vụ cũ |
| AC-14 | API switch nguyên tử: xác minh trước đóng/tạo; lỗi rollback, khóa 20:00 | test_attendance_switch.py, test_phase4_regression.py | L kiểm tra API tương thích; UI không có nút switch trực tiếp |
| AC-15 | Admin sửa tên/địa chỉ/Polygon; User cấm; timezone/cutoff cố định | test_office.py, test_office_map_recovery.py | L + T cấu hình Geofence thực, không đổi giờ |
| AC-16 | Che GPS đúng 30 ngày dù chưa purge; purge tọa độ/accuracy, giữ phiên/xác minh; restore purge trước mở | test_location_retention.py, test_admin_onsite.py, test_admin_history.py | L thêm diễn tập pg_dump/pg_restore; T worker/backup policy được owner nhận |
| AC-17 | Admin cấp USER duy nhất username; không public signup/Google/role escalation; chỉ một Admin | test_accounts.py, test_bootstrap.py, test_constraints.py, test_browser.py | L + T quy trình cấp mật khẩu ngoài app an toàn |
| AC-18 | Mật khẩu cấp dùng ngay; đổi chủ động thu hồi session, giữ role | test_accounts.py, test_auth_sessions.py, test_auth_races.py, test_browser.py | L + T đăng nhập lại browser thật |
| AC-19 | Admin reset User, giữ role/lịch sử, thu hồi session; User/khách không reset người khác | test_accounts.py, test_auth_races.py, test_browser.py | L + T bàn giao mật khẩu/reset thực theo quyền |
| NFR-01 | Luồng đơn giản, chỉ dữ liệu cần thiết; dùng được điện thoại/máy tính | test_user_mobile_layout.py, test_daily_action_ui.py, test_leave_day_flow.py | T thiết bị thật + P phản hồi sử dụng |
| NFR-02 | GPS chỉ vào Office, 30 ngày, không log/storage; backup có vòng đời, restore không tái lộ | test_location_retention.py, test_phase4_browser.py, test_admin_onsite.py | L rà log/restore; T cấu hình log/backups; owner dữ liệu xác nhận |
| NFR-03 | Quyền User/Admin đúng, lịch sử minh bạch; không lộ dữ liệu người khác | test_auth_races.py, test_admin_history.py, test_admin_dashboard.py | L + T same-origin/CSRF/cookie Secure/DB privilege |
| NFR-04 | ≥95% API backend ≤2000ms từ nhận request tới body cuối; không tính GPS/mạng client; báo cả lỗi | Chưa có phép đo baseline Phase 0–5; Task 3 bổ sung harness và báo cáo | L số đo chỉ local; T đo cấu hình đích; P đo 5 ngày, lỗi báo riêng không loại khỏi mẫu |
| NFR-05 | Đánh giá GPS/GIS/DB ổn định; accuracy thống kê, không chặn | test_office_attendance.py, test_attendance_races.py, test_phase4_regression.py | L đồng thời/rollback; T GPS thật/DB reconnect; P thống kê thành công/từ chối/timeout và phản hồi |

## Các cổng nghiệm thu

1. Local: full suite mới, pip check/diff check; không lỗi mất dữ liệu/trùng phiên/sai quyền. Mọi lỗi mới phải có phân tích nguyên nhân và kiểm thử hồi quy.
2. Vận hành: backup/restore cô lập kiểm chứng; secret/DB role/log/worker/HTTPS có cấu hình và chủ chịu trách nhiệm; chưa suy ra hạ tầng thật đã được cấu hình.
3. Đích thật: HTTPS/GPS, bộ thiết bị, đo backend đích và rollback rehearsal được cho phép cụ thể và ghi kết quả.
4. Pilot: khoảng 10 User đủ 5 ngày làm việc, AC đạt, NFR-04 đạt, không còn lỗi gây mất dữ liệu/trùng phiên/sai phân quyền. Chưa qua đủ cổng thì Phase 6 vẫn mở.
