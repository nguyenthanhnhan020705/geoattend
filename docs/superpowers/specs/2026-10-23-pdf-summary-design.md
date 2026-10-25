# Thiết kế tóm tắt PDF và phân chia phase

Ngày: 23/10/2026. Trạng thái: **Đã được người dùng duyệt; đã triển khai trong worktree riêng và đạt 90 kiểm thử trong phạm vi PDF; hồi quy toàn dự án còn lỗi được ghi riêng; chưa triển khai lên môi trường ứng dụng**.

Rà soát độc lập thiết kế: đã hoàn tất, không còn câu hỏi quan trọng cản trở lập kế hoạch. Chi tiết schema, đồng bộ revision khi cùng hash, ưu tiên PDF mới so với backfill và lịch polling do người triển khai quyết định trong các ràng buộc dưới đây.

Nguồn yêu cầu: `README(Read_PDF).md`. Tài liệu này thay thế thiết kế AI/RAG cũ trong phạm vi công việc mới, không sửa hoặc xóa tài liệu, code, PDF hay migration cũ.

## 1. Mục tiêu và phạm vi

**Điều chỉnh cuối được người dùng làm rõ ngày 24/10:** upload xong thì worker tự tạo và giao diện tự hiển thị khung tóm tắt cạnh thông tin file, không có nút mở/đóng tóm tắt. Chỉ có Tải PDF và Xem trước PDF để chủ động chọn. Mỗi báo cáo có khung trạng thái/kết quả/retry riêng, chuyển xuống dưới trên mobile; không tải/render PDF khi chỉ đọc summary. Thay thế cả phương án gộp ban đầu và phương án ba nút trung gian; giữ cơ chế worker, API, phân quyền và lưu cache.

Tự động tạo một đoạn tóm tắt tiếng Việt khoảng 80–150 từ cho toàn bộ mỗi PDF báo cáo tuần, gồm PDF chữ, scan và hỗn hợp. Lưu kết quả để mở lại không gọi AI. Khung tóm tắt nằm cạnh vùng xem PDF; khi màn hình hẹp chuyển xuống dưới PDF.

**Phân quyền cập nhật theo yêu cầu mới nhất:** chỉ Admin xem/tạo lại tóm tắt nhân viên. User tiếp tục upload/xem/tải PDF của mình, không có khung summary và không gọi API summary. Cả URL summary gốc và URL Admin đều kiểm tra require_admin, trả 403 cho User. Worker tiếp tục tạo và lưu tóm tắt độc lập với vai trò người upload.

**Xem trước được cập nhật:** thao tác Xem trước PDF mở khung nhỏ dưới thông tin file ngay trong trang cho cả User/Admin, có chuyển trang và đóng, không đổi tab. Dùng PDF.js đã vendored, GET có xác thực/revision, chỉ tải khi được chọn; giới hạn chiều cao, pixel và dung lượng, hủy khi đóng/DOM bị thay. Khung này độc lập với summary tự hiện chỉ dành cho Admin.

Không có chatbot, RAG, embedding, vector database, chỉnh sửa tóm tắt hoặc mô hình tự huấn luyện. Không thay đổi nghiệp vụ chấm công, GPS, thời hạn báo cáo, upload và download hiện hành. Không dùng lại các phần AI đã bị yêu cầu dừng ngày 23/10.

## 2. Hiện trạng đã kiểm tra

- Checkout chính: `main`, commit `7616426`; PDF lưu dạng bytea trong `weekly_reports`, có `content_sha256` và `revision`. Khi thay file, id báo cáo giữ nguyên nhưng revision tăng.
- Module báo cáo đã tách riêng, có kiểm tra quyền, CSRF, session và readiness. Upload dùng transaction và UUID chống gửi trùng.
- Main chưa có trình xem PDF trong trang. Worktree `.worktrees/report-ai` có viewer PDF.js dành cho Admin, tải file có kiểm tra revision; có nhiều thay đổi chưa commit cần giữ nguyên.
- Worktree cũ có `007_weekly_report_ai.sql` và cấu trúc job/result/source phục vụ thiết kế cũ. Chưa kiểm chứng database thực tế trong công việc này. Không sửa checksum, xóa bảng hay giả định migration đó chưa áp dụng.
- Không tìm thấy tích hợp Gemini/OpenAI đang hoạt động trong các module và dependency đã đọc. Chưa đọc PDF thật, chưa kiểm tra nội dung nhạy cảm, chưa gọi dịch vụ AI.
- Các thay đổi có sẵn ở main: `docs/PROJECT_OVERVIEW.md`, `README(Read_PDF).md`, thiết kế AI cũ ngày 22/10. Không ghi đè chúng.

