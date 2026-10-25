# Kiểm chứng tóm tắt PDF

## Điều hướng tuần Admin ngày 25/10/2026

Thêm Trước/Sau dưới ô ngày, chuyển một tuần rồi tự tải, giữ nhân viên đang chọn và reset trang 1. RED thiếu nút Tuần trước; GREEN 2 ca desktop/mobile 1280/360: đã nộp → tuần thiếu → đã nộp, giữ đúng nhân viên, chọn Chủ Nhật qua năm mới, bấm nhanh hai lần, xem tất cả và không tràn ngang. Không đổi API, dữ liệu, quyền, worker hay logic xác định thiếu tuần.

## Khắc phục lỗi đầu ra ngày 25/10/2026

Chẩn đoán file 3 trang: Gemini HTTP 200, STOP, JSON hợp lệ, readable=true, một đoạn 158 từ. Bộ kiểm tra cũ từ chối vì vượt 150 từ. File mới 5 trang cũng từng FAILED/INVALID_OUTPUT; thử lại trả 108 từ hợp lệ và đã lưu. Worker trước đó dừng riêng trong khi web vẫn chạy.

Provider `vi-paragraph-v2` giữ kiểm tra 80–150 từ. Chỉ với đầu ra 151–180 từ, một đoạn thuần văn bản, có thể giữ tiền tố kết thúc ở câu hoàn chỉnh trong khoảng 80–150 từ. Không thêm nội dung, không cắt giữa câu, không gọi AI thêm; không có điểm kết thúc phù hợp thì vẫn báo lỗi. Những lỗi định dạng khác không được bỏ qua. Worker chỉ ghi reason thuộc danh sách cố định, không ghi PDF/tóm tắt/phản hồi thô.

RED: 7 ca mới thất bại trước bản sửa. GREEN: 28 kiểm thử provider/worker trên cả source và checkout phục vụ 8000; sau đó 43 passed, 1 warning có sẵn với queue/API trên PostgreSQL kiểm thử UUID cổng 55442 (55441 báo bind denied). Phục hồi file 3 trang bằng một lượt sau bản sửa được người dùng duyệt: COMPLETE, 148 từ. Sáu PDF hiện hành đều COMPLETE lúc kiểm tra 08:51 ngày 25/10; bản tóm tắt cũ giữ nguyên. Hai lượt phục hồi ngoại lệ của file 3 trang được duyệt riêng và ghi audit ngoài Git; không reset attempt_count, không thay giới hạn retry của hệ thống. Web không khởi động lại. Kết quả bên dưới là lịch sử trước bản sửa này.

Ngày cập nhật: 24/10/2026. Nơi triển khai local: `.worktrees/pdf-summary`, nhánh `feat/pdf-summary`, tách từ main `7616426`.

Trạng thái mới nhất 24/10/2026: chức năng đã tích hợp vào checkout `.worktrees/phase-1` đang phục vụ `http://127.0.0.1:8000/`, giữ bản thử `8002` riêng. Người dùng đã cho phép Gemini xử lý cả PDF cũ/mới của bản chính; worker chính đã bật. Migration `008` và quyền runtime có sẵn, không chạy lại/sửa migration cũ. Public đã chuẩn bị gói phát hành; chưa merge, push hoặc publish.

## Kiểm chứng triển khai local ngày 24/10/2026

**Preview trong trang theo yêu cầu mới nhất:** Xem trước PDF mở khung dưới báo cáo, không mở tab, áp dụng User/Admin. Module `pdf-preview.js` dùng PDF.js đã vendored; có phân trang, đóng/bấm lại để ẩn, khung cuộn 420px/360px mobile. GET gửi xác thực và revision; stale không render, timeout/hỏng báo lỗi riêng, đóng/đổi DOM hủy request/render và giải phóng worker. Không sửa backend, worker Gemini hoặc quyền summary. Sáu file giao diện trang báo cáo đổi phiên bản `inline-preview-20261024`.

