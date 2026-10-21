> **Tài liệu lưu trữ:** nội dung và số liệu bên dưới phản ánh thời điểm lập tài liệu. Các hướng dẫn/quy tắc cũ có thể đã được thay thế; xem [tài liệu hiện hành](../README.md) trước khi thực hiện.

# GeoAttend — Tổng kết hoàn thành Phase 0–5

Tiếp quản Phase 6 ngày 16/10/2026: [bàn giao hiện hành](handoff/README_PHASE_6.md), [báo cáo mới](../PHASE_6_VERIFICATION.md). Nội dung và số test trong tổng kết này giữ làm bằng chứng lịch sử; Phase 6 chưa nghiệm thu môi trường thật/pilot.

- **Ngày tổng hợp:** 16/10/2026.
- **Workspace:** `.worktrees/phase-1`.
- **Branch:** `feat/phase-1-foundation-auth`.
- **Mốc mã nguồn đã hoàn tất chức năng:** `2472785`.

## 1. Trạng thái hiện tại

**Phase 0, 1, 2, 3, 4 và 5 đã hoàn thành trong phạm vi thiết kế, triển khai và kiểm thử đã thống nhất.** Các bổ sung lịch sử Admin, UI User, Check-out sớm và Xin nghỉ cũng đã hoàn thành.

Full suite gần nhất sau tất cả điều chỉnh đạt **267 passed, 1 warning** trên PostgreSQL 17/PostGIS test riêng và Edge headless. Phase 6 về môi trường thực, triển khai và pilot chưa hoàn thành; kết quả phát triển này chưa phải chứng nhận sẵn sàng production.

Thông báo **“Hiện chưa có thao tác khả dụng. Ngày làm việc kết thúc lúc 20:00.”** khi nhân viên chưa bắt đầu nhưng đã qua 20:00 là hành vi đúng quy tắc đã chốt. Nó không phải lỗi do sửa Xin nghỉ và không làm thay đổi kết luận hoàn thành Phase 5.

## 2. Phase 0 — Chốt nghiệp vụ và thiết kế

Đã xác định mục tiêu MVP, phạm vi và hai vai trò:

- **Admin:** cấp/quản lý tài khoản, cấu hình văn phòng/Geofence, xem trạng thái, bản đồ và lịch sử nhân viên; không chấm công cá nhân.
- **User:** tài khoản do Admin cấp; chấm công Office/Remote, nghỉ trưa, xin nghỉ, Check-out và xem lịch sử cá nhân.

Đã chốt bảng trạng thái, nguyên tắc GPS, múi giờ Việt Nam, cutoff 20:00, mô hình ngày/phiên/sự kiện, API, giao diện và tiêu chí nghiệm thu/pilot. Đã chọn kiến trúc FastAPI/Pydantic, Psycopg, PostgreSQL/PostGIS, HTML/CSS/JavaScript và bản đồ Leaflet/MapLibre.

Tài liệu nền: [BRD](../REQUIREMENTS.md), [thiết kế MVP](superpowers/specs/2026-10-14-geoattend-mvp-design.md), [bảng chuyển trạng thái](../STATE_TRANSITIONS.md), [roadmap](ROADMAP.md). Những điều chỉnh được người dùng xác nhận sau đó được cập nhật và ưu tiên hơn nghiệp vụ cũ.

## 3. Phase 1 — Nền tảng, xác thực và tài khoản

- Dựng ứng dụng FastAPI, cấu hình môi trường, kết nối database và health endpoint.
- Có migration với version/checksum; tách quyền database runtime và migration, không sửa migration đã áp dụng.
- Khởi tạo Admin ban đầu; đăng nhập/đăng xuất bằng tài khoản nội bộ, kiểm tra quyền Admin/User.
- Bảo vệ session/cookie và CSRF cho thao tác ghi; kiểm tra session hết hạn/thu hồi.
- Admin tạo tài khoản nhân viên, cấp lại mật khẩu; User đổi mật khẩu. Thu hồi session khi cần theo hợp đồng xác thực.
- Có giao diện đăng nhập, tài khoản cá nhân và quản lý nhân viên, kiểm thử quyền truy cập và nội dung HTML độc hại.

