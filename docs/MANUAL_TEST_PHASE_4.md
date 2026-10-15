# GeoAttend — Kiểm thử tay Phase 4

Chỉ thực hiện trên môi trường test riêng với User/Admin test, Geofence test và thời gian Backend kiểm soát. Không tạo tài khoản, Geofence hoặc chấm công thử trên Supabase thật. Checklist này dành cho kiểm thử thiết bị thực tiếp theo; bằng chứng tự động nằm trong [PHASE_4_VERIFICATION](PHASE_4_VERIFICATION.md).

## Chuẩn bị

- Dựng ứng dụng/maintenance với database test riêng theo [DEVELOPMENT](DEVELOPMENT.md); Admin cấu hình vùng test, cấp User test.
- Đăng nhập User, mở `/user`; kiểm tra trên màn hình 360px và desktop.
- Thông tin nhân viên ở đầu trang. Chọn **CHECK-IN REMOTE** hoặc **XIN NGHỈ** để mở form lý do; mở **Lịch sử cá nhân** cuối trang khi cần kiểm tra timeline. Form và lịch sử mặc định thu gọn để dùng trên điện thoại.
- Chỉ Office xin GPS một lần; Remote/nghỉ/Check-out không xin GPS. Các nút thay đổi theo trạng thái server, bị khóa trong khi gửi hoặc đang chờ xác nhận.

## Tám kịch bản

Mỗi dòng bắt đầu ở ngày test mới trước 20:00 giờ Việt Nam. Không sửa đồng hồ thiết bị để vượt thời gian Backend.

| Luồng | Kiểm tra |
| --- | --- |
| Office → Nghỉ trưa → Tiếp tục Office → Check-out | Hai phiên, hai lần GPS, phiên sáng kết thúc tại lúc nghỉ, khoảng nghỉ không nằm trong phiên. |
| Remote → Nghỉ trưa → Tiếp tục Remote → Check-out | Hai lý do độc lập, hai phiên, không GPS. |
| Remote → Nghỉ trưa → Tiếp tục Office | Phiên Remote cũ được giữ, Office xác minh GPS mới. |
| Office → Nghỉ trưa → Tiếp tục Remote | Phiên Office cũ được giữ, Remote yêu cầu lý do mới. |
| Nghỉ buổi sáng → Office | Lý do nghỉ được giữ; có thể bắt đầu ngay khi quay lại trước 20:00, GPS bắt buộc. |
| Nghỉ buổi sáng → Remote | Lý do nghỉ và lý do Remote khác nhau; không chờ đến buổi chiều. |
| Nghỉ cả ngày | Không phiên/GPS; có lý do trong lịch sử. Chỉ có hai nút hủy nghỉ kết hợp bắt đầu, không có hủy nghỉ độc lập. |
| Office/Remote → Check-out → bắt đầu lại | Phiên cũ đóng và được giữ, phiên mới có ID khác, Office xác minh GPS lại. |

## Hủy nghỉ, chuyển chế độ và lỗi

- Nghỉ cả ngày → Hủy nghỉ và bắt đầu Office/Remote: lịch sử giữ cả đăng ký nghỉ, hủy nghỉ và phiên mới; trạng thái ngày chuyển làm việc. GPS ngoài vùng hoặc Remote không có lý do giữ nguyên nghỉ cả ngày.
- Office → Chuyển sang Remote và Remote → Chuyển sang Office: đóng phiên nguồn/mở phiên đích tại cùng thời điểm; GPS/lý do sai giữ phiên nguồn mở. Không cho bắt đầu/chuyển cùng chế độ.
- Nghỉ sáng/cả ngày chỉ có ở `NOT_STARTED`; nghỉ trưa chỉ khi đang làm việc. Lý do trắng hoặc quá 1000 ký tự bị từ chối; lý do chứa HTML hiển thị dạng text.
- Chặn quyền GPS, GPS timeout/ngoài vùng: giữ trạng thái, cho phép thử lại hoặc tự chọn Remote. Kiểm tra storage không chứa tọa độ/accuracy của bất kỳ action Office nào.
- Mất phản hồi sau commit: bấm **Gửi lại thao tác**, giữ UUID/payload cũ, không nhân đôi phiên/event. Với thao tác không GPS, tải lại trang rồi retry vẫn giữ UUID; với Office, GPS chỉ giữ trong bộ nhớ tab, reload đọc lại trạng thái server.
- Hai tab cùng revision: chỉ một thao tác thành công, tab kia nhận xung đột và tải lại. Khi User bị khóa hoặc session bị thu hồi trong lúc chờ khóa, thao tác bị từ chối.
- Tại 19:59 cho tiếp tục/hủy nghỉ/chuyển chế độ; đúng 20:00 trở đi từ chối. Nghỉ trưa qua cutoff chỉ thêm một `DAY_END` SYSTEM, không sửa giờ kết thúc phiên trước nghỉ. Giao diện ghi rõ hệ thống kết thúc ngày, không phải giờ kết thúc thực tế.
- Dừng worker qua cutoff rồi chạy lại trên test: đối soát bù đúng một lần; ngày mới `NOT_STARTED`, giữ lịch sử ngày cũ. Nghỉ sáng/cả ngày không tự đổi thành Check-out.
- Admin không có quyền chấm công; User chỉ đọc lịch sử bản thân. Kiểm tra retention 30 ngày vẫn che GPS và giữ kết quả xác minh.

Chưa xác nhận GPS điện thoại thật, HTTPS production, hiệu năng/pilot; các mục đó thuộc Phase 6. Không dùng checklist để thử trên Supabase thật.