RED chứng minh thiếu canvas trong trang ở giao diện mở tab cũ. Source cuối đạt **47 passed, 1 warning, 283,84 giây**, log `inline-final.log`: User/Admin360/1280, chuyển trang, tải đúng byte, đóng/mở lại, không popup, stale, Pages bearer, preview timeout, upload/download/Admin Excel, summary chỉ Admin, quyền/CSRF/cache, build/artifact/health. Lượt green đầu có 5 lỗi trong test mới: bộ đếm tính cả download và Playwright tự gọi function được trả từ phép gán window.open; đã sửa đúng test harness, không đổi hành vi sản phẩm để né test. Riêng test Pages cũ chỉ cập nhật hành vi xem trước và đồng bộ clock với server fixture đã đóng băng, không sửa helper/menu/auth sản phẩm.

**Tích hợp bản chính 8000 và chuẩn bị public:** xác minh cổng 8000 chạy `.worktrees/phase-1`, khác checkout tính năng. 16 file runtime cần ghép khớp commit nền; sao lưu và ghép có kiểm tra các file feature/test, giữ byte của file ngoài phạm vi (manifest `main-integration-20261024/applied.json`). Venv bản chính đã có HTTPX đúng phiên bản, chỉ bổ sung pypdf 6.21.2, pip check sạch. Bộ kiểm tra tại chính checkout đó đạt **98 passed, 1 warning, 186,98 giây**; gồm provider/worker/queue/API/User/Admin/Pages/restore/upload/readiness/migrations/policy/health/auth. Log `.worktrees/phase-1/.local-tests/pdf-summary-main/verification.log`.

Đã kiểm tra read-only schema/quyền và 5 báo cáo trước chuyển. Khởi động lại đúng 4 tiến trình Python thuộc web 8000 từ launcher cũ, không dừng shell/IDE/8002/PostgreSQL. Launcher mới 23652, Uvicorn 20728; worker chính 10328 tại lúc bật, PID/log trong `phase-1/.local-tests/pdf-summary-main/`. HTTP health200/databaseOK, reports khi chưa đăng nhập401, API summary có trong OpenAPI và asset khớp source đã tích hợp. Không dùng tài khoản thử hoặc đổi mật khẩu tài khoản thật trên bản chính.

Backfill thực tế được người dùng duyệt: 5 job, 4 COMPLETE và 1 FAILED/INVALID_OUTPUT, attempt 1 cho mỗi job. Worker thường trực tiếp tục xử lý file mới; không tự retry job lỗi. Đối chiếu digest các bảng profiles, attendance_days, work_sessions, attendance_events, office_locations, weekly_reports trước/sau: giữ nguyên. Không in/lưu nội dung PDF hoặc summary vào log.

Public kiểm tra chỉ đọc: Pages dùng API `https://geoattend-api-a7xf.onrender.com`, backend health200/databaseOK, chưa có summary routes; Pages và remote main ở commit `7616426cfca5e2738156b71e0717e199b6662cf2`, workflow active. Gói patch/source/Pages được chuẩn bị trên đúng commit đó, không chứa bí mật; cấu hình worker riêng giữ ngoài archive. Chi tiết `docs/PDF_SUMMARY_RELEASE.md`. Cấu hình runtime Render có sẵn trùng thông tin kết nối local; vẫn đối chiếu lại secret settings thực tế trước phát hành. Các mục worker tắt/chỉ tổng hợp bên dưới là lịch sử đã được quyền mới thay thế.

**Phân quyền hiện hành — chỉ Admin thấy tóm tắt:** theo yêu cầu mới nhất, User chỉ có Xem trước PDF/Tải PDF; không render khung hoặc gọi API summary. Admin vẫn tự thấy kết quả/trạng thái/retry cạnh từng file. Hai URL summary (gốc và Admin) đều yêu cầu Admin; User GET/POST bị 403 kể cả báo cáo của chính mình. Upload/xem/tải PDF vẫn hoạt động, worker vẫn tự xử lý để Admin đọc kết quả. Tệp giao diện trang báo cáo đã đổi phiên bản `admin-summary-20261024`.

