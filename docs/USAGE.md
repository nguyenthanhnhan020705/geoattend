# Hướng dẫn sử dụng GeoAttend

Sau khi web và maintenance đã chạy theo [hướng dẫn cài đặt](DEVELOPMENT.md), mở `http://127.0.0.1:8000/login`. Môi trường triển khai dùng địa chỉ HTTPS do người vận hành cung cấp.

## Nhân viên

1. Đăng nhập bằng tài khoản Admin cấp. Có thể dùng ngay mật khẩu được cấp hoặc chủ động đổi tại **Đổi mật khẩu**.
2. Khi chưa bắt đầu ngày, chọn **CHECK-IN OFFICE**, **CHECK-IN REMOTE** hoặc **XIN NGHỈ**.
3. Office xin vị trí một lần và kiểm tra vùng văn phòng. Remote cần lý do, không xin GPS. Xin nghỉ yêu cầu chọn **BUỔI SÁNG/CẢ NGÀY**, nhập lý do rồi xác nhận.
4. Ở ca đầu, chọn **NGHỈ TRƯA** để đóng phiên và nghỉ; khi quay lại chọn **TIẾP TỤC OFFICE/REMOTE**. Office xác minh GPS lại; Remote nhập lý do cho phiên mới.
5. Nếu kết thúc ở ca đầu, chọn **CHECK-OUT SỚM**, nhập lý do rồi xác nhận. Sau nghỉ trưa hoặc nghỉ sáng, dùng **CHECK-OUT** cuối ngày; không bắt buộc lý do sớm.

Mọi Check-out và nghỉ cả ngày đều kết thúc ngày. Ngày hôm sau theo giờ Việt Nam mới bắt đầu lại. Nghỉ sáng cho phép tiếp tục buổi chiều Office/Remote trước 20:00 mà không cần chờ một giờ bắt đầu buổi chiều cố định.

Lúc 20:00 giờ Việt Nam, hệ thống đóng phiên còn mở; đang nghỉ trưa thì kết thúc ngày mà không kéo dài phiên trước nghỉ. Giao diện ghi rõ nguồn hệ thống, không coi 20:00 là giờ nhân viên thực tế kết thúc làm việc. Từ 20:00 không thể bắt đầu hoặc tiếp tục phiên.

Mở **Lịch sử cá nhân** ở cuối trang, chọn khoảng ngày để xem các phiên và sự kiện. Lịch sử chỉ tải khi mở phần này. Tọa độ/độ chính xác GPS đủ 30 ngày sẽ hết hạn lưu; lịch sử phiên và kết quả xác minh vẫn còn.

## Quản lý

- **Nhân viên:** tạo tài khoản User và cấp thông tin đăng nhập; đặt lại mật khẩu khi cần. Admin không chấm công cá nhân.
- **Văn phòng:** nhập tên/địa chỉ, chọn **Vẽ vùng**, bấm ít nhất ba đỉnh; chỉnh đỉnh nếu cần, chọn **Xem trước** rồi **Lưu vùng văn phòng**. Vùng mới chỉ áp dụng cho các lần xác minh tiếp theo.
- **Dashboard:** xem số lượng, danh sách theo trạng thái và bản đồ Onsite. Dữ liệu tự làm mới mỗi 30 giây khi tab đang hiển thị; có nút tải lại thủ công.
- **Lịch sử:** chọn nhân viên, lọc khoảng ngày và xem các phiên/sự kiện. Quyền xóa ngày có điều kiện và yêu cầu nhập đúng tên tài khoản; xem [ADMIN_HISTORY](ADMIN_HISTORY.md).

Marker Onsite là vị trí Check-in Office gần nhất đã xác minh của phiên đang mở. Ứng dụng không theo dõi GPS liên tục. Nhân viên rời trạng thái Office sẽ không còn Marker sau khi dữ liệu được làm mới.

## Nộp và xem báo cáo tuần

User bấm **NỘP BÁO CÁO TUẦN** cạnh **Đổi mật khẩu**, chọn một PDF tổng hợp nội dung tuần hiện tại (thứ Hai–Chủ nhật), tối đa 10 MB, rồi **Nộp báo cáo**. Muốn sửa file, chọn PDF mới và **Thay thế báo cáo**, xác nhận trước khi ghi đè. Sau hết Chủ nhật theo giờ Việt Nam, tuần cũ chỉ xem/tải và không nộp hoặc thay thế được; hạn báo cáo độc lập với cutoff chấm công 20:00.

Chủ nhật chưa nộp sẽ được nhắc **“BẠN CÒN 1 NGÀY ĐỂ NỘP BÁO CÁO NHÉ!!”**. Nếu tuần liền trước chưa nộp, tuần này hiện **“TUẦN VỪA RỒI BẠN CHƯA NỘP BÁO CÁO. HÃY TRÌNH BÀY NỘI DUNG ĐÓ GỘP VỚI TUẦN NÀY NHÉ!”**; tự gộp nội dung vào PDF tuần hiện tại. Thông báo nằm cả trên trang User và trang báo cáo khi đăng nhập.

Admin bấm **BÁO CÁO TUẦN** cạnh **Dashboard**, chọn tuần/nhân viên rồi **Xem báo cáo**; danh sách cho biết ai đã nộp/chưa nộp/quá hạn hoặc tuần chưa áp dụng. Dùng **Xem PDF** để mở tab mới hoặc **Tải PDF**. User chỉ xem file của mình; Admin xem báo cáo nhân viên, không nộp thay.

Nếu mất phản hồi, giữ tab và dùng **Gửi lại báo cáo**, không tạo yêu cầu mới khi chưa rõ kết quả. Sau reload phải kiểm tra trạng thái server trước khi chọn lại file; PDF không được lưu trong browser storage. Cần migration 005 trên môi trường đang dùng trước khi sử dụng chức năng này; chi tiết tại [báo cáo tuần](features/WEEKLY_REPORTS.md).

## Khi gặp lỗi

| Tình huống | Cách xử lý |
| --- | --- |
| Chưa có vùng văn phòng | Admin cấu hình Geofence trước khi nhân viên Check-in Office |
| Không lấy được GPS hoặc bị từ chối quyền | Bật quyền vị trí rồi thử lại; có thể tự chọn Remote và nhập lý do |
| Vị trí nằm ngoài vùng | Kiểm tra GPS/vùng văn phòng; hệ thống giữ trạng thái cũ, không tự chuyển Remote |
| Chưa rõ thao tác đã được ghi nhận do lỗi mạng | Dùng **Gửi lại thao tác** khi được hiển thị; giữ nguyên mã thao tác để tránh ghi trùng |
| Trang báo trạng thái đã thay đổi | Tải lại trạng thái trước khi thao tác tiếp |
| Bản đồ nền không tải | Chọn **Tải lại bản đồ**; editor vẫn có thể sửa vùng bằng tọa độ, danh sách/lịch sử vẫn dùng được |
| Lưu vùng bị timeout | Tải lại bản đã lưu để kiểm tra kết quả; chú ý bản nháp chưa lưu |
| Quên mật khẩu User | Nhờ Admin cấp lại; mọi phiên cũ của User sẽ bị thu hồi |

Các quy tắc chi tiết nằm trong [ACCOUNT_RULES](ACCOUNT_RULES.md) và [STATE_TRANSITIONS](STATE_TRANSITIONS.md).
