# Phase 6 — Runbook vận hành, triển khai và khôi phục

**Chuẩn bị, chưa triển khai.** Mẫu Linux/systemd + Caddy phù hợp một web process/worker riêng và khoảng 10 User. Máy phát triển hiện là Windows; unit/Caddy chưa được chạy trên host đích. Không dùng `scripts.local_run` cho kiểm thử hoặc deploy vì launcher đọc `.env` ứng dụng. Các lệnh trong mục triển khai chỉ chạy sau phê duyệt đích cụ thể.

## Trách nhiệm và điều kiện mở dịch vụ

| Vai trò phải được chỉ định | Trách nhiệm |
| --- | --- |
| Owner triển khai/on-call | DNS/TLS/firewall, bản release, systemd, health/alert/log, triển khai và rollback; kiểm tra backup hằng ngày |
| Owner dữ liệu (đại diện công ty) | Cấp quyền Admin, cấp mật khẩu an toàn, Geofence, vòng đời dữ liệu/backup, phê duyệt phục hồi và đối soát xóa |
| Người giữ khóa backup (có người dự phòng) | Khóa giải mã tách nơi lưu backup; kiểm tra truy cập/khôi phục hằng tháng, thu hồi khóa khi thay người |
| Người phụ trách pilot | Khoảng 10 User, lịch 5 ngày làm việc, phản hồi/triage, xác nhận đủ bằng chứng |

Tên người/đơn vị hiện **chưa được cung cấp**; đây là cổng go-live, không giả định agent là người trực vận hành. Mục tiêu đề xuất để owner duyệt: RPO ≤24 giờ; RTO ≤4 giờ gồm đối soát xóa/purge/kiểm thử. Diễn tập local vài giây không chứng minh RTO đích.

## Kiến trúc và HTTPS

Trình duyệt → Caddy 80/443 → FastAPI `127.0.0.1:8000` → PostgreSQL qua TLS được xác minh. Frontend và API cùng origin. Chỉ Caddy công khai; database không mở cho Internet rộng, chỉ IP backend/operator đã duyệt. Không cấu hình CORS wildcard. Chỉ tin forwarded headers từ loopback proxy, không dùng `*`.

Mẫu ở `deploy/Caddyfile.example`, `geoattend-web.service`, `geoattend-maintenance.service`, `runtime.env.example`, `logging.json`. Thay domain/đường dẫn/người chạy theo đích duyệt; không đặt secret trong unit/Git. Caddy cần DNS A/AAAA đúng, 80/443 và data directory ghi được, bền vững để cấp/gia hạn chứng chỉ. Mẫu HSTS 1 ngày, chưa includeSubDomains/preload; tăng chỉ sau xác minh toàn bộ HTTPS. [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).

Trước mở public:

1. Kiểm tra artifact/revision, Python/platform và lockfile phù hợp host; lock hiện được tạo Windows/Python3.13, chưa chứng minh cài trên Linux.
2. `caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile`; `systemd-analyze verify` hai unit đã thay đường dẫn. Caddy 2.11.7 tạm trong `.local-tests` đã adapt template và chạy probe lỗi HTTP loopback; chưa validate HTTPS trên đích hoặc chạy systemd, chưa tuyên bố các lệnh kiểm chứng đích này đạt.
3. `GEOATTEND_ORIGIN=https://<domain-chính-xác>` không path; `GEOATTEND_SECURE_COOKIES=true`. Cấu hình hiện có từ chối HTTPS với cookie không Secure.
4. Xác minh HTTP chuyển HTTPS, chain/domain/renewal, cookie HttpOnly/Secure/SameSite=Lax, no-store cho trang bảo vệ/API nhạy cảm, CSRF/Origin chặn nguồn khác, User không vào trang/API Admin.
5. Điện thoại vào domain HTTPS tin cậy, `window.isSecureContext` và Geolocation hoạt động; HTTP LAN không được coi là bằng chứng HTTPS/GPS. Test từ chối quyền không tự chuyển Remote.

Nền map cần Internet/WebGL; kiểm tra nguồn tile/style và credits/CSP hiện có. Map lỗi không làm mất chấm công/danh sách/lịch sử. Không thêm origin rộng để tránh lỗi CSP.