Đã quan sát RED riêng cho UI (User vẫn thấy 2 khung) và API (User đọc được 200 thay vì 403), rồi sửa. Bộ kiểm tra cuối **47 passed, 1 warning, 101,08 giây**, log `admin-only-green.log`; gồm User/Admin desktop/mobile, upload User và xem summary Admin trên Pages, API quyền/CSRF/stale/retry/thu hồi session, file/upload, build/artifact/health. Warning TestClient/HTTPX hiện có. Bản thử 8002 đã khởi động lại riêng web sau khi xác minh PID/cổng; worker giữ chạy. Kiểm tra trực tiếp HTTP và Edge: User không có khung/không request summary, User GET/POST summary 403, file GET 200, Admin GET summary 200 và hiển thị đúng cache. Metadata tại `preview-20261024/admin-only-verification.json`, không lưu/in tài liệu hay summary. Tài khoản `previewadmin` do bản thử tự tạo đã được cấp mật khẩu thử để người dùng kiểm tra giao diện Admin; không chỉnh tài khoản Supabase hoặc dữ liệu báo cáo. Các mục bên dưới là lịch sử trước thay đổi phân quyền này.

**Giao diện hiện hành sau khi người dùng làm rõ yêu cầu:** tóm tắt tự hiển thị cạnh thông tin file, chỉ còn Tải PDF/Xem trước PDF. Không cần nút mở tóm tắt. Mỗi dòng báo cáo có khung và vòng cập nhật riêng; khi đổi trang/bộ lọc, khung cũ hủy request/timer. Trên mobile khung nằm dưới thông tin file. Tệp trang báo cáo, module nhập và CSS có phiên bản `auto-summary-20261024` để tránh dùng module cũ sau khi tải lại. Kiểm tra HTTP xác nhận 8002 phục vụ đúng mã worktree, không chứa nút gộp hoặc nút mở summary. Cổng 8000 đang phục vụ mã khác, không được thay đổi trong lượt này.

Kiểm chứng: RED thấy vẫn có nút thứ ba trước thay đổi; 7 ca browser đầu đạt sau sửa. Bộ mở rộng có thêm Admin nhiều báo cáo: 46 passed, 1 failed (validator artifact coi phần query của URL module là tên file). Sửa đúng validator để kiểm tra `urlsplit(ref).path`, giống cách nó đã kiểm tra URL HTML; chạy lại build/artifact đạt 18/18. Các ca User/Admin desktop/mobile, summary hiện tự động, tải/xem PDF theo lựa chọn, upload Pages tự cập nhật, retry, stale revision, hủy polling và nhiều summary độc lập đều đạt. Log: `auto-red.log`, `auto-green.log`, `auto-final.log`; không chạy lại toàn dự án. Preview dữ liệu hiện có: revision 4, 137 đơn vị, COMPLETE/attempt 1, tự hiển thị và reload dùng cache; không lưu ảnh hoặc in nội dung tài liệu. Các đoạn bên dưới là bằng chứng lịch sử của giao diện trước.

**Yêu cầu giao diện mới:** người dùng yêu cầu tách Tải PDF / Xem trước PDF / Tóm tắt PDF. Nút tóm tắt chỉ đọc endpoint summary và mở khung nội dung; bỏ việc tải/render PDF trong khung này. Các bằng chứng canvas/hai cột dưới đây mô tả thiết kế ban đầu, đã được thay bằng kiểm tra ba thao tác độc lập. Chỉ đổi ba selector báo cáo từ Xem PDF sang Xem trước PDF trong test Pages files hiện có để khớp nhãn người dùng yêu cầu, không sửa helper/menu/auth/timing.

Kiểm chứng điều chỉnh: test RED ghi nhận giao diện cũ chưa có ba thao tác đúng thứ tự. Bộ cuối đạt **46 passed, 1 warning** trong 55,12 giây (`separate-final.log`): User/Admin 360px/1280px, tải PDF đúng byte, xem trước mở cửa sổ riêng, summary không tải file/PDF.js/canvas, đóng/mở lại không gọi AI, retry/poll/close/stale revision, Pages bearer, API/upload/build/artifact/health. Lượt đầu lộ race trong test mới đọc danh sách nút trước khi Admin tải dữ liệu; sửa bằng assertion chờ của Playwright, không đổi timeout/helper chung. Preview file 5 trang kiểm tra trực tiếp summary riêng/cached 140 đơn vị/attempt 1, không in nội dung hoặc lưu ảnh tài liệu người dùng. Build Pages riêng thành công; không publish.

