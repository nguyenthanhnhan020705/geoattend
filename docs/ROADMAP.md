# GeoAttend — Lộ trình phát triển MVP

Điều chỉnh Xin nghỉ tiếp theo: chọn buổi rồi lý do; sau nghỉ sáng tiếp tục ca chiều rồi CHECK-OUT cuối ngày; nghỉ cả ngày kết thúc ngày. Full suite mới **267 passed, 1 warning**, `pip check`/`git diff --check` đạt. Xem [báo cáo mới](LEAVE_FLOW_VERIFICATION.md). Các số test ở các mốc trước là bằng chứng lịch sử.

Điều chỉnh sau Phase 5, 16/10/2026: CHECK-OUT SỚM bắt buộc lý do và kết thúc ngày; mọi Check-out khóa đến ngày hôm sau. Full suite mới **259 passed, 1 warning**, `pip check`/`git diff --check` đạt. Xem [báo cáo điều chỉnh](EARLY_CHECKOUT_VERIFICATION.md); kết quả 249 test bên dưới là mốc Phase 5 trước thay đổi này.

## 1. Mục đích và hiện trạng

Chia phạm vi trong [BRD](../README.md) thành các phase có thứ tự phụ thuộc, công việc và điều kiện hoàn thành rõ ràng.

Tại thời điểm bắt đầu dự án (14/10/2026), workspace chỉ có `README.md`. Hiện **Phase 0–5 đã triển khai** trong worktree `.worktrees/phase-1`, nhánh `feat/phase-1-foundation-auth`. Phase 3/4 và các bổ sung lịch sử Admin/UI User được giữ nguyên. Phase 5 bổ sung Dashboard/Onsite, đã review độc lập và chạy full suite **249 passed** ngày 16/10/2026; xem [báo cáo Phase 5](PHASE_5_VERIFICATION.md). Phase 6 production/pilot **chưa thực hiện**; chưa chứng nhận mục tiêu hiệu năng.

Đây là roadmap cấp dự án. Thiết kế và kế hoạch triển khai chi tiết sẽ được lập theo từng phase, sau khi các quyết định nghiệp vụ liên quan đã được chốt. Roadmap không tự quyết định thay các câu hỏi mở trong BRD.

## 2. Tổng quan các phase

| Phase | Trọng tâm | Kết quả có thể kiểm tra | Phụ thuộc |
| --- | --- | --- | --- |
| 0 | Chốt nghiệp vụ và thiết kế MVP | Bộ quyết định nghiệp vụ, sơ đồ trạng thái, mô hình dữ liệu và phạm vi API | BRD |
| 1 | Nền tảng, database và đăng nhập | Chạy ứng dụng, kết nối database, đăng nhập và phân quyền User/Admin | Phase 0 |
| 2 | Phiên làm việc và Remote | Nhân viên bắt đầu/kết thúc Remote, xem trạng thái và lịch sử đã lưu | Phase 1 |
| 3 | Geofence và Office | Admin cấu hình vùng; nhân viên Check-in Office với xác minh GPS | Phase 2 |
| 4 | Nghỉ trưa, nghỉ và luồng hỗn hợp | Hoàn thành các kịch bản làm việc trong ngày theo BRD | Phase 3 |
| 5 | Dashboard và bản đồ Admin | Theo dõi trạng thái, bản đồ Onsite và lịch sử từng nhân viên | Phase 4 |
| 6 | Kiểm thử tổng thể, triển khai và pilot | MVP chạy trên môi trường thử nghiệm với khoảng 10 người dùng | Phase 5 |

Thứ tự thực hiện: **0 → 1 → 2 → 3 → 4 → 5 → 6**.

Ưu tiên hoàn thành luồng Remote trước để kiểm chứng phiên làm việc, phân quyền và lưu dữ liệu. Sau đó bổ sung xác minh không gian cho Office trên cùng nền tảng. Mỗi phase chức năng bao gồm cả API, giao diện tối thiểu và kiểm thử liên quan.

## 3. Chi tiết từng phase

### Phase 0 — Chốt nghiệp vụ và thiết kế MVP

