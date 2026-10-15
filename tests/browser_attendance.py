"""User interactions shared by attendance browser regression tests."""


def open_history(page):
    details = page.locator('#personal-history')
    if details.get_attribute('open') is None:
        details.locator('summary').click()


def open_remote(page):
    page.locator('#choose-remote').click()


def open_leave(page):
    page.get_by_role('button',name='XIN NGHỈ',exact=True).click()
