# BRD: Chức năng tóm tắt nội dung chính của file PDF

> Tài liệu yêu cầu nghiệp vụ (Business Requirements Document) dành cho agent đang phát triển dự án.
> Tài liệu chỉ mô tả **cái gì cần làm và làm đến mức nào**. Cách triển khai (ngôn ngữ, framework, cấu trúc DB, vị trí code) do agent tự xác định dựa trên mã nguồn hiện có của dự án.

---

## 1. Tổng quan

### 1.1 Bối cảnh
Dự án hiện có phần lưu trữ và xem các file PDF. Người dùng muốn nắm nhanh nội dung chính của một file mà không phải đọc hết toàn bộ.

### 1.2 Mục tiêu
Thêm một chức năng mới: **tự động đọc nội dung file PDF và tóm tắt nội dung chính thành một đoạn văn ngắn, hiển thị trong một khung nhỏ nằm bên cạnh file PDF đó.**

### 1.3 Giá trị mang lại
- Người dùng hiểu nội dung chính của file trong vài giây.
- Dễ quyết định có cần đọc chi tiết file hay không.

---

## 2. Phạm vi

### 2.1 Trong phạm vi (In scope)
- Tạo bản tóm tắt cho mỗi file PDF.
- Lưu bản tóm tắt để dùng lại, không tạo lại mỗi lần mở file.
- Hiển thị bản tóm tắt trong khung nhỏ bên cạnh file PDF.
- Hiển thị trạng thái rõ ràng khi bản tóm tắt đang được tạo hoặc bị lỗi.
- Tạo bản tóm tắt cho các PDF đã có sẵn trong hệ thống.

### 2.2 Ngoài phạm vi (Out of scope)
- **Không** làm chức năng hỏi đáp (chatbot) trên nội dung PDF.
- **Không** xây dựng hệ thống RAG, vector database hoặc embedding. Mỗi file chỉ khoảng 10 trang, nên gửi toàn bộ nội dung cho mô hình ngôn ngữ để tóm tắt là đủ.
- **Không** huấn luyện hay tự xây dựng mô hình ngôn ngữ. Chỉ gọi dịch vụ AI có sẵn qua API.
- **Không** cho người dùng chỉnh sửa nội dung bản tóm tắt.
- **Không** thay đổi các chức năng đang chạy ổn định của dự án.

---

## 3. Đặc điểm dữ liệu đầu vào

| Nội dung | Mô tả |
|---|---|
| Loại file | PDF |
| Độ dài | Khoảng 10 trang mỗi file |
| Dạng nội dung | Gồm cả PDF có text và PDF là ảnh scan (có thể có file lẫn cả hai dạng) |
| Ngôn ngữ tài liệu | Chủ yếu tiếng Việt (agent kiểm tra thêm với dữ liệu thực tế) |

**Yêu cầu quan trọng:** giải pháp phải đọc được **cả PDF scan**, không chỉ PDF có text. Nếu cách đọc text thông thường không lấy được nội dung từ file scan, agent phải dùng cách khác (ví dụ gửi trực tiếp file PDF cho mô hình AI hỗ trợ đọc PDF/ảnh, hoặc OCR hỗ trợ tiếng Việt).

---

## 4. Yêu cầu chức năng

### FR-01. Tạo bản tóm tắt
- Hệ thống đọc toàn bộ nội dung file PDF và tạo ra **một đoạn văn** tóm tắt nội dung chính.
- Bản tóm tắt viết bằng **tiếng Việt**, văn phong rõ ràng, trung lập.
- Độ dài khoảng **80 đến 150 từ**. Là đoạn văn liền mạch, không dùng gạch đầu dòng, tiêu đề hay định dạng phức tạp.
- Bản tóm tắt chỉ dựa trên nội dung có trong file, **không tự bịa thêm thông tin** không có trong tài liệu.
- Nếu tài liệu có số liệu, tên riêng, mốc thời gian quan trọng thì nên giữ lại đúng như trong tài liệu.

### FR-02. Thời điểm tạo bản tóm tắt
- Khi một file PDF mới được tải lên, hệ thống **tự động** tạo bản tóm tắt.
- Việc tạo bản tóm tắt **không được làm chậm hoặc chặn** thao tác tải lên của người dùng. Nên chạy ở chế độ nền và cập nhật kết quả khi xong.
- Với các PDF đã tồn tại trước khi có chức năng này, cần có cách tạo bản tóm tắt cho chúng (ví dụ một lần chạy hàng loạt, hoặc tạo khi file được mở lần đầu). Agent chọn cách phù hợp với kiến trúc hiện tại.

### FR-03. Lưu trữ bản tóm tắt
- Bản tóm tắt được lưu lại, gắn với đúng file PDF tương ứng.
- Khi người dùng mở file, hệ thống đọc bản tóm tắt đã lưu, **không gọi AI lại** mỗi lần xem.
- Cần lưu kèm trạng thái của bản tóm tắt: **chưa tạo / đang tạo / hoàn tất / lỗi**.

### FR-04. Hiển thị trên giao diện
- Bản tóm tắt hiển thị trong **một khung nhỏ nằm bên cạnh file PDF** ở màn hình xem file.
- Khung có tiêu đề rõ ràng, ví dụ "Tóm tắt nội dung".
- Khung phải gọn gàng, không che hay làm lệch việc xem file PDF.
- Nếu đoạn tóm tắt dài hơn khung, khung cho phép cuộn thay vì làm vỡ bố cục.
- Giao diện mới phải thống nhất với phong cách thiết kế hiện có của dự án.

