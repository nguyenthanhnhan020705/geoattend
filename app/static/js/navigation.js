import {pageUrl} from './transport.js';

const userMenu = [
  ['Trang chủ chấm công', '/user'],
  ['Lịch sử cá nhân', '/user', '#history'],
  ['Nộp báo cáo tuần', '/user/weekly-reports'],
  ['Đổi mật khẩu', '/account'],
];
const adminMenu = [
  ['Xem trạng thái hôm nay', '/admin/dashboard'],
  ['Nhân viên báo cáo tuần', '/admin/weekly-reports'],
  ['Quản lý nhân viên', '/admin/users'],
  ['Vùng văn phòng', '/admin/office'],
  ['Tài khoản cá nhân', '/account'],
];

export function configureNavigation(role) {
  const sidebar = document.querySelector('.app-sidebar');
  if (!sidebar) return;
  const nav = sidebar.querySelector('nav');
  const logout = document.getElementById('logout');
  nav.replaceChildren();
  for (const [label, path, hash=''] of role === 'ADMIN' ? adminMenu : userMenu) {
    const link = document.createElement('a');
    link.href = pageUrl(path) + hash;
    link.textContent = label;
    nav.append(link);
  }
  nav.append(logout);
  sidebar.querySelector('.brand').href = pageUrl(role === 'ADMIN' ? '/admin/dashboard' : '/user');
  const markCurrent = () => {
    for (const link of nav.querySelectorAll('a')) {
      const url = new URL(link.href);
      const selected = url.pathname === location.pathname && url.hash === (location.hash === '#history' ? '#history' : '');
      if (selected) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    }
  };
  markCurrent();
  window.addEventListener('hashchange', markCurrent);
}

export function configureAttendanceViews() {
  const history = document.getElementById('personal-history');
  const attendance = document.querySelector('.attendance-panel');
  const employee = document.getElementById('employee-account');
  if (!history || !attendance || !employee) return;
  const selectView = () => {
    const showHistory = location.hash === '#history';
    history.hidden = !showHistory;
    attendance.hidden = showHistory;
    employee.hidden = showHistory;
    document.title = (showHistory ? 'Lịch sử cá nhân' : 'Trang chủ chấm công') + ' · GeoAttend';
  };
  selectView();
  window.addEventListener('hashchange', selectView);
}
