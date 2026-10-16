# Phase 6 — Phép đo API backend

**Chỉ đo local, chưa chứng minh production/pilot.** NFR-04 yêu cầu ≥95% API hoàn tất ≤2000ms từ backend nhận request đến hoàn tất phản hồi, không tính lấy GPS/mạng client. Báo cả lỗi và tỷ lệ thành công trong ngưỡng, không bỏ mẫu chậm hoặc lỗi.

## Phương pháp tái lập

`tests/integration/test_phase6_load.py` dùng fixture DB UUID riêng PostgreSQL/PostGIS, migration hiện có, Uvicorn TCP loopback thật và httpx thread pool. Không dùng `.env`, Supabase hoặc DSN ứng dụng. `app.telemetry.ApiTiming` dùng perf_counter trước dispatch đến ASGI body cuối, bao gồm xếp hàng trong app, chờ pool/khóa/DB và dựng phản hồi. Socket accept/OS queue trước ASGI và mạng client không nằm trong số đo; cần đo riêng saturation/lỗi connection trên đích. Harness thất bại nếu HTTP/transport lỗi; lỗi transport trước ASGI không có mẫu timing và phải báo riêng, không được loại khỏi báo cáo.

Dữ liệu tổng hợp: 1 Admin + 10 User, 5 ngày lịch sử/User, 1 phiên Remote + 2 event/ngày (50 ngày/50 phiên/100 event), một Geofence hình vuông; accuracy Office 50000m để giữ kiểm chứng không accuracy gate. Không dữ liệu người thật. Dữ liệu ngày đo thêm 10 ngày; tối đa một phiên mở/User kiểm tra qua logic thực, cuối tải không còn phiên mở.

Đồng hồ nghiệp vụ cố định **16/10/2026 09:00 Việt Nam**, gồm login/dependency; mọi request dùng ngày server, không lấy giờ thiết bị. Đây là cách cho phép chạy buổi tối sau cutoff mà không phá quy tắc 20:00; timing monotonic, HTTP, SQL, transaction/lock/GIS vẫn thật. Không chứng minh tải qua cutoff bằng benchmark; full suite có clock/lock riêng cho cutoff/ngày mới.

Workload closed-loop không think time:

- 10 actor User, mỗi actor giữ cookie/CSRF riêng: login có đo; bắt đầu Office/Remote, replay cùng UUID mô phỏng mất phản hồi, lunch/resume, status/history, switch API tương thích và Checkout. Một User nghỉ sáng/resume Office, một User full-day leave; không dùng lại action mới sau ngày kết thúc.
- 10 actor đọc Admin dùng cùng quyền Admin (mô phỏng nhiều tab đồng thời), lặp dashboard/onsite/lịch sử từng User/health. Đây là tải stress mạnh hơn một Admin refresh 30 giây của pilot; không suy ra tổ chức cần 10 Admin.
- Executor max concurrency 1, 10, 20. Tối đa 20 actor phát request nối tiếp; không phải 20 request luôn đang bay, reader có thể vào hàng chờ ở c1/c10. Báo thông số này để không hiểu concurrency là số User hoặc open-loop RPS cố định.
- Warmup/setup tạo tài khoản, 11 login + `/auth/me` ban đầu tách khỏi mẫu. Trong mẫu vẫn có **11 login mới** (10 User + Admin), không che chi phí Argon2. Mỗi mức rounds=10 có **1217 request**: login 11, actions 126, status 180, history User 100, Dashboard/Onsite/Admin history/health mỗi loại 200. Tổng ba mức **3651**.
- Phân vị nearest-rank; tỷ lệ ≤2s bao gồm cả response lỗi; báo thêm `successful_within_2s_percent`, mã lỗi theo endpoint (harness đòi 0 lỗi ngoài kỳ vọng). Không tính response setup/warmup vào mẫu, không lấy `httpx elapsed` làm thời gian backend.