**Mục tiêu:** có đủ quy tắc để triển khai nhất quán.

- [x] Rà soát workspace hiện tại: chỉ có tài liệu, chưa có mã nguồn để tái sử dụng; kế hoạch dựng nền tảng từ đầu trong workspace này.
- [x] Chốt TBD-01 — Phương án A: Check-out đóng phiên đang mở, không lấy GPS hoặc kiểm tra Geofence, kể cả khi ngoài vùng hoặc không có GPS.
- [x] Chốt phần ranh giới của TBD-02: chấp nhận trong vùng và trên ranh giới; từ chối ngoài vùng, không dùng vùng đệm.
- [x] Chốt phần độ chính xác GPS của TBD-02: chỉ lưu để tra cứu, không dùng sai số làm điều kiện từ chối Check-in hoặc tiếp tục Office.
- [x] Chốt phần lỗi GPS của TBD-02: không tạo phiên Office, giữ nguyên trạng thái, hướng dẫn bật quyền/thử lại; người dùng có thể tự chọn Remote và nhập lý do, không tự chuyển Remote.
- [x] Chốt phần sáng/chiều của TBD-03: sau nghỉ sáng, nhân viên tự bắt đầu Office/Remote khi quay lại, không khóa theo mốc giờ sáng/chiều nhưng phải trước 20:00.
- [x] Chốt tự đóng phiên của TBD-03: lúc 20:00 hằng ngày, đóng các phiên Office/Remote còn mở; ghi rõ do hệ thống đóng, không coi là giờ kết thúc thực tế.
- [x] Chốt múi giờ và giới hạn ngày của TBD-03: dùng giờ Việt Nam (`Asia/Ho_Chi_Minh`, UTC+07:00); từ đúng 20:00 đến hết ngày không cho bắt đầu/tiếp tục Office hoặc Remote.
- [x] Chốt bắt đầu lại sau Check-out (TBD-04): cho phép tạo phiên mới trước 20:00 giờ Việt Nam; Office xác minh GPS lại, Remote nhập lý do; giữ nguyên lịch sử phiên cũ.
- [x] Chốt thay đổi nghỉ cả ngày (TBD-04): cho phép hủy nghỉ để bắt đầu Office/Remote trước 20:00 giờ Việt Nam; lưu lịch sử đăng ký và hủy nghỉ.
- [x] Chốt chuyển trực tiếp Office ↔ Remote (TBD-04): trước 20:00, xác minh GPS/lý do cho chế độ mới rồi đóng phiên cũ và tạo phiên mới; nếu kiểm tra thất bại giữ nguyên phiên hiện tại.
- [x] Chốt TBD-05: Admin sửa tên, địa chỉ văn phòng và Polygon Geofence; cố định giờ Việt Nam và mốc tự đóng 20:00 trong MVP.
- [x] Chốt TBD-06: khoảng 10 người dùng trong 5 ngày làm việc; toàn bộ tiêu chí chức năng đạt; không còn lỗi mất dữ liệu, trùng phiên hoặc sai phân quyền; ít nhất 95% yêu cầu API xử lý tại Backend trong tối đa 2 giây, không tính thời gian lấy GPS; thống kê độ chính xác GPS.
- [x] Chốt TBD-07: tự động xóa tọa độ và độ chính xác GPS sau 30 ngày kể từ lúc ghi nhận; giữ lịch sử phiên và kết quả xác minh, hiển thị thông báo hết hạn vị trí.
- [x] Chốt xử lý `LUNCH_BREAK` lúc 20:00: chuyển `CHECKED_OUT`, ghi “hệ thống kết thúc ngày”, không kéo dài phiên trước nghỉ trưa.
- [x] Hoàn thiện và duyệt bảng chuyển trạng thái, quy tắc thao tác lặp/đồng thời trong [STATE_TRANSITIONS.md](STATE_TRANSITIONS.md) và thiết kế Phase 0.
- [x] Duyệt mô hình dữ liệu/ERD đã viết tại mục 4 của bản thiết kế Phase 0, gồm cả dữ liệu xác thực và GPS tách riêng.
- [x] Chốt phương thức đăng nhập theo yêu cầu cập nhật: tên tài khoản/mật khẩu do Admin tạo và cấp cho User; không đăng ký công khai hoặc đăng nhập Google trong MVP.
- [x] Chốt đổi mật khẩu lần đầu: User dùng ngay mật khẩu được cấp, có thể chủ động đổi sau; không bắt buộc đổi ở lần đăng nhập đầu tiên.
- [x] Chốt khôi phục mật khẩu User: Admin đặt lại và cấp mật khẩu mới, User được dùng ngay và tự đổi sau; không khôi phục qua email trong MVP.
- [x] Chốt số lượng Admin: một tài khoản Admin được khởi tạo khi thiết lập hệ thống, không có chức năng cấp thêm quyền Admin trong MVP.
- [x] Chốt phạm vi Admin: chỉ quản lý, không chấm công cá nhân; không tính vào số nhân viên và nhóm trạng thái/Onsite.
- [x] Chốt tổ chức ứng dụng: FastAPI phục vụ giao diện HTML/CSS/JavaScript và API trên cùng một địa chỉ.
- [x] Duyệt thiết kế kỹ thuật: đã có [bản thiết kế Phase 0](superpowers/specs/2026-10-14-geoattend-mvp-design.md) với xác thực, bản đồ, kết nối database, cấu trúc dự án và quy trình Admin.
- [x] Duyệt phác thảo màn hình và hợp đồng API đã viết tại mục 8–9 của bản thiết kế Phase 0: dữ liệu vào/ra, lỗi và quyền truy cập.

