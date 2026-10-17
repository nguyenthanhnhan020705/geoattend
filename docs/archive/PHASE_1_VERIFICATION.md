> **Tài liệu lưu trữ:** nội dung và số liệu bên dưới phản ánh thời điểm lập tài liệu. Các hướng dẫn/quy tắc cũ có thể đã được thay thế; xem [tài liệu hiện hành](../README.md) trước khi thực hiện.

# GeoAttend — Kiểm chứng Phase 1

## Kết quả bàn giao

- Nhánh: `feat/phase-1-foundation-auth`, worktree `.worktrees/phase-1`.
- Hoàn thành 6 task của [kế hoạch](superpowers/plans/2026-10-14-phase-1-foundation-auth.md): nền tảng cùng nguồn, migration PostGIS, một Admin, đăng nhập/phân quyền, vòng đời mật khẩu và giao diện tài khoản.
- Bộ kiểm thử cuối: **46 passed**, không có failures. `pip check`: **No broken requirements found**; `git diff --check`: không có lỗi whitespace.
- PostgreSQL 17/PostGIS thử nghiệm được chạy riêng trên loopback, dưới worktree. Không dùng/thay đổi database PostgreSQL có sẵn hoặc Supabase thực tế.
- Kiểm chứng Edge headless: Admin cấp User, User đổi mật khẩu, Admin reset, thu hồi phiên và logout; tên giống HTML được hiển thị bằng text; giao diện không tràn ngang ở 360px và desktop.
- Có một cảnh báo deprecation từ Starlette TestClient khi dùng HTTPX đã pin; không che cảnh báo và không có lỗi dependency.
- Hướng dẫn chạy, migration và tài khoản: [DEVELOPMENT.md](../DEVELOPMENT.md).

## TDD và tiến độ

| Task | Bằng chứng RED → GREEN |
| --- | --- |
| 1 | 5 kiểm thử lỗi route/config chưa có → 5 đạt; dependency check đạt. |
| 2 | Migration chưa có → migration/checksum/constraint/runtime permission đạt. Phát hiện lỗi Unicode CLI Windows, tái hiện và sửa UTF-8; 12 kiểm thử nền tảng/migration đạt. |
| 3 | 11 kiểm thử password/bootstrap lỗi do chưa có chức năng → 12 password/bootstrap đạt, gồm tạo đồng thời và xác nhận CLI. |
| 4 | 5 API auth lỗi route chưa có → bộ hiện tại 29 đạt; kiểm tra 12 giờ, revoked/inactive, CSRF và giới hạn thử sai. |
| 5 | Create/reset/change/race chưa có → bộ hiện tại 39 đạt; các phiên User thu hồi, phiên Admin không bị reset User tác động. |
| 6 | 3 page tests lỗi trước triển khai → bộ 43 đạt, gồm live browser. |
| Lượt sửa cuối | Tái hiện 3 lỗi: deadlock reset/change với session hết hạn và CSRF không ASCII → **46/46 đạt**. |

Kết quả integration dùng database UUID riêng do fixture tạo. Database/config thử nghiệm và nhật ký tạm được dọn sau bàn giao; không phải tài khoản ứng dụng thực được cấp cho người dùng.

## Review độc lập

Reviewer đọc toàn bộ nhánh từ `6c03c2e` đến `03bac82`, đối chiếu kế hoạch, thiết kế và các quyết định thực hiện; không sửa checkout. Root xử lý một lượt sửa sau review, không yêu cầu review lặp.

- **Important:** login dọn session hết hạn trước lấy khóa profile, trong khi reset/change khóa profile trước cập nhật session → deadlock. Đã loại global session cleanup khỏi transaction login; login chỉ dọn lần thử sai của username đang xử lý. Dọn session chạy bằng `scripts.prune_auth` trong giao dịch riêng.
- **Minor theo reviewer, nâng lên Important khi đánh giá tác động:** CSRF header không ASCII gây TypeError/HTTP 500. Đã từ chối bằng 403 trước constant-time comparison. Kiểm thử header byte 0xff tái hiện lỗi rồi đạt.
- Không có Critical. Không còn reviewer minors hoãn lại.

