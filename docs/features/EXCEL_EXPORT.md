# Xuất Excel chấm công cho Admin

Yêu cầu được duyệt ngày 20/10/2026: Admin xuất lịch sử chấm công ra `.xlsx`, chọn khoảng ngày và tất cả hoặc một nhân viên.

## Cách dùng

Vào **Quản lý nhân viên → Xuất Excel chấm công**, chọn **Từ ngày**, **Đến ngày**, **Nhân viên** rồi bấm **Xuất Excel**. Mặc định là 7 ngày gần nhất theo giờ Việt Nam và tất cả nhân viên; cho phép tối đa 366 ngày trong một file. Bộ lọc được giữ khi tải lại danh sách nhân viên.

File `geoattend_YYYY-MM-DD_YYYY-MM-DD.xlsx` có sheet **Chấm công** với các cột:

| Cột | Nội dung |
| --- | --- |
| Ngày | Ngày làm việc theo giờ Việt Nam, kiểu ngày Excel |
| Họ tên | Nhân viên tương ứng, kể cả tài khoản đã khóa còn lịch sử |
| Hình thức | Tổng hợp Office, Remote, nghỉ buổi sáng hoặc nghỉ cả ngày |
| Check-in sáng | Lần bắt đầu phiên sáng đầu tiên |
| Nghỉ trưa | Mốc bắt đầu nghỉ trưa |
| Check-in chiều | Lần bắt đầu đầu tiên sau nghỉ trưa/nghỉ sáng; nếu không có sự kiện nghỉ, phân buổi theo 12:00 giờ Việt Nam |
| Check-out | Mốc kết thúc phiên cuối; trống khi còn làm việc hoặc mới nghỉ trưa |
| Lý do | Tổng hợp lý do nghỉ và Remote, ghi rõ hình thức |

Mỗi nhân viên trong một ngày có một dòng, kể cả khi đổi Office/Remote hoặc nghỉ sáng rồi làm chiều. Nhân viên trùng họ tên vẫn có các dòng riêng. Ngày nghỉ không có giờ chấm công được để trống. File có tiêu đề cố định khi cuộn, bộ lọc và độ rộng cột; ngày/giờ dùng kiểu Excel. Khoảng không có ghi nhận trả file có tiêu đề, không tự suy ra nghỉ/vắng.

Mốc hệ thống tự đóng ghi kèm “hệ thống tự đóng” trong ô Check-out, không xác nhận giờ nhân viên thực tế ngừng làm việc. Không xuất GPS, độ chính xác, thông tin đăng nhập hoặc lịch sử đã xóa. Họ tên và lý do được ghi dưới dạng văn bản, không thực thi thành công thức Excel.

## Triển khai và quyền

- `GET /api/admin/attendance/export?from=YYYY-MM-DD&to=YYYY-MM-DD&user_id=UUID`: chỉ Admin. Không truyền `user_id` để xuất toàn bộ nhân viên.
- Tối đa 366 ngày, kiểm tra kiểu ngày, thứ tự khoảng ngày và nhân viên đích. Mặc định 7 ngày nếu không truyền khoảng.
- Dùng chung khóa profile với Dashboard/chấm công; kiểm tra lại quyền và phiên đăng nhập sau chờ khóa. Đối soát ngày quá hạn trước khi xuất. Dữ liệu được đọc trong cùng transaction; tạo workbook sau khi nhả khóa.
- Phản hồi `Cache-Control: no-store`; file tải xuống nằm trên máy Admin, không lưu bản xuất trên server.
- Mã: `app/admin/export.py`, `xlsx.py`, endpoint ở `routes.py`, `app/static/js/admin-export.js` và trang Quản lý nhân viên. Dùng thư viện chuẩn Python để tạo OOXML; không thêm dependency hoặc migration.
- Khi web đang chạy phiên bản cũ, cần khởi động lại tiến trình web để nạp endpoint Python mới. Không cần khởi động lại maintenance hoặc sửa database.

## Kiểm chứng

Test API/PostGIS: `tests/integration/test_admin_export.py`. Kiểm tra quyền, bộ lọc, ngày/giờ Excel, nghỉ, phiên mở/tự đóng, tài khoản khóa, lịch sử đã xóa và văn bản có ký tự công thức. Test trình duyệt: `test_admin_export_browser.py` kiểm tra tải file ở 360px/1280px, lỗi/thử lại và giữ bộ lọc. Chỉ sử dụng database test cô lập; không tạo dữ liệu thử trên database ứng dụng.

Đã kiểm chứng local ngày 20/10/2026: **41 test** export/Dashboard/quyền/trình duyệt đạt, sau đó **1 test** bổ sung thu hồi phiên Admin khi chờ khóa đạt. Có một cảnh báo Starlette/httpx sẵn có. File mẫu đã được mở bằng Microsoft Excel cài trên máy ở chế độ chỉ đọc: sheet **Chấm công**, 7 cột, ngày `2026-10-14`, Check-in `09:00:00`, kết thúc `17:00:00` đúng. Ảnh và file mẫu nằm trong `.local-tests/excel-export/artifacts/`.

Review độc lập chỉ đọc không tìm thấy lỗi quan trọng; trường hợp `to=0001-01-01` gây tràn ngày mặc định đã được sửa và kiểm tra trả 422. `git diff --check` đạt. Web local đã khởi động lại, health 200 và OpenAPI có endpoint mới; không chạy migration hoặc tạo dữ liệu thử trên database ứng dụng. Chưa tuyên bố nghiệm thu mọi phiên bản Excel hoặc môi trường production.