**Bản xem thử có thể thao tác:** `http://127.0.0.1:8002/user/weekly-reports`, tài khoản local `pdfdemo`, database UUID `geoattend_test_pdf_preview_*` trên cổng 55441. Dùng cùng code GeoAttend và PDF tổng hợp hỗn hợp 10 trang; Gemini tạo đoạn 120 đơn vị trong 6,59 giây, attempt 1. Đã kiểm tra bằng Edge headless: đăng nhập, mở PDF và summary, chuyển trang, đóng/mở lại dùng kết quả lưu, desktop/mobile không tràn ngang và không có lỗi JavaScript. Ảnh tại `.local-tests/pdf-summary/preview-20261024/desktop.png` và `mobile.png` là file tổng hợp ban đầu. Không tạo tài khoản/dữ liệu thử trên Supabase, không gửi 4 PDF hiện có. Launcher và state riêng được lưu trong thư mục ignored này.

**Cập nhật sau khi người dùng tải PDF 5 trang:** xác minh upload thành công, revision 3, chưa có job vì worker preview ban đầu tắt. Người dùng đã cho phép xử lý PDF họ chủ động tải lên bản thử 8002. Đã bật worker thường trực chỉ cho database preview được kiểm tra host/port/tên UUID; không truyền DSN Supabase. File 5 trang chuyển COMPLETE, 140 đơn vị, attempt 1. Edge xác minh canvas và summary đúng kết quả đã lưu, đóng/mở lại không tạo job/gọi AI mới. Không lưu ảnh chụp hay in nội dung tài liệu/tóm tắt của người dùng vào log. Bằng chứng metadata tại `.local-tests/pdf-summary/preview-20261024/uploaded-verification.json`; PID launcher worker lưu trong `worker-launcher.pid`. Các PDF tải lên bản thử sau này được worker nhận tự động; worker Supabase vẫn tắt.

- Xác định máy local không có backend/worker GeoAttend trước khi triển khai. Supabase PostgreSQL 17.11/PostGIS kết nối được bằng runtime và migration credentials; runtime không có quyền CREATE schema. Có 4 báo cáo và migration AI thử nghiệm `007`, được giữ nguyên.
- Checksum migration `001–006` khớp bản Git/LF. File checkout Windows dùng CRLF nên không chạy launcher migrate trực tiếp trên thư mục đó. Thư mục migration tạm lấy nguyên byte từ Git cho migration cũ, dùng LF cho `008`; không sửa checksum trong DB hoặc file migration đã áp dụng.
- Sao lưu riêng schema `geoattend`, bỏ dữ liệu `office_locations` theo chính sách GPS hiện hành, archive custom 11.151.029 byte. Backup không phải bản sao toàn bộ Supabase. Archive, cấu hình riêng và bằng chứng nằm trong `.local-tests/pdf-summary/rollout-20261024/`, bị Git ignore; không đưa vào artifact public.
- Khôi phục thử 15 bảng trong database UUID local. PostGIS đặt ở schema `extensions` để khớp Supabase; so sánh digest trong múi giờ UTC. Mọi bảng được sao lưu giữ nguyên dữ liệu (office_locations rỗng theo chính sách). Diễn tập thêm duy nhất `008` thành công, không đổi dữ liệu cũ.
- Lượt cấp quyền đầu dùng nhầm tên đăng nhập pooler có hậu tố project; toàn bộ giao dịch rollback. Lượt sau lấy SQL `current_user` thực tế, thêm `008` và cấp SELECT/INSERT/UPDATE bảng mới trong cùng giao dịch, thành công. Không đổi quyền các bảng cũ.
- Kiểm tra mới `test_pdf_summary_restore.py` chứng minh pg_dump/pg_restore giữ PDF, hash, revision, summary, attempts, model/prompt và thời điểm migration; worker không claim lại kết quả COMPLETE; runtime không có quyền CREATE schema/DELETE summary.
- Hai bộ kiểm tra trước triển khai đạt **37 passed** (queue/API/provider/worker/restore) và **54 passed** (viewer desktop/mobile/Pages, upload, readiness, migrations, build/artifact, health, policy). Log `rollout-tests-20261024.log` và `rollout-browser-20261024.log` trong thư mục kiểm chứng ignored. Warning TestClient/HTTPX hiện có.
- Nghiệm thu Gemini mới trên PDF tổng hợp 10 trang và DB UUID riêng: **1 passed, 1 deselected**, worker 6,07 giây, 103 đơn vị, attempt 1, model `gemini-3.5-flash-lite`; đọc lại ba lần và worker chạy lại không gọi AI. Không dùng Supabase ứng dụng. Log `rollout-live-20261024.log`; có thêm warning quyền thư mục cache giữa các tài khoản Windows, không ảnh hưởng kết quả ca kiểm tra. Bằng chứng chi tiết JSON chỉ chứa tài liệu tổng hợp.
- Backend local dùng tài khoản runtime, không nhận Gemini key. Health/login/static viewer trả 200; API báo cáo không đăng nhập trả 401 và trang báo cáo chuyển hướng đăng nhập. Không thử tài khoản thật hoặc thay mật khẩu.
- Tóm tắt PDF hiện có sẽ hiển thị trạng thái chờ vì worker tắt. Không bật `pdf-summary`, `--once` hoặc backfill trên Supabase khi chưa được phép gửi PDF thật: mọi chế độ xử lý đều có thể chọn báo cáo hiện có. Việc tạo tự động cho dữ liệu thật chưa kích hoạt.

