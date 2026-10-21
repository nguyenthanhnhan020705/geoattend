import {loadAccount} from './api.js';
import {isPages, sessionToken, pageUrl, clearSession, redirectToLogin} from './transport.js';
import {configureNavigation, configureAttendanceViews} from './navigation.js';

let checking;
function navigate(path) {
  window.location.replace(pageUrl(path));
  return new Promise(()=>{});
}
export async function requirePageAccount(role=null) {
  if (!isPages) {
    const account = role ? null : await loadAccount();
    configureNavigation(role || account.role);
    configureAttendanceViews();
    return account;
  }
  try {
    sessionToken();
    const account = await (checking ||= loadAccount());
    if (role && account.role!==role) return navigate(account.role==='ADMIN'?'/admin/users':'/user');
    configureNavigation(account.role);
    configureAttendanceViews();
    document.body.removeAttribute('data-session-pending');
    return account;
  } catch (error) {
    if (error.code==='AUTH_REQUIRED') { clearSession(); redirectToLogin(); return new Promise(()=>{}); }
    document.body.removeAttribute('data-session-pending');
    for (const form of document.forms) form.inert=true;
    const notice=document.querySelector('#message, #report-message, #dashboard-message, #list-message');
    if (notice) notice.textContent=error.message;
    return new Promise(()=>{});
  }
}
