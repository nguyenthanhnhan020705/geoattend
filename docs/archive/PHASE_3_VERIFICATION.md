> **Tài liệu lưu trữ:** nội dung và số liệu bên dưới phản ánh thời điểm lập tài liệu. Các hướng dẫn/quy tắc cũ có thể đã được thay thế; xem [tài liệu hiện hành](../README.md) trước khi thực hiện.

# GeoAttend — Kiểm chứng Phase 3

Phạm vi: Admin cấu hình một Geofence, User bắt đầu Office với GPS, Check-out không GPS, xác minh lại khi bắt đầu phiên mới, che và xóa GPS sau 30 ngày. Thiết kế nguồn: MVP Phase 0 đã duyệt; phương pháp inline và ủy quyền tự triển khai/test được giữ từ phiên trước.

**Kết quả cuối:** 119/119 ca đạt sau một lượt sửa review, 99.09 giây, một warning upstream Starlette TestClient. `pip check` và `git diff --check` không lỗi. Web và một maintenance worker đã được khởi động lại bằng local_run; health/database ok. Không có Minor từ review Phase 3.

## Bằng chứng trước review

- Baseline: 85/85 ca đạt trên PostgreSQL 17/PostGIS riêng, 65.44 giây.
- Task 1: endpoint/module chưa tồn tại gây RED; triển khai xong 10/10 ca đạt. Kiểm tra Admin/User/CSRF, Polygon rỗng/tự cắt/zero-area/sai loại/sai tọa độ, revision, khởi tạo đồng thời. PostGIS được cài trong schema `extensions` riêng để kiểm tra giống Supabase.
- Task 2: RED 9 ca thiếu Office/retention; sau triển khai 29 ca Office/retention/Remote đạt. Trong vùng/ranh giới được nhận, ngoài vùng giữ trạng thái, accuracy lớn vẫn nhận, sai GPS bị từ chối, Check-out không GPS, phiên mới xác minh vùng mới, lỗi ghi GPS rollback toàn bộ. Yêu cầu chờ khóa văn phòng qua 20:00 bị chặn. Hash Remote Phase 2 không đổi.
- Expiry: ngay trước 30 ngày còn GPS, đúng expires_at API che point/accuracy trước khi purge; replay chỉ trả ID/kết quả gốc. Purge null point/accuracy, giữ sự kiện verified/session; chạy lặp không đổi. Role runtime hạn chế được kiểm tra thật.
- Task 3: browser/config RED 4 ca, sau triển khai 14 ca đạt. Browser Edge headless 360px/desktop: Admin thêm đỉnh/xem trước/lưu/tải lại; tile lỗi vẫn lưu được; bản nháp giữ khi conflict; User GPS trong vùng, từ chối quyền, ngoài vùng, Check-out không GPS và vị trí mới cho phiên sau. Không JavaScript error hoặc tràn ngang.
- Browser mất response sau commit: retry cùng UUID/payload, chỉ một phiên, chỉ một lần lấy GPS, không raw GPS trong sessionStorage/localStorage. PostGIS schema extensions kiểm tra toàn luồng save/verify/store/history/purge.
- Races bổ sung: Polygon thay đổi lúc User chờ khóa được áp dụng; phiên bị thu hồi trong lúc chờ bị từ chối.
- Full suite trước review: **118 passed, 1 warning trong 70.87 giây**. `pip check`: không lỗi phụ thuộc. `git diff --check`: không lỗi whitespace. Warning upstream Starlette TestClient/HTTPX được giữ nguyên.

## Review độc lập và lượt sửa

Agent `phase3_final_review` (GPT-6-astra), chỉ đọc, review base `cff6b05` đến `e20c1c0`; không truy cập Supabase hoặc bí mật. Không Critical, một Important, không Minor.

Important: Admin có thể sửa trong lúc GET tải lại vùng đang chờ, phản hồi tới sau xóa bản nháp mới. Regression `test_office_loading_blocks_edits_until_response` thất bại vì input vẫn enabled. Đã sửa bằng trạng thái busy dùng chung cho tải lần đầu/tải lại/lưu, khóa form/map/drag/reload và khôi phục cả khi lỗi. Browser kiểm tra chậm/lỗi/giữ draft: 3/3 ca đạt.

Lần chạy hồi quy đầu sau sửa ghi nhận 118 đạt/1 lỗi trong ca trên do helper chờ JavaScript bị CSP chặn unsafe-eval, không phải lỗi sản phẩm. Helper được sửa sang chờ DOM attribute, giữ nguyên CSP; các assertion đọc/ghi thực và phản hồi bị giữ vẫn giữ nguyên. Toàn suite được chạy lại sau sửa helper.

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.local-tests/phase-3/full-tmp -o cache_dir=.local-tests/phase-3/cache
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

## Quyết định triển khai

