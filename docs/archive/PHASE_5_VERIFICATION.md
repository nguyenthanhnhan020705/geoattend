> **Tài liệu lưu trữ:** nội dung và số liệu bên dưới phản ánh thời điểm lập tài liệu. Các hướng dẫn/quy tắc cũ có thể đã được thay thế; xem [tài liệu hiện hành](../README.md) trước khi thực hiện.

# GeoAttend — Kiểm chứng Phase 5

Điều chỉnh Xin nghỉ tiếp theo và kết quả mới: [LEAVE_FLOW_VERIFICATION](LEAVE_FLOW_VERIFICATION.md). Nghỉ sáng tiếp tục ca chiều với CHECK-OUT cuối ngày; nghỉ cả ngày kết thúc ngày. Phạm vi Dashboard/Onsite không đổi.

Điều chỉnh sau nghiệm thu 16/10/2026: người dùng yêu cầu CHECK-OUT SỚM có lý do bắt buộc và kết thúc ngày, không Check-in lại. Báo cáo/kiểm chứng mới ở [EARLY_CHECKOUT_VERIFICATION](EARLY_CHECKOUT_VERIFICATION.md). Các kết quả Phase 5 dưới đây là bằng chứng lịch sử trước điều chỉnh này.

Ngày: 16/10/2026, giờ Việt Nam. Worktree `.worktrees/phase-1`, branch `feat/phase-1-foundation-auth`; bắt đầu từ baseline thực tế `8dd1af2`. Không reset hoặc triển khai lại Phase 0–4.

## Phạm vi

Dashboard `/admin/dashboard`, API `GET /api/admin/dashboard` và `GET /api/admin/onsite`. Dùng lại dialog lịch sử/xóa ngày và editor tên/địa chỉ/Geofence; không thêm migration hoặc phụ thuộc. Login Admin vẫn đến `/admin/users`, có liên kết Dashboard ở trang nhân viên/văn phòng. UI User và API ghi chấm công giữ nguyên.

Snapshot khóa profile Admin và toàn bộ User theo UUID trước day/session; chọn `as_of` và kiểm tra lại session sau khi có khóa. Dùng `reconcile_locked` trước đọc ngày hiện tại, gồm tài khoản bị khóa. Số lượng chứa đủ bảy trạng thái kể cả 0, tổng khớp danh sách và không tính Admin. Onsite chỉ dùng `WORKING_OFFICE` với phiên Office mở tương ứng có `WORK_START.location_verified`; gọi lại bộ đọc GPS có retention hiện hữu, không lưu bản sao GPS.

Dashboard trả `as_of`, `work_date`, `total_users`, `counts`, `items`, `onsite`, `office`. Employee có `id`, `username`, `full_name`, `is_active`, `status`, `open_session` (`id`, `work_mode`, `start_time`, `start_reason` hoặc null). Onsite thêm `location_verified`, `location`; `available` có tọa độ/accuracy, `expired` chỉ có `status`/`expires_at`, thiếu vị trí trả null. Endpoint Onsite là projection `as_of`, `work_date`, `items`, `office` của cùng builder. Schema nằm ở `app/admin/schemas.py` và được kiểm chứng qua API/database thật.

## RED → GREEN theo task

| Task | RED đã quan sát | GREEN đã chạy | Commit |
| --- | --- | --- | --- |
| 1 — Snapshot | 7 failed vì endpoint chưa có | 10 passed, 1 warning, 45.35s | `ae5765d` |
| 2 — Onsite | 7 failed vì endpoint chưa có | 17 passed, 1 warning, 97.93s | `39339f6` |
| 3 — Dashboard/map | 3 failed vì thiếu trang/điều hướng | 13 passed, 1 warning, 87.72s, gồm Office browser/UI User | `2f339d3` |
| 4 — Refresh/hồi quy | 3 failed: polling, phản hồi cũ/nhãn cũ, 403; 401 đã đạt nhờ code chung | 4 passed cho refresh; 63 passed hồi quy Admin/Office/UI User; lượt bổ sung cuối 28 passed, 1 warning, 49.26s | `4c80dbc` |

