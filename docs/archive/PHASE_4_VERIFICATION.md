> **Tài liệu lưu trữ:** nội dung và số liệu bên dưới phản ánh thời điểm lập tài liệu. Các hướng dẫn/quy tắc cũ có thể đã được thay thế; xem [tài liệu hiện hành](../README.md) trước khi thực hiện.

# GeoAttend — Kiểm chứng Phase 4

Ngày: 15/10/2026. Phạm vi: nghỉ trưa/tiếp tục, nghỉ sáng/cả ngày, hủy nghỉ kết hợp bắt đầu và chuyển Office ↔ Remote; API, UI, lịch sử và worker hiện có. Làm trong `.worktrees/phase-1`, branch `feat/phase-1-foundation-auth`, từ bàn giao `e52d2dd`. Không triển khai lại Phase 3.

**Kết quả:** Phase 4 hoàn thành 5 task, toàn suite 195/195 đạt, review độc lập không có lỗi chặn. Một Minor về thứ tự hiển thị event trùng timestamp được hoãn và ghi rõ bên dưới.

## Bằng chứng theo task

- Baseline mới chạy: **122 passed**, 1 warning upstream Starlette/httpx, 132.69 giây.
- Task 1 (`b0722d1`): 10 ca RED do thiếu action nghỉ trưa; GREEN 22 test breaks/races. Bốn tổ hợp Office/Remote trước/sau nghỉ, đóng đúng phiên, xác minh GPS/lý do lại, rollback event, maintenance trước/đúng/sau cutoff/chạy bù và chờ profile lock qua cutoff/ngày mới.
- Task 2 (`11cc860`): 18 ca RED do thiếu action nghỉ/hủy; GREEN 18 test leave. Reason trim, thiếu/thừa/GPS, trạng thái bị cấm, bắt đầu sau nghỉ sáng ngay buổi sáng, hủy nghỉ nguyên tử, lịch sử đăng ký/hủy, rollback và hai request cùng revision, chờ khóa qua cutoff/ngày mới/logout/reset/khóa tài khoản. Một lỗi fixture test thiếu `dict_row` đã sửa; không phải lỗi production.
- Task 3 (`47912ed`): RED thiếu switch; GREEN 31 test switch/Office. Hai chiều, cùng chế độ bị từ chối, lỗi GPS/lý do giữ nguồn, rollback GPS/event/replay, cùng/khác UUID, switch vs Check-out/worker, chờ khóa Office qua cutoff/ngày mới/logout. Hash START_REMOTE/START_OFFICE cũ và replay ngày sau được kiểm tra; expectation accuracy trong test hash chuẩn hóa float theo hợp đồng cũ.
- Task 4 (`b20e0d9`): RED thiếu nút nghỉ; GREEN **8 browser test**, chạy lại 28.04 giây. Edge headless 360px/desktop, timeline tiếng Việt, HTML lý do dạng text, nghỉ/hủy/switch/resume, GPS permission/retry, không GPS trong storage, timeout mở retry và reload giữ UUID không GPS, nhãn kết thúc ngày SYSTEM. Ảnh test: `.local-tests/phase-4/artifacts/timeline-desktop.png`.
- Task 5: **18 test regression đạt**, bao phủ bảng chuyển trạng thái bị cấm, allowed_actions, mốc 19:59/20:00/20:01, replay nghỉ trưa qua ngày và luồng Phase 4 bằng database runtime role hạn chế.

## Toàn suite và review

Toàn suite: **195 passed, 1 warning**, 227.76 giây trên PostgreSQL 17/PostGIS test riêng và Edge headless. `pip check`: không lỗi phụ thuộc. `git diff --check`: không lỗi whitespace. Warning có sẵn của Starlette TestClient/httpx; không thay dependency ngoài phạm vi.

