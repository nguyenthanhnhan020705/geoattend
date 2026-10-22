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

const mobileItems = {
  '/user': ['Chấm công', 'attendance.jpg', 'attendance'],
  '/user#history': ['Lịch sử', 'history.png', 'history'],
  '/user/weekly-reports': ['Nộp báo cáo', 'reports.jpg', 'reports'],
  '/account': ['Đổi mật khẩu', 'password.jpg', 'password'],
  logout: ['Đăng xuất', 'logout.jpg', 'logout'],
};

function decorateMobileItem(element, label, key) {
  const [shortLabel, filename, kind] = mobileItems[key];
  element.dataset.mobileLabel = shortLabel;
  element.dataset.compactLabel = shortLabel;
  element.title = label;
  element.setAttribute('aria-label', label);
  const icon = document.createElement('span');
  icon.className = 'mobile-nav-icon mobile-nav-icon--' + kind;
  icon.setAttribute('aria-hidden', 'true');
  const image = document.createElement('img');
  image.src = new URL('../images/navigation/' + filename, import.meta.url).href;
  image.alt = '';
  image.width = 28; image.height = 28;
  icon.append(image);
  const text = document.createElement('span');
  text.className = 'nav-label'; text.textContent = label;
  element.replaceChildren(icon, text);
}

const adminIcons = {
  '/admin/dashboard': ['Trạng thái', 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z'],
  '/admin/weekly-reports': ['Báo cáo tuần', 'M8 3h8v3H8z M6 5H4v16h16V5h-2 M8 11h8 M8 15h8'],
  '/admin/users': ['Nhân viên', 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M20 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75'],
  '/admin/office': ['Vùng văn phòng', 'M21 10c0 6-9 12-9 12S3 16 3 10a9 9 0 1 1 18 0 M15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0'],
  '/account': ['Tài khoản', 'M7 10V7a5 5 0 0 1 10 0v3 M5 10h14v12H5z'],
  logout: ['Đăng xuất', 'M9 5H4v14h5 M14 8l4 4-4 4 M8 12h13'],
};

function decorateAdminItem(element, label, key) {
  const [shortLabel, path] = adminIcons[key];
  element.dataset.mobileLabel = shortLabel;
  element.dataset.compactLabel = shortLabel;
  element.setAttribute('aria-label', label);
  element.title = label;
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.classList.add('navigation-icon');
  for (const [name, value] of Object.entries({viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.8','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true'})) icon.setAttribute(name, value);
  const drawing = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  drawing.setAttribute('d', path); icon.append(drawing);
  const text = document.createElement('span');
  text.className = 'nav-label'; text.textContent = label;
  element.replaceChildren(icon, text);
}

export function configureNavigation(role) {
  const sidebar = document.querySelector('.app-sidebar');
  if (!sidebar) return;
  document.body.dataset.navigationRole = role;
  const nav = sidebar.querySelector('nav');
  const logout = document.getElementById('logout');
  nav.replaceChildren();
  for (const [label, path, hash=''] of role === 'ADMIN' ? adminMenu : userMenu) {
    const link = document.createElement('a');
    link.href = pageUrl(path) + hash;
    link.textContent = label;
    if (role === 'USER') decorateMobileItem(link, label, path + hash);
    else decorateAdminItem(link, label, path);
    nav.append(link);
  }
  if (role === 'USER') decorateMobileItem(logout, 'Đăng xuất', 'logout');
  else decorateAdminItem(logout, 'Đăng xuất', 'logout');
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
