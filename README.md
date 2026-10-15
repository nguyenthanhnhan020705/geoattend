# GeoAttend — Tài liệu yêu cầu nghiệp vụ (BRD)

> **Business Requirements Document** cho hệ thống chấm công và quản lý trạng thái làm việc dựa trên GIS.

Bàn giao agent tiếp theo: [README Phase 0–4 — kết quả và kế hoạch triển khai](handoff/README.md).

Bổ sung được người dùng xác nhận 15/10/2026: [Admin xem và xóa vĩnh viễn lịch sử từng ngày của nhân viên](docs/ADMIN_HISTORY.md), có xác nhận tên tài khoản và chặn ngày đang làm việc/nghỉ trưa. Quyền này thay thế giới hạn không xóa lịch sử trong thiết kế ban đầu; không cấp quyền xóa cho User.

Lộ trình triển khai: [Các phase phát triển MVP](docs/ROADMAP.md).

Chạy nền tảng và tài khoản: [Hướng dẫn phát triển](docs/DEVELOPMENT.md).

Thiết kế Phase 0 đã duyệt: [Kiến trúc, dữ liệu, API và màn hình MVP](docs/superpowers/specs/2026-10-14-geoattend-mvp-design.md).

| Thuộc tính | Nội dung |
| --- | --- |
| Dự án | GeoAttend |
| Phạm vi tài liệu | Phiên bản MVP |
| Trạng thái tài liệu | Bản nháp; các điểm cần làm rõ được ghi tại mục 10 |
| Đối tượng sử dụng | Người quản lý, nhân viên và nhóm phát triển |
| Quy mô thử nghiệm | 01 công ty, 01 văn phòng, 01 nhóm/phòng ban, khoảng 10 người dùng |

## Mục lục

