"""User interactions shared by attendance browser regression tests."""


def open_history(page):
    if page.locator('#personal-history').is_hidden():
        page.get_by_role('link',name='Lịch sử cá nhân',exact=True).click()


def open_attendance(page):
    if page.locator('.attendance-panel').is_hidden():
        page.get_by_role('link',name='Trang chủ chấm công',exact=True).click()


def open_remote(page):
    open_attendance(page)
    page.locator('#choose-remote').click()


def open_leave(page):
    open_attendance(page)
    page.get_by_role('button',name='XIN NGHỈ',exact=True).click()