Review độc lập đọc toàn bộ thay đổi Phase 4 và các trọng điểm bàn giao. Không phát hiện Critical/Important. Một Minor được hoãn: `history` sắp sự kiện trùng cả `event_time`/`recorded_at` theo UUID; hai event cùng thao tác có thể hiển thị đảo thứ tự (bắt đầu trước kết thúc hoặc trước hủy nghỉ). Thời gian, trạng thái, phiên và thứ tự event IDs của replay vẫn đúng; cần thứ tự hiển thị ổn định hơn ở đợt chỉnh timeline tiếp theo.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.local-tests/phase-4/full-review -o cache_dir=.local-tests/phase-4/cache
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Database PostgreSQL 17/PostGIS local test tại loopback port 55440; fixture tạo rồi dọn `geoattend_test_<uuid>`. Không nạp `.env` ứng dụng vào test, không tạo dữ liệu thử trên Supabase thật. Log RED/GREEN được giữ tại `.local-tests/phase-4/`, không commit dữ liệu/bí mật môi trường.

## Đối chiếu nghiệm thu

| Yêu cầu | Bằng chứng |
| --- | --- |
| Office/Remote cả ngày và hai luồng hỗn hợp sau nghỉ | `test_lunch_closes_session_and_resume_creates_new` (4 tổ hợp), browser timeline. |
| Nghỉ sáng → Office/Remote, không khóa giờ chiều | `test_leave_then_start_and_cancel_atomic`, clock 09:00 Việt Nam. |
| Nghỉ cả ngày không phiên/GPS, hủy giữ lịch sử | `test_leave_reason_input_history_and_cutoff`, `test_leave_then_start_and_cancel_atomic`, browser leave. |
| Làm một phần ngày, bắt đầu lại | Hồi quy `test_remote_checkout_restart_persisted`, `test_office_replay_checkout_and_new_verification`. |
| Hai chiều switch, nguồn giữ nguyên khi thất bại | `test_switch_closes_and_opens_atomically`, validation/rollback/races. |
| Cutoff, đối soát nghỉ trưa, UUID cũ | Breaks/races, Phase 4 regression, old-payload hash tests. |
| Quyền/GIS/retention/auth hồi quy | Toàn suite Phase 1–4, không làm lại triển khai Phase 3. |

## Quyết định và giới hạn

- Dùng PowerShell/Python ledger thay Bash helpers không có trên máy; bằng chứng giữ trong log và Git, chi phí là theo dõi thủ công.
- Action nghỉ dùng `MORNING_LEAVE`/`FULL_DAY_LEAVE` theo kế hoạch Phase 4 trong handoff; thiết kế Phase 0 dùng tên đề xuất `LEAVE_MORNING`/`LEAVE_FULL_DAY`. Không thêm alias chưa từng phát hành; client mới dùng tên trong OpenAPI. Nghiệp vụ không đổi.
- Không cần migration mới: schema/event/replay/quyền đã đủ; có test runtime role hạn chế. Không sửa migration cũ hay áp dụng dữ liệu trên Supabase thật.
- Giữ nguyên branch/worktree theo bàn giao; không merge/push/deploy. Checklist tay tại [MANUAL_TEST_PHASE_4](MANUAL_TEST_PHASE_4.md) dành cho môi trường test riêng, chưa tuyên bố đã chạy trên điện thoại thật.
- GPS test giả lập; HTTPS/thiết bị thật/hiệu năng/pilot/backup production thuộc Phase 6. Dashboard/Onsite/thống kê Admin thuộc Phase 5; Phase 4 đã giữ trạng thái thực cùng lịch sử đăng ký/hủy để Phase 5 dùng đúng.
- Các phần reviewer chưa đánh giá được giữ đúng phạm vi đã duyệt: thống kê/Marker/lịch sử Admin cần nghiệm thu khi làm Phase 5; GPS thiết bị thật và vận hành production cần kiểm chứng Phase 6. Chi phí nếu giả định sai: chưa thể coi dữ liệu/UI Phase 5 hoặc khả năng vận hành production là đã nghiệm thu.
