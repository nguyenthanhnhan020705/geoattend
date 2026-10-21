# Phase 6 — Thiết bị thật, HTTPS và pilot

**Chưa thực hiện trên thiết bị thật; pilot chưa bắt đầu.** Checklist này là phần chuẩn bị. Không điền pass bằng kết quả Edge headless/GPS giả lập. Chỉ bắt đầu sau quyền đích cụ thể, owner vận hành/dữ liệu và người tham gia xác nhận.

## Phiếu duyệt triển khai cần hoàn thiện trước tác động bên ngoài

| Trường | Chuẩn bị hiện tại / điều kiện duyệt |
| --- | --- |
| Đích | Chưa có host/IP/domain/nhà cung cấp được duyệt; DB staging/pilot phải được nêu chính xác, không mặc định Supabase hiện có |
| Thay đổi | Release SHA cuối Phase 6; FastAPI/static cùng origin qua Caddy HTTPS, worker riêng, telemetry khử nhạy cảm, systemd/backup/log/alert |
| Schema/quyền | Phase 6 không thêm migration; kiểm tra 001–004/checksum, runtime/migration role riêng; việc provision/migrate/grant DB đích cần duyệt |
| Dữ liệu ảnh hưởng | Cấp khoảng 10 User thật bởi Admin; Geofence thực do owner xác nhận; chấm công/GPS pilot nhạy cảm, không dùng làm dữ liệu test phá hủy |
| Chi phí | Chưa có báo giá vì chưa chọn đích: compute, DB/PostGIS, domain, backup mã hóa/storage/egress, monitoring; không mua/cấp dịch vụ tự động |
| Backup | Một snapshot trước thay đổi, backup GPS-free mã hóa giữ 7 ngày; xác minh restore vào DB riêng; owner tiếp nhận policy và giới hạn GPS/PITR |
| Rollback | Proxy maintenance, drain mutation, dừng worker, quay code/env/venv revision trước, health/smoke; restore DB chỉ khi owner duyệt mất ghi sau snapshot |
| Xác minh | TLS/cookie/CSRF/roles/health/worker/retention + bộ thiết bị dưới đây + đo backend đích ≥95%≤2s + pilot 5 ngày |
| Người duyệt/chịu trách nhiệm | Chưa chỉ định; cần owner triển khai/on-call, dữ liệu, pilot và người giữ khóa backup |

Không xin một quyền “deploy chung” không rõ đích. Khi người dùng cung cấp đích, điền toàn bộ trường/chi phí/SHA rồi trình phiếu cụ thể; hoàn tất chuẩn bị local trước. Không dùng connector để gửi thông báo cho người tham gia.

## Bộ thiết bị tối thiểu

| Nhóm thiết bị thật | Browser | Kết quả hiện tại |
| --- | --- | --- |
| Android điện thoại | Chrome phiên bản thực tại ngày test | Chưa chạy |
| iPhone | Safari phiên bản iOS thực tại ngày test | Chưa chạy |
| Máy tính Windows | Edge và Chrome phiên bản thực | Chưa chạy thiết bị với HTTPS đích |
| Máy tính macOS nếu có người dùng pilot | Safari phiên bản thực | Chưa chạy; ghi rõ giới hạn nếu không có thiết bị |

Ghi model/OS/browser/viewport/ngày/đích/release và tester bằng mã, không thu serial/IMEI. Kiểm tra Wi-Fi văn phòng và mạng di động (HTTPS công khai tin cậy), ít nhất một mạng yếu/mất kết nối. Không biến emulation viewport thành thiết bị thật.

## Checklist thực hiện cho mỗi thiết bị