1. Tiếp tục linked worktree/branch hiện tại và inline execution theo ủy quyền; không merge/push. Chi phí nếu sai: thay đổi local có thể hoàn nguyên.
2. Dùng PowerShell/Python cho checklist/ledger thay Bash helpers không có trên máy. Chi phí: khác cách ghi chứng cứ RED/GREEN/commit.
3. Không tự chọn tọa độ văn phòng thực; Admin cấu hình qua UI. Chi phí: cần một lần thiết lập vùng trước Check-in Office thực tế.
4. Office retry chỉ giữ GPS trong bộ nhớ tab, không lưu trình duyệt. Reload đọc trạng thái mới; thao tác chưa commit cần GPS mới. Chi phí: không thể gửi lại payload GPS gốc sau reload, phù hợp giới hạn lưu dữ liệu.
5. Function PostGIS luôn dùng schema thực từ pg_extension, không thay search_path của kết nối. Chi phí: thêm truy vấn metadata; hỗ trợ cả public/extensions.
6. Polygon giới hạn 10 rings, 1001 điểm/ring, 2000 điểm tổng; chỉ tọa độ 2D có giới hạn. Chi phí: vùng phức tạp vượt giới hạn phải đơn giản hóa; phù hợp một văn phòng MVP.
7. Chỉ trang Admin văn phòng cho phép inline styles mà Leaflet cần và origin tile được cấu hình. Các trang khác giữ CSP hiện tại. Chi phí: CSP trang bản đồ cho phép style động; script vẫn chỉ từ self.
8. Lưu toàn bộ phiên/sự kiện/GPS atomically, recheck giờ và phiên sau chờ lock văn phòng; Geofence revision được giữ bằng shared lock. Chi phí: thao tác sửa vùng có thể chờ User xác minh trong transaction.
9. Không cần migration mới: các cột/ràng buộc Phase 1 đủ cho Phase 3; quyền runtime hiện có gồm UPDATE office_locations. Chi phí: thay đổi nghiệp vụ dùng schema đã chuẩn bị, phải smoke-test trên Supabase trước handoff.
10. Khóa editor trong lúc tải/lưu thay vì cho chỉnh rồi đoán bản nháp nào mới nhất; giữ draft khi tải lỗi và yêu cầu xác nhận trước bỏ draft. Chi phí: Admin chờ phản hồi trước khi chỉnh tiếp; tránh mất dữ liệu.
11. Các mục reviewer không đánh giá được giữ đúng phase: GPS thiết bị thực/HTTPS và backup/hiệu năng production ở Phase 6; Dashboard/Onsite/nghỉ/chuyển chế độ ở Phase 4–5. Leaflet internals là thư viện có license; dùng bản pinned và kiểm thử tích hợp thay review minified code. Root kiểm tra Supabase riêng. Chi phí: chưa tuyên bố nghiệm thu thiết bị/pilot/production.

## Thư viện và nguồn kỹ thuật

Leaflet 1.9.4 JS/CSS được phục vụ local, kèm BSD license tại `app/static/vendor/leaflet/LICENSE`. Download pinned từ package Leaflet chính thức qua unpkg. SHA256 JS `db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a`; CSS `a7837102824184820dfa198d1ebcd109ff6d0ff9a2672a074b9a1b4d147d04c6`.

- [ST_Covers](https://postgis.net/docs/ST_Covers.html): kiểm tra cả nội vùng và ranh giới.
- [ST_IsValid](https://postgis.net/docs/ST_IsValid.html): từ chối Polygon không hợp lệ.
- [Leaflet](https://leafletjs.com/reference.html): Polygon/marker kéo đỉnh và tile layer.

## Giới hạn

- GPS browser trong test được giả lập để kiểm soát điểm trong/ngoài và lỗi; chưa chứng nhận độ chính xác GPS trên thiết bị thực hoặc triển khai HTTPS cho điện thoại.
- Dọn GPS cần maintenance chạy; API vẫn che dữ liệu hết hạn khi worker tạm dừng. Khôi phục backup phải chạy maintenance trước mở dịch vụ; vòng đời backup production thuộc Phase 6.
- Không tạo Geofence hoặc dữ liệu chấm công thử trên Supabase thực. Không thay mật khẩu/tài khoản thực.
- Office/Remote trực tiếp chuyển chế độ và nghỉ thuộc Phase 4; Dashboard/Onsite thuộc Phase 5; pilot/hiệu năng/production thuộc Phase 6.
- Smoke-test Supabase chỉ đọc: `geoattend_runtime`, TLS true; get_office và ST_MakePoint/ST_X qua schema extensions hoạt động; quyền UPDATE văn phòng/vị trí có sẵn. Văn phòng thực chưa cấu hình; tài khoản thực vẫn 1 Admin/1 User.
- Web sau restart: `/api/health` 200/database ok, `/login` và Leaflet JS 200; API office/attendance chưa đăng nhập trả 401. OpenAPI xác nhận START_OFFICE và GET/PUT office. Maintenance mới chạy đóng ngày/dọn auth/purge GPS; đã dừng hai chuỗi worker cũ, chỉ giữ một worker mới.
- PostgreSQL thử nghiệm port 55440 đã dừng sau kiểm chứng. Log/ảnh ở `.local-tests/phase-3`, ledger tạm được giữ trong `.superpowers/sdd/2026-10-15-phase-3-office-geofence` (Git ignore); không lặp lại thao tác xóa đã bị policy chặn trong phiên trước. Branch/worktree được giữ để phát triển tiếp.
