# Chuẩn bị phát hành tóm tắt PDF

Cập nhật 25/10/2026: gói hiện hành là `release-week-navigation-20261025/`, bao gồm điều hướng tuần Admin giữ bộ lọc nhân viên, sửa đầu ra Gemini vượt nhẹ 150 từ và chẩn đoán lỗi an toàn. Gói `release-inline-preview/` trước đó đã cũ. Bản sửa provider/worker đã áp dụng local 8000; chưa xuất bản public. Kiểm tra tại checkout chính: 43 passed, 1 warning có sẵn; 6 PDF hiện hành COMPLETE, gồm file 3 trang đã phục hồi. Không thay quyền Admin hoặc chức năng upload/xem/tải.

Ngày chuẩn bị: 24/10/2026. Người dùng đã yêu cầu tích hợp vào local 8000 và chuẩn bị public; chưa yêu cầu xuất bản.

## Bản chính local

`http://127.0.0.1:8000/` chạy từ `.worktrees/phase-1`. Đã ghép riêng chức năng PDF sau khi sao lưu và đối chiếu các file, giữ thay đổi có sẵn ngoài phạm vi. Worker độc lập sử dụng cùng Supabase, chỉ ghi kết quả dẫn xuất vào `pdf_summaries`; web không nhận Gemini key. Người dùng đã cho phép xử lý PDF cũ và mới trên bản chính.

Chỉ Admin thấy tóm tắt tự động cạnh thông tin file và được tạo lại khi lỗi. User tiếp tục upload, xem trước và tải PDF; API summary từ chối User. Xem trước PDF hiện mở khung nhỏ ngay bên dưới trong trang, có chuyển trang/đóng, không mở tab. Không dùng tài khoản demo của cổng 8002 trên hệ thống chính.

Bằng chứng local trong `.worktrees/phase-1/.local-tests/pdf-summary-main/`: `verification.log` (98 passed), `http-check.json`, `audit.json`, `worker-result.json`, PID/log web và worker. Backup file trước tích hợp ở `.worktrees/pdf-summary/.local-tests/pdf-summary/main-integration-20261024/before/`; cấu hình riêng được sao lưu ngoài Git.

## Môi trường public đã xác minh chỉ đọc

- Frontend: `https://nguyenthanhnhan020705.github.io/geoattend/`.
- API: `https://geoattend-api-a7xf.onrender.com`.
- Pages, remote main và bản chuẩn bị cùng nền `7616426cfca5e2738156b71e0717e199b6662cf2` tại thời điểm kiểm tra.
- Pages workflow đang active; backend health và database trả OK, chưa có summary routes.
- Không thay API origin hoặc workflow trong giai đoạn chuẩn bị. Push main sẽ kích hoạt Pages; cần điều phối backend sẵn sàng trước giao diện mới.

## Gói phát hành local

Thư mục ignored `.local-tests/pdf-summary/main-integration-20261024/release-week-navigation-20261025/` chứa patch, source zip, Pages artifact và manifest SHA-256 hiện hành. Patch được kiểm tra rồi áp dụng thử lên bản sạch của commit nền. Artifact Pages cấu hình đúng API public, không chứa backend, khóa hoặc backup. Các thư mục release trước đó là ứng viên lịch sử; dùng `release-week-navigation-20261025/` cho review.

`worker.private.env` nằm ngoài source zip/Pages và chứa cấu hình riêng để operator nạp vào secret settings của worker. Không đưa file đó vào Git, frontend, PR hoặc log. Mẫu công khai tại `deploy/pdf-summary-worker.env.example`.

## Trình tự khi người dùng duyệt xuất bản

1. Xác minh lại remote main vẫn là commit nền; nếu đã thay đổi, ghép và kiểm thử trên phiên bản mới. Review patch chỉ trong phạm vi PDF; giữ nguyên dữ liệu và migration đã áp dụng.
2. Điều phối Pages workflow trong đợt phát hành để frontend mới chỉ được xuất bản sau backend. Chưa thực hiện thao tác này khi chuẩn bị.
3. Backup database theo runbook hiện hành, xác minh `008_pdf_summaries.sql` và quyền runtime trên đúng database public. Không chỉnh migration 001–007 hoặc checksum. Supabase local đã có 008; chỉ coi public dùng cùng database sau khi operator đối chiếu cấu hình, không suy ra chỉ từ URL backend.
4. Backend Render dùng lockfile đã cập nhật. Giữ cấu hình/start command web hiện có; xác minh `/api/health`, summary routes, CORS Pages và quyền Admin/User trước khi tiếp tục. Web không cần Gemini key.
5. Cấu hình Background Worker riêng, cùng repository/commit và runtime database role: build `pip install -r requirements.lock.txt`, start `python -u -m scripts.pdf_summary_worker`. Nạp ba biến từ mẫu worker; không cấp migration credentials. Render hỗ trợ tiến trình Background Worker chạy liên tục, tách khỏi web: [tài liệu chính thức](https://render.com/docs/background-workers). Tạo service cần được chủ dự án duyệt cấu hình và chi phí phù hợp; chưa tạo service trong giai đoạn chuẩn bị.
6. Chuyển trách nhiệm xử lý sang worker public khi đã xác minh nó nhận job; dừng đúng worker local bằng PID đã lưu nếu không còn cần. Không xóa queue hoặc reset attempts. Worker xử lý lỗi gián đoạn theo retry thủ công, không tự gọi lại khi kết quả trước chưa rõ.
7. Xuất bản Pages, kiểm tra Admin tự thấy summary, User không thấy/không được gọi API, upload/xem/tải file và mở lại dùng cache. Không tạo tài khoản thử hoặc đổi mật khẩu tài khoản thật khi kiểm tra.

## Quay lại bản trước

Dừng worker mới và quay lại code/artifact đã xác minh; giữ `pdf_summaries` và migration 008 để không mất kết quả đã lưu. Bản web trước không phụ thuộc bảng mới. Không restore toàn database chỉ để quay lại giao diện. Local 8000 có backup đúng byte của các file đã thay; kiểm tra PID/checkout/cổng trước khi dừng hoặc chuyển tiến trình.

Một kết quả `INVALID_OUTPUT` nghĩa là phản hồi AI không đạt schema/độ dài/định dạng đã kiểm tra; Admin có thể chọn Tạo lại. Không tự xóa trạng thái lỗi hoặc gửi lại để che lỗi; retry có thể phát sinh thêm lượt API.