Rollback local: dừng đúng web launcher/process được ghi ở `rollout-20261024/web-launcher.pid`/log rồi chạy lại checkout cũ nếu cần. Giữ bảng `pdf_summaries` và migration `008`; không xóa dữ liệu hoặc restore toàn DB để quay lại code cũ. Worker hiện chưa chạy nên không cần dừng worker.

## Phạm vi bằng chứng

- Database test trên PostgreSQL/PostGIS loopback 55441, fixture tạo database UUID riêng và từ chối DSN ứng dụng trùng với DSN test.
- Provider test gửi nguyên PDF qua HTTP transport giả lập. Parser chạy thật trên PDF chữ, scan, hỏng, có mật khẩu và quá số trang. Ngoài ra đã gọi Gemini thật với ba PDF tổng hợp tiếng Việt 10 trang, gồm chữ/scan/hỗn hợp.
- Browser dùng Edge headless, kiểm tra canvas PDF.js, summary lưu sẵn, quyền User/Admin, desktop/mobile, retry, stale revision và Pages bearer.
- Baseline kiểm tra báo cáo/health/policy: 22 passed, 1 warning. Python root thiếu Pillow; venv tính năng được tạo riêng từ lockfile, không sửa môi trường root hoặc report-ai.
- Các lượt RED đã quan sát: thiếu queue, thiếu provider, thiếu API, launcher chưa truyền key và chưa có nút viewer. Log trong `.local-tests/pdf-summary/` của worktree.
- Test Pages mới tự đồng bộ giờ browser với fixture server ngày 21/10; không sửa helper Pages dùng chung hoặc auth sản phẩm.
- Phát hiện test cũ có giả định menu/ảnh/timing không còn khớp; hai lỗi đã tái hiện trên main nguyên trạng. Theo nhắc lại phạm vi của người dùng ngày 24/10, **đã hoàn trả toàn bộ 13 file test cũ ngoài phạm vi về HEAD**, kể cả helper/timeout dùng chung. Không đưa các thử nghiệm sửa test chấm công/menu/auth vào nhánh bàn giao. Chỉ giữ cập nhật migration list và setup readiness vì bảng summary mới có khóa ngoại tới weekly_reports.
- Các lượt chạy cũ gặp lỗi quyền thư mục tạm do khác Windows account; lượt hồi quy cuối dùng basetemp/cache mới trong worktree. Ngày 24/10 cụm PostgreSQL test đang tắt, đã xác minh đường dẫn/phiên bản/trạng thái và khởi động lại cụm có sẵn trên loopback 55441; không initdb hoặc xóa cụm.
- Thử nghiệm cục bộ cho thấy mock timeout của test nghỉ phép ảnh hưởng cả auth/status lúc khởi tạo. Các sửa thử và kết quả chạy riêng được giữ trong log ignored để tham khảo; **không còn trong code bàn giao**. Lượt full suite đã nạp module trước khi hoàn trả nên kết quả đó chỉ là bằng chứng chẩn đoán, không được coi là toàn bộ nhánh hiện tại đã đạt.

