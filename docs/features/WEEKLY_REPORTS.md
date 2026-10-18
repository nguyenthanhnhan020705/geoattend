# Báo cáo tuần — Đặc tả chức năng

**Ngày:** 18/10/2026. **Trạng thái:** thiết kế trong hội thoại đã được người dùng đồng ý; bản đặc tả này chờ duyệt trước khi lập kế hoạch triển khai. Chưa có mã chức năng, migration được áp dụng hoặc kết quả kiểm thử mới.

## 1. Mục tiêu và phạm vi

User nộp một PDF tổng hợp toàn bộ nội dung công việc trong tuần; Admin xem hoặc tải PDF trong ứng dụng. Không gửi file qua email/chat. Chức năng bổ sung vào GeoAttend hiện tại, dùng phân quyền, session và CSRF/Origin có sẵn.

- User: liên kết **NỘP BÁO CÁO TUẦN** nằm ngay bên cạnh **Đổi mật khẩu**.
- Admin: liên kết **BÁO CÁO TUẦN** nằm ngay bên cạnh **Dashboard** trong điều hướng quản trị. Trang Dashboard cũng có liên kết sang báo cáo tuần.
- Mỗi User có tối đa một PDF hiện hành cho mỗi tuần; nộp lại trong hạn thay thế PDF trước đó sau xác nhận, không lưu lịch sử các bản PDF thay thế trong ứng dụng.
- User chỉ xem/tải báo cáo của chính mình. Admin xem/tải báo cáo của các User, kể cả báo cáo đã nộp của tài khoản inactive; Admin không nộp báo cáo thay User.

Ngoài phạm vi: phê duyệt/chấm điểm, bình luận, AI đọc PDF, thông báo ngoài ứng dụng, mở lại hạn, nộp bù cho tuần cũ, tự động ghép PDF, xóa báo cáo qua giao diện và refactor chấm công.

## 2. Tuần và hạn nộp

- Tuần bắt đầu lúc 00:00 thứ Hai, kết thúc ngay trước 00:00 thứ Hai kế tiếp, theo giờ Việt Nam. Dùng ngày thứ Hai làm khóa tuần và hiển thị cả ngày bắt đầu/kết thúc, không chỉ số tuần.
- Cho nộp và thay thế PDF của tuần hiện tại trong toàn bộ tuần, kể cả sau 20:00. Cutoff 20:00 chỉ thuộc chấm công.
- Từ đúng 00:00 thứ Hai kế tiếp, chặn cả nộp lần đầu lẫn thay thế cho tuần cũ. Không cho nộp trước cho tuần tương lai.
- Backend dùng thời gian server để kiểm tra tuần; không tin đồng hồ trình duyệt. Kiểm tra lại sau khi nhận đủ file và sau khi chờ khóa, ngay trước khi ghi. Upload khởi đầu trước hạn nhưng hoàn tất kiểm tra sau hạn bị từ chối, giữ nguyên PDF cũ nếu có.
- Sang tuần mới tự có đợt nộp mới, PDF tuần cũ vẫn đọc được nếu đã nộp.

Ví dụ: tuần 19–25/10/2026 cho nộp đến trước 00:00 ngày 26/10/2026 Việt Nam; từ mốc này chỉ có thể nộp cho tuần 26/10–01/11/2026.

## 3. Thông báo trong ứng dụng

Hiển thị trên trang User và trang nộp báo cáo; không cần người dùng mở trang báo cáo mới thấy nhắc hạn. Thông báo được tính từ dữ liệu server, không phụ thuộc maintenance chạy đúng giờ.

| Điều kiện | Nội dung chính xác |
| --- | --- |
| Từ 00:00 Chủ nhật đến trước 00:00 thứ Hai, chưa có PDF tuần hiện tại | **BẠN CÒN 1 NGÀY ĐỂ NỘP BÁO CÁO NHÉ!!** |
| Trong tuần hiện tại, tuần liền trước đã hết hạn nhưng chưa có PDF | **TUẦN VỪA RỒI BẠN CHƯA NỘP BÁO CÁO. HÃY TRÌNH BÀY NỘI DUNG ĐÓ GỘP VỚI TUẦN NÀY NHÉ!** |

- Kèm khoảng ngày liên quan ngoài nguyên văn thông báo để phân biệt tuần bị lỡ và tuần đang nhận báo cáo.
- Nhắc Chủ nhật biến mất sau khi nộp thành công. Nhắc tuần trước giữ trong tuần kế tiếp để giải thích việc gộp nội dung; không tự giả định hệ thống kiểm tra được nội dung PDF đã gộp.
- Hai thông báo có thể cùng xuất hiện vào Chủ nhật nếu cả tuần trước lẫn tuần này đều chưa nộp.
- Khi tab quay lại hiển thị và khi qua mốc thay đổi ngày/tuần, tải lại trạng thái từ server; không tự mở quyền nộp bằng thời gian client.
- Không truy thu các tuần trước khi chức năng được bật hoặc trước khi tài khoản tồn tại. Tuần đầu có trách nhiệm nộp là tuần chứa thời điểm muộn hơn giữa ngày tạo User và ngày áp dụng migration chức năng. Không phụ thuộc có chấm công/nghỉ cả ngày hay không.