## Secret và database

- Runtime chỉ nhận DSN role riêng; file `/etc/geoattend/runtime.env` do root quản lý, mode 0600, không shell echo/env dump. Service user không được sửa code, env hoặc backup. Không truyền password trên command line/URL công khai; không chụp màn hình trang có secret.
- Migration DSN chỉ có trong phiên operator ngắn hạn, không có trong web/worker. Role runtime không superuser/CREATEDB/CREATEROLE/BYPASSRLS, không owner schema; không membership role quản trị. Grant hiện có: usage schema/PostGIS; SELECT/INSERT/UPDATE chín bảng; DELETE auth_sessions/auth_attempts và ba bảng con work_sessions/attendance_events/office_locations cho xóa ngày. Không DELETE profiles/attendance_days/attendance_requests, không CREATE/ALTER.
- PostGIS có thể ở public/extensions; dùng công cụ migration hiện có, không hardcode chuyển schema extension. Schema geoattend không exposed qua API dữ liệu Supabase; frontend không nhận khóa database.
- `sslmode=verify-full` và CA theo provider, chứng minh hostname/cert đích; không tự đổi sang disable khi lỗi kết nối. Runtime/migration DSN không được dùng làm test DSN.
- Rotation: cập nhật secret trong secret store/file kín, restart web/worker, health/login/role check; thu hồi credential cũ sau xác minh. Sự cố token ứng dụng: operator thu hồi session bằng quy trình được duyệt; không xuất token ra log.

## Migration, release và rollback

Phase 6 hiện **không có migration mới**; giữ checksum 001–004. Với DB mới, operator được duyệt tạo runtime role rồi chạy `python -m scripts.migrate` bằng môi trường quản trị riêng. Chạy lại phải no-op; không sửa SQL đã áp dụng hoặc dùng drop schema trên DB thật. Kiểm tra quyền bằng runtime role sau migration. Bootstrap Admin bằng prompt ẩn chỉ khi DB chưa có Admin, không tự chạy lại reset Admin.

Quy trình release đích sau duyệt:

1. Ghi revision hiện tại/mới, migration/checksum/quyền dự kiến, downtime, chi phí, người rollback; tạo backup mã hóa và xác minh nó đọc/restore được ở DB cô lập.
2. Đặt reverse proxy ở maintenance, không nhận mutation mới; drain web và dừng worker có chủ rõ ràng. Không kill tiến trình không rõ chủ.
3. Chuẩn bị `/opt/geoattend/releases/<sha>` và venv từ lock đã kiểm chứng host. Không `pip install` tùy ý trên release đang phục vụ. `pip check` phải đạt.
4. Nếu có migration tương lai: chỉ chạy theo phiếu duyệt cụ thể, backup/rollback riêng; Phase 6 này không có. Cập nhật symlink current tới release đã kiểm chứng.
5. Chạy maintenance một lần trên DB đích đã duyệt; kiểm tra expired GPS remaining=0. Khởi động worker độc lập rồi web, health và smoke qua proxy nội bộ; mở public sau kiểm tra quyền/trạng thái/HTTPS.
6. Theo dõi lỗi, p95/tỷ lệ ≤2s và heartbeat; nếu lỗi phân quyền, mất/trùng dữ liệu hoặc 5xx tăng, đóng traffic mutation, giữ bằng chứng đã khử nhạy cảm.

Rollback mã: maintenance proxy, drain web, dừng worker, trỏ current về revision ngay trước release và dùng venv tương ứng; restart, maintenance/health/smoke, mở lại. Không cần restore DB cho thay đổi mã Phase 6 vì schema/payload tương thích. **Không rollback về nghiệp vụ cũ trước 2472785.** Restore DB là phương án thảm họa có mất ghi sau backup; cần owner dữ liệu duyệt, không thay thế rollback code thông thường.

## Worker, health, log và cảnh báo