Lệnh task chính: `python -m pytest tests/integration/test_admin_dashboard.py -q`; sau đó thêm `test_admin_onsite.py`; browser Task 3 thêm `test_admin_dashboard_browser.py`, `test_user_mobile_layout.py`, `test_daily_action_ui.py`; Task 4 thêm `test_admin_dashboard_refresh.py`, các test lịch sử Admin/văn phòng sẵn có. Tất cả dùng `.venv` và DSN test riêng bên dưới. Log ở `.local-tests/phase-5/`, không commit.

Các hồi quy bổ sung gồm nghỉ trưa trước/đúng/sau cutoff/ngày mới, User bị khóa/chưa có ngày, hủy nghỉ/xóa hôm nay, action/xóa song song và session bị thu hồi khi chờ khóa; GPS đúng 30 ngày chưa purge, tiếp tục Office lấy điểm mới, thiếu vị trí, PostGIS ở schema `extensions`, sửa Geofence giữ điểm gốc. Browser kiểm tra 360px/1280px, tên/lý do HTML chỉ là text, Popup → lịch sử → văn phòng/nhân viên, map lỗi vẫn dùng danh sách/lịch sử, expiry/Check-out xóa Marker, timer 30 giây/ẩn tab/quay lại/manual, không gọi GPS, timeout/503 giữ snapshot, phản hồi đảo thứ tự và 401/403.

Baseline đầu phiên có **217 passed, 1 failed** (`test_admin_map_and_user_gps_flow`: trang văn phòng còn “Đang tải…”), 717.94s. Không sửa/nới test cũ; ca đó đạt ở lượt riêng và nhóm hồi quy 63 test. Một lệnh chờ trong test Playwright mới bị CSP chặn eval đã đổi sang assertion thuộc tính DOM tương đương; CSP không được nới. Lần full-01 bị daemon restart ngắt trước khi có kết quả, không dùng làm bằng chứng.

## Xác minh cuối

Lượt **full-02** kết thúc 16/10/2026 khoảng 09:10 giờ Việt Nam: **249 passed, 1 warning**, 406.93s (6 phút 46 giây), gồm toàn bộ 218 ca cũ và 31 ca mới. Cảnh báo deprecation Starlette/httpx có sẵn; không sửa phụ thuộc để che cảnh báo. Không bỏ hoặc nới test cũ.

Review độc lập toàn phạm vi `8dd1af2..4c80dbc` không có Critical/Important. Hai nhận xét Minor: dòng trắng cuối hai file được làm sạch để đáp ứng kiểm tra diff; lifecycle khi tài liệu thật sự được khôi phục từ back/forward cache được ghi nhận bên dưới. Chưa có lỗi có mức chặn bàn giao.

Kiểm tra cuối sau hoàn thiện tài liệu: `pip check` trả **No broken requirements found**; `git diff --check` và `git diff 8dd1af2 --check` đều không có lỗi whitespace. Chỉ có nhắc nhở Git chuyển LF → CRLF theo cấu hình Windows. Diff từ baseline không thay migration, lockfile hoặc test cũ; bốn file test Phase 5 đều là file mới. Các sửa đổi README/handoff có sẵn trước khi bắt đầu được giữ lại và cập nhật tiếp theo phạm vi bàn giao.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.local-tests/phase-5/full-02 -o cache_dir=.local-tests/phase-5/cache
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Cluster test PostgreSQL 17/PostGIS đã có ở `.local-tests/phase-3/pgdata`, được khởi động lại tại loopback port 55440; không initdb hoặc xóa cluster. Fixture chỉ tạo/drop database `geoattend_test_<uuid>` riêng. Không đọc/in bí mật `.env`, không tạo/xóa dữ liệu thử hoặc chạy migration trên Supabase thật.

## Đối chiếu tiêu chí