Mốc kiểm chứng lịch sử: **46 test đạt**. Chi tiết: [PHASE_1_VERIFICATION](PHASE_1_VERIFICATION.md).

## 4. Phase 2 — Chấm công Remote và ngày làm việc

- Bắt đầu Remote có lý do, lưu ngày làm việc, phiên và sự kiện vào PostgreSQL.
- Check-out đóng phiên; API trạng thái và lịch sử cá nhân đọc dữ liệu đã lưu.
- Tối đa một phiên mở cho mỗi nhân viên; thao tác ghi chạy trong transaction với profile lock và kiểm tra lại ngữ cảnh sau khi chờ khóa.
- `request_id` chống ghi trùng; cùng UUID/payload trả lại kết quả đã commit. UUID khác payload, revision cũ hoặc ngày cũ bị từ chối.
- Giao diện giữ payload chờ xác nhận để retry an toàn khi mất phản hồi; không tự tạo UUID mới cho cùng thao tác chưa rõ kết quả.
- Tự đóng phiên lúc 20:00 giờ Việt Nam, ghi nguồn `SYSTEM`; maintenance/API xử lý bù khi dịch vụ từng dừng.
- Có launcher local cho web và maintenance độc lập.

Mốc kiểm chứng lịch sử: **85 test đạt**. Chi tiết: [PHASE_2_VERIFICATION](PHASE_2_VERIFICATION.md).

Quyền bắt đầu lại sau Check-out của thiết kế giai đoạn này đã được thay thế bằng quy tắc khóa ngày hiện hành ở mục 9.

## 5. Phase 3 — Office, GPS và Geofence

- Admin xem/sửa tên, địa chỉ và vùng Polygon văn phòng, gồm vùng loại trừ; kiểm soát revision để tránh ghi đè bản sửa của người khác.
- User bắt đầu Office bằng một lần lấy GPS cho mỗi thao tác vào Office; backend dùng PostGIS `ST_Covers`, chấp nhận điểm trong hoặc trên ranh giới, không dùng vùng đệm.
- Lưu accuracy để tra cứu, không dùng accuracy làm ngưỡng từ chối.
- Ngoài vùng, không có quyền GPS hoặc lỗi xác minh: giữ trạng thái trước đó, không tự chuyển sang Remote.
- Lưu GPS riêng, gắn với đúng phiên/sự kiện đã xác minh; không theo dõi GPS liên tục và không ghi GPS vào local/session storage.
- Tọa độ và accuracy có retention **30 ngày**. API che ngay khi hết hạn dù maintenance chưa purge vật lý.
- Có editor bản đồ và UI lấy GPS; bổ sung phục hồi nền bản đồ, giữ bản nháp và bảo vệ thao tác trong lúc tải/lưu.

Mốc kiểm chứng lịch sử: **119 test**, sau sửa bản đồ **122 test đạt**. Chi tiết: [PHASE_3_VERIFICATION](PHASE_3_VERIFICATION.md), [MAP_RECOVERY](MAP_RECOVERY.md).

## 6. Phase 4 — Nghỉ trưa, xin nghỉ và tiếp tục làm việc

- Nghỉ trưa đóng phiên hiện tại, lưu sự kiện và trạng thái `LUNCH_BREAK`.
- Tiếp tục Office/Remote tạo phiên mới; Office xác minh GPS lại, Remote nhập lý do.
- Nghỉ buổi sáng/cả ngày có lý do và lịch sử; không tạo phiên làm việc giả cho thời gian nghỉ.
- API chuyển trực tiếp Office ↔ Remote đóng phiên cũ và tạo phiên mới nguyên tử, giữ phiên cũ nếu xác minh/ghi dữ liệu thất bại.
- Đối soát nghỉ trưa tại 20:00 chỉ ghi kết thúc ngày, không kéo dài phiên đã đóng trước nghỉ trưa.
- Kiểm thử rollback, cạnh tranh đồng thời, quyền/session bị thay đổi khi chờ khóa, cutoff/ngày mới, UUID và browser.

