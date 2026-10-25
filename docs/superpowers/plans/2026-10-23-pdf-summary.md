# PDF Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tự động tóm tắt PDF chữ/scan bằng Gemini, lưu kết quả và hiển thị bên cạnh PDF mà không chặn upload.

**Architecture:** Worker độc lập quét PostgreSQL và claim job có lease. Provider gửi toàn PDF tới Gemini; API chỉ đọc DB hoặc yêu cầu retry đúng quyền. UI dùng viewer riêng, không sửa nghiệp vụ chấm công.

**Tech Stack:** Python/FastAPI/Psycopg/PostgreSQL, HTTPX, pypdf, PDF.js, JavaScript/CSS hiện có.

**Spec:** `docs/superpowers/specs/2026-10-23-pdf-summary-design.md` — người dùng duyệt 23/10/2026.

## Global Constraints

**Triển khai local được duyệt ngày 24/10:** Người dùng yêu cầu tiếp tục, chọn chạy local với Supabase đã cấu hình và chỉ cho thử PDF tổng hợp. Đã xác minh môi trường, bổ sung cấu hình riêng, backup/restore 15 bảng, áp dụng duy nhất migration `008` và bật web `127.0.0.1:8000`. Worker Supabase giữ tắt để không gửi 4 PDF hiện có. Kiểm chứng mới: 37 + 54 ca đạt, 1 ca Gemini tổng hợp đạt (6,07 giây, 103 đơn vị). Đây là ngoại lệ được người dùng duyệt đối với giới hạn chưa migrate ở giai đoạn phát triển dưới đây; vẫn không merge/push/publish hoặc sửa chức năng khác. Chi tiết tại `docs/PDF_SUMMARY_VERIFICATION.md`.

**Tiến độ 24/10:** Phase 1–4 đã triển khai; hai lỗi quan trọng từ review độc lập đã sửa RED→GREEN. Phase 5 đạt 90 kiểm thử trong phạm vi PDF sau khi hoàn trả 13 file test ngoài phạm vi theo nhắc lại của người dùng. Lượt chẩn đoán toàn dự án: 495 passed, 7 failed, 1 skipped; chi tiết và giới hạn tại `docs/PDF_SUMMARY_VERIFICATION.md`. Gemini thật đạt trên PDF tổng hợp 10 trang bằng `gemini-3.5-flash-lite`; worker thật hoàn tất trong 14,17 giây, đọc lại không gọi AI. Chưa migrate database ứng dụng hoặc bật worker runtime.

- Tóm tắt tiếng Việt, một đoạn, 80–150 đơn vị tách khoảng trắng; không suy đoán khi thiếu nội dung.
- Upload vẫn tối đa 10.000.000 byte; Gemini PDF tối đa 1.000 trang theo tài liệu đã tra cứu.
- Không sửa/xóa migration cũ, PDF thật, code ổn định ngoài phạm vi hoặc thay đổi worktree report-ai.
- API key chỉ backend; thiếu cấu hình/schema không làm hỏng upload/xem/tải.
- Không merge/push/publish hoặc migrate database ứng dụng trong quá trình triển khai local.

## Review Focus

- Upload cùng nội dung nhưng revision tăng: kết quả hiện hành dùng lại được mà không gọi AI.
- Worker chết sau khi gửi AI: trạng thái không rõ phải lỗi, không tự tính phí lại.
- PDF đổi khi UI/worker đang xử lý: không ghép PDF cũ với tóm tắt mới.
- Lỗi schema/quyền/cấu hình: tóm tắt unavailable, luồng báo cáo cũ vẫn dùng được.
- Session hết hạn hoặc đổi role: API retry/file/summary không lộ dữ liệu hoặc cho vượt quyền.

## Task 1 / Phase 1: Dữ liệu và hàng đợi bền vững

**Files:** Create `migrations/008_pdf_summaries.sql`, `app/reports/summaries.py`, `tests/integration/test_pdf_summaries.py`; Modify `app/db/migrations.py` (grant bảng mới nếu tồn tại), test migration list.

**Interfaces:** `discover(conn, limit=20) -> int`; `claim(conn) -> dict | None`; `finish(conn, job, summary=None, error_code=None) -> bool`; `ready(conn) -> bool`. Các hàm tự quản lý transaction, caller cung cấp connection nhàn rỗi. Job: id/report_id/hash/lease_token/pdf; trạng thái PENDING/PROCESSING/COMPLETE/FAILED. Public response không chứa PDF/hash/key.

- [x] Viết test DB: discover idempotent, claim không trùng, stale hash không commit, cùng hash dùng lại, lease cũ bị từ chối, expired processing thành lỗi, schema thiếu không chặn báo cáo.
- [x] Chạy test và xác nhận fail do chức năng chưa có.
- [x] Tạo schema riêng với unique(report_id,content_sha256), lease 90 giây, attempt_count tối đa 3; discovery ưu tiên báo cáo mới. Không hook vào upload transaction.
- [x] Chạy `python -m pytest tests/integration/test_pdf_summaries.py tests/integration/test_weekly_reports.py -q` trên DB test UUID riêng; phải pass.
- [ ] Ghi kết quả và checkpoint Git nếu quyền cho phép, chỉ stage file thuộc tính năng.