### FR-05. Các trạng thái hiển thị trong khung

| Trạng thái | Hiển thị |
|---|---|
| Đang tạo | Thông báo ngắn như "Đang tạo bản tóm tắt..." |
| Hoàn tất | Đoạn tóm tắt |
| Lỗi | Thông báo lỗi thân thiện và nút **"Tạo lại"** |
| Không đọc được nội dung | Thông báo "Không thể đọc nội dung tài liệu để tóm tắt" |

### FR-06. Tạo lại bản tóm tắt
- Người dùng có thể bấm "Tạo lại" khi bản tóm tắt bị lỗi.
- Nếu file PDF bị thay bằng phiên bản mới, bản tóm tắt cũ phải được xem là hết hiệu lực và được tạo lại.

---

## 5. Yêu cầu phi chức năng

- **Hiệu năng:** mỗi file khoảng 10 trang nên tóm tắt xong trong vòng khoảng 1 phút. Người dùng không bị chặn thao tác trong lúc chờ.
- **Độ tin cậy:** lỗi khi gọi AI (hết hạn mức, mất mạng, file hỏng) không được làm hỏng chức năng upload hay xem PDF hiện có.
- **Bảo mật:** khóa API của dịch vụ AI phải nằm trong biến môi trường hoặc file cấu hình bí mật, **không** ghi cứng trong mã nguồn và **không** đưa lên kho mã nguồn.
- **Chi phí:** mỗi file chỉ gọi AI một lần cho mỗi phiên bản nội dung (nhờ lưu bản tóm tắt). Không gọi lại không cần thiết.
- **Khả năng mở rộng:** thiết kế sao cho sau này có thể thay dịch vụ AI khác mà không phải viết lại toàn bộ chức năng.

---

## 6. Quy tắc nghiệp vụ

1. Mỗi file PDF có tối đa một bản tóm tắt hiện hành.
2. Bản tóm tắt phải bám sát nội dung tài liệu. Nếu không đủ thông tin để tóm tắt thì báo "không đọc được tài liệu", không được suy đoán.
3. Dịch vụ AI: ưu tiên dịch vụ đang được dùng trong dự án. Nếu dự án chưa có, dùng **Gemini API**. Agent kiểm tra tài liệu hiện hành của dịch vụ về giới hạn dung lượng, số trang và tên mô hình trước khi triển khai.

---

## 7. Trường hợp đặc biệt cần xử lý

- PDF scan mờ, chữ nhỏ hoặc chất lượng kém.
- PDF bị đặt mật khẩu hoặc hỏng, không mở được.
- PDF gần như không có chữ (chỉ có hình, bảng biểu).
- PDF có số trang vượt giới hạn của dịch vụ AI.
- Gọi AI thất bại hoặc quá thời gian chờ.
- Người dùng mở file khi bản tóm tắt vẫn đang được tạo.
- Hai yêu cầu tạo tóm tắt cho cùng một file chạy cùng lúc (tránh tạo trùng).

---

## 8. Tiêu chí nghiệm thu

- [ ] Upload một PDF có text mới: bản tóm tắt xuất hiện trong khung bên cạnh file, nội dung đúng với tài liệu.
- [ ] Upload một PDF dạng ảnh scan: vẫn tạo được bản tóm tắt đúng nội dung chính.
- [ ] Bản tóm tắt là một đoạn văn tiếng Việt, khoảng 80-150 từ.
- [ ] Mở lại cùng một file nhiều lần: bản tóm tắt hiện ngay và **không** phát sinh thêm lệnh gọi AI.
- [ ] Khi đang tạo, khung hiện thông báo "đang tạo"; khi lỗi, khung hiện thông báo lỗi và nút "Tạo lại" hoạt động.
- [ ] Việc upload PDF không bị chậm đáng kể hoặc bị lỗi do chức năng tóm tắt.
- [ ] Các PDF đã có sẵn trước đó có thể có bản tóm tắt.
- [ ] Khung hiển thị gọn, không làm vỡ bố cục trang xem PDF trên các kích thước màn hình mà dự án đang hỗ trợ.
- [ ] Khóa API không xuất hiện trong mã nguồn hay kho mã nguồn.
- [ ] Các chức năng cũ của dự án vẫn hoạt động bình thường.

---

## 9. Giả định và điểm agent được tự quyết định

Các điểm sau chưa được chỉ định cụ thể, agent tự chọn phương án phù hợp nhất với dự án hiện tại và ghi lại lựa chọn trong phần mô tả thay đổi:

- Vị trí chính xác và kích thước của khung tóm tắt.
- Cách chạy nền (hàng đợi, tác vụ nền hay cơ chế sẵn có của dự án).
- Cách lưu bản tóm tắt (thêm cột vào bảng PDF hiện có hay bảng riêng).
- Cách tạo bản tóm tắt cho các PDF đã có sẵn.
- Cách đọc PDF scan (gửi file trực tiếp cho AI hay OCR riêng), dựa trên thử nghiệm với file thật.

**Giả định:** dữ liệu trong PDF được phép gửi tới dịch vụ AI bên ngoài. Nếu agent phát hiện tài liệu có vẻ chứa thông tin nhạy cảm, hãy báo lại cho chủ dự án trước khi triển khai.

---

## 10. Hướng phát triển sau này (không làm ở giai đoạn này)

- Cho phép hỏi đáp trên nội dung PDF (lúc đó mới cần RAG).
- Cho chọn độ dài hoặc kiểu tóm tắt (ngắn, chi tiết, gạch đầu dòng).