Mốc kiểm chứng lịch sử: **195 test đạt**. Commit bàn giao: `d1c57d9`. Chi tiết: [PHASE_4_VERIFICATION](PHASE_4_VERIFICATION.md).

Giai đoạn này từng hỗ trợ hủy nghỉ cả ngày để làm tiếp. Theo yêu cầu mới nhất, thao tác mới như vậy hiện bị chặn; UUID hủy nghỉ đã commit từ phiên bản cũ vẫn replay được.

## 7. Các bổ sung Admin/User đã hoàn thành

### Lịch sử nhân viên dành cho Admin

- Xem lịch sử theo nhân viên, lọc ngày và phân trang.
- Xóa vĩnh viễn từng ngày với xác nhận đúng username và revision; chặn ngày đang làm/nghỉ trưa hoặc còn phiên mở.
- Xóa phiên, sự kiện, lý do và GPS trong cùng transaction; giữ tombstone UUID/hash/revision tối thiểu để tab cũ hoặc retry không phục hồi dữ liệu đã xóa.
- Admin xóa ngày hôm nay đưa ngày về `NOT_STARTED`; đây là ngoại lệ quản trị đã được chấp thuận đối với khóa ngày.

Commit: `effce0e`; migration lịch sử `004_history_deletion.sql` thuộc baseline đã có. Chi tiết: [ADMIN_HISTORY](../ADMIN_HISTORY.md).

### Giao diện User ưu tiên điện thoại

- Thông tin nhân viên ở đầu, thao tác theo ca ở giữa, lịch sử cá nhân thu gọn cuối trang.
- Chỉ mở form lý do khi chọn thao tác tương ứng; giữ bản nháp, quản lý focus và trạng thái đang gửi.
- Lịch sử chỉ tải khi mở; phản hồi cũ không ghi đè lượt tải mới.
- UI hoạt động ở kích thước mobile/desktop giả lập; tên/lý do được hiển thị như văn bản an toàn.

Commit: `161f724`, `8dd1af2`. Các mốc kiểm chứng bổ sung: **210 → 213 → 218 test đạt**. Chi tiết: [USER_MOBILE_UI](USER_MOBILE_UI.md).

## 8. Phase 5 — Dashboard và bản đồ Onsite cho Admin

| Task | Kết quả đã hoàn thành | Commit |
| --- | --- | --- |
| 1 | API snapshot Dashboard nhất quán: toàn bộ User, bảy nhóm trạng thái, tổng số và danh sách; loại Admin khỏi thống kê | `ae5765d` |
| 2 | API Onsite từ đúng phiên Office đang mở đã xác minh; bảo toàn retention GPS 30 ngày | `39339f6` |
| 3 | Trang `/admin/dashboard`, Geofence, Marker có tên/Popup và liên kết tới lịch sử/editor có sẵn | `2f339d3` |
| 4 | Refresh 30 giây khi tab hiển thị, tải lại khi quay lại tab/tải tay; chống phản hồi cũ, giữ snapshot có nhãn khi lỗi mạng; hồi quy điều hướng/quyền/lịch sử | `4c80dbc` |
| 5 | Full suite, review độc lập, báo cáo, roadmap và bàn giao | `0ce352a` |

Dashboard gồm User chưa chấm công và tài khoản bị khóa; bảy nhóm là `NOT_STARTED`, `WORKING_OFFICE`, `WORKING_REMOTE`, `LUNCH_BREAK`, `MORNING_LEAVE`, `FULL_DAY_LEAVE`, `CHECKED_OUT`. Tổng số khớp danh sách.