**Đầu ra:** tài liệu quyết định nghiệp vụ, sơ đồ trạng thái, ERD và thiết kế MVP; cập nhật BRD với những quyết định đã thống nhất.

**Điều kiện hoàn thành:** các câu hỏi mở có quyết định hoặc được loại khỏi phạm vi một cách rõ ràng; luồng Office, Remote, nghỉ và quyền truy cập không mâu thuẫn.

### Phase 1 — Nền tảng, database và đăng nhập

**Kế hoạch chi tiết:** [Phase 1 — nền tảng và tài khoản](superpowers/plans/2026-10-14-phase-1-foundation-auth.md), đã được người dùng duyệt bằng việc chọn `superpowers:executing-plans`; đã thực hiện 6 task, qua review độc lập và lượt sửa cuối. [Kết quả kiểm chứng](PHASE_1_VERIFICATION.md): 46 kiểm thử đạt.

**Yêu cầu BRD:** FR-01, FR-16, FR-17, FR-18; nền tảng NFR-01, NFR-03.

- [x] Dựng Backend FastAPI, Frontend cơ bản và cấu hình môi trường mẫu không chứa bí mật.
- [x] Thiết lập PostgreSQL/PostGIS và migration cho 9 bảng ứng dụng theo thiết kế Phase 0; tách dữ liệu xác thực, trạng thái ngày và GPS khỏi phiên/sự kiện.
- [x] Thiết lập quy trình khởi tạo một Admin khi cài đặt; chạy lại không tạo thêm Admin, không đưa mật khẩu vào mã nguồn/Git. Dữ liệu User/văn phòng được tạo trong database kiểm thử riêng, không cấp tài khoản thực tế tự động.
- [x] Triển khai đăng nhập bằng tên tài khoản/mật khẩu, đăng xuất và xác thực phía Backend theo AC-01.
- [x] Triển khai đổi mật khẩu cá nhân tùy chọn, không chặn lần đăng nhập đầu tiên; kiểm thử mật khẩu cũ/mới sau khi đổi theo AC-18.
- [x] Triển khai giao diện/API Admin tạo và cấp tài khoản User; kiểm tra tên tài khoản duy nhất, quyền tạo tài khoản và vai trò mặc định `USER` theo AC-17.
- [x] Triển khai Admin đặt lại mật khẩu User theo AC-19; kiểm thử quyền truy cập, mật khẩu cũ/mới và bảo toàn lịch sử.
- [x] Áp dụng phân quyền cho API và điều hướng giao diện theo vai trò.
- [x] Có kiểm tra tình trạng dịch vụ/database, hướng dẫn chạy local và nền tảng chạy kiểm thử.

