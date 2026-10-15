# GeoAttend — Bảng chuyển trạng thái

Nguồn: [BRD](../README.md), các quyết định Phase 0 đã được người dùng xác nhận.

Mục 1–2 tổng hợp quy tắc đã chốt. Mục 3–4 đã được duyệt cùng [bản thiết kế Phase 0](superpowers/specs/2026-10-14-geoattend-mvp-design.md).

## 1. Điều kiện chung đã chốt

- Bảng chuyển trạng thái áp dụng cho tài khoản `USER`. Admin chỉ quản lý, không có trạng thái chấm công cá nhân và không được thực hiện các thao tác trong bảng.
- Ngày làm việc và mốc 20:00 dùng giờ Việt Nam (`Asia/Ho_Chi_Minh`, UTC+07:00).
- Mọi thao tác bắt đầu, tiếp tục hoặc chuyển Office/Remote phải diễn ra trước 20:00.
- Office cần vị trí trong hoặc trên ranh giới Geofence; không dùng vùng đệm và không chặn theo sai số GPS. Lưu độ chính xác để tra cứu.
- Remote cần lý do; không lấy GPS. Check-out và thao tác nghỉ cũng không lấy GPS.
- Thao tác Office không xác minh được vị trí giữ nguyên trạng thái; không tự chuyển Remote.
- Phiên đã đóng được giữ trong lịch sử; bắt đầu lại tạo phiên mới.

## 2. Các chuyển đổi đã chốt

| Trạng thái hiện tại | Thao tác | Trạng thái sau khi thành công | Tác động lên dữ liệu |
| --- | --- | --- | --- |
| `NOT_STARTED` | Check-in Office | `WORKING_OFFICE` | Xác minh vị trí, tạo phiên Office và sự kiện bắt đầu. |
| `NOT_STARTED` | Check-in Remote | `WORKING_REMOTE` | Kiểm tra lý do, tạo phiên Remote và sự kiện bắt đầu. |
| `NOT_STARTED` | Nghỉ buổi sáng | `MORNING_LEAVE` | Lưu sự kiện nghỉ và lý do; không tạo phiên làm việc. |
| `NOT_STARTED` | Nghỉ cả ngày | `FULL_DAY_LEAVE` | Lưu sự kiện nghỉ và lý do; không tạo phiên làm việc. |
| `WORKING_OFFICE` hoặc `WORKING_REMOTE` | Nghỉ trưa | `LUNCH_BREAK` | Đóng phiên hiện tại tại thời điểm nghỉ và lưu sự kiện nghỉ trưa. |
| `LUNCH_BREAK` | Tiếp tục Office | `WORKING_OFFICE` | Xác minh lại vị trí, tạo phiên mới. |
| `LUNCH_BREAK` | Tiếp tục Remote | `WORKING_REMOTE` | Nhập lý do và tạo phiên mới. |
| `MORNING_LEAVE` | Bắt đầu Office | `WORKING_OFFICE` | Xác minh vị trí, tạo phiên; không phải chờ mốc bắt đầu buổi chiều. |
| `MORNING_LEAVE` | Bắt đầu Remote | `WORKING_REMOTE` | Nhập lý do, tạo phiên; không phải chờ mốc bắt đầu buổi chiều. |
| `WORKING_OFFICE` hoặc `WORKING_REMOTE` | Check-out | `CHECKED_OUT` | Đóng phiên hiện tại, lưu sự kiện kết thúc do nhân viên thao tác. |
| `CHECKED_OUT` trước nghỉ trưa | Bắt đầu Office | `WORKING_OFFICE` | Xác minh vị trí, tạo phiên mới; giữ phiên cũ. |
| `CHECKED_OUT` trước nghỉ trưa | Bắt đầu Remote | `WORKING_REMOTE` | Nhập lý do, tạo phiên mới; giữ phiên cũ. |
| `FULL_DAY_LEAVE` | Hủy nghỉ và bắt đầu Office | `WORKING_OFFICE` | Giữ sự kiện đăng ký nghỉ, ghi hủy nghỉ và tạo phiên Office sau xác minh. |
| `FULL_DAY_LEAVE` | Hủy nghỉ và bắt đầu Remote | `WORKING_REMOTE` | Giữ sự kiện đăng ký nghỉ, ghi hủy nghỉ và tạo phiên Remote có lý do. |
| `WORKING_OFFICE` | Chuyển sang Remote | `WORKING_REMOTE` | Kiểm tra lý do rồi đóng phiên Office và tạo phiên Remote trong cùng giao dịch. |
| `WORKING_REMOTE` | Chuyển sang Office | `WORKING_OFFICE` | Xác minh GPS rồi đóng phiên Remote và tạo phiên Office trong cùng giao dịch. |
| `WORKING_OFFICE` hoặc `WORKING_REMOTE` | Hệ thống tự đóng lúc 20:00 | `CHECKED_OUT` | Đóng phiên và ghi nguồn hệ thống; không coi mốc này là giờ kết thúc thực tế. |
| `LUNCH_BREAK` | Hệ thống kết thúc ngày lúc 20:00 | `CHECKED_OUT` | Chỉ ghi sự kiện kết thúc ngày; không tạo phiên, không sửa thời gian kết thúc phiên trước nghỉ trưa. |