Onsite hiển thị **vị trí Check-in đã xác minh**, không phải vị trí trực tiếp. Nhân viên rời trạng thái Office sẽ rời nhóm Marker khi dữ liệu được làm mới. GPS hết hạn/thiếu không được thay bằng tâm văn phòng hoặc điểm giả.

Tái sử dụng lịch sử/xóa ngày và editor văn phòng; không tạo chức năng quản trị trùng lặp hoặc migration mới. Login Admin vẫn đến `/admin/users`, có liên kết Dashboard.

Mốc nghiệm thu Phase 5: **249 passed, 1 warning**, 406.93s; review không có Critical/Important. Chi tiết: [PHASE_5_VERIFICATION](PHASE_5_VERIFICATION.md), [checklist Phase 5](MANUAL_TEST_PHASE_5.md).

## 9. Các điều chỉnh cuối cùng sau Phase 5

### Check-out sớm — commit `e704600`

- CHECK-OUT SỚM bắt buộc lý do 1–1000 ký tự sau trim và có nút xác nhận.
- Lưu lý do vào phiên/sự kiện kết thúc, đọc lại được trong lịch sử User/Admin.
- Mọi Check-out kết thúc ngày, chặn Check-in mới đến ngày hôm sau theo giờ Việt Nam, kể cả reload/gọi API.
- Retry UUID đã commit, kể cả Check-out cũ chưa có lý do, vẫn trả kết quả cũ.

Mốc kiểm chứng: **259 passed, 1 warning**. Chi tiết: [EARLY_CHECKOUT_VERIFICATION](EARLY_CHECKOUT_VERIFICATION.md).

### Xin nghỉ — commit `2472785`

1. Bấm **XIN NGHỈ**, chọn **BUỔI SÁNG / CẢ NGÀY**, sau đó nhập lý do và xác nhận.
2. **Buổi sáng:** hiện “Đang nghỉ buổi sáng”, hai lựa chọn tiếp tục buổi chiều Office/Remote. Tiếp tục thành công hiện “Đang làm việc” kèm chế độ, chỉ còn **CHECK-OUT** cuối ngày, không hiện Nghỉ trưa/Check-out sớm. Office/Remote giữ yêu cầu GPS/lý do tương ứng.
3. **Cả ngày:** lưu lý do và `FULL_DAY_LEAVE`, kết thúc ngày; không Check-in hoặc hủy nghỉ để làm tiếp. Ngày mới mở lại.
4. Cờ ca lấy từ sự kiện trên server, không suy ra bằng giờ thiết bị; reload vẫn đúng. Giữ khóa 20:00, ngoại lệ Admin reset và replay UUID lịch sử.

Mốc kiểm chứng mới nhất: **267 passed, 1 warning**. Chi tiết: [LEAVE_FLOW_VERIFICATION](LEAVE_FLOW_VERIFICATION.md).

## 10. Quy tắc vận hành hiện hành

| Tình huống | Hành vi |
| --- | --- |
| Chưa bắt đầu, trước 20:00, không có thao tác pending | Dùng được CHECK-IN OFFICE, CHECK-IN REMOTE, XIN NGHỈ |
| Ca đầu thông thường | NGHỈ TRƯA hoặc CHECK-OUT SỚM có lý do |
| Nghỉ trưa | Tiếp tục Office/Remote; sau tiếp tục chỉ CHECK-OUT cuối ngày |
| Nghỉ sáng | Tiếp tục buổi chiều Office/Remote; sau tiếp tục chỉ CHECK-OUT cuối ngày |
| Đã Check-out hoặc nghỉ cả ngày | Khóa thao tác mới đến ngày hôm sau; UUID đã commit vẫn replay |
| Từ đúng 20:00 | Không bắt đầu/tiếp tục/chuyển chế độ, kể cả chưa từng làm việc trong ngày |
| Phiên còn mở tại 20:00 | Hệ thống đóng với nguồn SYSTEM; không coi đó là giờ kết thúc thực tế của nhân viên |
| Admin xóa lịch sử hôm nay hợp lệ | Reset về chưa bắt đầu với revision tăng; vẫn tuân thủ cutoff và tombstone |