Reviewer không đánh giá chức năng chấm công/GPS/bản đồ/maintenance nghiệp vụ chưa triển khai hoặc cấu hình Supabase/HTTPS production; các phần đó thuộc phase sau và triển khai môi trường.

## Các quyết định thực hiện và chi phí

Danh sách sau giữ toàn bộ các `Ruling:` của nhật ký theo thứ tự, để không mất quyết định khi dọn workspace tạm.

1. Tạo worktree trước commit ignore file, sau khi xác nhận đường dẫn được ignore; giữ tài liệu gốc chưa commit. Chi phí: khác thứ tự commit của skill, không mất dữ liệu gốc.
2. Không có Bash script skill trên host Windows; dùng bookkeeping Python/PowerShell tương đương theo đúng workspace kế hoạch. Chi phí: đối chiếu nhật ký với commit/test thủ công.
3. Dùng PostgreSQL 17/PostGIS riêng trong worktree, không dùng dịch vụ có sẵn/Supabase. Chi phí: cần kiểm chứng quyền/cấu hình hosted khi triển khai.
4. Sửa đường dẫn copy tài liệu thành nguồn tuyệt đối sau lỗi workdir; bản gốc không bị thay đổi. Chi phí: một lần thử setup bổ sung.
5. Giữ pin của kế hoạch và cảnh báo deprecation Starlette/HTTPX hiển thị. Chi phí: cần chuyển dependency TestClient trong lần nâng cấp sau, chưa làm trong phạm vi này.
6. Fixture tạo database UUID dùng một lần thay vì dọn schema của database được cung cấp. Chi phí: tài khoản test cần CREATEDB; quyền runtime dùng role test riêng.
7. Dùng import package `tests.conftest` để sửa trùng tên conftest trong bộ đầy đủ. Chi phí: không đổi hành vi sản phẩm.
8. Cấu hình stdout/stderr UTF-8 cho CLI để không nhầm lỗi in tiếng Việt với lỗi migration. Chi phí: output chuyển thành UTF-8 thay cho codepage hệ thống.
9. Dùng database thật cho API auth thay mock repository phức tạp. Chi phí: API tests cần test DSN.
10. Dùng Playwright thay kiểm tra browser chỉ bằng tay, thêm dev dependency 1.64.0. Chi phí: cần Edge hoặc Chromium khi chạy toàn bộ tests.
11. Giữ test cluster/ledger đến hết review và lượt sửa, sau đó dọn đúng workspace kế hoạch. Chi phí: tiến trình local tạm tồn tại trong lúc review.
12. Nâng lỗi CSRF không ASCII từ Minor lên Important vì invalid input phải trả 403, không gây 500. Chi phí: thêm một regression test/fix, không mở rộng chức năng.
13. Tách global session cleanup khỏi transaction login; cung cấp lệnh prune_auth riêng. Chi phí: xóa vật lý session phụ thuộc tác vụ dọn, session hết hạn vẫn bị từ chối ngay.
14. Giữ chấm công/GPS/bản đồ/maintenance nghiệp vụ ở phase sau. Chi phí: các chức năng đó chưa dùng được ở Phase 1.
15. Supabase exposed-schema/permissions/HTTPS production là bước triển khai môi trường. Chi phí: phải kiểm chứng riêng trước triển khai thực tế.

## Giới hạn và bước tiếp theo

Chưa tạo Supabase project, cấu hình production, cấp tài khoản thật, push hoặc merge. Branch/worktree được giữ để người dùng chọn tích hợp. Phase 2 xây dựng phiên Remote và lịch sử cá nhân trên nền tảng tài khoản này.