**Đầu ra:** ứng dụng chạy local, người dùng đăng nhập và truy cập đúng chức năng theo vai trò.

**Điều kiện hoàn thành:** dựng được database từ migration trên môi trường mới; tài khoản hợp lệ đăng nhập được; yêu cầu chưa xác thực hoặc sai quyền bị từ chối ở Backend; cấu hình bí mật không được đưa vào Git.

### Phase 2 — Phiên làm việc và luồng Remote

**Yêu cầu BRD:** FR-03, FR-08 (Remote), FR-09, FR-10 (cá nhân); BR-02, BR-05.

- [x] Xây dựng cơ chế tạo/đóng phiên và ghi sự kiện nhất quán trong transaction.
- [x] Triển khai Check-in Remote có lý do và Check-out Remote; hỗ trợ tạo phiên mới sau Check-out trước 20:00, giữ nguyên phiên cũ theo AC-12.
- [x] Triển khai cơ chế tự đóng phiên lúc 20:00 giờ Việt Nam và chặn bắt đầu/tiếp tục Office/Remote từ 20:00 đến hết ngày, phân biệt với Check-out thủ công; chạy lặp không tạo sự kiện trùng. Kiểm thử mốc trước/đúng/sau 20:00 và cơ chế xử lý bù khi tác vụ chạy trễ theo thiết kế được chốt.
- [x] Tính trạng thái hiện tại theo bảng chuyển trạng thái đã chốt.
- [x] Xây dựng màn hình trạng thái, thao tác Remote và lịch sử cá nhân.
- [x] Ngăn thao tác không hợp lệ, phiên mở trùng và ghi nhận trùng khi gửi lại yêu cầu.
- [x] Kiểm thử truy cập chéo lịch sử giữa hai nhân viên.

**Đầu ra:** đăng nhập → Remote → Check-out → xem lịch sử, dữ liệu tồn tại sau tải lại trang.

**Điều kiện hoàn thành:** AC-03 và phần Remote/cá nhân của AC-01, AC-06 đạt; thiếu lý do bị từ chối; thao tác lặp không tạo phiên trùng; Remote không yêu cầu vị trí; người dùng không đọc được lịch sử người khác.

### Phase 3 — Geofence và luồng Office

**Đã thực hiện:** [kế hoạch Phase 3](superpowers/plans/2026-10-15-phase-3-office-geofence.md), [kiểm chứng 119/119](PHASE_3_VERIFICATION.md). Admin cấu hình vùng thực tế qua `/admin/office`; hệ thống không tự chọn tọa độ văn phòng.

**Yêu cầu BRD:** FR-02, FR-08 (Office), FR-14; BR-01, BR-08; phần GPS của NFR-02, NFR-05.

- [x] Xây dựng giao diện bản đồ để Admin xem/chỉnh sửa và lưu Geofence.
- [x] Kiểm tra Polygon hợp lệ và quyền quản trị tại API.
- [x] Lấy vị trí bằng Browser Geolocation khi nhân viên thực hiện thao tác Office cần xác minh.
- [x] Kiểm tra Point-in-Polygon phía Backend bằng PostGIS theo quy tắc ranh giới/sai số đã chốt.
- [x] Triển khai Check-in Office và Check-out Office theo quyết định TBD-01; xác minh GPS lại khi tạo phiên Office mới sau Check-out theo AC-12.
- [x] Ghi kết quả xác minh, vị trí và độ chính xác phù hợp với chính sách dữ liệu.
- [x] Triển khai tự động xóa tọa độ/độ chính xác GPS đủ 30 ngày, không trả vị trí hết hạn qua API; giữ lịch sử phiên và kết quả xác minh, kiểm thử theo AC-16.
- [x] Hiển thị lỗi dễ hiểu khi ngoài vùng, thiếu quyền vị trí, GPS lỗi; lưu độ chính xác GPS để tra cứu, không từ chối chỉ vì sai số lớn.

