from tests.browser_navigation import choose_menu, open_menu
"""User interactions shared by attendance browser regression tests."""


def open_history(page):
    if page.locator('#personal-history').is_hidden():
        choose_menu(page, 'Lịch sử cá nhân')


def open_attendance(page):
    if page.locator('.attendance-panel').is_hidden():
        choose_menu(page, 'Trang chủ chấm công')


def open_remote(page):
    open_attendance(page)
    page.locator('#choose-remote').click()


def open_leave(page):
    open_attendance(page)
    page.get_by_role('button',name='XIN NGHỈ',exact=True).click()