Lệnh đo (không chạy suite khác đồng thời với lượt đo nghiệm thu):

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55440/postgres'
$env:GEOATTEND_LOAD_ROUNDS='10'
./.venv/Scripts/python.exe -m pytest tests/integration/test_phase6_load.py -q --basetemp=.local-tests/phase-6/load-measure-02 -o cache_dir=.local-tests/phase-6/cache-load
Remove-Item Env:GEOATTEND_LOAD_ROUNDS
```

Môi trường: Windows 11 build 26200, Python **3.13.3**, PostgreSQL **17.9**, PostGIS **3.6.1**, Intel Core **i7-1255U**, **12 logical CPU**, **15.69 GiB RAM** (GlobalMemoryStatusEx). Uvicorn **1 worker**, Psycopg pool **max 5**, DB/web/load generator cùng laptop, không proxy/TLS, không GPS/client Internet. Không thay pool/quyền/khóa để làm xanh. Phiên bản phụ thuộc theo lockfile hiện hành; máy Windows có tiến trình người dùng khác, không phải host dành riêng.

## Kết quả trước tối ưu — giữ bằng chứng FAIL

Smoke rounds=1 khi baseline còn chạy: c1/c10 đạt; c20 **173 request, 0 lỗi, 94.21965% ≤2s**, p95 **2044.166ms**, max **2944.557ms**. Lượt này không dùng chứng minh đạt vì có cạnh tranh tài nguyên.

Lượt dài `load-measure-01` sau baseline (mỗi mức 1217 request):

| Concurrency | ≤2s/thành công ≤2s | p50 ms | p95 ms | p99 ms | max ms | Lỗi HTTP |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 100% | 41.484 | 128.283 | 242.033 | 659.379 | 0 |
| 10 | 99.09614% | 400.727 | 1058.781 | 1965.643 | 2551.800 | 0 |
| 20 | **93.50863% — FAIL** | 757.379 | 2171.957 | 2716.128 | 3368.867 | 0 |

Ở c20: Dashboard p95 2686.667ms, Onsite 2250.788ms, actions 2428.329ms, login 2237.043ms. Không có lỗi transport/HTTP; chậm vẫn là không đạt ngưỡng. Lượt dài có probe timeline rất ngắn trong thời gian setup; không còn baseline/browser suite chạy cạnh tranh trong phần c10/c20.

Nguyên nhân quan sát: Dashboard đọc snapshot qua nhiều truy vấn/User trong lúc giữ khóa profile toàn bộ; các reader serialize và giữ pool trong khi chờ khóa. Test query bound RED đo số query **6 → 24** cho 1 → 10 User chưa có ngày. Sửa: gom đọc ngày/phiên/xác minh, chỉ reconcile những User có ngày quá cutoff; giữ nguyên profile lock UUID trước day/session, thời điểm/recheck session, xử lý inactive và bộ đọc GPS retention. Không đổi migration hoặc snapshot API. Test quyền/cutoff/race/onsite phải đạt trước đo lại.

## Kết quả sau tối ưu

Lượt `load-measure-02`: **3 passed, 164.10s**, sau tối ưu đọc snapshot; hoàn tất 16/10/2026 khoảng 22:09 Việt Nam. Mỗi mức 1217 request, tổng **3651**, **0 lỗi HTTP/transport**, không loại mẫu. Query bound và Dashboard/Onsite hồi quy đã đạt trước đo (**35 passed, 1 warning**, 103.17s cho nhóm gồm restore/unit).

| Concurrency | ≤2s/thành công ≤2s | p50 ms | p95 ms | p99 ms | max ms | Request/s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 100% | 23.116 | 108.394 | 176.057 | 496.253 | 24.83 |
| 10 | 100% | 225.222 | 579.407 | 1001.291 | 1312.891 | 37.19 |
| 20 | 99.91783% | 257.879 | 806.608 | 1392.458 | 2009.836 | 53.18 |

Ở c20 vẫn có **1 request >2s**; ngưỡng 95% đạt local, không nói mọi request đạt. Dashboard p95 1142.978ms/max 2009.836ms; Onsite 702.139ms; actions 1077.678ms; login 1570.918ms. Tỷ lệ toàn 3651 request **99.97261%**. [JSON tổng hợp sau tối ưu](evidence/phase6/load-after.json) chứa từng endpoint/môi trường; log local `load-measure-02.log`. Không sửa lock/pool và không giảm concurrency để đạt. `workload_failures` được bổ sung vào harness để các lượt lỗi tương lai vẫn xuất số liệu trước fail; thay đổi báo cáo lỗi này không ảnh hưởng số đo lượt thành công.

Kết quả full suite smoke không thay thế lượt dài này. Phép đo chỉ cho mô hình local/dataset/workload nêu trên; không chứng minh lịch sử lớn, nhiều công ty hoặc nhiều văn phòng.

## Số đo cuối sau review — dùng khi bàn giao

Review phát hiện timing unhandled 500 nằm bên trong ServerErrorMiddleware; đã đặt wrapper ngoài toàn stack FastAPI và kiểm tra final body có delay. Khi đo lại, phát hiện race collector clear lúc warmup `/auth/me` chưa hoàn tất. Lượt `load-review-final` có 1218 mẫu ở c10 nên **không dùng làm số liệu cuối**; có thêm warning cache ACL Windows, không phải lỗi HTTP. Sửa collector chọn request tại đầu bằng header chỉ của harness; count request gửi độc lập, chờ callback cuối và assert không warmup/không mất mẫu. Không sửa/ngắt profile lock hoặc ngưỡng 95%.

Lượt **`load-final-verified`**, bản đã sửa review/collector: **3 passed, 83.97s**. Mỗi mức **1217 gửi / 1217 mẫu**, missing_timings **0**, workload_failures rỗng, tổng **3651 request**, **0 lỗi HTTP/transport**, **100% ≤2s** ở cả ba mức. [JSON số đo cuối](evidence/phase6/load-final.json).

| Concurrency | p50 ms | p95 ms | p99 ms | max ms | Request/s | Thành công ≤2s |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 13.377 | 43.567 | 82.898 | 220.569 | 51.59 | 100% |
| 10 | 107.815 | 215.304 | 430.972 | 1045.577 | 79.86 | 100% |
| 20 | 193.972 | 606.620 | 891.801 | 1405.177 | 66.29 | 100% |

Do Windows sandbox lỗi tài khoản 1909, lượt cuối chạy bằng quyền nâng được duyệt, cùng laptop/database loopback nhưng context chạy khác các lượt đầu. Không diễn giải chênh lệch latency giữa mọi lượt thành mức tăng tốc nhân quả hoặc suy rộng production; bằng chứng query bound/SQL và hồi quy bảo vệ thay đổi tối ưu. Máy vẫn có tải nền của người dùng, không host benchmark chuyên dụng.

## Cổng môi trường đích

Chưa có host/domain/DB/chi phí/quyền đích. Cần chạy đo trên staging/pilot cùng CPU/RAM/pool/worker/proxy/TLS/DB network thực đã duyệt; đo server-side bằng log api_request, giữ tỷ lệ lỗi và số mẫu, xác minh clock/health/worker. Harness này chỉ cho phép DB test cô lập, không trỏ vào production để tạo/xóa dữ liệu. Muốn load staging thực phải chuẩn bị workload riêng với tài khoản/dữ liệu được duyệt, không đổi guard an toàn của fixture.

Trong pilot đo đủ 5 ngày, báo số người/samples/ngày/endpoint và p50/p95/p99, tỷ lệ ≤2s, lỗi/mất log. **Local đạt không đồng nghĩa NFR-04 production đạt.** NFR-05 GPS thực/accuracy/permission và độ ổn định DB/worker trong pilot vẫn pending.