## 3. Phương án đề xuất

### Các cách đã cân nhắc

1. **Gửi PDF trực tiếp tới Gemini, worker riêng và hàng đợi PostgreSQL — đề xuất.** Đọc đồng thời chữ/hình, không cần dựng OCR; hàng đợi bền qua restart và dùng hạ tầng hiện có.
2. OCR tiếng Việt từng trang rồi gửi văn bản cho AI. Thêm dependency và bước xử lý; dễ mất bố cục bảng, hình và nội dung scan. Chỉ cân nhắc sau nếu thử nghiệm cho thấy Gemini không đọc đủ tốt.
3. Tác vụ nền bên trong web process. Ít cấu hình nhưng dễ mất việc khi web restart, khó điều phối nhiều instance. Không phù hợp với yêu cầu tránh trùng và không ảnh hưởng upload.

Với yêu cầu đã giao cho agent tự chọn trong BRD, lựa chọn kỹ thuật đề xuất là phương án 1. Không thêm Redis/Celery cho quy mô hiện tại.

### Gemini và đọc PDF

- Provider nằm sau interface riêng để thay dịch vụ mà không viết lại job/API/UI.
- Backend gửi toàn bộ PDF qua request trực tiếp; không đưa API key hoặc gọi Gemini từ trình duyệt. Giới hạn upload ứng dụng vẫn 10.000.000 byte.
- Tài liệu Gemini hiện hành mô tả khả năng hiểu chữ, ảnh, bảng và biểu đồ trong PDF; giới hạn PDF 50 MB / 1.000 trang. Kiểm tra file/mật khẩu/số trang bằng parser trước khi gọi API; không cắt trang âm thầm và không áp giới hạn 10 trang chỉ vì tài liệu thường dài khoảng 10 trang.
- Model cấu hình bằng biến môi trường. Tài liệu model hiện liệt kê `gemini-3.8-flash` ổn định; phải xác minh model khả dụng với project thực tế lúc tích hợp. Không dùng alias tự đổi model âm thầm.
- Kết quả có cấu trúc nội bộ phân biệt đọc được/không đọc được và đoạn tóm tắt. Kiểm tra đầu ra: một đoạn, độ dài 80–150 đơn vị tách bằng khoảng trắng, không Markdown/tiêu đề. Không gọi lại AI tự động để kéo dài một tài liệu thiếu thông tin; không ép AI bịa đủ từ.
- Prompt yêu cầu chỉ lấy dữ liệu trong file, giữ đúng tên/số liệu/mốc thời gian, bỏ qua chỉ dẫn bên trong tài liệu. Tài liệu không đủ nội dung, bị mờ hoặc không đọc được phải trả trạng thái tương ứng.
- Không thể bảo đảm tuyệt đối AI không sai chỉ bằng prompt. Nghiệm thu phải đối chiếu PDF và kết quả thật, đặc biệt tên riêng, số liệu và scan.

Nguồn đã tra cứu ngày 23/10/2026:

- https://ai.google.dev/gemini-api/docs/document-processing
- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/structured-output

### Dữ liệu và tiến trình nền

