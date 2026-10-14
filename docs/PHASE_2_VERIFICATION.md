# GeoAttend — Kiểm chứng Phase 2

Phạm vi: Remote, Check-out, bắt đầu lại, lịch sử bản thân, đối soát 20:00, maintenance độc lập. Office và thao tác nghỉ thuộc Phase 3–4. Nghiệp vụ theo thiết kế MVP đã duyệt.

## Bằng chứng trước review

- Baseline Phase1:46/46. Lần đầu45pass/1error do thư mục tạm Windows bị từ chối ghi; chuyển basetemp/cache riêng khắc phục, không đổi mã để bỏ qua lỗi.
- Task1:13 ca RED vì endpoint chưa có →13GREEN; start/checkout/restart, lý do, inputthừa, quyền/CSRF, revision/replay, lịch sử cá nhân, transactionrollback.
- Task2:3caRED vì chưa có maintenance; tổng13GREEN cho deadline/concurrency. Giờ19:59:59/20:00/20:00:01 ViệtNam, chờ profilelockqua20:00, catchupqua ngày, replay saucutoff, lunch/leave, concurrentUUID, checkoutvsworker.
- Task3:browserRED thiếucontrol→GREEN. Edgeheadless360px:Remote/reload/checkout/restart/history, lýdoXSShiểnthịtext, khôngGPS, khôngoverflow/JSerror. Mấtresponse sauservercommit → gửi lại cùngUUID/payload và chỉ1phiên.
- Task4:4configtestsRED thiếu launcher→GREEN; mật khẩu có dấu nháy/backslash/khoảngtrắng được giữ nguyên, runtime/adminDSNs tách biệt, không thừa hưởng adminsecret vào tiến trìnhweb.
- Kiểm tra bổ sung:passwordreset trong khi action chờlock RED trả200→GREEN401 sau kiểm tra lại session dưới khóa.
- Fullsuite trước review:78passed,1warning trong81.91s; Pytest vớiPostgreSQL17/PostGIS riêng tại127.0.0.1:55439. Không dùngSupabase để chạytests.
- pipcheck:No broken requirements found. gitdiffcheck:không lỗi whitespace. Một warning upstream StarletteTestClient/HTTPX còn giữ, không suppress.

Lệnh chạy:

```powershell
$env:GEOATTEND_TEST_DATABASE_URL='postgresql://postgres@127.0.0.1:55439/postgres'
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.local-tests/phase-2/tmp-full -o cache_dir=.local-tests/phase-2/cache
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

## Rulings

1. Dùnglinkedworktreehiện tại, tiếp tụcinline đãchọn; khôngmerge/push. Chi phí nếu sai: thayđổilocalcóthểhoànnguyên.
2. Bashkhôngcó; checklist/ledger đượcghi bằngPowerShell thayBashhelpers. Chi phí:khácformatbookkeeping, chứngcứRED/GREEN/commitgiữnguyên.
3. Người dùngủyquyền tựcode/test; thiết kếMVPđãduyệt lànguồnquyếtđịnh, khôngxinlạiquyềnscope. Chi phí:quyếtđịnhimplementationlocalcóthểsửa.
4. Migration003bổsungresultstatus/revision/date/session đểreplaykếtquảgốc sauchuyểntrạngtháikhác. Khônglưupayload/GPS. Chi phí:thêm4cộtdatabase vàindexdueday; khôngsửamigrationcũ.
5. Revalidateauthsessiondướikhóaprofile đểyêucầuchờkhôngvượtquathu hồi/expiry. Chi phí:thêm1SELECTmỗilầnkiểmtra; chặnrequest đãthu hồiđúngquytắc.
6. Catchupcommittrướckhitrảlỗixungđộtaction; lỗi ghiSQL vẫnrollbacktoànbộaction. Chi phí:nếuactionbịtừchối thìtrạngtháingàyhếthạn vẫn đượcđóngnhưthiếtkế.

## Giới hạn vận hành

- Maintenance phải chạy trênmáycònbật. Localtắtmáy sẽ xử lýbùkhichạylại/APIđọc; productioncầnworkerđộclập hoạt độngliêntục.
- Khôngtạo dữliệuchấmcôngthửtrênSupabasethực. TàikhoảnAdmin/Usercủangườidùngđượcgiữnguyên.
- Khôngkhẳngđịnhpilot/benchmarkAPI95%<=2s/HTTPSGPS: thuộcphasecuối.
- Reviewđộclập vàbằngchứngchạythựcđượcbổsungsaulượtcuối.