- [1. Tổng quan và bối cảnh nghiệp vụ](#1-tổng-quan-và-bối-cảnh-nghiệp-vụ)
- [2. Mục tiêu nghiệp vụ](#2-mục-tiêu-nghiệp-vụ)
- [3. Phạm vi dự án](#3-phạm-vi-dự-án)
- [4. Các bên liên quan và vai trò](#4-các-bên-liên-quan-và-vai-trò)
- [5. Yêu cầu chức năng](#5-yêu-cầu-chức-năng)
- [6. Quy trình nghiệp vụ](#6-quy-trình-nghiệp-vụ)
- [7. Quy tắc nghiệp vụ và trạng thái](#7-quy-tắc-nghiệp-vụ-và-trạng-thái)
- [8. Yêu cầu phi chức năng](#8-yêu-cầu-phi-chức-năng)
- [9. Dữ liệu và thông tin quản trị](#9-dữ-liệu-và-thông-tin-quản-trị)
- [10. Giả định, phụ thuộc và các điểm cần làm rõ](#10-giả-định-phụ-thuộc-và-các-điểm-cần-làm-rõ)
- [11. Tiêu chí nghiệm thu và kế hoạch thử nghiệm](#11-tiêu-chí-nghiệm-thu-và-kế-hoạch-thử-nghiệm)
- [12. Tiến độ và định hướng phát triển](#12-tiến-độ-và-định-hướng-phát-triển)
- [Phụ lục A. Định hướng kỹ thuật](#phụ-lục-a-định-hướng-kỹ-thuật)
- [Phụ lục B. Thuật ngữ](#phụ-lục-b-thuật-ngữ)

## 1. Tổng quan và bối cảnh nghiệp vụ

**GeoAttend** là ứng dụng WebGIS hỗ trợ doanh nghiệp nhỏ ghi nhận trạng thái làm việc linh hoạt: tại văn phòng (Office), từ xa (Remote), nghỉ trưa, nghỉ buổi sáng hoặc nghỉ cả ngày.

Người quản lý cần biết nhân viên nào đang Office, Remote, nghỉ trưa, nghỉ hoặc đã kết thúc phiên làm việc, đồng thời có thể tra cứu lịch sử làm việc trong ngày. Doanh nghiệp không yêu cầu quản lý khắt khe giờ bắt đầu và kết thúc công việc.

Hệ thống tập trung vào hai nhu cầu:

- **Xác minh không gian:** xác minh nhân viên có nằm trong khu vực công ty khi thực hiện thao tác Office bằng GPS kết hợp Geofence và PostGIS.
- **Quản lý trạng thái:** ghi nhận và hiển thị trạng thái làm việc hiện tại cùng lịch sử của từng nhân viên.

GPS chỉ được sử dụng tại thời điểm cần xác minh thao tác Office. Hệ thống không theo dõi vị trí liên tục và không tự động đánh giá nhân viên dựa trên thời gian bắt đầu, kết thúc hoặc số giờ làm việc.

## 2. Mục tiêu nghiệp vụ

| Mã | Mục tiêu |
| --- | --- |
| OBJ-01 | Cho phép nhân viên ghi nhận trạng thái làm việc trên điện thoại hoặc máy tính. |
| OBJ-02 | Xác minh vị trí khi làm việc tại văn phòng bằng GPS và Geofence. |
| OBJ-03 | Hỗ trợ Office, Remote, nghỉ trưa, nghỉ buổi sáng, nghỉ cả ngày và thay đổi Office/Remote giữa sáng và chiều. |
| OBJ-04 | Giúp Admin theo dõi trạng thái toàn bộ nhân viên qua Dashboard và bản đồ nhân viên đang được ghi nhận làm việc tại văn phòng. |
| OBJ-05 | Lưu thời gian và lịch sử từng phiên làm việc để tra cứu, thống kê. |
| OBJ-06 | Hạn chế thu thập vị trí không cần thiết, bảo đảm minh bạch dữ liệu với người dùng. |

## 3. Phạm vi dự án

### 3.1. Trong phạm vi MVP

- 01 công ty, 01 văn phòng, 01 nhóm/phòng ban và khoảng 10 người dùng thử nghiệm.
- Hai vai trò: `USER` và `ADMIN`. MVP có một tài khoản Admin được khởi tạo khi thiết lập hệ thống; Admin tạo và cấp tài khoản User.
- Đăng nhập bằng tên tài khoản/mật khẩu và phân quyền; Admin tạo, cấp tài khoản cho User.
- Check-in Office có xác minh vị trí; Check-in Remote có lý do.
- Nghỉ trưa và bắt đầu phiên Office/Remote sau nghỉ trưa.
- Ghi nhận nghỉ buổi sáng hoặc nghỉ cả ngày có lý do.
- Check-out, quản lý phiên làm việc và lịch sử cá nhân.
- Dashboard Admin, trạng thái hiện tại, Onsite Attendance Map và lịch sử từng nhân viên.
- Quản lý Geofence và các cài đặt hệ thống.

### 3.2. Ngoài phạm vi MVP

- Quản lý nhiều chi nhánh hoặc nhiều phòng ban.
- Payroll, tính lương và đánh giá năng suất.
- Theo dõi GPS liên tục.
- Quy trình phê duyệt Remote hoặc nghỉ.
- AI/RAG xử lý báo cáo và các chức năng mở rộng tại mục 12.2.

## 4. Các bên liên quan và vai trò

| Vai trò | Nhu cầu | Chức năng trong phạm vi |
| --- | --- | --- |
| `USER` — Nhân viên | Ghi nhận trạng thái và tra cứu lịch sử cá nhân | Đăng nhập; Check-in Office/Remote; nghỉ trưa; tiếp tục Office/Remote; Check-out; ghi nhận nghỉ; nhập lý do; xem trạng thái và lịch sử của mình. |
| `ADMIN` — Quản lý | Theo dõi tình trạng làm việc của nhân viên | Xem Dashboard, trạng thái, Onsite Map, vị trí Check-in Office đã xác minh và lịch sử từng nhân viên; quản lý Geofence và cài đặt hệ thống; tạo, cấp tài khoản đăng nhập và đặt lại mật khẩu cho User. Admin chỉ quản lý, không chấm công cá nhân. |

## 5. Yêu cầu chức năng

Các mã yêu cầu dưới đây dùng để đối chiếu với tiêu chí nghiệm thu tại mục 11.

| Mã | Chức năng | Yêu cầu nghiệp vụ |
| --- | --- | --- |
| FR-01 | Đăng nhập và phân quyền | MVP đăng nhập bằng tên tài khoản và mật khẩu, phân quyền theo `USER`/`ADMIN`. Có một tài khoản Admin được khởi tạo khi thiết lập hệ thống; không có chức năng cấp thêm quyền Admin trong MVP. Admin tạo và cấp tài khoản cho User; User dùng thông tin được cấp để đăng nhập và sử dụng ngay; không bắt buộc đổi mật khẩu lần đầu, có thể tự đổi sau. Không có đăng ký công khai hoặc đăng nhập Google trong MVP. |
| FR-02 | Check-in Office | Lấy vị trí GPS, kiểm tra Geofence và cho phép Check-in khi vị trí nằm trong hoặc đúng trên ranh giới Geofence công ty; từ chối khi ngoài vùng, không áp dụng vùng đệm. Khi thành công, lưu nhân viên, thời gian, chế độ `OFFICE` và kết quả xác minh vị trí. |
| FR-03 | Check-in Remote | Yêu cầu nhập lý do, tạo phiên `REMOTE`; không lấy GPS, không kiểm tra Geofence và không cần Admin phê duyệt. Admin xem được trạng thái và lý do. |
| FR-04 | Nghỉ trưa | Đóng phiên làm việc hiện tại và chuyển trạng thái sang `LUNCH_BREAK`. |
| FR-05 | Tiếp tục sau nghỉ trưa | Cho phép chọn Office hoặc Remote; Office cần xác minh lại vị trí, Remote cần nhập lý do. |
| FR-06 | Nghỉ buổi sáng | Ghi nhận nghỉ và lý do, không cần phê duyệt; cho phép bắt đầu Office hoặc Remote khi nhân viên quay lại, không khóa theo mốc giờ sáng/chiều nhưng phải trước 20:00 theo BR-11. |
| FR-07 | Nghỉ cả ngày | Ghi nhận nghỉ và lý do, không cần phê duyệt; khi đang nghỉ không yêu cầu Check-in/Check-out và không lấy GPS. Cho phép hủy nghỉ để bắt đầu Office/Remote trước 20:00 giờ Việt Nam; giữ lịch sử đăng ký và hủy nghỉ. |
| FR-08 | Check-out | Kết thúc phiên đang mở tại thời điểm nhân viên lựa chọn; ghi nhận thời gian kết thúc để tra cứu lịch sử. Check-out Office/Remote không lấy GPS và không kiểm tra Geofence; ngoài vùng hoặc không có GPS vẫn được đóng phiên. Có thể nhập lý do nếu cần khi kết thúc làm việc một phần trong ngày. |
| FR-09 | Trạng thái cá nhân | Cho phép nhân viên xem trạng thái hiện tại của mình. |
| FR-10 | Lịch sử làm việc | Nhân viên xem lịch sử cá nhân; Admin xem Timeline của từng nhân viên, gồm các phiên và sự kiện trong ngày. |
| FR-11 | Dashboard Admin | Hiển thị tổng quan số lượng và danh sách tài khoản `USER` theo trạng thái chưa bắt đầu, Office, Remote, nghỉ trưa, nghỉ và đã Check-out. Không tính tài khoản Admin vào số nhân viên hoặc các nhóm chấm công. |
| FR-12 | Onsite Attendance Map | Hiển thị Geofence và Marker có tên của nhân viên đang `WORKING_OFFICE`, tại vị trí Check-in Office gần nhất đã được xác minh. |
| FR-13 | Popup nhân viên | Khi Admin chọn Marker, hiển thị tên, trạng thái, thời gian Check-in, trạng thái xác minh GPS và thao tác xem chi tiết. |
| FR-14 | Quản lý Geofence | Cho phép Admin chỉnh sửa Polygon khi khu vực công ty thay đổi, cần điều chỉnh ranh giới hoặc xử lý tình trạng GPS lệch ở ranh giới. |
| FR-15 | Cài đặt hệ thống | Admin được sửa tên, địa chỉ văn phòng và Polygon Geofence (theo FR-14). Múi giờ Việt Nam (`Asia/Ho_Chi_Minh`, UTC+07:00) và mốc tự đóng phiên 20:00 được cố định trong MVP, không cho chỉnh qua giao diện hoặc API cài đặt. |
| FR-16 | Cấp tài khoản User | Admin tạo tên tài khoản duy nhất và mật khẩu ban đầu, cấp thông tin đăng nhập cho nhân viên. Tài khoản được tạo qua chức năng này có vai trò `USER`; User không có quyền tạo tài khoản. User được dùng ngay mật khẩu ban đầu, không bắt buộc đổi ở lần đăng nhập đầu tiên. |
| FR-17 | Đổi mật khẩu cá nhân | Người dùng đã đăng nhập có thể tự đổi mật khẩu của mình. Đổi mật khẩu là tùy chọn, không phải điều kiện sử dụng hệ thống ở lần đăng nhập đầu tiên. |
| FR-18 | Đặt lại mật khẩu User | Khi User quên mật khẩu, Admin đặt lại và cấp mật khẩu mới. User đăng nhập được ngay bằng mật khẩu mới, có thể tự đổi sau; không có luồng khôi phục qua email trong MVP. |

## 6. Quy trình nghiệp vụ

### 6.1. Bắt đầu ngày làm việc

```text
Chưa bắt đầu
├── Office → Lấy GPS → Kiểm tra Geofence
│                       ├── Trong khu vực → Tạo phiên OFFICE
│                       └── Ngoài khu vực → Từ chối Check-in
├── Remote → Nhập lý do → Tạo phiên REMOTE
└── Nghỉ → Chọn buổi sáng/cả ngày → Nhập lý do → Ghi nhận nghỉ
```

### 6.2. Nghỉ trưa và tiếp tục làm việc

1. Nhân viên đang làm việc chọn **Nghỉ trưa**.
2. Hệ thống đóng phiên hiện tại và ghi nhận `LUNCH_BREAK`.
3. Sau nghỉ trưa, nhân viên chọn Office hoặc Remote.
4. Hệ thống xác minh GPS/Geofence đối với Office hoặc yêu cầu lý do đối với Remote, sau đó tạo phiên mới.

### 6.3. Nghỉ và kết thúc làm việc

- **Nghỉ buổi sáng:** nhân viên nhập lý do; khi quay lại có thể bắt đầu Office hoặc Remote, không phải chờ mốc giờ bắt đầu buổi chiều, nhưng phải trước 20:00 theo BR-11.
- **Nghỉ cả ngày:** nhân viên nhập lý do; trong ngày không cần Check-in hoặc Check-out.
- **Kết thúc làm việc:** nhân viên chọn Check-out, hệ thống ghi nhận kết thúc phiên. Có thể kết thúc sau buổi sáng hoặc tại thời điểm phù hợp, không cần trạng thái riêng cho nghỉ buổi chiều.

### 6.4. Các kịch bản được hỗ trợ

| Kịch bản | Luồng nghiệp vụ |
| --- | --- |
| Office cả ngày | Office → Nghỉ trưa → Office → Check-out |
| Remote cả ngày | Remote → Nghỉ trưa → Remote → Check-out |
| Remote sáng, Office chiều | Remote → Nghỉ trưa → Office có xác minh GPS → Check-out |
| Office sáng, Remote chiều | Office → Nghỉ trưa → Remote → Check-out |
| Nghỉ sáng, Office chiều | Nghỉ buổi sáng → Office có xác minh GPS → Check-out |
| Nghỉ sáng, Remote chiều | Nghỉ buổi sáng → Remote → Check-out |
| Nghỉ cả ngày | Ghi nhận nghỉ cả ngày |
| Làm việc một phần trong ngày | Office/Remote → Check-out; ví dụ Office từ 09:00 đến 12:30, có thể nhập lý do nếu cần. |

Mọi lần bắt đầu phiên Office đều áp dụng xác minh vị trí; mọi lần bắt đầu phiên Remote đều yêu cầu lý do.

## 7. Quy tắc nghiệp vụ và trạng thái

### 7.1. Quy tắc nghiệp vụ

| Mã | Quy tắc |
| --- | --- |
| BR-01 | Check-in hoặc tiếp tục Office chấp nhận vị trí nằm trong hoặc đúng trên ranh giới Geofence công ty. Vị trí ngoài vùng bị từ chối; không áp dụng vùng đệm ngoài ranh giới. Độ chính xác GPS chỉ được lưu để tra cứu, không đặt ngưỡng sai số để từ chối Check-in hoặc tiếp tục Office. |
| BR-02 | Remote và nghỉ phải có lý do, không cần Admin phê duyệt và không thu thập GPS. |
| BR-03 | Nghỉ trưa đóng phiên hiện tại; tiếp tục làm việc tạo một phiên Office hoặc Remote mới. |
| BR-04 | Nhân viên nghỉ buổi sáng tự bắt đầu Office hoặc Remote khi quay lại, không bị khóa theo mốc giờ sáng/chiều nhưng phải trước 20:00 theo BR-11; Office vẫn cần xác minh vị trí, Remote vẫn cần lý do. Nghỉ cả ngày không cần Check-in/Check-out. |
| BR-05 | Thời gian bắt đầu và kết thúc dùng để theo dõi lịch sử; không tự động phân loại đi trễ, về sớm, đúng giờ hoặc đánh giá chất lượng công việc theo số giờ làm. |
| BR-06 | Marker biểu thị vị trí Check-in Office gần nhất đã xác minh, không phải vị trí GPS trực tiếp. |
| BR-07 | Marker không còn trong nhóm Onsite khi nhân viên Check-out, chuyển sang Remote hoặc không còn ở trạng thái `WORKING_OFFICE`, bao gồm nghỉ trưa. |
| BR-08 | Chỉ lấy GPS khi Check-in hoặc tiếp tục Office, dừng sau thao tác và không theo dõi liên tục. Check-out không lấy GPS, không kiểm tra Geofence và cho phép đóng phiên đang mở kể cả khi ngoài vùng hoặc không có GPS. |
| BR-09 | Không tạo trạng thái nghỉ buổi chiều riêng; nhân viên có thể kết thúc phiên sớm bằng Check-out. |
| BR-10 | Khi Check-in hoặc tiếp tục Office không lấy được vị trí hoặc bị từ chối quyền GPS, không tạo phiên Office và giữ nguyên trạng thái. Hiển thị hướng dẫn bật quyền hoặc thử lại; cho phép người dùng tự chọn Remote và nhập lý do, không tự chuyển chế độ làm việc. |
| BR-11 | Lúc 20:00 hằng ngày, hệ thống tự đóng các phiên Office/Remote còn mở, chuyển trạng thái thành `CHECKED_OUT` và ghi rõ nguồn đóng là hệ thống. Nếu nhân viên đang `LUNCH_BREAK` lúc 20:00, chuyển sang `CHECKED_OUT` và ghi sự kiện “hệ thống kết thúc ngày”; giữ nguyên giờ kết thúc phiên trước nghỉ trưa, không tạo thêm thời gian làm việc. Mốc tự đóng không được coi là giờ nhân viên thực tế kết thúc làm việc; không lấy GPS. Áp dụng giờ Việt Nam (`Asia/Ho_Chi_Minh`, UTC+07:00) để xác định ngày làm việc và mốc tự đóng. Từ đúng 20:00 đến hết ngày, không cho bắt đầu hoặc tiếp tục Office/Remote. |
| BR-12 | Sau Check-out, nhân viên được bắt đầu phiên mới trong cùng ngày nếu trước 20:00 giờ Việt Nam. Office phải xác minh lại vị trí theo BR-01, Remote phải nhập lý do. Tạo phiên mới, không mở lại hoặc sửa phiên đã đóng; giữ nguyên lịch sử phiên cũ. |
| BR-13 | Nhân viên được hủy nghỉ cả ngày để bắt đầu Office/Remote trước 20:00 giờ Việt Nam. Giữ lịch sử đăng ký và hủy nghỉ; không xóa sự kiện nghỉ ban đầu. Phiên Office phải xác minh vị trí theo BR-01, phiên Remote phải có lý do. Thao tác hủy nghỉ không lấy GPS; GPS chỉ phục vụ bắt đầu Office. |
| BR-14 | Cho phép chuyển trực tiếp Office ↔ Remote trước 20:00 giờ Việt Nam. Chuyển sang Office phải xác minh vị trí theo BR-01; sang Remote phải có lý do. Chỉ khi điều kiện chế độ mới hợp lệ mới đóng phiên cũ và tạo phiên mới trong cùng một giao dịch, giữ nguyên lịch sử. Nếu kiểm tra thất bại, giữ phiên và trạng thái hiện tại. |

Bảng chuyển trạng thái và các quy tắc thiết kế liên quan: [Trạng thái làm việc](docs/STATE_TRANSITIONS.md).

### 7.2. Danh mục trạng thái

| Trạng thái | Ý nghĩa |
| --- | --- |
| `NOT_STARTED` | Chưa bắt đầu làm việc. |
| `WORKING_OFFICE` | Đang được ghi nhận làm việc tại văn phòng. |
| `WORKING_REMOTE` | Đang làm việc Remote. |
| `LUNCH_BREAK` | Đang nghỉ trưa. |
| `MORNING_LEAVE` | Nghỉ buổi sáng. |
| `FULL_DAY_LEAVE` | Nghỉ cả ngày. |
| `CHECKED_OUT` | Đã kết thúc phiên làm việc. |

## 8. Yêu cầu phi chức năng

| Mã | Nhóm | Yêu cầu |
| --- | --- | --- |
| NFR-01 | Khả năng sử dụng | Giao diện sử dụng được trên điện thoại và máy tính; thao tác của nhân viên đơn giản, chỉ yêu cầu thông tin cần thiết. |
| NFR-02 | Quyền riêng tư | Chỉ thu thập vị trí khi cần xác minh Office; không lấy GPS khi Check-out, Remote/nghỉ và không thu thập liên tục. Giữ tọa độ và độ chính xác GPS trong 30 ngày kể từ lúc ghi nhận, sau đó tự động xóa; giữ lịch sử phiên, thời gian, chế độ làm việc và kết quả xác minh. |
| NFR-03 | Phân quyền và minh bạch | Nhân viên xem lịch sử của mình; Admin xem trạng thái tổng thể, lịch sử nhân viên và quản lý Geofence/cài đặt theo vai trò. |
| NFR-04 | Hiệu năng | Trong pilot, ít nhất 95% yêu cầu API có thời gian xử lý tại Backend không quá 2 giây. Đo từ khi Backend nhận yêu cầu đến khi hoàn tất xử lý phản hồi; không tính thời gian trình duyệt lấy GPS hoặc truyền mạng đến/đi từ Backend. |
| NFR-05 | Độ ổn định | Đánh giá khả năng lấy GPS, độ chính xác vị trí, xác minh Geofence và độ ổn định cơ sở dữ liệu trong thử nghiệm. |

## 9. Dữ liệu và thông tin quản trị

### 9.1. Nhóm dữ liệu cần quản lý

| Nhóm | Thông tin chính |
| --- | --- |
| Nhân viên | Danh tính, họ tên, email, vai trò và trạng thái hoạt động. |
| Văn phòng | Tên, địa chỉ và ranh giới Geofence. |
| Phiên làm việc | Nhân viên, ngày làm việc, Office/Remote, thời gian bắt đầu/kết thúc, lý do và dữ liệu vị trí liên quan đến xác minh Office. |
| Sự kiện chấm công | Bắt đầu làm việc, nghỉ trưa, kết thúc làm việc, nghỉ buổi sáng, nghỉ cả ngày; thời gian, lý do và kết quả xác minh nếu có. |

Thiết kế bảng và trường dữ liệu dự kiến được trình bày tại phụ lục A.

### 9.2. Dashboard và bản đồ

Ví dụ tổng hợp trạng thái của 10 nhân viên:

| Office | Remote | Nghỉ trưa | Nghỉ | Check-out | Tổng |
| --- | --- | --- | --- | --- | --- |
| 4 | 2 | 1 | 1 | 2 | 10 |

Dashboard kèm danh sách tên nhân viên và thông tin thời gian hoặc hình thức nghỉ tương ứng. Bản đồ hiển thị Geofence, Marker có tên và số nhân viên Onsite.

Ví dụ Popup: **Nguyễn Thành Nhân** — Office — Check-in **08:12** — GPS **Đã xác minh** — **Xem chi tiết**.

### 9.3. Lịch sử làm việc

Ví dụ Timeline của Nguyễn Thành Nhân ngày 14/10/2026:

| Thời gian | Sự kiện | Thông tin bổ sung |
| --- | --- | --- |
| 09:05 | Check-in Office | GPS đã xác minh |
| 12:20 | Nghỉ trưa | Đóng phiên Office |
| 13:30 | Check-in Remote | Bắt đầu phiên Remote |
| 17:40 | Check-out Remote | Đóng phiên Remote |

### 9.4. Chỉ số đánh giá sau thử nghiệm

- Số lần Check-in Office, số lần thành công và số lần bị từ chối do ngoài Geofence.
- Độ chính xác GPS trung bình.
- Số phiên Office, số phiên Remote và số ngày nghỉ.
- Thời gian phản hồi API.

Các chỉ số nhằm đánh giá tính ổn định và khả năng sử dụng; không dùng số liệu thời gian để tự động đánh giá hiệu suất nhân viên. Mục tiêu hiệu năng và điều kiện nghiệm thu pilot được quy định tại NFR-04 và mục 11; độ chính xác GPS được thống kê để đánh giá, không dùng làm ngưỡng chặn Check-in.

## 10. Giả định, phụ thuộc và các điểm cần làm rõ

### 10.1. Giả định và phụ thuộc

- MVP được thử nghiệm trong môi trường một công ty, một văn phòng và khoảng 10 người dùng.
- Luồng Office phụ thuộc vào khả năng cung cấp vị trí của Browser Geolocation và dữ liệu Geofence của văn phòng.
- Kiểm tra không gian dự kiến được xử lý bằng PostgreSQL/PostGIS; Backend sử dụng FastAPI.
- Thư viện bản đồ được chốt là Leaflet trong thiết kế Phase 0.

### 10.2. Các điểm cần làm rõ trước nghiệm thu

Bảng dưới theo dõi các quyết định cần làm rõ trong mô tả ban đầu. Mục ghi **Đã chốt** đã được người dùng xác nhận; các mục còn lại vẫn là câu hỏi mở.

| Mã | Nội dung cần làm rõ | Ảnh hưởng |
| --- | --- | --- |
| TBD-01 — Đã chốt | Phương án A: chỉ xác minh GPS khi Check-in hoặc tiếp tục Office. Check-out không lấy GPS, không kiểm tra Geofence và cho phép đóng phiên đang mở khi ngoài vùng hoặc không có GPS. | FR-08, BR-08 |
| TBD-02 — Đã chốt | Đã chốt: chấp nhận vị trí trong vùng hoặc đúng trên ranh giới, từ chối ngoài vùng và không dùng vùng đệm. Đã chốt: lưu độ chính xác GPS để tra cứu, không dùng sai số làm điều kiện từ chối Check-in hoặc tiếp tục Office. Khi không lấy được vị trí hoặc bị từ chối quyền GPS: không tạo phiên Office, giữ nguyên trạng thái, hướng dẫn bật quyền hoặc thử lại; người dùng có thể tự chọn Remote và nhập lý do, hệ thống không tự chuyển sang Remote. | FR-02, FR-05, NFR-05 |
| TBD-03 — Đã chốt | Đã chốt: sau nghỉ buổi sáng, nhân viên tự bắt đầu Office/Remote khi quay lại mà không phải chờ mốc giờ buổi chiều, nhưng phải trước 20:00. Đã chốt: hệ thống tự đóng các phiên Office/Remote còn mở lúc 20:00 hằng ngày, ghi rõ do hệ thống đóng và không coi 20:00 là giờ kết thúc làm việc thực tế. Áp dụng giờ Việt Nam (`Asia/Ho_Chi_Minh`, UTC+07:00); từ đúng 20:00 đến hết ngày không cho bắt đầu hoặc tiếp tục Office/Remote. | FR-04 đến FR-08, FR-10 |
| TBD-04 — Đã chốt | Đã chốt: sau Check-out được bắt đầu phiên Office/Remote mới trong cùng ngày nếu trước 20:00 giờ Việt Nam; Office xác minh GPS lại, Remote nhập lý do và giữ nguyên lịch sử phiên cũ. Đã chốt: cho phép hủy nghỉ cả ngày để bắt đầu Office/Remote trước 20:00 giờ Việt Nam, giữ lịch sử đăng ký và hủy nghỉ. Đã chốt: cho phép chuyển trực tiếp Office ↔ Remote trước 20:00; đóng phiên cũ và tạo phiên mới sau khi xác minh GPS đối với Office hoặc nhập lý do đối với Remote. | Quy tắc chuyển trạng thái |
| TBD-05 — Đã chốt | Admin được sửa tên, địa chỉ văn phòng và Polygon Geofence. Giờ Việt Nam và mốc tự đóng 20:00 cố định trong MVP. | FR-15 |
| TBD-06 — Đã chốt | Pilot khoảng 10 người dùng trong 5 ngày làm việc; toàn bộ tiêu chí nghiệm thu chức năng đạt; không còn lỗi gây mất dữ liệu, trùng phiên hoặc sai phân quyền. Ít nhất 95% yêu cầu API xử lý tại Backend trong tối đa 2 giây, không tính thời gian lấy GPS. Độ chính xác GPS được thống kê để đánh giá, không dùng làm ngưỡng chặn Check-in. | NFR-04, NFR-05 |
| TBD-07 — Đã chốt | Giữ tọa độ và độ chính xác GPS trong 30 ngày kể từ lúc ghi nhận, sau đó tự động xóa. Giữ lịch sử phiên, thời gian, chế độ làm việc và kết quả xác minh. Lịch sử cũ hiển thị “Dữ liệu vị trí đã hết hạn lưu”, không còn tọa độ trên bản đồ. | NFR-02, dữ liệu lịch sử |

## 11. Tiêu chí nghiệm thu và kế hoạch thử nghiệm

### 11.1. Tiêu chí nghiệm thu chức năng dự thảo

Các tiêu chí được diễn giải từ yêu cầu nêu trên để phục vụ thử nghiệm MVP; những trường hợp còn mở tại mục 10 cần được thống nhất thêm.

| Mã | Yêu cầu liên quan | Kết quả cần đạt |
| --- | --- | --- |
| AC-01 | FR-01, FR-09, FR-10 | User đăng nhập được bằng tên tài khoản/mật khẩu do Admin cấp; sai tên tài khoản hoặc mật khẩu không cấp quyền truy cập nghiệp vụ. Sau đăng nhập, người dùng truy cập chức năng theo vai trò; nhân viên xem được trạng thái và lịch sử cá nhân, Admin xem được lịch sử nhân viên. Admin không được tạo phiên làm việc, ghi nhận nghỉ hoặc thực hiện chấm công cá nhân; Backend từ chối các thao tác này khi tài khoản có vai trò `ADMIN`. |
| AC-02 | FR-02 | Với vị trí trong hoặc đúng trên ranh giới Geofence, Check-in Office tạo phiên `OFFICE` và ghi nhận xác minh; độ chính xác GPS được lưu để tra cứu, sai số lớn không làm thao tác bị từ chối. Vị trí ngoài Geofence bị từ chối, không áp dụng vùng đệm. Quy tắc này cũng áp dụng khi tiếp tục Office. Nếu không lấy được vị trí hoặc bị từ chối quyền GPS, không tạo phiên Office và giữ nguyên trạng thái; hiển thị hướng dẫn bật quyền/thử lại. Chỉ tạo phiên Remote khi người dùng tự chọn Remote và nhập lý do. |
| AC-03 | FR-03 | Check-in Remote yêu cầu lý do, tạo phiên `REMOTE`, không yêu cầu GPS hoặc phê duyệt; Admin xem được lý do. |
| AC-04 | FR-04, FR-05 | Nghỉ trưa đóng phiên hiện tại; tiếp tục Office xác minh lại vị trí, tiếp tục Remote yêu cầu lý do và tạo phiên mới. |
| AC-05 | FR-06, FR-07 | Nghỉ sáng/cả ngày yêu cầu lý do, không lấy GPS hoặc cần phê duyệt; sau nghỉ sáng có thể bắt đầu Office/Remote khi quay lại mà không bị chặn bởi mốc giờ sáng/chiều nhưng phải trước 20:00 theo BR-11; Office cần xác minh vị trí và Remote cần lý do. |
| AC-06 | FR-08, BR-05 | Check-out ghi nhận thời gian kết thúc; lịch sử thể hiện thời gian bắt đầu/kết thúc mà không tự động đánh giá đi trễ, về sớm hoặc hiệu suất. Check-out Office không yêu cầu quyền vị trí hoặc kiểm tra Geofence; phiên đang mở được đóng khi ngoài vùng hoặc không có GPS. |
| AC-07 | FR-11 | Dashboard hiển thị số lượng và danh sách tương ứng với trạng thái đã ghi nhận của các tài khoản `USER`, gồm cả chưa bắt đầu; tài khoản Admin không xuất hiện trong các nhóm trạng thái, tổng số nhân viên hoặc Marker Onsite. |
| AC-08 | FR-12, FR-13 | Bản đồ hiển thị Geofence, tên và vị trí Check-in Office đã xác minh; Popup có đủ thông tin; Marker rời nhóm Onsite khi không còn `WORKING_OFFICE`. |
| AC-09 | FR-14 | Admin chỉnh sửa và lưu được Polygon Geofence của văn phòng. |
| AC-10 | NFR-01, NFR-02 | Kiểm tra các luồng chính trên điện thoại và máy tính; xác nhận không lấy GPS khi Remote/nghỉ và không theo dõi vị trí liên tục. |
| AC-11 | BR-11 | Đến 20:00, phiên Office/Remote còn mở được hệ thống đóng một lần, chuyển sang `CHECKED_OUT`; lịch sử ghi rõ tự đóng và không trình bày mốc này như giờ kết thúc thực tế. Với `LUNCH_BREAK` lúc 20:00, chuyển sang `CHECKED_OUT` và ghi “hệ thống kết thúc ngày”, không tạo phiên mới hoặc kéo dài phiên trước nghỉ trưa. Phiên đã đóng trước đó không bị thay đổi; không yêu cầu GPS. Áp dụng giờ Việt Nam (`Asia/Ho_Chi_Minh`, UTC+07:00). Yêu cầu bắt đầu/tiếp tục Office hoặc Remote từ đúng 20:00 đến hết ngày bị từ chối và không tạo phiên. Kiểm thử thời điểm trước, đúng và sau 20:00; giới hạn của ngày trước kết thúc khi sang ngày mới. |
| AC-12 | BR-12 | Từ `CHECKED_OUT`, bắt đầu Office/Remote trước 20:00 tạo phiên mới sau khi đáp ứng xác minh vị trí/lý do tương ứng; phiên cũ và lịch sử không đổi. Khi xác minh Office thất bại hoặc thiếu lý do Remote, không tạo phiên mới và giữ trạng thái `CHECKED_OUT`. Từ 20:00 đến hết ngày, yêu cầu bắt đầu lại bị từ chối. |
| AC-13 | FR-07, BR-13 | Nhân viên đang nghỉ cả ngày có thể hủy nghỉ và bắt đầu Office/Remote trước 20:00 theo điều kiện tương ứng. Lịch sử hiển thị cả đăng ký và hủy nghỉ; ngày nghỉ đã hủy không được thống kê là nghỉ cả ngày còn hiệu lực. Từ 20:00 đến hết ngày không cho bắt đầu phiên làm việc. |
| AC-14 | BR-14 | Trước 20:00, chuyển Office → Remote với lý do hoặc Remote → Office với vị trí hợp lệ đóng phiên cũ và tạo đúng một phiên mới. Thiếu lý do hoặc xác minh GPS thất bại không đóng phiên cũ. Từ 20:00 đến hết ngày không cho chuyển chế độ; phiên còn mở được xử lý theo BR-11. |
| AC-15 | FR-14, FR-15 | Admin sửa và lưu được tên, địa chỉ văn phòng và Polygon Geofence hợp lệ; User không có quyền sửa. Giờ Việt Nam và mốc tự đóng 20:00 không thể thay đổi qua giao diện hoặc API cài đặt. |
| AC-16 | NFR-02 | Khi dữ liệu GPS đủ 30 ngày kể từ lúc ghi nhận, tự động xóa tọa độ và độ chính xác GPS ở các bản ghi liên quan; API không trả dữ liệu vị trí đã hết hạn. Lịch sử phiên, thời gian, chế độ làm việc và kết quả xác minh vẫn còn; giao diện hiển thị “Dữ liệu vị trí đã hết hạn lưu” và không hiển thị tọa độ cũ trên bản đồ. Kiểm thử trước, đúng và sau thời điểm hết hạn bằng dữ liệu có thời gian ghi nhận được kiểm soát. |
| AC-17 | FR-01, FR-16 | Admin tạo được tài khoản có vai trò `USER`, nhân viên dùng thông tin được cấp để đăng nhập. Tên tài khoản trùng bị từ chối; User và người chưa đăng nhập không thể tạo tài khoản hoặc tự cấp quyền Admin. Hệ thống có đúng một Admin được khởi tạo khi thiết lập; các chức năng tạo/cập nhật tài khoản trong MVP không cho cấp thêm quyền Admin. MVP không cung cấp đăng ký công khai hay đăng nhập Google. |
| AC-18 | FR-01, FR-17 | User đăng nhập lần đầu bằng mật khẩu được Admin cấp và truy cập ngay chức năng theo vai trò, không bị buộc đổi mật khẩu. Khi chủ động đổi mật khẩu thành công, mật khẩu mới dùng được cho lần đăng nhập tiếp theo, mật khẩu cũ bị từ chối và tài khoản vẫn giữ vai trò ban đầu. |
| AC-19 | FR-18 | Admin đặt lại được mật khẩu của tài khoản User. Sau khi thành công, mật khẩu mới đăng nhập được, mật khẩu cũ bị từ chối; vai trò và lịch sử làm việc không thay đổi. User và người chưa đăng nhập không được đặt lại mật khẩu cho tài khoản khác. Không buộc đổi mật khẩu vừa được cấp ở lần đăng nhập tiếp theo. |

Pilot đạt khi toàn bộ tiêu chí nghiệm thu chức năng đạt, không còn lỗi gây mất dữ liệu, trùng phiên hoặc sai phân quyền và đáp ứng NFR-04: ít nhất 95% yêu cầu API xử lý tại Backend trong tối đa 2 giây. Báo cáo ghi số lượng yêu cầu được đo và tỷ lệ đáp ứng ngưỡng; không tính thời gian lấy GPS vào thời gian xử lý Backend.

### 11.2. Kế hoạch thử nghiệm

- **Quy mô và thời gian:** khoảng 10 người dùng trong môi trường công ty, thử nghiệm trong 5 ngày làm việc.
- **Thiết bị:** kiểm tra khả năng truy cập trên điện thoại và máy tính.
- **GPS/GIS:** lấy GPS, ghi nhận độ chính xác, xác minh Geofence và kiểm tra các tình huống cần làm rõ tại mục 10.
- **Luồng nhân viên:** Office, Remote, nghỉ trưa, nghỉ buổi sáng/cả ngày, Check-out và các kịch bản phối hợp tại mục 6.4.
- **Luồng quản lý:** Dashboard, trạng thái hiện tại, Onsite Map, Popup, lịch sử và chỉnh sửa Geofence.
- **Vận hành:** ghi nhận thời gian phản hồi Backend và độ ổn định cơ sở dữ liệu.

Kết quả mong đợi là nhân viên thực hiện được luồng từ đăng nhập đến ghi nhận trạng thái, kết thúc phiên và xem lịch sử; Admin theo dõi được trạng thái, bản đồ và lịch sử, đồng thời quản lý được Geofence.

## 12. Tiến độ và định hướng phát triển

### 12.1. Tiến độ ghi nhận trong README ban đầu

> Danh sách dưới đây giữ lại thông tin tiến độ của tài liệu ban đầu, không phải kết quả kiểm chứng mã nguồn trong lần định dạng tài liệu này.

| Trạng thái | Hạng mục |
| --- | --- |
| Đã hoàn thành | Phân tích bài toán, xác định MVP, thiết kế vai trò User/Admin; các luồng Office, Remote, nghỉ, nghỉ trưa và Office/Remote hỗn hợp; nguyên lý GPS/Geofence; Onsite Attendance Map; giao diện User/Admin dự kiến. |
| Đã hoàn thành | Dựng cấu trúc project trên VS Code, FastAPI Backend và Frontend cơ bản; tách Router Auth/Attendance/Admin. |
| Đang thực hiện | Tạo Supabase project, kích hoạt PostGIS, thiết kế database và các bảng `profiles`, `office`, `work_sessions`, `attendance_events`; kết nối FastAPI với PostgreSQL/PostGIS. |
| Tiếp theo | Authentication User/Admin; tạo và chỉnh sửa Geofence; Browser GPS; API Point-in-Polygon; Check-in Office/Remote; nghỉ trưa; Leave; Check-out; Work Session; User History. |
| Tiếp theo | Admin Dashboard, Current Employee Status, Onsite Attendance Map, Popup Employee; triển khai Backend/Frontend và pilot với người dùng thực tế. |

### 12.2. Định hướng sau MVP

- Progressive Web App (PWA) và thông báo.
- Báo cáo ngày/tuần/tháng, xuất Excel/CSV/PDF và Dashboard thống kê nâng cao.
- Audit Log và yêu cầu điều chỉnh dữ liệu (Correction Request).
- Dynamic QR Verification.
- Nhiều văn phòng, nhiều phòng ban và ứng dụng di động.
- **AI + RAG:** nhân viên tải lên file báo cáo; hệ thống đọc, tóm tắt và hiển thị nội dung chính cho Admin. Chức năng này chỉ triển khai sau khi hệ thống cốt lõi hoạt động ổn định.

## Phụ lục A. Định hướng kỹ thuật

Phụ lục tóm tắt thiết kế Phase 0 đã duyệt. FastAPI phục vụ giao diện HTML/CSS/JavaScript và API trên cùng một địa chỉ; mô hình dữ liệu và hợp đồng chi tiết nằm trong bản thiết kế liên kết ở đầu README. Đây là thiết kế MVP; Phase 1 đã có mã nguồn nền tảng và tài khoản, các chức năng chấm công/bản đồ còn ở các phase sau. Trạng thái cập nhật nằm trong roadmap.

### A.1. Kiến trúc và công nghệ

```text
USER / ADMIN
      ↓
Frontend: HTML / CSS / JavaScript
      ↓
API: FastAPI
      ├── Business Logic
      └── GIS Logic: PostGIS
                 ↓
      PostgreSQL / Supabase
```

| Thành phần | Công nghệ dự kiến | Trách nhiệm |
| --- | --- | --- |
| Frontend | HTML5, CSS3, JavaScript, Leaflet | Giao diện User/Admin, Browser Geolocation, bản đồ, Geofence và Marker nhân viên. |
| Backend | Python, FastAPI | API, nghiệp vụ, Check-in/Check-out, phiên làm việc, trạng thái, phân quyền và giao tiếp cơ sở dữ liệu. |
| Database | PostgreSQL, PostGIS, Supabase | Lưu người dùng, vai trò, văn phòng, Geofence, phiên làm việc, sự kiện, vị trí Office, lý do Remote/nghỉ và lịch sử. |
| GIS | GPS, Point, Polygon, Geofence, EPSG:4326, Point-in-Polygon, Spatial Query, Spatial Index | Xử lý dữ liệu không gian và xác minh vị trí. |

Geofence lưu bằng `geometry(Polygon, 4326)`. Phép xác minh dùng `ST_Covers` để chấp nhận điểm trong vùng và trên ranh giới, không dùng vùng đệm. Độ chính xác GPS được lưu để tra cứu, không áp dụng ngưỡng sai số để chặn thao tác Office.

### A.2. Thiết kế dữ liệu

Chi tiết trường, ràng buộc và ERD tại mục 4 của [thiết kế Phase 0](docs/superpowers/specs/2026-10-14-geoattend-mvp-design.md).

| Bảng | Mục đích |
| --- | --- |
| `profiles` | Tên tài khoản, họ tên, hash mật khẩu, vai trò và trạng thái hoạt động; không yêu cầu email. |
| `auth_sessions` | Phiên đăng nhập, hash token, CSRF và hạn phiên. |
| `auth_attempts` | Giới hạn các lần đăng nhập sai. |
| `office` | Văn phòng, Polygon Geofence và revision. |
| `attendance_days` | Trạng thái và revision theo từng User/ngày Việt Nam. |
| `work_sessions` | Phiên Office/Remote, thời gian và nguồn kết thúc USER/SYSTEM. |
| `attendance_events` | Sự kiện làm việc/nghỉ/hủy nghỉ/kết thúc ngày và kết quả xác minh. |
| `office_locations` | GPS bắt đầu phiên Office, tự xóa tọa độ/độ chính xác sau 30 ngày; không lưu GPS Check-out. |
| `attendance_requests` | Chống gửi lặp thao tác; không lưu bản sao tọa độ hoặc phản hồi GPS. |

### A.3. Luồng dữ liệu

```text
Office Check-in
Employee → Frontend → navigator.geolocation → Latitude/Longitude
         → FastAPI → PostGIS → Kiểm tra Office Geofence
                              ├── INSIDE → Work Session + Attendance Event
                              └── OUTSIDE → Từ chối

Remote Check-in
Employee → Remote → Lý do → FastAPI → Work Session (REMOTE)
Không lấy GPS.

Leave
Employee → Nghỉ buổi sáng/cả ngày → Lý do → FastAPI → Attendance Event
Không lấy GPS.
```

### A.4. Cấu trúc API dự kiến

| Router | Phạm vi trách nhiệm |
| --- | --- |
| `/api/auth` | Xác thực và vai trò. |
| `/api/attendance` | Office, Remote, Lunch, Leave, Check-out và Work Session. |
| `/api/admin` | Dashboard, Current Status, Onsite Map, Employee History, Geofence và cấp tài khoản User. |

## Phụ lục B. Thuật ngữ

| Thuật ngữ | Diễn giải |
| --- | --- |
| BRD | Business Requirements Document — Tài liệu yêu cầu nghiệp vụ. |
| MVP | Phiên bản tối thiểu để thử nghiệm các chức năng cốt lõi. |
| Office / Onsite | Làm việc tại văn phòng. |
| Remote | Làm việc từ xa. |
| Geofence | Ranh giới không gian dùng để xác minh vị trí thuộc khu vực văn phòng. |
| Work Session | Phiên làm việc có chế độ Office/Remote và thời gian bắt đầu/kết thúc. |
| Attendance Event | Sự kiện ghi nhận một thao tác hoặc thay đổi trạng thái làm việc. |
| Onsite Attendance Map | Bản đồ hiển thị vị trí Check-in đã xác minh của nhân viên đang được ghi nhận làm việc tại văn phòng. |
| GPS Accuracy | Độ chính xác vị trí do thiết bị/trình duyệt cung cấp. |
| TBD | Nội dung cần được làm rõ hoặc thống nhất thêm. |