## 4. Luồng User

1. Mở trang báo cáo từ liên kết cạnh Đổi mật khẩu; hiển thị tuần hiện tại và hạn chót theo giờ Việt Nam.
2. Chọn một file `.pdf`, tối đa **10 MB = 10.000.000 byte**; hiển thị tên/dung lượng trước khi nộp. Không cho chọn nhiều file.
3. Nếu chưa nộp: bấm **Nộp báo cáo**. Nếu đã nộp: có thông tin file/thời điểm nộp và nút **Thay thế báo cáo**, yêu cầu xác nhận trước khi ghi đè.
4. Thành công: hiển thị trạng thái đã nộp, file hiện hành, thời điểm nộp gần nhất và nút **Xem PDF** / **Tải PDF**.
5. Có danh sách lịch sử báo cáo của bản thân theo tuần, phân trang; tuần cũ chỉ xem/tải. Mỗi tuần chỉ có một bản hiện hành.

Lỗi file/hạn/quyền hoặc lỗi database giữ nguyên bản đã nộp. Mất phản hồi có thể gửi lại cùng mã yêu cầu; không báo thành công trước khi backend xác nhận. Hai tab cùng thay thế phải kiểm tra revision, tránh bản cũ âm thầm ghi đè bản mới.

## 5. Luồng Admin

- Mặc định mở tuần hiện tại; chọn tuần khác và lọc nhân viên, có phân trang.
- Hiển thị tên/tài khoản, khoảng ngày, trạng thái **Đã nộp**, **Chưa nộp** hoặc **Quá hạn chưa nộp**, tên file, dung lượng, thời điểm nộp gần nhất.
- Với tài khoản/tuần trước thời điểm bắt đầu có trách nhiệm nộp, hiển thị **Không áp dụng**, không quy thành thiếu báo cáo.
- Trạng thái tài khoản inactive được ghi rõ. Vẫn đọc được PDF đã nộp; không cho tài khoản inactive nộp/xem bằng session cũ.
- Mở PDF trong tab mới hoặc tải file qua endpoint có kiểm tra quyền; không dùng URL public của database hoặc đường dẫn thư mục static.
- Làm mới danh sách sẽ thấy bản thay thế mới nhất; không thay đổi snapshot Dashboard chấm công để tải thêm file PDF.

## 6. Lưu trữ, API và transaction

Lựa chọn đã đồng ý trong hội thoại: lưu PDF trong PostgreSQL. Phương án kho file riêng cần thêm cấu hình, quyền và đối soát file/database; chưa cần cho quy mô khoảng 10 User. Đổi lại, dung lượng database và backup tăng theo số tuần/file.