- Đồng bộ đồng hồ host bằng NTP, kiểm tra lệch giờ khi triển khai/khôi phục; log timestamp UTC, nghiệp vụ vẫn `Asia/Ho_Chi_Minh`/20:00 cố định. Không chỉnh giờ server thật để mô phỏng pilot/cutoff; clock điều khiển chỉ thuộc DB/test riêng. Owner kiểm tra ngày Việt Nam và lịch worker trước mở dịch vụ.
- Worker riêng chạy mỗi 60 giây, restart on-failure, không gắn vào web worker hoặc phụ thuộc tab. Nếu dừng, API đối soát bù nhưng đó không thay thế vận hành worker. Log đếm đóng ngày/prune/purge và journal timestamp; không GPS/token/lý do.
- `/api/health`: 200 DB ok hoặc 503 thông báo chung, không DSN. Không phải readiness đầy đủ cho worker/retention/checksum/backup. Monitor loopback mỗi phút; cảnh báo sau 3 lần lỗi. Sau restart đối soát ngày cũ trước mở ngày mới.
- Alert heartbeat worker không có lượt thành công trong 3 phút; backup >26 giờ hoặc restore drill tháng chưa đạt; expired GPS chưa purge sau 3 phút; TLS còn <14 ngày; 5xx >1% trong 5 phút; API ≤2s <95% trong cửa sổ đủ ≥100 request. Owner quyết định ngưỡng/đích nhận alert trước go-live; agent chưa gửi thông báo.
- `ApiTiming` đo từ ASGI nhận request đến hoàn tất body cuối, gồm chờ pool/khóa/DB/serialization; không tính GPS/client/network đến server. Log INFO `geoattend.api` có route template, method allowlist, status và duration_ms; không raw path/query/ID/body/header.
- `deploy/logging.json` dùng SafeFormatter: diagnostic chỉ level/logger/timestamp, không interpolate message/exception stack có thể chứa SQL/DSN. Uvicorn access log tắt; Caddy không bật access log **và global default logger loại `http.log.error`**, vì lỗi 502 vẫn có thể ghi query/header dù access log tắt. Probe Caddy thật đã RED/GREEN sentinel khi upstream chết. Đổi lại phải giám sát status/health bằng synthetic probe không nhạy cảm, không dựa vào log lỗi request của proxy. Không thêm logger khác ghi lại namespace đã loại; kiểm tra log collector/provider ở đích. [Caddy global log options](https://caddyserver.com/docs/caddyfile/options#log). Worker mẫu cũng nạp formatter. Điều tra sâu chỉ trên bản sao cô lập có dữ liệu tổng hợp; không bật debug/SQL body dump trên đích thật.
- Lưu log vận hành đã khử nhạy cảm **14 ngày**, quota/rotation theo host; hạn chế người đọc và không xuất dữ liệu người dùng. Traceback chi tiết bị bỏ có chủ ý, đổi lại cần tái hiện cô lập để tìm nguyên nhân. Kiểm tra thêm logging của provider, DB statement log, proxy/WAF/APM/session replay trước go-live; tuyệt đối không capture body/bind parameters/cookie/query. Chưa audit cấu hình provider thật.

SQL gate bằng runtime/monitor role được duyệt (chỉ xuất count):

```sql
SELECT count(*) AS expired_remaining FROM geoattend.office_locations
WHERE expires_at <= now() AND (point IS NOT NULL OR accuracy_m IS NOT NULL);
SELECT count(*) AS overdue_open FROM geoattend.work_sessions s
JOIN geoattend.attendance_days d ON d.id=s.day_id
WHERE s.end_time IS NULL
AND (d.work_date + time '20:00') AT TIME ZONE 'Asia/Ho_Chi_Minh' <= now();
```

## Backup và chính sách dữ liệu

Chính sách chuẩn bị để owner tiếp nhận: **mỗi ngày một backup logic mã hóa, giữ 7 bản ngày, tự xóa khi quá 7 ngày; không bản tháng/archive dài hạn; khóa giải mã tách nơi lưu; một bản ngoài máy chủ theo đích được duyệt.** Tất cả là dữ liệu nhạy cảm dù không GPS (hash mật khẩu/session/lý do). Backup staging chỉ trên volume mã hóa có ACL riêng, xóa ngay sau mã hóa/xác minh; không đặt trong repo/log. Đích lưu, khóa, quota, quyền xóa và job retention chưa được triển khai.

**Backup chuẩn không lấy dữ liệu `geoattend.office_locations`** để không kéo dài retention GPS 30 ngày của bản live. Không lưu backup vật lý/WAL/PITR chứa GPS ngoài chính sách riêng được owner duyệt; phải kiểm tra dịch vụ hosted có tự giữ các bản này không. Nếu provider giữ GPS quá hạn mà không kiểm soát được, chưa đạt cổng quyền riêng tư, cần đổi chính sách/đích trước pilot.

Lệnh mẫu dùng PG service/passfile kín (không password trong CLI); thực hiện bằng role backup được duyệt, có SELECT đủ bảng và connect. Schema/PostGIS/migration ledger có trong dump:

```sh
# PG service/passfile được operator cấp, staging là volume mã hóa mode 0700.
PGSERVICE=geoattend_backup pg_dump --format=custom --no-owner --no-privileges \
  --exclude-table-data=geoattend.office_locations --file=/private-staging/geoattend.dump
# Mã hóa bằng công cụ/khóa của đích đã được duyệt, xác minh checksum ciphertext,
# chuyển bản mã tới kho đích, xóa staging và chạy retention 7 ngày.
```

Không backup role passwords bằng pg_dumpall; định nghĩa role/quyền giữ dưới dạng IaC không bí mật và cấp lại khi restore. Không kiểm tra backup chỉ bằng file tồn tại/pg_restore --list: phải restore vào DB riêng, chạy gate và API. Diễn tập ít nhất mỗi tháng và trước nâng PostgreSQL/PostGIS; dùng client cùng major server, xác minh extension đích. [pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html), [pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html).

Trade-off: backup chuẩn không phục hồi GPS/accuracy, kể cả còn hạn; giữ thời gian/phiên/sự kiện/xác minh và tombstone. Sau restore Onsite có thể báo không có dữ liệu vị trí, không đặt Marker giả; Office kế tiếp phải xác minh lại như bình thường. Không tự kết thúc ngày hoặc tái Check-in để tạo Marker. Diễn tập legacy-with-gps riêng chứng minh API che/purge khi khôi phục bản cũ có GPS, không có nghĩa được phép tạo backup legacy mới trên production.

Admin xóa ngày chỉ xóa DB live; bản backup trước xóa có thể còn lý do/lịch sử đến lúc hết hạn 7 ngày. Owner phải thông báo rõ điều này và giữ sổ xóa tối thiểu **account ID + ngày + thời điểm xóa**, không lý do/GPS/token, mã hóa/quyền hẹp, giữ qua vòng đời backup. Khi restore, đối soát tất cả xóa sau snapshot trước mở traffic; dùng API/quy trình xóa theo đúng hợp đồng rồi kiểm tra tombstone. App chưa có tự động đồng bộ xóa tới backup hoặc audit export; không coi việc khôi phục backup cũ là được phép phục hồi lịch sử đã xóa. Nếu không có sổ xóa đủ tin cậy, dừng phục hồi public và yêu cầu owner xử lý; không suy đoán.

## Restore bắt buộc trước mở dịch vụ

1. Được owner duyệt điểm khôi phục/RPO và mất ghi sau snapshot. Chọn **DB mới cô lập**, chặn public; không pg_restore --clean vào DB đang phục vụ. Giữ DB lỗi làm bằng chứng theo chính sách, không tự xóa.
2. Giải mã trên staging kín, xác minh checksum; provision extension/role không superuser cho runtime. Restore bằng operator role vào DB mới với `--no-owner --no-privileges --exit-on-error`; lỗi bất kỳ không mở dịch vụ.
3. Chạy migration tool để xác minh checksum (Phase 6 phải no-op), cấp lại quyền runtime; kiểm tra runtime không owner/DDL/DELETE profiles. Không đưa migration DSN vào web/worker.
4. **Chạy `python -m scripts.maintenance --once` với runtime DSN restore trước public**; kiểm tra expired_remaining=0 và overdue_open=0. Bản cũ có GPS hết hạn phải null point/accuracy; chạy lần hai không tạo trùng. API vốn che ngay nhưng không thay thế purge gate.
5. Thu hồi các phiên đăng nhập được phục hồi sau khi hoàn tất kiểm chứng tombstone; owner/operator có quyền thực hiện `UPDATE geoattend.auth_sessions SET revoked_at=now() WHERE revoked_at IS NULL` trên DB restore được duyệt. Không cho token đăng xuất/thu hồi sau snapshot sống lại. Login mới để smoke; không đưa session từ bản restore vào kết quả thử nghiệm.
6. Đối soát sổ xóa sau backup: với từng account ID/ngày đã được ghi nhận xóa, lấy đúng User/username bằng API Admin; lọc history theo ngày, lấy day ID/revision mới nhất rồi DELETE bằng xác nhận username hiện hành. Kiểm tra lại history rỗng, phiên/event/GPS không còn và UUID cũ trả HISTORY_DELETED. Nếu ngày còn active/phiên mở hoặc revision thay đổi, dừng gate, không ép Checkout/đổi trạng thái hoặc bỏ điều kiện xóa; owner phải xử lý bằng quy trình riêng được duyệt trước public. Không có sổ xóa tin cậy cũng phải dừng. Kiểm tra số User/Admin/phiên/sự kiện so với manifest tổng hợp, quyền và GIS. Với backup GPS-free mọi vị trí trống là dự kiến; không kết luận dữ liệu GPS được phục hồi.
7. Chạy health/API User/Admin/retry/cutoff/read_history và đo tải đích; owner ký rồi đổi DSN runtime, restart worker/web, mở proxy. Theo dõi; rollback về DB cũ chỉ nếu an toàn và owner duyệt vì có thể phân nhánh dữ liệu.

## Bằng chứng local

Bổ sung báo cáo tuần (18/10/2026): migration **005_weekly_reports.sql** thêm bảng `weekly_reports` chứa PDF/metadata trong database. Khi phát hành chức năng này, xác minh checksum 001–005 và grant runtime SELECT/INSERT/UPDATE bảng mới; không sửa các migration cũ. Các mô tả 001–004/no-op ở trên là phạm vi bản Phase 6 trước bổ sung, không có nghĩa bỏ qua 005 khi phát hành báo cáo tuần. Database ứng dụng hiện chưa được agent áp dụng migration mới.

Backup GPS-free vẫn lấy PDF/metadata báo cáo tuần. Dự trù dung lượng DB/backup tăng tối đa 10 MB/User/tuần; PDF cũ bị thay trong ứng dụng vẫn có thể nằm trong backup cũ đến hết retention backup. Khi restore phải giữ cả bảng mới và mốc `applied_at` của 005 để không thay đổi tuần bắt đầu có trách nhiệm nộp; kiểm tra lại xem/tải PDF sau khi đăng nhập mới. Không tự thêm job xóa báo cáo hoặc thay retention GPS. Diễn tập restore test riêng được mở rộng kiểm tra bytes PDF và mốc kích hoạt, không thay bằng chứng host/backup đích thật.

`tests/integration/test_phase6_restore.py` tạo DB source/target UUID riêng, dùng pg_dump/pg_restore thật. Kiểm tra hai chính sách GPS-free và legacy-with-gps, checksum, runtime quyền hẹp, lịch sử/xác minh/tombstone, API trước purge, maintenance hai lần và thu hồi session. Kịch bản thứ ba dump trước, xóa source sau dump, restore riêng thấy dữ liệu đã xóa được phục hồi, rồi thực hiện đúng quy trình sổ xóa bằng API trên ngày đã Checkout: history/session/event/GPS biến mất và replay HISTORY_DELETED. Đây là diễn tập quy trình thủ công, không tự động hóa đồng bộ sổ xóa hoặc cho phép xóa ngày active. Kết quả thực tế ở [báo cáo Phase 6](PHASE_6_VERIFICATION.md). Không có backup/restore/migration nào chạy trên Supabase thật. Chưa chứng minh dung lượng, khóa mã hóa, retention job hoặc khôi phục toàn host thật.
