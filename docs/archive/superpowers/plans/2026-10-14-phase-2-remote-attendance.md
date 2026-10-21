> **Tài liệu lưu trữ:** nội dung và số liệu bên dưới phản ánh thời điểm lập tài liệu. Các hướng dẫn/quy tắc cũ có thể đã được thay thế; xem [tài liệu hiện hành](../../../README.md) trước khi thực hiện.

# Phase 2 — Remote và lịch sử cá nhân Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** User bắt đầu/kết thúc Remote, xem lịch sử và tự đóng phiên lúc 20:00 giờ Việt Nam.

**Architecture:** Giữ FastAPI/Psycopg và schema Phase 1. Mọi đọc/ghi nghiệp vụ khóa profile trước, đối soát ngày quá hạn, rồi thao tác ngày hiện tại trong transaction. Maintenance độc lập chạy mỗi phút, cùng dịch vụ đối soát với API. Không lấy GPS cho Remote.

**Tech Stack:** Python 3.13, FastAPI, PostgreSQL 17/PostGIS, Pytest, Playwright/Edge, JavaScript thuần.

**Spec:** `docs/superpowers/specs/2026-10-14-geoattend-mvp-design.md` §§4,5,7,8,9; `docs/STATE_TRANSITIONS.md`; `docs/ROADMAP.md` Phase 2.

**Authorization:** Thiết kế MVP đã duyệt; người dùng yêu cầu tiếp tục và tự code/test mọi phần công cụ làm được. Giữ inline execution đã chọn, không yêu cầu duyệt lại nghiệp vụ. Làm trong linked worktree hiện tại; không merge/push. Test PostgreSQL riêng tại 127.0.0.1:55439, không dùng Supabase cho bộ test.

## Global Constraints

- USER-only; lấy user_id từ phiên, kiểm tra lại active/role dưới khóa. ADMIN không có ngày chấm công.
- Thời gian UTC có múi giờ, ngày/mốc 20:00 theo UTC+7. Đọc giờ sau khi lấy khóa; không dùng giờ client.
- Remote chỉ START_REMOTE từ NOT_STARTED/CHECKED_OUT trong phase này. CHECK_OUT chỉ khi đang làm việc. Office/nghỉ/chuyển chế độ thêm ở Phase 3–4.
- expected_revision và UUID request_id; cùng payload chuẩn hóa trả lại kết quả sự kiện cũ, khác payload 409. Đối soát hết hạn được commit ngay cả khi action bị từ chối.
- History từ/to mặc định 7 ngày, phân trang theo ngày, page_size 20 tối đa 100. Không nhận user_id, không trả vị trí ở phase này.
- 20:00 đóng working bằng WORK_END, lunch bằng DAY_END; recorded_at là lúc xử lý, event_time/end_time là mốc 20:00. Chạy lặp không ghi trùng; xử lý ngày cũ trước mở ngày mới.

## Task 1: Remote service và API

**Files:** create `app/attendance/{__init__,schemas,service,routes}.py`; modify `app/main.py`; create `tests/integration/test_attendance.py`.

**Interfaces:** consumes require_user, ApiError, pool.connection, utc_now; produces status(conn,user_id), act(conn,user_id,body), history(conn,user_id,start,end,page,page_size), ActionInput. Response status includes work_date/status/revision/open_session/server_time/allowed_actions; action includes event_ids/session_id/work_date/status/revision. Các kết quả replay giữ revision/status kết quả gốc, trạng thái hiện tại tải bằng GET riêng.

