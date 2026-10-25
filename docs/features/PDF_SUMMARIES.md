# Tóm tắt nội dung PDF

Điều hướng báo cáo Admin ngày 25/10: hai nút Trước/Sau dưới ô ngày chuyển đúng một tuần và tự tải kết quả, giữ bộ lọc nhân viên, đưa phân trang về trang 1. Chọn ngày bất kỳ vẫn quy về tuần Thứ Hai–Chủ Nhật. Quy tắc Đã nộp/Chưa nộp/Quá hạn/Không áp dụng giữ nguyên; không thêm thống kê lịch sử hay thay đổi thời hạn nộp.

Cập nhật 25/10: provider `vi-paragraph-v2` xử lý đầu ra vượt nhẹ 151–180 từ bằng cách giữ phần đầu kết thúc ở câu hoàn chỉnh, rồi kiểm tra lại 80–150 từ. Không thêm nội dung/cắt giữa câu/gọi AI thêm. Đầu ra quá dài, thiếu từ, nhiều đoạn hoặc Markdown vẫn bị từ chối. Worker ghi mã nguyên nhân đã lọc, không ghi nội dung. Chi tiết nghiệm thu tại `docs/PDF_SUMMARY_VERIFICATION.md`.

Yêu cầu: `README(Read_PDF).md`. Thiết kế được duyệt ngày 23/10/2026 tại `docs/superpowers/specs/2026-10-23-pdf-summary-design.md`.

## Trạng thái local ngày 24/10/2026

Backend chính `http://127.0.0.1:8000/` hiện chạy từ `.worktrees/phase-1` với chức năng PDF đã tích hợp; bản thử `8002` vẫn độc lập. Migration `008` đã có trên Supabase; không sửa migration cũ. `.env` riêng của bản chính có cấu hình worker, launcher tự tạo DSN và chỉ truyền Gemini key cho worker.

**Người dùng đã cho phép xử lý PDF cũ và mới trên bản chính 8000.** Worker bản chính đã bật; lượt đầu xử lý 5 báo cáo: 4 COMPLETE, 1 FAILED/INVALID_OUTPUT, mỗi bản mới gọi 1 lần. Admin có thể chọn Tạo lại cho bản lỗi; không tự gửi lại. Dữ liệu PDF/tài khoản/chấm công được đối chiếu không đổi. Kiểm chứng tích hợp đạt 98 ca. Public mới được chuẩn bị, chưa xuất bản; xem `docs/PDF_SUMMARY_RELEASE.md` và `docs/PDF_SUMMARY_VERIFICATION.md`.

## Chức năng

Worker tự phát hiện PDF mới và PDF có sẵn, gửi toàn bộ PDF tới Gemini để hiểu cả chữ và ảnh scan. Mỗi bản nội dung có một kết quả lưu trong PostgreSQL; xem lại không gọi AI. Khi nội dung đổi, khung lấy tóm tắt của nội dung mới. Upload lại cùng nội dung có thể dùng kết quả cũ.

Theo yêu cầu phân quyền mới nhất ngày 24/10, **chỉ Admin được xem và tạo lại tóm tắt**. Sau khi User upload, worker vẫn tự tạo tóm tắt; khung **Tóm tắt nội dung** tự hiển thị cạnh thông tin file trong giao diện Admin. Mỗi báo cáo có khung riêng, nằm dưới thông tin file trên màn hình hẹp. User chỉ thấy **Tải PDF** và **Xem trước PDF**, không hiển thị khung và không gửi request summary. Cả endpoint Admin lẫn URL summary cũ đều từ chối User bằng 403. Quyền upload/xem/tải PDF hiện có giữ nguyên. Khi chưa có kết quả, Admin thấy trạng thái tự cập nhật; khi lỗi có Tạo lại; khi hoàn tất dùng kết quả lưu sẵn. Khung cho phép cuộn và không tự tải/render PDF.

Tóm tắt là một đoạn tiếng Việt 80–150 đơn vị tách bằng khoảng trắng. Mô hình được yêu cầu giữ đúng số liệu, tên riêng và thời gian, không dùng thông tin ngoài PDF. Kiểm tra tự động xác minh định dạng/độ dài; độ đúng ngữ nghĩa cần đối chiếu file thật, không thể bảo đảm chỉ bằng prompt.