- [ ] HTTPS chain/domain hợp lệ, HTTP chuyển HTTPS; secure context; cookie Secure/HttpOnly/SameSite và session hết hạn/logout/back không lộ quyền.
- [ ] Login User dùng mật khẩu được cấp ngay, tự đổi/reset bởi Admin theo quyền; không chia sẻ mật khẩu trong phiếu phản hồi.
- [ ] Luồng Office → lunch → Office → Checkout; Remote → lunch → Remote → Checkout; Office/Remote xen kẽ hai ca. Mỗi lần vào Office xin GPS một lần; sau lunch xác minh lại. Ngoài vùng/hole từ chối, không tự Remote.
- [ ] GPS quyền allow/prompt/deny, vị trí unavailable/timeout, hệ điều hành tắt Location, quyền approximate nếu thiết bị hỗ trợ; lỗi giữ trạng thái, có hướng dẫn/thử lại. Độ chính xác lớn được ghi nhận để đánh giá, không chặn Office nếu điểm ST_Covers hợp lệ.
- [ ] Remote/nghỉ/lunch/Checkout vẫn thực hiện khi quyền GPS bị từ chối; không hiện prompt, không gọi watchPosition, không tọa độ/accuracy trong localStorage/sessionStorage hoặc log debug.
- [ ] Xin nghỉ chọn BUỔI SÁNG/CẢ NGÀY trước nhập lý do. Nghỉ sáng resume Office/Remote, reload vẫn chỉ CHECK-OUT cuối ngày, không lý do sớm. Full-day khóa ngày không hủy làm tiếp.
- [ ] CHECK-OUT SỚM cần lý do trim 1–1000 ký tự và xác nhận; đóng/mở giữ bản nháp; sau mọi Checkout reload/API đều khóa ngày. Chỉ thử Admin reset trên tài khoản/ngày thử ở staging được duyệt, không xóa dữ liệu pilot để test.
- [ ] Mạng chậm/timeout trước gửi; mất phản hồi sau server commit; bấm lại/reload/retry không tạo phiên trùng. Remote giữ cùng UUID/payload sau reload; Office không GPS storage, reload phải đọc trạng thái server trước thao tác mới. Không tự tạo UUID mới khi chưa rõ kết quả cũ.
- [ ] Hai tab cùng tài khoản: revision cũ bị chặn, trạng thái tải lại đúng. Đăng xuất/reset password ở tab khác làm session cũ bị chặn; User không vào API Admin hoặc lịch sử người khác.
- [ ] Trước/đúng/sau 20:00 giờ Việt Nam: không bắt đầu/resume/switch dù NOT_STARTED; nguồn tự đóng SYSTEM rõ ràng. Lunch không kéo dài phiên. Ngày Việt Nam mới mở lại; không đổi đồng hồ thiết bị để vượt cutoff. Thử clock điều khiển chỉ staging có công cụ được duyệt, không sửa giờ server thật để mô phỏng.
- [ ] Admin tổng/danh sách/7 nhóm đúng User, không tính Admin; Onsite đúng vị trí Check-in đã xác minh, không vị trí trực tiếp. Rời Office Marker biến mất sau refresh; thiếu GPS không Marker giả.
- [ ] Dashboard visible refresh 30 giây, quay lại tab/back/forward/suspend máy/đổi mạng phục hồi. Bfcache thật ghi persisted có/không, không chỉ dispatch sự kiện; snapshot lỗi có nhãn cũ, map lỗi vẫn xem danh sách/lịch sử.
- [ ] Tên/lý do tiếng Việt dài không tràn ngang, bàn phím điện thoại/focus/chạm thao tác xác nhận dùng được. Không đưa HTML thực thi, không lộ mật khẩu trong screenshot.

Phiếu kết quả mỗi case: `Case ID | thiết bị/OS/browser | release/domain | thời gian VN | bước | mong đợi | thực tế | pass/fail/not-run | issue ID | tester mã hóa`. Ảnh chỉ khi cần, che tên/lý do/địa chỉ/tọa độ/token; không đính kèm network body hoặc cookie.

## Pilot khoảng 10 người trong 5 ngày làm việc

Điều kiện bắt đầu: local gate đạt; đích HTTPS và DB/worker/log/backup được duyệt/xác minh; Geofence đúng do owner chấp nhận; người tham gia được thông báo dữ liệu thu thập/retention/GPS chỉ khi Office, Onsite không tracking; xác định dữ liệu pilot có dùng nghiệp vụ chính thức hay không. Không bắt người dùng ra khỏi Geofence để hoàn tất Office hoặc cho dùng điểm giả.