| Hợp đồng | Bằng chứng |
| --- | --- |
| AC-01 Admin, AC-07 | Quyền API/trang, loại Admin, User chưa bắt đầu/inactive, bảy nhóm, tổng/danh sách; test Dashboard |
| AC-08 | Phiên Office đang mở đã xác minh, Marker/Popup/tên, rời Onsite; API/browser Onsite/Dashboard |
| AC-15 / FR-15 | Tái sử dụng editor hiện có và hồi quy văn phòng; tên/địa chỉ/Polygon/revision, User không sửa, không đổi cutoff/múi giờ |
| AC-16 | `get_location` che GPS đủ 30 ngày trước purge; expired không có tọa độ/accuracy, không Marker giả; xác minh giữ nguyên |
| Hợp đồng mục 3 bàn giao | Không đổi action/replay/hash/tombstone, migration, UI User/khóa cuối ngày; full suite hồi quy Phase 0–4 |

Ảnh browser đã xem: `.local-tests/phase-5/artifacts/dashboard-360.png` và `dashboard-1280.png`. Checklist và cách chạy browser: [MANUAL_TEST_PHASE_5](MANUAL_TEST_PHASE_5.md).

## Chạy ứng dụng và giới hạn

Không có migration mới. Restart web hiện có rồi Ctrl+F5; mở `/login`, đăng nhập Admin và chọn **Dashboard**, hoặc mở `/admin/dashboard`. Launcher hiện hữu: `.\.venv\Scripts\python.exe -m scripts.local_run serve`; maintenance ở terminal riêng bằng `-m scripts.local_run maintenance`. Không tạo dữ liệu thử trên database mà launcher đọc từ `.env` ứng dụng.

Chưa chạy pilot, HTTPS/điện thoại thật, đo GPS thực hoặc đo mục tiêu 95% API ≤2 giây; thuộc Phase 6. Nền map cần Internet/WebGL; test chủ động chặn nguồn nền để kiểm tra fallback. Chưa chứng nhận nguồn bản đồ ngoài Internet trong lượt Phase 5. Snapshot khóa toàn bộ profile, phù hợp quy mô MVP đã chốt; chưa đo tải lớn. Hạn chế timeline UUID khi sự kiện trùng cả `event_time`/`recorded_at` từ Phase 4 được giữ nguyên. Không merge, push hoặc deploy; giữ branch/worktree để người dùng quyết định tích hợp.

Minor còn lại: nếu trình duyệt khôi phục nguyên document từ back/forward cache, `pagehide` đã dừng loader mà chưa có `pageshow` khởi động lại. Probe lifecycle tổng hợp tái hiện được; Back thực tế trên Edge với header `no-store` của ứng dụng tải lại document và hoạt động đúng. Chưa chứng minh hành vi cache đó trên browser khác, nên để lại cải thiện có điều kiện; nếu gặp, tải lại trang để tiếp tục cập nhật. Không tuyên bố đã kiểm chứng back/forward cache đa trình duyệt.

## Các quyết định trong lượt bàn giao

- Làm sạch nhận xét Minor về whitespace vì người dùng yêu cầu diff sạch, kiểm tra thêm cả phạm vi từ baseline; không thay hành vi hoặc assertion, không có tác động nghiệp vụ.
- Tự hoàn tất phần full suite/tài liệu mà reviewer để executor xác minh: dùng kết quả full-02 thực tế và chạy checks cuối trước commit; không chấp nhận bằng chứng còn thiếu.
- GPS điện thoại thật, HTTPS, pilot và hiệu năng để Phase 6 theo phạm vi được giao; đổi lại chưa có chứng nhận môi trường thực.
- Giữ hạn chế timeline UUID khi trùng thời điểm từ baseline; đổi lại thứ tự hiển thị sự kiện ghép có thể không như mong đợi, trạng thái/transaction không đổi.
- Giữ đích login `/admin/users` và thêm link Dashboard để tương thích; đổi lại cần thêm một click để đến Dashboard.
- Không suy rộng probe Edge thành chứng nhận back/forward cache đa browser; đổi lại còn Minor refresh dừng có điều kiện nêu trên, có thể phục hồi bằng reload.