- [x] Write tests: Remote start → checkout → restart giữ hai phiên; lý do trắng/thiếu/1001 ký tự và GPS/user_id thừa bị 422; revision cũ và action không hợp lệ 409; cùng request replay cùng event_ids, payload khác 409; rollback khi ghi sự kiện lỗi; GET/POST ADMIN 403, chưa login 401, thiếu CSRF403; lịch sử cá nhân không lộ User khác; cache no-store.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/integration/test_attendance.py -q`; Expected: FAIL endpoints absent.
- [x] Implement schemas/service/routes: khóa profile FOR UPDATE, revalidate active USER, deadline reconciliation, revision và replay, ghi ngày/phiên/sự kiện/request trong transaction. Lý do trim 1–1000; checkout reason optional, extra forbid. Snapshot thời gian sau khóa.
- [x] Run same tests; Expected: PASS.
- [x] Commit `feat: add remote attendance API and personal history`.

## Task 2: Deadline, concurrency và maintenance

**Files:** create `scripts/maintenance.py`; create `tests/integration/test_attendance_time.py`, `test_attendance_races.py`; extend service.

**Interfaces:** consumes Task1 reconciliation; produces maintain(conn) trả số ngày đã đóng, maintenance CLI --once hoặc vòng lặp 60s. Profile khóa trước ngày/phiên, maintenance lần lượt mỗi user trong transaction riêng. Prune auth sau đối soát trong transaction riêng.

- [x] Tests literal times: 19:59:59 start accepted;20:00/20:00:01 rejected;late read closes at13:00UTC, recorded_at later;LUNCH_BREAK closes withDAY_END without altering old session;morning/full leave untouched;nextday catchup closes old beforestart; repeated maintenance no duplicates;retry original after deadline returns original IDs;wait for profilelock acrossdeadline rejected; concurrent sameUUID two calls one session, distinctUUIDsame revision one409; checkout vs maintenance oneend;runtime role operates withoutschema CREATE.
- [x] Run new files; Expected: FAIL maintenance missing or behaviors absent.
- [x] Implement maintain(conn), standalone --once/60second loop with sanitized error and graceful Ctrl+C. API reconciliation commits before returning conflict; transactional actions recheck clock immediately before write, transaction start timestamp never used for deadline.
- [x] Run new files; Expected: PASS. Commit `feat: reconcile attendance at Vietnam day cutoff`.

## Task 3: User interface và browser flow

**Files:** modify `app/static/user.html`, `app/static/js/user.js`, `app/static/css/app.css`; create `tests/integration/test_attendance_browser.py`.

**Interfaces:** consumes status/actions/history API. Client uses crypto.randomUUID, keeps exact pending payload after ambiguous network/503 error, prevents conflicting new mutation until retry succeeds or definitive4xx. Status refresh every60s/onfocus, does not overwrite pendingpayload. History date filters and next/previous pages. Formats Asia/Ho_Chi_Minh, SYSTEM labels explicitly.

- [x] Browser test on360px: createUSER,login,Remote with XSS-shaped reason → WORKING_REMOTE, reload preserves, checkout → CHECKED_OUT, restart → secondsession, history displays reason as text notHTML; noGPS, noJSerrors, nohorizontaloverflow. Simulate lost response after server committed and retry preservesrequestUUID/no duplicates. Reject invalid history date range without hiding olddata.
- [x] Run browser test; Expected: FAIL missing controls.
- [x] Implement status/action form/history, bounded refresh, clear failuremessages, safe textContent, retry support; preserve account/logout UI.
- [x] Run browser test; Expected: PASS. Commit `feat: add remote attendance user interface`.

## Task 4: Verification, setup và handoff

**Files:** update `docs/DEVELOPMENT.md`, `docs/ROADMAP.md`, `.env.example`; create `docs/PHASE_2_VERIFICATION.md`; create `scripts/local_run.py`; extend `tests/test_config.py` or new setup tests.

**Interfaces:** local_run reads ignored .env SUPABASE_DB_* and GEOATTEND_RUNTIME_DB_* withoutprintingDSNs, supports `serve`, `bootstrap-admin`, `maintenance`; child process environment uses runtime forserve/maintenance, admin onlybootstrap. Generic GEOATTEND_* DSNs continue supported. No more hand-pasting secrets intoPowerShell.

- [x] Write config tests proving role-specificconnectionstrings and literalpasswordescaping with spaces/quotes, missingkeys fail withoutsecret output; run ExpectedFAIL.
- [x] Implement local_run.py CLI; document startupafterreboot and autonomousmaintenance requirement. No realaccountcreation/testdatainSupabase.
- [x] Run completepytest onprivatePostgres includingbrowser, pipcheck, gitdiffcheck; ExpectedPASS. Recordexactcommands, count, warnings, limitations. Reviewfocus: networkretryduplicate, crossmidnightlocking, revocationduringwait, deadlockbetweenmaintenanceandpasswordreset, pagination/UTCdatehandling.
- [x] Commit `docs: record phase 2 verification and local startup`.

## Pre-flight and rulings

- Task1→2: shared profile lock and reconciliation; no competing lock order. Task1→3: replay returns originalresult, UI fetcheslateststatusafter everyaction. Task2→4: standalone worker must run independentlyofbrowser. No interfaces conflict.
- Ruling: use existingworktree ratherthannewone, preserve livePhase1process untilhandoff — avoids disrupting user and matches isolation skill.
- Ruling: no Bash executable detected; taskbriefs/checklists and ledger maintained with nativePowerShell/Python insteadofBash helper scripts — same RED/GREEN/commit evidence, no functionalcost.
- Ruling: user explicitly delegated coding/testing; approvedMVPspec remains binding; implementationdetaildecisions recorded here withoutreapproval — cost ifwrong is a reversiblelocalchange.

## Review Focus

Check retries after network loss, requestUUID reuse after cutoff, waiting across20:00, stale day acrossmidnight, transactionrollbackvscommittedcatchup, locks withpasswordreset, history ownership/paging/date ranges. Tests target each; reviewer checks paths tests maymiss.

## Final review rulings

- Review ??c l?p ph?t hi?n retry ch?a commit qua ng?y v? launcher migrate kh?ng c?p quy?n runtime; c? hai ?? s?a b?ng regression RED?GREEN. Th?m expected_work_date b?t bu?c trong payload v? hash, nh?ng UUID ?? commit v?n replay k?t qu? g?c. Migration c?p quy?n role l?y t? SELECT current_user qua k?t n?i runtime. Chi ph?: client c? ph?i t?i l?i v? th?m m?t k?t n?i khi migrate.
- Minor ho?n: browser Phase 2 c?n Edge, ch?a h? tr? bi?n fallback Chromium. Ki?m th? ?? ch?y th?nh c?ng tr?n Windows c? Edge.
- Office/GPS/ngh?/Admin dashboard v? worker production/benchmark thu?c c?c phase sau, kh?ng tuy?n b? ho?n th?nh MVP/pilot. Hosted database ???c root ki?m ch?ng ri?ng.
- B?ng ch?ng cu?i: docs/PHASE_2_VERIFICATION.md, 85/85 ki?m th? ??t.