## 11. Bằng chứng kiểm thử gần nhất

- Full suite sau mọi điều chỉnh: **267 passed, 1 warning**, **677.18s**; hoàn tất 10:36 ngày 16/10/2026 giờ Việt Nam.
- Log local: `.local-tests/phase-5/leave-full.log`. Warning là deprecation upstream Starlette/httpx.
- `pip check`: **No broken requirements found**. `git diff --check`: đạt tại mốc bàn giao mã nguồn.
- Review độc lập phần Phase 5 và các điều chỉnh tiếp theo: không có lỗi chặn còn lại.
- Kiểm thử dùng PostgreSQL 17/PostGIS local riêng và Edge headless; fixture tạo/drop database `geoattend_test_<uuid>` riêng.
- Không tạo/xóa dữ liệu thử hoặc chạy migration mới lên Supabase thật trong các lượt Phase 5/điều chỉnh này.

**Các số test theo phase là snapshot lịch sử của toàn suite tại từng mốc, không cộng lại.** Số 218 là baseline trước Phase 5; 249 là mốc Phase 5; 259 là sau sửa Check-out sớm; **267 là kết quả gần nhất sau sửa Xin nghỉ**. Lần viết bản tổng kết này chỉ đối chiếu Git/tài liệu/log, không chạy lại full suite.

## 12. Cách mở và kiểm tra ứng dụng

Trong môi trường đã cấu hình theo [DEVELOPMENT](../DEVELOPMENT.md):

```powershell
Set-Location 'D:\N.ThanhNhan\INTERN\geoattend\.worktrees\phase-1'
# Terminal 1: web
.\.venv\Scripts\python.exe -m scripts.local_run serve
# Terminal 2: tác vụ đối soát và retention
.\.venv\Scripts\python.exe -m scripts.local_run maintenance
```

Mở `http://127.0.0.1:8000/login`. Sau cập nhật mã, khởi động lại web và Ctrl+F5. Những điều chỉnh Check-out/Xin nghỉ không cần migration mới; không tự chạy migration trên database thật.

Khi cần chạy lại kiểm thử, khởi động PostgreSQL/PostGIS test riêng trước và dùng đúng DSN test, không dùng DSN ứng dụng:

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

## 13. Giới hạn còn lại và bước tiếp theo

**Bước tiếp theo là Phase 6**, không phải làm lại Phase 5:

- Kiểm tra GPS/Geolocation trên điện thoại thật và HTTPS thực tế.
- Đo và chứng minh mục tiêu ít nhất 95% API backend ≤2 giây, không tính thời gian lấy GPS.
- Hoàn thiện cấu hình/vận hành production, worker độc lập, log, sao lưu và khôi phục; migration/deploy thực tế cần được cho phép riêng.
- Chạy pilot khoảng 10 người trong 5 ngày làm việc, ghi nhận phản hồi và nghiệm thu vận hành.

Hai hạn chế Minor đã ghi nhận: timeline có thể đảo thứ tự các sự kiện trùng thời điểm vì thứ tự UUID; Dashboard có thể cần reload nếu một browser thực sự phục hồi document từ back/forward cache. Back thực tế trên Edge với header no-store đã hoạt động đúng; chưa chứng nhận mọi browser.

Chưa merge/push/deploy/pilot trong phạm vi công việc đã giao. Các chức năng ngoài MVP như PWA, thông báo, xuất báo cáo, Correction Request, QR, nhiều văn phòng/phòng ban và AI/RAG chưa được coi là đã hoàn thành.