## Ma trận nghiệm thu BRD

| Tiêu chí | Bằng chứng local / phần còn chờ |
|---|---|
| PDF chữ mới có tóm tắt đúng | Queue/worker/provider/UI đã kiểm tra; Gemini thật trên mẫu chữ 10 trang: 13,81 giây, 107 đơn vị, đối chiếu đúng dữ kiện chính |
| PDF scan có tóm tắt đúng | Gemini thật trên mẫu scan 10 trang: 14,77 giây, 121 đơn vị; mẫu hỗn hợp: 12,59 giây, 109 đơn vị; đúng dữ kiện chính |
| Một đoạn tiếng Việt 80–150 từ | Validator kiểm tra 79/80/150/151 và định dạng; cả ba kết quả Gemini thật là một đoạn tiếng Việt hợp lệ |
| Mở lại không gọi AI | Job COMPLETE không được claim lại; API đọc DB; browser mở lại không gửi POST tạo lại |
| Trạng thái/lỗi/Tạo lại | API và browser kiểm tra FAILED → PENDING → COMPLETE, giới hạn ba lượt |
| Upload không bị AI chặn | Upload không gọi provider hoặc ghi bảng summary; vẫn upload được khi bảng mới thiếu |
| PDF cũ có thể có summary | Worker discover không giới hạn tuần, cùng đường xử lý với PDF mới; dry-run không ghi DB |
| Giao diện gọn trên các màn hình | Browser User/Admin 360px/1280px, canvas phân trang và không overflow |
| Không lộ API key | Key repr ẩn, header riêng, URL không có key, launcher web không nhận key, .env ignored |
| Chức năng cũ hoạt động | 90 ca thuộc phạm vi PDF/tích hợp đạt; lượt chẩn đoán toàn dự án còn 7 lỗi ngoài phạm vi, không tuyên bố toàn bộ hồi quy đạt |

## Kết quả cuối trên phạm vi bàn giao

Sau khi hoàn trả 13 file test ngoài phạm vi, bộ kiểm tra PDF/provider/worker/queue/API/viewer/Pages/upload/readiness/migration/build/health/policy đạt **90 passed, 1 warning** trong 198,91 giây. Log: `.local-tests/pdf-summary/scoped-20261024-final.log`. Warning là deprecation hiện có của FastAPI/Starlette TestClient với HTTPX.

Lượt chẩn đoán toàn dự án kết thúc **495 passed, 7 failed, 1 skipped, 1 warning** trong 2.752,24 giây. Lượt này nạp một số sửa thử test trước khi chúng được hoàn trả, nên không đại diện một lượt full suite xanh trên nhánh cuối. Log: `.local-tests/pdf-summary/full-20261024-c.log`. Các lỗi được giữ nguyên phạm vi, không sửa chức năng hay test ngoài công việc:

- Hai ca checkout sớm dùng selector lịch sử cũ đã không tồn tại.
- Hai ca menu mobile đo vị trí trước khi CSS hoàn tất.
- Một ca nghỉ phép mô phỏng timeout/retry bị timeout khi bấm gửi lại.
- Một ca menu trước khi module tải bị timeout điều hướng login 5 giây.
- Load concurrency 20: 173 request, không có HTTP error; 86,13% hoàn tất trong 2 giây, thấp hơn ngưỡng 95%. Chưa xác minh nguyên nhân và không thay code tải/chấm công để xử lý trong phạm vi này.

