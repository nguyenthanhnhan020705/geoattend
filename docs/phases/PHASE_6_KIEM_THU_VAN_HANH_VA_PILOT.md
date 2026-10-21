# Phase 6 — Kiểm thử tổng thể, vận hành và pilot

**Trạng thái:** đã hoàn thành phần local/chuẩn bị, chưa hoàn tất toàn phase. Phụ thuộc Phase 0–5 và các bổ sung đã triển khai. Phạm vi: AC-01–19 và NFR-01–05 theo quy tắc hiện hành.

## Mục tiêu

Chứng minh ứng dụng đáp ứng các luồng chính và yêu cầu vận hành, sau đó triển khai HTTPS và nghiệm thu bằng thiết bị/người dùng thật.

## Phần đã thực hiện

| Hạng mục | Kết quả đã ghi nhận |
| --- | --- |
| Hồi quy local | 290 test đạt, một cảnh báo thư viện; bao gồm API/PostGIS/race/browser |
| Dashboard | Khôi phục refresh khi quay lại từ cache; tối ưu truy vấn dưới khóa profile |
| Đo tải | Lượt cuối 3.651 request/đủ mẫu, 0 lỗi, 100% ≤2 giây trên local; p95 ở concurrency 20 là 606,620 ms |
| Log/timing | Đo đến body cuối, xử lý cả lỗi 500; kiểm tra log không chứa giá trị nhạy cảm, bao gồm proxy lỗi upstream |
| Restore | Diễn tập backup/restore trên DB test riêng, retention GPS, thu hồi session và đối soát lịch sử bị xóa sau backup |
| Vận hành | Có mẫu Caddy/systemd/logging, runbook backup/restore/rollback và checklist thiết bị/pilot |

Thời gian nghiệp vụ và GPS trong kiểm thử được kiểm soát. Số đo local không chứng minh hiệu năng trên máy chủ đích. Kết quả chạy lại trước push ngày 17/10/2026 cũng đạt 290 test; lần biên soạn tài liệu này không chạy lại ứng dụng.

## Phần còn lại và điều kiện hoàn thành

1. Chốt host/domain/database, người vận hành và cấu hình triển khai cụ thể.
2. Triển khai HTTPS cùng nguồn, web/worker độc lập, quyền database, log/giám sát và backup thực tế.
3. Kiểm tra Android/iPhone và máy tính với GPS, Geofence, quyền vị trí, mạng yếu, browser cache, cutoff/ngày mới trên môi trường đích.
4. Đo yêu cầu ≥95% API backend hoàn tất trong ≤2 giây trên cấu hình đích, báo cả request chậm và lỗi.
5. Pilot khoảng 10 User trong 5 ngày làm việc; tổng hợp phản hồi, sửa lỗi cản trở và nghiệm thu AC/NFR.

Chỉ hoàn tất khi có bằng chứng cho các bước trên, không còn lỗi mất dữ liệu/trùng phiên/sai quyền và người vận hành tiếp nhận quy trình. Timeline trùng timestamp có thể sắp UUID khác thứ tự nhân quả; giới hạn trình bày này đang được ghi nhận, chưa sửa.

## Mã nguồn liên quan

`app/telemetry.py`, phần snapshot trong `app/admin/service.py`, lifecycle `admin-dashboard.js`, `scripts/phase6_load.py`, `scripts/phase6_restore_drill.py`, `deploy/` và các test Phase 6. Phase 6 không thêm migration hoặc dependency mới.

## Tài liệu chi tiết

- [Ma trận nghiệm thu](../PHASE_6_ACCEPTANCE.md): đối chiếu từng AC/NFR.
- [Báo cáo kiểm chứng](../PHASE_6_VERIFICATION.md): kết quả, các lần sửa và giới hạn.
- [Hiệu năng](../PHASE_6_PERFORMANCE.md): phương pháp, số đo và lệnh chạy.
- [Vận hành](../PHASE_6_OPERATIONS.md): HTTPS, log, backup, restore và rollback.
- [Pilot](../PHASE_6_PILOT.md): điều kiện triển khai, thiết bị, mẫu ghi kết quả và kế hoạch 5 ngày.
- [Bằng chứng JSON](../evidence/phase6/): số liệu đã khử thông tin nhạy cảm.

Đây là phần việc tiếp theo của MVP. Các chức năng sau MVP được tách ở [hướng phát triển](../FUTURE_DEVELOPMENT.md).