Marker Onsite chỉ tồn tại khi trạng thái là `WORKING_OFFICE`, dùng vị trí bắt đầu phiên Office đã xác minh. Mọi lần rời trạng thái này đều loại Marker khỏi nhóm Onsite khi dữ liệu được làm mới.

## 3. Bảo đảm dữ liệu nhất quán

Các lựa chọn sau đã được duyệt trong bản thiết kế Phase 0 để triển khai nhất quán các quy tắc nghiệp vụ.

- Tối đa một phiên đang mở cho mỗi nhân viên; chỉ `WORKING_OFFICE` và `WORKING_REMOTE` có phiên đang mở.
- Ghi thay đổi phiên, sự kiện và trạng thái trong cùng giao dịch. Lỗi ghi dữ liệu phải hủy toàn bộ thay đổi của thao tác.
- Hủy nghỉ và bắt đầu làm việc là một thao tác kết hợp: chỉ ghi hủy nghỉ sau khi điều kiện Office/Remote hợp lệ; thất bại giữ `FULL_DAY_LEAVE`. Không cung cấp thao tác hủy nghỉ độc lập trong MVP.
- Tuần tự hóa các thay đổi của cùng nhân viên; thao tác gửi từ màn hình đã cũ phải kiểm tra lại trạng thái tại Backend.
- Yêu cầu gửi lại với cùng mã thao tác và cùng nội dung trả kết quả trước đó, không tạo thêm phiên/sự kiện. Tái sử dụng mã với nội dung khác bị từ chối.
- Dùng thời gian Backend để quyết định trước hay sau 20:00; không cho thời gian thiết bị vượt qua giới hạn. Quy tắc này cần kiểm thử cả yêu cầu chờ xử lý qua mốc 20:00.
- Tác vụ tự đóng chạy lại không tạo sự kiện trùng. Nếu chạy trễ, lưu riêng mốc nghiệp vụ 20:00 và thời điểm thực thi thực tế; xử lý phiên cũ trước khi cho mở phiên mới.
- Từ 20:00 đến hết ngày, các yêu cầu tạo phiên bị từ chối dù tác vụ tự đóng chưa chạy xong.

## 4. Quy tắc bổ sung của bảng trạng thái

- Trạng thái gắn với từng ngày làm việc. Ngày mới bắt đầu `NOT_STARTED` nếu chưa có sự kiện của ngày đó; giữ nguyên lịch sử ngày trước.
- Không tự đổi `MORNING_LEAVE`, `FULL_DAY_LEAVE` hoặc `NOT_STARTED` thành `CHECKED_OUT` lúc 20:00: không có phiên làm việc cần đóng.
- Chỉ đăng ký nghỉ sáng/cả ngày từ `NOT_STARTED`; trường hợp đã làm việc rồi muốn kết thúc ngày dùng Check-out theo BR-09.
- Các thao tác không có trong bảng bị từ chối. Ví dụ: Check-out từ `NOT_STARTED`, nghỉ trưa khi không làm việc, Check-in cùng chế độ khi đã có phiên đang mở.
- Riêng thao tác gửi lại hợp lệ với cùng mã yêu cầu xử lý theo mục 3, không coi là một lần chuyển trạng thái mới.

Quy tắc mục 3–4, xác thực, mô hình dữ liệu, API và giao diện đã được duyệt cùng bản thiết kế Phase 0; triển khai theo kế hoạch từng phase.

## 5. Ngoại lệ quản trị được bổ sung 15/10/2026

Theo yêu cầu mới của người dùng, Admin được xóa vĩnh viễn lịch sử từng ngày đã dừng làm việc; chặn trạng thái đang làm việc/nghỉ trưa và mọi phiên mở. Phiên/sự kiện/lý do/GPS bị xóa trong cùng transaction; giữ revision/request UUID/hash kỹ thuật để chặn màn hình cũ/retry phục hồi lịch sử. Nếu xóa hôm nay, trạng thái trở về `NOT_STARTED` với revision tăng; thao tác User tiếp theo vẫn phải tuân thủ cutoff. Không thay đổi bảng chuyển trạng thái User thông thường. Xem [ADMIN_HISTORY](ADMIN_HISTORY.md).

## 6. Điều chỉnh luồng User theo ca, 15/10/2026

Người dùng yêu cầu chỉ hiển thị nghỉ trưa/Check-out sớm ở ca đầu, hai lựa chọn tiếp tục Office/Remote khi nghỉ trưa, và chỉ Check-out sau khi tiếp tục. Người dùng xác nhận **khóa đến ngày hôm sau** sau Check-out cuối ngày. Quy tắc mới thay thế quyền bắt đầu lại từ mọi trạng thái `CHECKED_OUT` của thiết kế ban đầu: chỉ Check-out trước khi đã nghỉ trưa còn cho bắt đầu lại trước 20:00.

Backend dùng `LUNCH_START` của ngày hiện tại để phân biệt: `CHECKED_OUT` có sự kiện này là ngày đã kết thúc (`day_finished=true`), không có action mới, API trả `DAY_FINISHED`; cùng UUID đã commit vẫn replay. Ngày mới bắt đầu `NOT_STARTED`. Admin xóa lịch sử theo mục 5 vẫn là ngoại lệ có quyền đưa ngày về chưa bắt đầu. API chuyển chế độ cũ giữ tương thích; giao diện không cung cấp nút chuyển trực tiếp khi đang làm việc.