Không coi kết quả các thử nghiệm sửa test cũ là thay đổi được bàn giao. Main và worktree report-ai không được chỉnh sửa; toàn bộ tính năng mới vẫn ở `feat/pdf-summary`.

## Kết quả gọi AI thật

Model mặc định chọn `gemini-3.5-flash-lite` sau khi đo thực tế. `gemini-3.8-flash` được project chấp nhận nhưng lượt PDF nhiều lần quá hạn; một lượt scan chẩn đoán cần khoảng 91 giây. Không tăng giới hạn production để che vấn đề: request vẫn tối đa 50 giây, provider subprocess tối đa 60 giây. Không tự fallback hoặc tự retry AI.

Ba mẫu lặp các dữ kiện tổng hợp: dự án Mẫu Sao Xanh, tuần 19–25/10/2026, 12 API, 48 ca kiểm thử (46 đạt, 2 cần sửa), chưa production, xử lý trùng yêu cầu/tối ưu truy vấn, thiếu thiết bị GPS, kế hoạch sửa lỗi và thử thiết bị thật. Đã đọc và đối chiếu cả ba kết quả với bản gốc. Prompt được điều chỉnh sau khi thử nghiệm phát hiện model rút ngắn tên riêng và tự diễn giải chữ viết tắt; lượt cuối giữ đúng các chi tiết này.

Ngày 24/10 đã kiểm tra thêm luồng thật upload → worker subprocess → Gemini → lưu DB → API đọc lại bằng PDF hỗn hợp tổng hợp 10 trang. Worker hoàn tất trong 14,17 giây, lưu đoạn 118 đơn vị, attempt_count=1; đọc API ba lần trả cùng đoạn, chạy worker tiếp không nhận lại job COMPLETE. Test độc lập đạt 1 passed; database test UUID riêng được fixture thu hồi. Đã đối chiếu nội dung kết quả với mẫu gốc.

PDF trắng tự tạo được Gemini trả `UNREADABLE` sau 2,83 giây, không sinh tóm tắt; test độc lập đạt 1 passed. Đây là kiểm tra nội dung thiếu thông tin, bổ sung cho test parser/HTTP giả lập.

Review độc lập phát hiện hai lỗi quan trọng: summary API phải chặn báo cáo có owner đã đổi khỏi role USER giống endpoint PDF; validator không được từ chối ký hiệu hợp lệ như C#, #123 và <5%. Đã tái hiện cả hai bằng test thất bại trước khi sửa; nhóm provider/API sau sửa đạt 28 passed.

Build Pages local thành công; `pip check` và `git diff --check` đạt. Đối chiếu nội bộ key riêng với 480 tệp có thể đưa vào Git và 251 tệp artifact: không có key bị đưa vào đó, artifact không chứa file backend `.py`, `.sql` hoặc `.env`. Không in key trong quá trình kiểm tra.

Log và PDF tổng hợp nằm trong `.local-tests/pdf-summary/live/` được Git ignore. Các mẫu chưa đại diện cho mọi dạng bảng, biểu đồ, scan mờ hoặc tài liệu thực tế; validator không chứng minh được độ đúng ngữ nghĩa của mọi kết quả AI.

## Việc còn lại trước kích hoạt môi trường ứng dụng

1. Cấu hình DSN runtime đúng môi trường; theo dõi quota khi chạy worker/backfill. Key đã được kiểm chứng với mẫu tổng hợp.
2. Trước khi gửi PDF nhân viên thật, kiểm tra nội dung nhạy cảm theo BRD. Chưa đọc/gửi PDF thật trong lượt triển khai này.
3. Operator triển khai migration/quyền runtime/web/worker vào môi trường được chọn theo `docs/features/PDF_SUMMARIES.md`, rồi kiểm tra thiết bị thật và HTTPS.

Không suy rộng kết quả trên mẫu tổng hợp thành bảo đảm độ đúng cho mọi PDF hoặc nghiệm thu production.
