"""Navigate through the collapsible sidebar using visible UI controls."""


def open_menu(page):
    toggle = page.locator('#sidebar-toggle')
    if toggle.count() and toggle.is_visible() and toggle.get_attribute('aria-expanded') == 'false':
        toggle.click()


def choose_menu(page, label):
    open_menu(page)
    page.locator('.app-sidebar nav').get_by_role('link', name=label, exact=True).click()