**Đầu ra:** Admin lưu vùng văn phòng; nhân viên trong vùng Check-in Office và xem phiên đã ghi nhận.

**Điều kiện hoàn thành:** AC-02, AC-09 và phần Office của AC-06 đạt; kiểm tra được điểm trong/ngoài/trên ranh giới và lỗi GPS; không lấy vị trí liên tục; User không sửa được Geofence.

### Phase 4 — Nghỉ trưa, nghỉ và luồng làm việc hỗn hợp

**Yêu cầu BRD:** FR-04 đến FR-07; BR-03, BR-04, BR-09; các kịch bản tại mục 6.4 của BRD.

- [x] Triển khai nghỉ trưa: đóng phiên và ghi trạng thái `LUNCH_BREAK`; lúc 20:00 tự chuyển `CHECKED_OUT`, ghi sự kiện kết thúc ngày mà không kéo dài phiên cũ theo AC-11.
- [x] Triển khai tiếp tục Office/Remote, áp dụng lại xác minh vị trí hoặc yêu cầu lý do.
- [x] Triển khai nghỉ buổi sáng/cả ngày có lý do, không phê duyệt và không lấy GPS.
- [x] Cho phép bắt đầu làm việc sau nghỉ sáng theo quy tắc đã chốt.
- [x] Cho phép hủy nghỉ cả ngày để bắt đầu Office/Remote trước 20:00; giữ lịch sử đăng ký/hủy và loại nghỉ đã hủy khỏi thống kê nghỉ cả ngày còn hiệu lực theo AC-13.
- [x] Triển khai chuyển trực tiếp Office ↔ Remote trước 20:00, đóng/mở phiên trong cùng giao dịch sau khi kiểm tra điều kiện; kiểm thử chuyển thành công và thất bại theo AC-14.
- [x] Hoàn thiện Timeline gồm phiên làm việc và các sự kiện nghỉ.
- [x] Kiểm thử tất cả kịch bản sáng/chiều trong BRD và các chuyển trạng thái bị cấm.

**Đầu ra:** nhân viên thực hiện trọn ngày Office/Remote, đổi hình thức sau nghỉ trưa hoặc ghi nhận nghỉ.

**Điều kiện hoàn thành:** AC-04, AC-05 đạt; cả 8 kịch bản tại mục 6.4 của BRD có kết quả đúng; phiên và trạng thái không mâu thuẫn; tiếp tục Office xác minh lại GPS; nghỉ không kích hoạt lấy vị trí.

### Phase 5 — Dashboard và bản đồ Admin

**Yêu cầu BRD:** FR-10 (Admin), FR-11 đến FR-13, FR-15; BR-06, BR-07.

**Đã thực hiện:** [bàn giao và Task 1–5](../handoff/README_PHASE_0_5.md), [kiểm chứng](PHASE_5_VERIFICATION.md), [checklist](MANUAL_TEST_PHASE_5.md). Không có migration hoặc editor văn phòng/lịch sử thứ hai. Minor lifecycle back/forward cache có điều kiện được ghi rõ trong báo cáo.

- [x] Hiển thị tổng số và danh sách mọi tài khoản `USER`, gồm chưa bắt đầu/bị khóa; bảy nhóm trạng thái, loại Admin theo AC-07.
- [x] Hiển thị Geofence và Marker có tên cho nhân viên đang `WORKING_OFFICE`.
- [x] Dùng điểm đã xác minh của đúng phiên Office đang mở; ghi rõ đây là vị trí Check-in, không phải GPS trực tiếp.
- [x] Hiển thị Popup tên, trạng thái, giờ Check-in, xác minh GPS và liên kết lịch sử dùng dialog hiện có.
- [x] Tái sử dụng lịch sử/xóa ngày [ADMIN_HISTORY](ADMIN_HISTORY.md); GPS đủ 30 ngày bị che trước purge, không Marker giả và có thông báo hết hạn theo AC-16.
- [x] Làm mới mỗi 30 giây khi tab visible, khi quay lại tab hoặc tải tay; bảo vệ phản hồi cũ và giữ snapshot có nhãn cũ khi mạng lỗi.
- [x] Tái sử dụng editor tên/địa chỉ/Polygon, bổ sung điều hướng; hồi quy revision/quyền, giữ cố định giờ Việt Nam và cutoff 20:00 theo AC-15.

