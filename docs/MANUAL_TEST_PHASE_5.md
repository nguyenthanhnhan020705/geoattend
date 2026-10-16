# Kiểm tra Dashboard và Onsite — Phase 5

Chỉ tạo tài khoản, Geofence, chấm công hoặc xóa lịch sử thử trên database test riêng. Không trỏ DSN test vào Supabase/database ứng dụng. Bộ pytest tự tạo và drop database `geoattend_test_<uuid>`; không dùng các database tạm đó cho web đang chạy.

## Kiểm tra tự động có trình duyệt

Chạy từ `.worktrees/phase-1` khi cluster PostgreSQL 17/PostGIS test local ở port 55440 đã sẵn sàng:

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
.\.venv\Scripts\python.exe -m pytest tests/integration/test_admin_dashboard_browser.py tests/integration/test_admin_dashboard_refresh.py -q --basetemp=.local-tests/phase-5/manual-browser-01 -o cache_dir=.local-tests/phase-5/cache
```

Đổi tên `manual-browser-01` khi chạy lại. Playwright dùng Edge headless mặc định trên máy bàn giao; có thể đặt `GEOATTEND_BROWSER_CHANNEL=chromium` nếu browser đó đã được cài. Ảnh 360px/1280px nằm ở `.local-tests/phase-5/artifacts/`, không commit dữ liệu/ảnh test.

## Checklist trên ứng dụng test riêng

1. Đăng nhập Admin, từ **Quản lý nhân viên** chọn **Dashboard**. Trang `/admin/dashboard` chỉ dành cho Admin; khách chuyển về login, User nhận 403.
2. Đối chiếu tổng nhân viên, bảy thẻ trạng thái và từng người trong danh sách. Gồm User chưa chấm công và User bị khóa; Admin không được tính. Trạng thái tài khoản bị khóa hiển thị riêng.
3. Đưa User qua Office, Remote, nghỉ trưa, nghỉ sáng, nghỉ cả ngày, Check-out. Hai loại nghỉ phải tách biệt; hủy nghỉ để làm việc không còn tính nghỉ cả ngày.
4. Với Office, kiểm tra Polygon, Marker và tên. Popup có tên, trạng thái, giờ Check-in Việt Nam, xác minh GPS và nút **Lịch sử**. Vị trí là lúc bắt đầu phiên đã xác minh, không phải GPS trực tiếp.
5. Mở lịch sử từ Marker và danh sách: đúng nhân viên, cùng bộ lọc/phân trang/xóa ngày đã có. Xóa chỉ trên test DB với xác nhận username/revision; ngày đang làm/nghỉ trưa không được xóa. Refresh Dashboard sau xóa ngày hôm nay phải về chưa bắt đầu.
6. Nghỉ trưa/chuyển Remote/Check-out, rồi tải lại: Marker Office biến mất. Tiếp tục Office phải dùng GPS của phiên mới, không dùng điểm cũ.
7. Kiểm tra hết hạn GPS trước/đúng/sau 30 ngày bằng clock/dữ liệu kiểm soát trong test: API không có tọa độ/accuracy hết hạn dù chưa purge. Danh sách báo **Dữ liệu vị trí đã hết hạn lưu**, không đặt Marker thay thế; thiếu vị trí cũng không dùng tâm văn phòng hoặc (0,0).
8. Đợi 30 giây khi tab visible, quay lại tab và bấm **Tải lại dữ liệu**. Snapshot thay đổi cùng số lượng/danh sách/Marker; tab ẩn ngừng polling, không gọi Geolocation. Snapshot ghi ngày và giờ Việt Nam.
9. Giả lập 503/timeout: giữ dữ liệu cũ, hiện nhãn **Dữ liệu cũ** và giữ thời điểm snapshot. Phục hồi mạng bỏ nhãn. Phản hồi cũ về muộn không ghi đè bản mới. 401 quay về login; 403 dừng polling.
10. Chặn nguồn bản đồ: danh sách/lịch sử vẫn dùng được; hiện thông báo và **Tải lại bản đồ**, không xóa snapshot. Thử cả trường hợp thư viện map không sẵn sàng.
11. Theo link **Văn phòng**: tên/địa chỉ/Polygon và revision vẫn dùng editor cũ. Sửa vùng không thay điểm lịch sử. Cutoff 20:00 và múi giờ không có cài đặt sửa. Theo link **Nhân viên**, **Tài khoản cá nhân** và quay lại Dashboard.
12. Nhập tên/lý do chứa HTML trên test DB: chỉ thấy văn bản, không chạy HTML/script trong danh sách, tooltip, popup hoặc lịch sử. Kiểm tra 360px và desktop không tràn ngang.
13. Chạy lại UI User theo ca: trước nghỉ chỉ Nghỉ trưa/Check-out sớm, nghỉ trưa chỉ hai lựa chọn tiếp tục, sau tiếp tục chỉ Check-out; Check-out cuối ngày khóa đến hôm sau. Ngoại lệ Admin xóa ngày/reset và replay UUID vẫn giữ nguyên.

Các ca browser tự động đã kiểm tra desktop/mobile giả lập và mạng lỗi; GPS trên điện thoại thật/HTTPS, nguồn nền bản đồ Internet thực tế và pilot thuộc Phase 6, chưa được chứng nhận bởi lượt này.
