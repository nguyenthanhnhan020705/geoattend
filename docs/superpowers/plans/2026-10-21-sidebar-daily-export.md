# Sidebar and daily attendance export

**Goal:** Put role-specific navigation on the left and the selected function on the right; export one employee-day per Excel row.

**Design:** Reuse existing page routes and authentication. Shared navigation renders the role's menu, marks the current page, and retains existing logout handlers. User `/user#history` selects personal history separately from the default attendance home. Keep all menu items on the left on mobile, with a compact width. Preserve existing forms, report uploads and maps.

**Export:** Move the existing export form to employee management. Columns: Ngày, Họ tên, Hình thức, Check-in sáng, Nghỉ trưa, Check-in chiều, Check-out, Lý do. Group by employee/day identity, distinguish morning leave and mixed modes, use lunch events to divide sessions (local noon fallback without lunch). Aggregate distinct leave/Remote reasons. Leave unavailable times blank; annotate system-closed final times. Exclude deleted histories, GPS and credentials; preserve authorization, date limits, session validation and literal spreadsheet text.

**Implementation:** Existing vanilla JavaScript, CSS, FastAPI and stdlib OOXML. Work in the current checkout; use the existing worktree's Python environment for verification. No dependency changes.

- [x] Add regression tests for daily grouping, leave, mixed modes, system closure and literal reasons; confirm failure.
- [x] Implement daily export projection and eight-column workbook, preserving access checks.
- [x] Implement shared sidebar on existing authenticated pages and User home/history selection.
- [x] Move export filters to employee management; remove dashboard coupling; normalize labels and the Admin brand home link.
- [x] Update affected browser expectations, verify navigation/layout and export downloads, run focused regressions and Pages build checks.

**Review focus:** Same-name employees remain separate; lunchtime closure is not Check-out; unfinished days have no invented Check-out; deleted history stays excluded; User/Admin menus and Pages base paths remain correct.


## Verification

- API/authentication/Pages build and artifact checks: 34 passed.
- Daily export and sidebar/attendance/Pages browser batch: 43 passed; the remaining test used the old hidden-history interaction. After updating it, the targeted rerun passed (2 tests, including Pages history navigation/logout).
- Reports, download, dashboard, office and account browser regressions: 18 passed in the first batch; old export-location/history selectors were corrected and passed in the subsequent batch.
- Report readiness and map-recovery checks: 5 passed.
- Reviewed desktop/mobile screenshots (1280px and 360px), no horizontal overflow; git diff --check passed. Independent read-only code review reported no actionable findings.
- Existing Starlette/httpx deprecation warning remains.