## Task 2 / Phase 2: PDF và Gemini provider

**Files:** Create `app/reports/summary_provider.py`, `tests/test_pdf_summary_provider.py`; Modify requirements runtime/lock.

**Interfaces:** `SummaryError(code)`; `SummarySettings.from_env()`; `GeminiProvider(settings).summarize(pdf: bytes) -> str`; `validate_document(pdf) -> int`; `validate_summary(text) -> str`.

- [x] Test PDF chữ/scan/hỏng/mật khẩu/giới hạn trang và output 79/80/150/151 từ, Markdown, timeout, 429, blocked, UNREADABLE, thiếu key. HTTP transport giả lập, parser/validator chạy thật.
- [x] Chạy test RED.
- [x] Dùng pypdf kiểm tra tài liệu trước mạng; gửi inline PDF, structured JSON, model cấu hình, HTTP timeout tổng khoảng 50 giây, không SDK retry tự động. Không log body/key, không coi output không hợp lệ là complete.
- [x] Chạy test GREEN và dependency check; ghi nhận chưa có bằng chứng chất lượng AI thật.

## Task 3 / Phase 3: Worker và API

**Files:** Create `scripts/pdf_summary_worker.py`, `app/reports/summary_routes.py`, `tests/integration/test_pdf_summary_api.py`, `tests/test_pdf_summary_worker.py`; Modify `app/main.py`, `scripts/local_run.py`.

**Interfaces:** `process_one(dsn, provider) -> bool`; worker CLI `--once`, `--backfill`, `--dry-run`, `--limit`; API GET/POST `/api/[admin/]weekly-reports/{id}/summary?expected_revision=N`. POST chỉ FAILED, không enqueue lại COMPLETE/PROCESSING; GET không gọi AI. Response `status,summary,error_code,message,revision,can_retry`.

- [x] Test RED: owner/admin/other, CSRF, stale revision, attempt cap, missing schema, failure recovery và worker không giữ connection/transaction trong lúc gọi provider.
- [x] Implement API dùng profile lock/quyền hiện hành; summary readiness riêng. Worker discover/claim commit trước provider, mở connection mới khi finish; thiếu key thì không claim; dry-run không ghi DB.
- [x] Test GREEN và hồi quy upload/readiness/auth; cấu hình local launcher chỉ truyền key tới worker, không frontend.

## Task 4 / Phase 4: Viewer và summary panel

**Files:** Create `app/static/js/pdf-summary-viewer.js`; Modify `reports-api.js`, `reports.css`, hai weekly reports HTML; thêm PDF.js vendor bằng copy có chọn lọc từ report-ai và mở rộng allowlist build. Tests browser/API file revision.

**Interfaces:** `openSummaryViewer(report, parent, admin=false)`; dùng module singleton viewer, có close/abort/poll cleanup; mở qua nút riêng cạnh link xem/tải hiện hữu, giữ tương thích link cũ.

- [x] Browser test RED: PDF đọc được và summary cạnh nhau, mobile không overflow, COMPLETE không gọi POST, FAILED retry, file thay từ chối stale, close dừng polling.
- [x] Add revision check optional cho file của cả User/Admin, không thay đổi response khi client cũ không gửi revision. Render PDF canvas bằng PDF.js, lấy summary cùng revision; trạng thái lỗi độc lập. Poll tối đa 2 phút, mỗi 3 giây; pause khi tab hidden; textContent và nút Tạo lại có giới hạn.
- [x] Run browser, Pages artifact và file permission tests GREEN.

## Task 5 / Phase 5: Hồi quy, tài liệu và bàn giao

**Files:** Create `docs/features/PDF_SUMMARIES.md`, `docs/PDF_SUMMARY_VERIFICATION.md`; cập nhật spec trạng thái và plan/ledger.

- [x] Chạy full suite trên DB test với Caddy local nếu sẵn có; phân biệt lỗi baseline và lỗi do thay đổi, không che giấu test lỗi.
- [x] Kiểm tra `pip check`, `git diff --check`, build Pages, không key/secret/backend artifact.
- [x] Viết cách chạy migration/worker/backfill/retry/disable và ma trận 10 tiêu chí BRD.
- [x] Thử AI thật chỉ khi có key hợp lệ và file tổng hợp; PDF thật phải xem xét nhạy cảm trước. Nếu thiếu thì ghi rõ nghiệm thu thật chưa hoàn thành.
- [x] Review độc lập toàn bộ thay đổi; sửa lỗi quan trọng bằng RED→GREEN; bàn giao nhánh/worktree, không tự merge/deploy.

## Execution ledger

- 23/10: người dùng đã duyệt thiết kế và yêu cầu tiếp tục. Thực thi trực tiếp theo phase, không yêu cầu duyệt lại lựa chọn kỹ thuật đã được giao agent quyết định.
- Worktree mới từ main `7616426`; không dùng lại worktree report-ai đang có thay đổi.
- Baseline Python root thiếu Pillow; dùng interpreter report-ai đã có Pillow cho kiểm tra ban đầu, không cài/sửa môi trường đó. Dependency mới sẽ nằm trong venv riêng.
