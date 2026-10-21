> **Tài liệu lưu trữ:** nội dung và số liệu bên dưới phản ánh thời điểm lập tài liệu. Các hướng dẫn/quy tắc cũ có thể đã được thay thế; xem [tài liệu hiện hành](../README.md) trước khi thực hiện.

# GeoAttend — Kiểm thử thủ công Phase 1–2

Mở `http://127.0.0.1:8000/login` trên chính máy chạy ứng dụng. Dùng cửa sổ thường cho Admin và cửa sổ ẩn danh cho User để hai phiên đăng nhập độc lập. Admin tạo một User chuyên kiểm thử, ví dụ `user_qa_01`; các thao tác qua giao diện được lưu vào Supabase thực.

## Các chức năng đã có

- Đăng nhập, đăng xuất; Admin tạo User và đặt lại mật khẩu.
- Tự đổi mật khẩu; đổi hoặc đặt lại mật khẩu thu hồi các phiên của tài khoản đó.
- Remote có lý do, Check-out, bắt đầu lại trước 20:00 giờ Việt Nam.
- Trạng thái hôm nay, lịch sử cá nhân và lọc khoảng ngày.
- Tự đóng phiên còn mở lúc 20:00, xử lý bù nếu hệ thống chạy lại sau gián đoạn.

Office/GPS, bản đồ Geofence, nghỉ trưa/nghỉ và Dashboard Admin chưa có trong Phase 2.

## Checklist tài khoản — kiểm thử bất kỳ giờ nào

| Bước | Thao tác | Kết quả cần thấy |
| --- | --- | --- |
| 1 | Admin đăng nhập, tạo `user_qa_01` | User mới xuất hiện trong danh sách. |
| 2 | Tạo lại cùng tên tài khoản | Thông báo tên đã tồn tại; không thêm tài khoản thứ hai. |
| 3 | Trong cửa sổ ẩn danh, User nhập sai mật khẩu một lần | Đăng nhập bị từ chối. |
| 4 | User đăng nhập bằng mật khẩu được cấp | Vào trang `/user`. |
| 5 | User mở `/admin/users` | Bị từ chối truy cập. Admin mở `/user` cũng bị từ chối. |
| 6 | User đổi mật khẩu | Phải đăng nhập lại; mật khẩu mới dùng được, mật khẩu cũ bị từ chối. |
| 7 | Admin đặt lại mật khẩu cho User, rồi User tải lại trang | Phiên User cũ bị từ chối; mật khẩu mới do Admin cấp dùng được. |
| 8 | User đăng xuất, mở lại `/user` | Chuyển đến đăng nhập. |

## Checklist Remote — thực hiện trước 20:00 giờ Việt Nam

| Bước | Thao tác | Kết quả cần thấy |
| --- | --- | --- |
| 1 | Đăng nhập bằng User chưa bắt đầu ngày hôm nay | Trạng thái “Chưa bắt đầu”, có form Remote. |
| 2 | Để lý do trống và bấm “Bắt đầu Remote” | Không tạo phiên, yêu cầu điền lý do. |
| 3 | Nhập lý do, bấm “Bắt đầu Remote” | “Đang làm Remote”, có giờ bắt đầu và nút Check-out. Không hỏi quyền GPS. |
| 4 | Tải lại trang | Vẫn đang Remote, cùng phiên đã ghi nhận. |
| 5 | Bấm Check-out | “Đã Check-out”; lịch sử có giờ bắt đầu và kết thúc. |
| 6 | Nhập lý do và bắt đầu Remote lần nữa | Tạo phiên mới; phiên cũ vẫn còn trong lịch sử. |
| 7 | Check-out lần nữa rồi lọc lịch sử ngày hôm nay | Xem được cả hai phiên. Chọn khoảng ngày không có dữ liệu thì có thông báo trống. |
| 8 | Chọn ngày bắt đầu sau ngày kết thúc | Báo khoảng ngày không hợp lệ. |
| 9 | Đăng nhập bằng User khác | Không xem được lịch sử của User vừa kiểm thử. |

## Quy tắc 20:00

- Từ đúng 20:00 đến hết ngày, không thể bắt đầu Remote; việc không có nút bắt đầu là hành vi dự kiến.
- Để kiểm thử thủ công tự đóng: mở Remote trước 20:00, giữ web và maintenance chạy qua mốc này, rồi bấm “Làm mới”. Phiên chuyển sang “Đã Check-out”; giờ kết thúc là 20:00 và lịch sử ghi nguồn hệ thống. Đây không phải giờ kết thúc thực tế của nhân viên.
- Nếu máy tắt lúc 20:00, chạy lại web/maintenance sẽ xử lý bù với cùng mốc nghiệp vụ 20:00.
- Kiểm thử tự động đã kiểm tra trước/đúng/sau 20:00, thao tác đồng thời và gửi lại qua ngày bằng đồng hồ kiểm soát trong database thử nghiệm riêng. Không cần đổi giờ Windows hoặc sửa dữ liệu Supabase để kiểm thử các mốc này.

## Nếu vừa khởi động lại máy

Mở PowerShell, vào đúng worktree và chạy web:

```powershell
cd D:\N.ThanhNhan\INTERN\geoattend\.worktrees\phase-1
.\.venv\Scripts\python.exe -m scripts.local_run serve
```

Mở PowerShell thứ hai để chạy maintenance:

```powershell
cd D:\N.ThanhNhan\INTERN\geoattend\.worktrees\phase-1
.\.venv\Scripts\python.exe -m scripts.local_run maintenance
```

Giữ hai Terminal mở. Không cần tạo lại role, chạy lại bootstrap Admin hay nhập lại DSN. Kiểm tra `http://127.0.0.1:8000/api/health`: kết quả bình thường là `{"status":"ok","database":"ok"}`.

## Ghi nhận kết quả

Với mỗi lỗi, ghi tài khoản/vai trò đang thử, các bước thao tác, giờ xảy ra, thông báo thực tế và kết quả mong đợi. Không gửi mật khẩu. Bằng chứng tự động gần nhất nằm trong [báo cáo Phase 2](PHASE_2_VERIFICATION.md).
