# Phase 2 — Remote, phiên làm việc và lịch sử

**Trạng thái:** đã triển khai. Phụ thuộc [Phase 1](PHASE_1_NEN_TANG_DATABASE_VA_TAI_KHOAN.md). Phạm vi chính: FR-03, FR-08 phần Remote, FR-09 và FR-10 phần cá nhân.

## Mục tiêu

Hoàn thành luồng User bắt đầu Remote có lý do → kết thúc phiên → xem lịch sử, đồng thời bảo đảm dữ liệu không trùng khi thao tác đồng thời hoặc gửi lại.

## Phân tích và triển khai

- Trạng thái theo User/ngày Việt Nam; ngày mới chưa thao tác là `NOT_STARTED`.
- Ghi phiên, sự kiện, trạng thái và kết quả yêu cầu trong một transaction; khóa profile trước ngày/phiên.
- `request_id` chống ghi trùng, `expected_revision` chặn màn hình cũ, `expected_work_date` chặn yêu cầu cũ chạy sang ngày mới.
- Remote yêu cầu lý do, không GPS. Lịch sử chỉ đọc dữ liệu bản thân, có lọc ngày và phân trang.
- Maintenance độc lập đối soát lúc 20:00; đọc/thao tác API cũng xử lý bù ngày quá hạn. Ghi riêng giờ nghiệp vụ và giờ thực thi khi worker chạy trễ.
- Kiểm tra lại thời gian sau khi chờ khóa; không dùng đồng hồ thiết bị để vượt cutoff.
- UI giữ pending không GPS để gửi lại cùng mã khi chưa rõ kết quả; dữ liệu tồn tại sau reload.

## Mã nguồn và dữ liệu

`app/attendance/`, `app/static/js/user.js`, `scripts/maintenance.py`, `scripts/local_run.py`. Các bảng `attendance_days`, `work_sessions`, `attendance_events`, `attendance_requests`; migration `003_attendance_replay.sql` bổ sung kết quả replay không chứa GPS.

API: `GET /api/attendance/status`, `POST /api/attendance/actions`, `GET /api/attendance/history`.

## Điều chỉnh hiện hành

Quyền bắt đầu lại sau Check-out của phase ban đầu đã bị thay thế: mọi Check-out hiện khóa ngày. Check-out ca đầu cần lý do; xem [luồng User bổ sung](../features/USER_FLOW.md). Replay UUID đã commit vẫn được giữ.

## Kiểm chứng và đầu ra

Test kiểm tra lý do, quyền, rollback, gửi trùng, hai request cạnh tranh, chờ khóa qua 20:00/ngày mới và worker chạy lại. Báo cáo lịch sử ghi mốc **85 test đạt của toàn suite**, không phải 85 test riêng Phase 2: [PHASE_2_VERIFICATION](../archive/PHASE_2_VERIFICATION.md).

[Kế hoạch Phase 2](../archive/superpowers/plans/2026-10-14-phase-2-remote-attendance.md) giữ chi tiết triển khai cũ. [Phase 3](PHASE_3_OFFICE_GEOFENCE_VA_GPS.md) mở rộng cùng cơ chế phiên sang Office có GIS.