| Ngày làm việc | Hoạt động và bằng chứng |
| --- | --- |
| D1 | Khoảng 10 User thật + 1 Admin quản lý; hướng dẫn User/Admin, login/Office hoặc Remote thực tế; kiểm tra Dashboard/Onsite, kiểm kê lỗi và backend samples |
| D2 | Các luồng hai ca theo nhu cầu làm việc thật; quan sát permission/accuracy/GIS, mạng di động; hỗ trợ các case thiếu trên tài khoản staging riêng |
| D3 | Nghỉ sáng/cả ngày nếu thực sự có nhu cầu; nếu không có, kiểm thử có kiểm soát ở staging, ghi rõ chưa quan sát tự nhiên; retry/mạng yếu trong phạm vi được tester đồng ý |
| D4 | Kiểm tra back/forward/tab/suspend, worker cutoff và ngày mới; diễn tập vận hành không phá dữ liệu pilot, xem backup/health/alert |
| D5 | Hoàn tất checklist còn thiếu, hồi quy lỗi đã sửa, tổng hợp AC/NFR, phản hồi sử dụng và owner quyết định đạt/chưa đạt |

Ngày cụ thể **chưa chốt**; 5 ngày làm việc có thể qua cuối tuần, không thay bằng 5 lượt script. Ghi số người thực tham gia từng ngày, thiết bị và số request đo; thiếu ngày/người phải nêu rõ, không tự xác nhận đủ pilot. Lỗi quan trọng cần sửa → chạy lại luồng ảnh hưởng và kéo dài pilot nếu chưa đủ bằng chứng ổn định.

Thu thập phản hồi tối giản theo ngày: mã người tham gia, case/time, thao tác, mong đợi/thực tế, lỗi hiển thị/code, mạng/thiết bị, mức cản trở, mức dễ dùng 1–5 và ghi chú tùy chọn. Không ghi password/token/DSN/tọa độ/lý do nghỉ cá nhân. Owner giữ mapping mã→người ở nơi kín nếu cần hỗ trợ. Review hằng ngày bởi người phụ trách pilot; không tự gửi email/chat.

Backend: thu toàn bộ api_request hợp lệ trong 5 ngày, mẫu có timestamp/route template/status/duration_ms; thống kê mỗi ngày và toàn pilot p50/p95/p99/max, tỷ lệ ≤2000ms, tỷ lệ thành công trong ngưỡng và lỗi riêng theo endpoint. Không bỏ request chậm/lỗi, không tính GPS/client RTT. Báo rõ số mẫu và phần log bị mất; không coi mẫu rỗng là đạt. Dùng cùng công thức nearest-rank của `scripts.phase6_load.summarize` trên log đã khử nhạy cảm.

GPS: chỉ thống kê tổng số lần thử Office/thành công/outside/deny/timeout, accuracy trung bình/phân vị trên các lần lấy được GPS; accuracy không thành gate. Không thêm tracking GPS hoặc log tọa độ để đo. Số liệu từ người thử/DB tổng hợp được owner cho phép; không xuất raw điểm hoặc lý do. NFR-05 còn cần kiểm tra DB/worker ổn định và sự cố reconnect thực.

## Phân loại, dừng và nghiệm thu

- Critical: mất/rò dữ liệu, sai quyền, trùng phiên hoặc ghi không thể đối soát → dừng pilot mutation, owner xử lý/backup và điều tra; không xóa dữ liệu để làm sạch bằng chứng.
- Important: không thể hoàn tất Office/Remote/nghỉ/Checkout hoặc worker/HTTPS liên tục lỗi → xử lý trước nghiệm thu, hồi quy và thêm thời gian theo dõi.
- Minor: lỗi trình bày có workaround, ví dụ timeline khi timestamp bằng nhau; ghi ảnh hưởng/tần suất, owner quyết định chấp nhận có điều kiện.

Đạt khi đủ khoảng 10 User/5 ngày làm việc, toàn AC theo hợp đồng hiện hành đạt, không lỗi mất dữ liệu/trùng phiên/sai phân quyền, NFR-04 ≥95% backend API ≤2 giây (báo tỷ lệ lỗi và endpoint yếu), NFR-01/02/03/05 có bằng chứng thiết bị/quyền riêng tư/độ ổn định; owner vận hành tiếp nhận runbook/backup/rollback. Chưa đủ thì **chưa nghiệm thu**, dù test local xanh.

## Mẫu báo cáo pilot — chưa có kết quả thực tế

`Ngày bắt đầu/kết thúc: chưa chạy; domain/release: chưa có; người/ngày: chưa có; thiết bị: chưa kiểm chứng; backend samples: 0 (không kết luận hiệu năng); GPS thực: chưa đo; issue/khắc phục: chưa có; AC/NFR: pending cổng T/P; quyết định và chữ ký owner: chưa có.`