- Tạo migration mới **005_weekly_reports.sql**, giữ nguyên checksum 001–004.
- Bảng `weekly_reports` lưu User, ngày thứ Hai của tuần, tên file đã làm sạch, nội dung PDF dạng `bytea`, dung lượng, hash nội dung, thời điểm nộp đầu/gần nhất, revision và thông tin kỹ thuật cho retry gần nhất. Unique `(user_id, week_start)`; constraint ngày thứ Hai và dung lượng trong giới hạn.
- Mốc bật chức năng lấy từ `schema_migrations.applied_at` của migration 005; khi restore giữ nguyên mốc này để không đổi lịch sử trách nhiệm nộp.
- Runtime chỉ được SELECT/INSERT/UPDATE bảng mới. Không bổ sung quyền xóa tài khoản hoặc thay quyền các bảng chấm công.
- Router riêng cho báo cáo User và Admin; trang riêng `/user/weekly-reports` và `/admin/weekly-reports`. API dưới `/api/weekly-reports` và `/api/admin/weekly-reports`, gồm trạng thái/danh sách, upload User và xem/tải PDF có quyền.
- Upload truyền binary PDF có giới hạn kích thước, kèm tuần, request UUID và expected revision; không cần thêm dependency multipart. Backend kiểm tra số byte thực dù thiếu hoặc giả Content-Length và dừng đọc khi quá giới hạn.
- Kiểm tra đuôi `.pdf`, media type và cấu trúc nhận diện PDF (header/kết thúc), từ chối file rỗng hoặc giả định dạng rõ ràng. Đây là kiểm tra định dạng cơ bản, không tuyên bố diệt mã độc hoặc chứng nhận mọi cấu trúc PDF; không chạy nội dung, trích xuất hay xử lý AI.
- Upload hoàn tất mới mở transaction ngắn: khóa profile User trước bản ghi báo cáo, kiểm tra lại tài khoản/session và thời hạn, rồi ghi nguyên tử metadata + PDF. Không giữ connection/khóa trong lúc nhận file từ mạng.
- Cùng request UUID và nội dung của lần ghi gần nhất trả lại xác nhận cũ mà không ghi lại, kể cả retry sau deadline. UUID gần nhất khác nội dung bị từ chối. Retry cũ sau một lần thay thế mới bị từ chối bởi revision, không phục hồi PDF cũ.
- Nộp lần đầu expected revision 0; thay thế phải gửi revision đang xem. Hai request đồng thời chỉ một request được ghi ở cùng revision.
- Xác thực/CSRF/Origin dùng cơ chế có sẵn; xem/tải kiểm tra quyền từ database, không tin User ID do client gửi. Mutation kiểm tra lại session sau khi chờ khóa.
- PDF trả `application/pdf`, tên file trong Content-Disposition được encode an toàn, `no-store`, `nosniff`; không nhúng tên file thành HTML. Xem PDF mở tab mới với `noopener`; mọi API báo cáo tránh cache dữ liệu riêng tư.
- Trang User chỉ tải trạng thái nhắc hạn nhỏ; danh sách không SELECT cột PDF. Chỉ endpoint xem/tải mới đọc file, tránh làm tăng tải cho chấm công/Dashboard.
- Không log PDF, tên file người dùng, cookie/token, DSN hoặc request body. Không lưu PDF vào localStorage/sessionStorage.

## 7. Migration, backup và tài liệu

- Chỉ áp dụng migration và kiểm thử trên database test cô lập trong phạm vi triển khai local. Áp dụng vào database ứng dụng thật cần yêu cầu riêng.
- Backup logic hiện có sẽ chứa báo cáo trong bảng mới; chính sách loại `office_locations` không loại báo cáo. Tài liệu vận hành phải nêu tăng dung lượng và PDF thay thế có thể còn trong backup cũ theo vòng đời backup.
- Không tự thêm thời hạn xóa báo cáo hoặc job xóa; bản PDF hiện hành được giữ để Admin tra cứu các tuần. Thiết kế này không thay chính sách GPS 30 ngày.
- Cập nhật hướng dẫn User/Admin, features, PROJECT_OVERVIEW, ROADMAP, phần chức năng quản trị liên quan Phase 5 và hướng dẫn migration/backup khi triển khai; trạng thái chỉ chuyển đã triển khai/đã kiểm chứng theo kết quả thực tế.
- Không tự push, merge, deploy, gửi thông báo bên ngoài hoặc tác động Supabase thật.

## 8. Tiêu chí kiểm thử

1. Điều hướng đúng vị trí; User nộp, xem/tải và thay thế PDF; Admin lọc tuần/nhân viên, xem trạng thái thiếu và mở đúng file.
2. User khác, khách và session hết hạn/thu hồi không đọc hoặc thay file; Admin không upload; CSRF/Origin bảo vệ upload; tên file độc hại không tạo XSS/header injection.
3. Chấp nhận file hợp lệ trong giới hạn; từ chối file giả/rỗng/quá dung lượng/stream quá giới hạn. Lỗi không mất bản trước.
4. Tuần thứ Hai–Chủ nhật đúng giờ Việt Nam, qua tháng/năm và không chịu cutoff chấm công 20:00. Từ chối tuần tương lai/cũ và request chờ qua deadline.
5. Chủ nhật chưa nộp có đúng nguyên văn nhắc hạn; nộp thành công hết nhắc. Tuần trước thiếu có đúng nguyên văn thông báo mới; không nhắc hồi tố trước bật chức năng/tạo User; hai nhắc cùng tồn tại được.
6. Nộp lại thay đúng một file; rollback, revision cũ, hai upload cạnh tranh và retry mất phản hồi không tạo trùng hoặc khôi phục bản cũ.
7. Migration lặp no-op, checksum 001–004 giữ nguyên, runtime role đủ quyền hẹp; backup/restore giữ PDF và metadata trên database test riêng.
8. Browser ở 360px và desktop; lỗi mạng, trạng thái gửi, xác nhận thay thế, trở lại tab và đổi tuần không để UI cũ vượt hạn.

Kiểm thử tập trung cho chức năng trước, rồi hồi quy phù hợp các phần auth/migration/pages/database và suite hiện có. Không dùng kết quả 290 test lịch sử làm kết quả của thay đổi này. GPS/thiết bị thật/HTTPS và pilot Phase 6 vẫn còn mở.