**Xem trước PDF trong trang:** User/Admin bấm Xem trước PDF để mở khung nhỏ ngay dưới thông tin báo cáo, không mở tab/cửa sổ mới. Khung có Trang trước PDF, Trang sau PDF và Đóng xem trước; chiều cao cuộn tối đa 420px (360px trên mobile). Chỉ tải PDF khi bấm, gửi xác thực hiện có và `expected_revision` để từ chối file đã bị thay. Đóng khung/đổi bộ lọc hủy request và giải phóng canvas/worker. Tải PDF vẫn tải file riêng; tóm tắt Admin không phụ thuộc việc mở/đóng preview.

## Trạng thái và lỗi

| Trạng thái | Hiển thị / hành vi |
|---|---|
| NOT_CREATED | Chưa tạo, chờ worker; mở file không gọi AI |
| PENDING / PROCESSING | Đang tạo bản tóm tắt... |
| COMPLETE | Đoạn tóm tắt đã lưu |
| FAILED | Thông báo an toàn; Tạo lại nếu còn lượt |
| UNREADABLE | Không thể đọc nội dung tài liệu để tóm tắt |
| PDF_PASSWORD / PAGE_LIMIT | Cần PDF không mật khẩu / trong giới hạn trang |
| UNCERTAIN_RESULT | Worker bị gián đoạn, có thể API đã tính phí; người dùng quyết định tạo lại |

Tối đa ba lần xử lý cho một report/hash. Không tự thử lại sau lỗi AI hoặc crash. Retry chuyển FAILED về PENDING; worker nhận sau đó. Hai yêu cầu đồng thời chỉ một yêu cầu chuyển được trạng thái. Không cho retry COMPLETE. Khung kiểm tra trạng thái mỗi ba giây, tối đa khoảng hai phút; dừng khi đóng/chuyển file, rời trang hoặc tab bị ẩn. Sau đó có nút kiểm tra trạng thái, không gọi AI mới.

Nếu file thay revision khi khung đang tải/poll, API trả STALE_REVISION và khung yêu cầu tải lại danh sách; không ghép PDF cũ với tóm tắt mới.

## Cấu hình bí mật

API key chỉ dùng ở backend worker. Không nhập key trong giao diện, runtime-config.js hoặc biến public của Pages. `.env` đã được Git ignore.

Trong worktree phát triển `.worktrees/pdf-summary`, đã tạo sẵn `.env` riêng với chỗ trống:

```dotenv
GEOATTEND_GEMINI_API_KEY=
GEOATTEND_SUMMARY_MODEL=gemini-3.5-flash-lite
GEOATTEND_DATABASE_URL=
```

Điền key sau dấu `=` trên máy. Khi muốn chạy worker, điền DSN **runtime** của môi trường đã áp dụng migration, giữ cấu hình web hiện hành của môi trường đó. Không dán key/DSN vào chat hoặc Git. `local_run` chỉ chuyển key/model tới chế độ `pdf-summary`, không chuyển key tới web hoặc maintenance. Chưa có key thì worker dừng trước khi nhận job.

Model có thể thay bằng `GEOATTEND_SUMMARY_MODEL`; adapter mới có thể thay Gemini mà không đổi API/UI/hàng đợi. Trước khi đổi model, xác minh hỗ trợ PDF, structured output, thinking configuration và project có quyền dùng. Đổi model không tự tính phí tạo lại các bản đã hoàn tất.

## Chuẩn bị triển khai

Những bước dưới đây là hướng dẫn cho operator, **chưa được chạy trên database ứng dụng** trong quá trình phát triển tính năng.

1. Cài dependency từ `requirements.lock.txt` vào môi trường triển khai.
2. Backup database theo quy trình hiện có.
3. Đối chiếu `schema_migrations`. Migration `007_weekly_report_ai.sql` thuộc thử nghiệm cũ có thể đã tồn tại ở môi trường khác; không sửa nội dung/checksum hoặc xóa bảng cũ. Tính năng này chỉ thêm `008_pdf_summaries.sql`, không cần các bảng RAG cũ.
4. Operator áp dụng migration bằng quy trình `scripts.migrate`; cập nhật quyền runtime bằng `grant_runtime` hiện hành. Không dùng tài khoản migration cho worker thường trực.
5. Cấu hình key, model và DSN riêng. Khởi động phiên bản web có API/viewer mới và worker riêng. Giữ tiến trình maintenance chấm công độc lập.