- Thêm bảng tóm tắt/hàng đợi riêng bằng migration mới, không sửa migration đã áp dụng. Chọn tên và số sau khi đối chiếu lịch sử migration ở các môi trường; không tái sử dụng tên `007_weekly_report_ai.sql` cho nội dung mới.
- Khóa duy nhất theo report id và hash nội dung; lưu revision nguồn, trạng thái, đoạn tóm tắt, lỗi an toàn, model, phiên bản prompt, timestamps, lease và mã lần xử lý. Cùng nội dung upload lại có thể dùng kết quả đã lưu; file đổi hash không dùng kết quả cũ. Tại một thời điểm chỉ bản khớp PDF hiện hành được trả cho UI.
- Worker riêng quét báo cáo thiếu tóm tắt và thêm job bằng thao tác idempotent. Nhờ vậy upload không phụ thuộc bảng mới, dịch vụ AI hoặc trạng thái worker. PDF cũ được xử lý cùng cơ chế; thêm chế độ backfill có giới hạn và dry-run.
- Worker claim job bằng `FOR UPDATE SKIP LOCKED` và lease, commit trước khi gọi AI. Không giữ transaction/profile lock hay connection DB trong thời gian chờ mạng.
- Trước xử lý và khi lưu kết quả đều kiểm tra hash/revision hiện hành; dùng lease token để worker cũ không ghi đè kết quả của worker mới. Kết quả phiên bản cũ không xuất hiện cạnh file mới.
- Không gọi lại job đã hoàn tất. Các lỗi xác định được lưu và chỉ chạy lại theo yêu cầu hợp lệ; giới hạn số lần thử và chống nhấn liên tục.
- Lease hết hạn sau crash: phân biệt job chưa gửi API và job đã gửi nhưng chưa lưu kết quả. Trường hợp không biết API đã tính phí hay chưa chuyển lỗi cần người dùng bấm Tạo lại, không tự gọi lặp. Không hứa exactly-once với API bên ngoài khi nhà cung cấp không có idempotency.
- Mục tiêu: quét hàng đợi mỗi vài giây, một file khoảng 10 trang hoàn thành khoảng 1 phút trong điều kiện bình thường. Đây là mục tiêu đo thực tế, không phải cam kết khi hạn mức hoặc mạng không đáp ứng. Giới hạn đồng thời ban đầu 1; timeout một lần gọi tối đa khoảng 50 giây, có giới hạn tổng request thực tế.

### API và giao diện

- API mới cho đọc trạng thái/kết quả và yêu cầu tạo lại; kiểm tra quyền như API PDF. Yêu cầu tạo lại là POST có CSRF, mang định danh phiên bản và chỉ dành cho trạng thái lỗi. Chưa tạo/đang tạo không tạo thêm job khi người dùng bấm lặp.
- Phân biệt chưa tạo, đang tạo, hoàn tất, lỗi; lỗi không đọc được có mã riêng. Chưa tạo không giả là đang tạo nếu worker chưa hoạt động. Thiếu cấu hình/schema chỉ làm khung mới thông báo chưa sẵn sàng, không chặn upload/xem/tải PDF.
- Viewer và summary dùng chung định danh file; nếu file bị thay trong lúc đang mở, dừng polling kết quả cũ và yêu cầu tải phiên bản mới. Không hiển thị PDF cũ cạnh tóm tắt mới.
- Tái sử dụng có chọn lọc viewer PDF.js đã có sau kiểm tra code và kiểm thử; mở rộng User bằng endpoint có quyền tương ứng. Giữ nút tải PDF, xử lý file hỏng/mật khẩu thân thiện.
- Desktop: PDF và khung tiêu đề “Tóm tắt nội dung” thành hai cột; khung có chiều cao giới hạn và cuộn. Mobile: một cột, không cuộn ngang toàn trang. Dùng CSS/màu/chữ hiện có.
- Poll khi khung mở và job chưa kết thúc; dừng khi đóng/chuyển file/hết phiên/tab rời trang, có giới hạn thời gian và khoảng chờ. Mở lại đọc DB, không tạo job AI mới cho kết quả đã hoàn tất.
- Render tóm tắt bằng textContent, không HTML. Không đưa PDF/đầu ra nhạy cảm/key vào log hay thông báo lỗi. Kiểm tra artifact Pages để cấu hình bí mật không lọt vào frontend.

## 4. Các phase và điều kiện hoàn thành

### Phase 0 — Khảo sát và chốt thiết kế (đang thực hiện)

- Đọc BRD, kiểm tra main/worktree, luồng báo cáo và tài liệu API Gemini.
- Lập thiết kế này; rà soát tính khả thi và duyệt trước khi viết code sản phẩm.
- Đầu ra: phạm vi, kiến trúc, checklist từng phase và rủi ro đã được trình bày rõ. Không đánh dấu tính năng đã hoạt động.

### Phase 1 — Nền tảng dữ liệu và cô lập thay đổi