**Đầu ra:** Admin theo dõi trạng thái, bản đồ và lịch sử từ dữ liệu thực của các phase trước.

**Điều kiện hoàn thành:** AC-07, AC-08 và phần Admin của AC-01 đạt; số lượng khớp danh sách; Marker rời nhóm Onsite sau nghỉ trưa/Remote/Check-out khi dữ liệu được làm mới; User không truy cập được API Admin; FR-15 được kiểm tra theo danh sách cài đặt đã chốt.

### Phase 6 — Kiểm thử tổng thể, triển khai và pilot

**Yêu cầu BRD:** toàn bộ AC-01 đến AC-19, NFR-01 đến NFR-05 và các ngưỡng thống nhất ở Phase 0.

- [ ] Chạy kiểm thử hồi quy API, database, phân quyền, trạng thái và GIS.
- [ ] Kiểm tra luồng đầu cuối trên điện thoại/máy tính và tình huống gửi lại thao tác khi mạng không ổn định.
- [ ] Đo thời gian xử lý tại Backend và xác nhận ít nhất 95% yêu cầu API hoàn tất trong tối đa 2 giây, không tính thời gian lấy GPS; thống kê độ chính xác GPS để đánh giá, không dùng làm ngưỡng chặn Check-in.
- [ ] Kiểm tra chính sách thu thập/lưu/xóa vị trí và nội dung log.
- [ ] Triển khai Backend/Frontend qua HTTPS để kiểm tra Browser Geolocation trên môi trường thực tế.
- [ ] Thiết lập cấu hình production, migration, log vận hành, sao lưu và hướng dẫn khôi phục.
- [ ] Chạy pilot với khoảng 10 người dùng trong 5 ngày làm việc, ghi nhận lỗi và phản hồi.
- [ ] Sửa lỗi cản trở sử dụng, kiểm tra lại các luồng bị ảnh hưởng và tổng hợp kết quả nghiệm thu.

**Đầu ra:** bản MVP dùng được trên môi trường thử nghiệm, hướng dẫn sử dụng User/Admin và báo cáo pilot.

**Điều kiện hoàn thành:** tiêu chí nghiệm thu chức năng và ngưỡng vận hành đã thống nhất đều đạt; lỗi cản trở luồng chính được xử lý, không còn lỗi gây mất dữ liệu, trùng phiên hoặc sai phân quyền; có bằng chứng kiểm thử và kết quả pilot trong 5 ngày làm việc.

## 4. Nguyên tắc thực hiện và theo dõi

- Mỗi phase được chia tiếp thành các task có đầu ra kiểm chứng được trước khi viết mã.
- Chỉ đánh dấu hoàn thành khi đã kiểm tra đầu ra và lưu bằng chứng phù hợp; có giao diện nhưng chưa lưu dữ liệu thực chưa được xem là hoàn thành luồng.
- Kiểm thử đi cùng từng phase; Phase 6 tập trung tích hợp, thiết bị thật và pilot.
- Quy tắc nghiệp vụ được xác nhận phải cập nhật về BRD để tài liệu và triển khai thống nhất.
- Chưa gán lịch theo tuần vì chưa biết số người phát triển và thời gian dành cho dự án. Ước lượng sau khi chia task và xác nhận nguồn lực.
- PWA, notification, xuất báo cáo, Audit Log, Correction Request, QR, nhiều văn phòng/phòng ban, mobile và AI/RAG thuộc giai đoạn sau MVP.

**Bước tiếp theo:** Phase 5 — Dashboard, Onsite và lịch sử nhân viên cho Admin, dùng trạng thái và lịch sử bất biến của Phase 4. Xem [hướng dẫn chạy](DEVELOPMENT.md). Ứng dụng local đang dùng Supabase; bộ kiểm thử tự động dùng database riêng. Chưa triển khai production hoặc chạy pilot.
