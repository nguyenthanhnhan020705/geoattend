# GeoAttend — Quy tắc tài khoản MVP

Nguồn: [BRD](REQUIREMENTS.md), các quyết định tài khoản được xác nhận trong Phase 0.

## 1. Phạm vi đã chốt

| Nội dung | Quy tắc |
| --- | --- |
| Đăng nhập | Tên tài khoản và mật khẩu. |
| Admin | Một tài khoản được khởi tạo khi thiết lập hệ thống; không có chức năng cấp thêm quyền Admin trong MVP. |
| Phạm vi Admin | Chỉ quản lý, không chấm công cá nhân; không được tính vào tổng số nhân viên, nhóm trạng thái và bản đồ Onsite. |
| Cấp tài khoản | Admin tạo tên tài khoản duy nhất và mật khẩu ban đầu, cấp cho User. |
| Đăng nhập lần đầu | User sử dụng ngay mật khẩu được cấp; không buộc đổi mật khẩu. |
| Đổi mật khẩu | Người dùng đã đăng nhập có thể chủ động đổi mật khẩu cá nhân. |
| Quên mật khẩu User | Admin đặt lại và cấp mật khẩu mới; không khôi phục qua email trong MVP. |
| Bảo toàn dữ liệu | Đổi/đặt lại mật khẩu không đổi vai trò hoặc lịch sử làm việc. |

## 2. Luồng tài khoản

```text
Thiết lập hệ thống → Khởi tạo một Admin
Admin đăng nhập → Tạo tài khoản USER → Cấp thông tin đăng nhập
User đăng nhập → Sử dụng chức năng theo vai trò
              └── Chủ động đổi mật khẩu nếu muốn

User quên mật khẩu → Liên hệ Admin
Admin đặt lại mật khẩu → Cấp mật khẩu mới → User đăng nhập
```

Cấp thông tin cho nhân viên là công việc của Admin; tài liệu này không mặc định hệ thống gửi email hoặc tin nhắn.

## 3. Thiết kế kỹ thuật đã duyệt

- Cơ chế xác thực, nơi lưu thông tin xác thực, phiên đăng nhập và đăng xuất.
- Cách chuẩn hóa tên tài khoản và yêu cầu mật khẩu.
- Quy trình thiết lập/khôi phục tài khoản Admin duy nhất mà không lưu bí mật trong mã nguồn.
- Kiểm tra mật khẩu hiện tại khi người dùng tự đổi; xử lý phiên đăng nhập sau đổi/đặt lại mật khẩu.
- API chấm công cá nhân chỉ nhận vai trò `USER`; Admin chỉ đọc trạng thái/lịch sử nhân viên qua API quản lý.

Các nội dung mục 3 đã được mô tả và duyệt trong [bản thiết kế Phase 0](archive/superpowers/specs/2026-10-14-geoattend-mvp-design.md), mục 3. Phần tài khoản đã triển khai; hướng dẫn vận hành hiện hành tại [DEVELOPMENT](DEVELOPMENT.md).

## 4. Đối chiếu yêu cầu

Cập nhật theo yêu cầu người dùng 15/10/2026: Admin được xem lịch sử từng nhân viên và xóa vĩnh viễn từng ngày sau xác nhận tên tài khoản. Không xóa ngày đang làm việc/nghỉ trưa; không cấp quyền xóa cho User. Chi tiết tại [ADMIN_HISTORY](ADMIN_HISTORY.md).

- FR-01 / AC-01: đăng nhập và phân quyền.
- FR-16 / AC-17: khởi tạo một Admin và cấp tài khoản User.
- FR-17 / AC-18: đổi mật khẩu cá nhân tùy chọn.
- FR-18 / AC-19: Admin đặt lại mật khẩu User.
