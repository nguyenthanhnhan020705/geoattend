# GeoAttend

Ứng dụng WebGIS chấm công và quản lý trạng thái làm việc cho một công ty, một văn phòng. Backend dùng FastAPI và PostgreSQL/PostGIS; giao diện HTML/CSS/JavaScript cùng nguồn, bản đồ Leaflet/MapLibre.

## Chức năng hiện có

- Đăng nhập, phân quyền User/Admin, cấp tài khoản, đổi và đặt lại mật khẩu.
- Check-in Office có GPS/Geofence; Remote có lý do; nghỉ trưa, nghỉ sáng và nghỉ cả ngày.
- Check-out và lịch sử cá nhân; tự kết thúc phiên lúc 20:00 giờ Việt Nam.
- Dashboard, bản đồ Onsite, quản lý Geofence và lịch sử nhân viên cho Admin.
- Xóa lịch sử từng ngày theo quyền Admin; xóa tọa độ và độ chính xác GPS sau 30 ngày.

Mọi Check-out và nghỉ cả ngày đều kết thúc ngày; ngày hôm sau mới bắt đầu lại, trừ ngoại lệ Admin xóa lịch sử hôm nay hợp lệ. Chi tiết tại [quy tắc trạng thái](docs/STATE_TRANSITIONS.md).

**Tiến độ:** Phase 0–5 đã triển khai; Phase 6 đã kiểm chứng local và chuẩn bị vận hành. HTTPS trên môi trường đích, GPS/thiết bị thật và pilot khoảng 10 người trong 5 ngày làm việc còn chờ thực hiện. Xem [roadmap](docs/ROADMAP.md).

## Chạy trên Windows

Cần Python 3.13, Git và kết nối PostgreSQL có PostGIS. Mã đầy đủ hiện nằm trên nhánh `feat/phase-1-foundation-auth`.

```powershell
git clone --branch feat/phase-1-foundation-auth https://github.com/nguyenthanhnhan020705/geoattend.git
cd geoattend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```

Trong thư mục vừa tải, tạo `.env` từ [.env.example](.env.example), điền kết nối database thực tế. `.env` và `.venv` được giữ riêng trên từng máy. Nếu dùng database đã cấu hình, giữ tài khoản/dữ liệu hiện có. Nếu dựng database mới, làm theo phần thiết lập trong [DEVELOPMENT](docs/DEVELOPMENT.md) trước khi chạy.

Terminal thứ nhất:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_run serve
```

Terminal thứ hai:

```powershell
.\.venv\Scripts\python.exe -m scripts.local_run maintenance
```

Mở **http://127.0.0.1:8000/login**. Khi bật máy lại, chạy lại hai lệnh trên. Máy cần kết nối tới database; nền bản đồ cần Internet. Khi dùng Supabase đã cấu hình, các máy cùng kết nối sẽ dùng chung dữ liệu.

## Tài liệu

| Nhu cầu | Tài liệu |
| --- | --- |
| Nắm nội dung toàn dự án | [Tổng hợp dự án](docs/PROJECT_OVERVIEW.md) |
| Đọc phân tích từng Phase 0–6 | [Mục lục theo phase](docs/README.md) |
| Chức năng bổ sung và định hướng | [Chức năng bổ sung](docs/features/README.md), [hướng phát triển](docs/FUTURE_DEVELOPMENT.md) |
| Hướng dẫn thao tác User/Admin | [Sử dụng](docs/USAGE.md) |
| Cài đặt, cấu hình database và kiểm thử | [Phát triển](docs/DEVELOPMENT.md) |
| Phạm vi và tiến độ | [Yêu cầu nghiệp vụ](docs/REQUIREMENTS.md), [roadmap](docs/ROADMAP.md) |
| Tra cứu toàn bộ tài liệu hiện hành | [Mục lục tài liệu](docs/README.md) |
| Triển khai HTTPS, backup và khôi phục | [Vận hành](docs/PHASE_6_OPERATIONS.md) |
| Kế hoạch, báo cáo và bàn giao cũ | [Kho lưu trữ](docs/archive/README.md) |

## Cấu trúc dự án

| Thư mục/file | Vai trò |
| --- | --- |
| `app/` | Backend, giao diện và thư viện bản đồ kèm giấy phép |
| `migrations/` | Các migration SQL đánh số |
| `scripts/` | Chạy local, migration, tài khoản Admin, maintenance và hỗ trợ kiểm thử |
| `tests/` | Kiểm thử API, database, trình duyệt và vận hành |
| `deploy/` | Mẫu cấu hình triển khai |
| `docs/` | Tài liệu hiện hành; `archive/` lưu lịch sử phát triển |
| `requirements*.txt`, `pyproject.toml` | Dependency, phiên bản cố định và cấu hình kiểm thử |

`.env`, `.venv`, `.local-tests`, `.pytest_cache`, `__pycache__` và `.superpowers` là cấu hình/môi trường/kết quả local, không được đưa lên GitHub. Thư mục `.local-tests` trên máy phát triển có thể chứa database test và bằng chứng kiểm thử; không phải tất cả nội dung trong đó đều là cache có thể xóa tùy ý.