- Tạo nơi làm việc riêng từ main, giữ các thay đổi có sẵn và chỉ đưa vào phần viewer cần thiết sau khi kiểm tra.
- Đối chiếu migration đã áp dụng bằng kiểm tra chỉ đọc được giới hạn; tạo migration bổ sung và quyền runtime cần thiết, readiness riêng cho tóm tắt.
- Tạo repository/state machine; kiểm thử unique job, đổi hash, retry, claim/lease và mất lease trên DB test cô lập.
- Hoàn thành khi dữ liệu tóm tắt được quản lý đúng và upload/xem/tải vẫn chạy khi tính năng mới chưa kích hoạt.

### Phase 2 — Đọc PDF và tích hợp Gemini

- Tạo provider, kiểm tra PDF/số trang/mật khẩu, timeout và phân loại lỗi.
- Kiểm tra cấu hình API key/model ở backend; viết prompt và validator đầu ra.
- Kiểm thử giả lập không tính phí: PDF chữ/scan/hỗn hợp, phản hồi lỗi, hết hạn mức, timeout, kết quả sai dạng và không đọc được.
- Hoàn thành phần tích hợp local khi contract provider đạt; chất lượng AI thực tế chưa được coi là đã nghiệm thu nếu chưa gọi thật.

### Phase 3 — Worker, PDF cũ và API

- Worker độc lập, quét tự động PDF mới/cũ, backfill giới hạn, khóa trùng và lưu kết quả.
- API trạng thái/retry đúng quyền User/Admin; kết quả cũ không hiển thị khi file mới đã thay.
- Kiểm thử crash, tranh chấp hai worker, retry đồng thời, session bị thu hồi và DB/AI không sẵn sàng.
- Hoàn thành khi upload không chờ AI và mở lại file không phát sinh thêm lời gọi AI.

### Phase 4 — Viewer và khung tóm tắt

- Tích hợp viewer, khung cạnh PDF, đầy đủ trạng thái và nút Tạo lại.
- Kiểm thử desktop/mobile, cookie cùng origin và bearer qua Pages, polling cleanup, file đổi phiên bản và tải PDF.
- Hoàn thành khi khung không che PDF hoặc làm vỡ bố cục; lỗi tóm tắt không ảnh hưởng thao tác xem/tải.

### Phase 5 — Nghiệm thu và bàn giao

- Chạy nhóm kiểm thử liên quan, sau đó suite hồi quy phù hợp; kiểm tra build Pages và bí mật không nằm trong artifact.
- Kiểm chứng Gemini thực với PDF chữ, scan tiếng Việt, hỗn hợp và file khó đọc; đo thời gian và đối chiếu nội dung/80–150 từ. Dùng file tổng hợp trước; PDF thật phải kiểm tra nhạy cảm trước khi gửi theo BRD.
- Cần API key/project hợp lệ được cấu hình ngoài Git; không yêu cầu dán key vào chat. Nếu thiếu, ghi rõ phần nghiệm thu thực chưa làm, không báo hoàn tất toàn bộ.
- Viết hướng dẫn cấu hình worker, migration, backfill, giới hạn chi phí và vô hiệu hóa tính năng bằng dừng worker/tắt cấu hình mà giữ PDF/dữ liệu.
- Bàn giao bảng đối chiếu 10 tiêu chí nghiệm thu trong BRD với bằng chứng cụ thể; tách kết quả local và triển khai thật.

## 5. Ranh giới thay đổi và triển khai

Trong lượt khảo sát này chỉ tạo tài liệu mới. Khi triển khai, chỉ chỉnh code cần thiết cho báo cáo/viewer/cấu hình/build và test; không dọn dẹp hoặc refactor các module ổn định ngoài phạm vi.

Không tự merge/push/publish, chạy migration lên DB ứng dụng, sửa bí mật, khởi động lại dịch vụ đang dùng hoặc gửi PDF thật cho AI trong phase thiết kế. Chuẩn bị bản thay đổi và hướng dẫn có thể kiểm tra trước các bước vận hành. Thiếu API key hay PDF được phép gửi không chặn việc xây dựng và kiểm thử local bằng mock/file tổng hợp.

Các phase trên là trình tự và tiêu chí đầu ra; kế hoạch thao tác ở mức file/test sẽ được viết sau khi thiết kế được duyệt. Thời gian và chi phí AI thực tế chỉ được kết luận từ đo lường.
