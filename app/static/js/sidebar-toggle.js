const sidebar = document.querySelector('.app-sidebar');
const toggle = document.getElementById('sidebar-toggle');
const storageKey = 'geoattend.sidebarCollapsed';

if (sidebar && toggle) {
  function setCollapsed(collapsed, remember = true) {
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    toggle.setAttribute('aria-expanded', String(!collapsed));
    const label = collapsed ? 'Mở menu' : 'Thu gọn menu';
    toggle.setAttribute('aria-label', label);
    toggle.title = label;
    if (remember) {
      try { sessionStorage.setItem(storageKey, String(collapsed)); } catch { /* UI remains usable without storage. */ }
    }
    window.dispatchEvent(new Event('resize'));
  }
  function restore() {
    let collapsed = false;
    try { collapsed = sessionStorage.getItem(storageKey) === 'true'; } catch { /* Default to the visible menu. */ }
    setCollapsed(collapsed, false);
  }
  restore();
  window.addEventListener('pageshow', restore);
  toggle.addEventListener('click', () => setCollapsed(toggle.getAttribute('aria-expanded') === 'true'));
  sidebar.addEventListener('click', event => {
    const link = event.target.closest('nav a');
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.target === '_blank') return;
    setCollapsed(true);
    toggle.focus({preventScroll:true});
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setCollapsed(true);
      toggle.focus({preventScroll:true});
    }
  });
}