Chạy local bằng Python trong venv đã cài dependency, tại thư mục checkout có `.env` phù hợp:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_run pdf-summary
```

Một lượt xử lý:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_run pdf-summary --once
```

`local_run` không tự nạp `.env` ở checkout khác. Người dùng đã điền key trong `.env` riêng; DSN runtime còn để trống nên worker chưa được kích hoạt. Tên biến đúng là `GEOATTEND_DATABASE_URL` (có chữ G đầu tiên). Không cần DSN để kiểm tra provider trực tiếp; worker cần DSN để đọc PDF và lưu kết quả.

## PDF có sẵn và backfill

Worker thường trực tự quét cả báo cáo mới và cũ, ưu tiên bản nộp gần đây. Không cần sửa upload transaction; lỗi bảng tóm tắt/AI/worker không thể làm upload thất bại.

Các lệnh trực tiếp bên dưới đọc biến môi trường của tiến trình, không tự đọc `.env`. Dùng môi trường được operator cấp bí mật trước khi chạy:

```powershell
python -m scripts.pdf_summary_worker --dry-run
python -m scripts.pdf_summary_worker --backfill --limit 20
```

Dry-run chỉ đếm PDF chưa có job, không ghi DB và không cần key. Backfill xử lý tối đa 20 job rồi dừng; job phát hiện trong quá trình quét vẫn tồn tại trong hàng đợi. Worker thường trực sẽ tiếp tục xử lý chúng khi được bật. Theo dõi hạn mức trước khi bật worker trên toàn bộ kho PDF.

## Vận hành và giới hạn

- Một worker xử lý tuần tự; có thể chạy nhiều worker nhờ `SKIP LOCKED`. Claim dùng lease 90 giây và token riêng. Gọi AI không giữ transaction hoặc connection DB.
- Tác vụ provider có subprocess giới hạn 60 giây, gồm kiểm tra PDF và request; phần request có deadline 50 giây. Lease hết hạn chuyển lỗi, không tự gọi lại khi không biết request trước đã tính phí hay chưa.
- Không có bảo đảm exactly-once cho hệ thống ngoài khi có mất mạng/crash. Kết quả đã lưu không được gọi lại; retry thủ công có thể phát sinh chi phí mới.
- Upload vẫn tối đa 10 MB; kiểm tra PDF không mật khẩu và tối đa 1.000 trang. Không âm thầm bỏ trang. Model nhận toàn file, không dùng text extraction thay thế cho scan.
- Log worker chỉ chứa số job hoặc thông báo chung, không key/PDF/tóm tắt. Kiểm tra cả cấu hình log của HTTP proxy trước triển khai.
- Tắt tính năng bằng dừng worker và giữ nguyên PDF/database. Upload/xem/tải vẫn dùng được; bản tóm tắt đã có vẫn đọc được. Không cần rollback bằng xóa dữ liệu.
- Với ba PDF tổng hợp tiếng Việt 10 trang (chữ/scan/hỗn hợp), model mặc định trả kết quả hợp lệ trong 12,59–14,77 giây. Đây là mẫu thử, không bảo đảm thời gian hoặc độ đúng với mọi tài liệu thực tế. Gemini 3.8 Flash gọi được nhưng các lượt PDF chậm/quá hạn; giữ khả năng cấu hình model thay vì tự fallback và phát sinh thêm lượt gọi.

## Nguồn API

Đã đối chiếu ngày 23/10/2026: [PDF và giới hạn](https://ai.google.dev/gemini-api/docs/document-processing), [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite), [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [structured output](https://ai.google.dev/gemini-api/docs/structured-output). Key không gắn cứng với một phiên bản model; quyền và quota phụ thuộc project. Đã gọi thật với key được cung cấp, chỉ dùng PDF tổng hợp, không gửi tài liệu nhân viên.

Không có chatbot, RAG, embedding hoặc vector database trong tính năng này.

