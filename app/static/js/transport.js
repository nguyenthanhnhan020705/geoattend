import {runtimeConfig as config} from './runtime-config.js';

export const isPages = config.mode === 'pages';
const routes = new Set(['/login','/user','/account','/admin/users','/admin/dashboard','/admin/office','/user/weekly-reports','/admin/weekly-reports']);
const namespace = `geoattend:${config.apiOrigin}:${config.basePath}:`;
const sessionKey = namespace + 'session';
let redirectingToLogin=false;
export const pendingStorageKey = isPages ? namespace + 'pendingAttendance' : 'geoattend.pendingAttendance';

export function pageUrl(path) {
  if (!routes.has(path)) throw new Error('Đường dẫn trang không hợp lệ.');
  return isPages ? config.basePath + path.slice(1) + '/' : path;
}

export function apiUrl(path) {
  if (typeof path !== 'string' || !path.startsWith('/api/') || /[\\\s#]/.test(path)) throw new Error('Đường dẫn API không hợp lệ.');
  let decoded;
  try { decoded = decodeURIComponent(path.split('?')[0]); } catch { throw new Error('Đường dẫn API không hợp lệ.'); }
  if (/[\\\s]/.test(decoded) || decoded.split('/').some(part=>part==='.' || part==='..')) throw new Error('Đường dẫn API không hợp lệ.');
  if (isPages && !config.apiOrigin) throw new Error('Dịch vụ chưa được kết nối. Vui lòng liên hệ Admin.');
  return isPages ? config.apiOrigin + path : path;
}

export function checkSessionStorage() {
  if (!isPages) return;
  try { sessionStorage.setItem(namespace+'probe','1'); sessionStorage.removeItem(namespace+'probe'); }
  catch { throw new Error('Trình duyệt không cho lưu phiên. Cho phép bộ nhớ trang rồi tải lại.'); }
}

export function saveSession(token, expiresAt) {
  checkSessionStorage();
  if (!/^[A-Za-z0-9_-]{20,256}$/.test(token) || !Number.isFinite(Date.parse(expiresAt))) throw new Error('Phiên đăng nhập không hợp lệ.');
  sessionStorage.setItem(sessionKey, JSON.stringify({token,expiresAt}));
}

export function clearSession({discardPending=false}={}) {
  try {
    sessionStorage.removeItem(sessionKey);
    if(discardPending)sessionStorage.removeItem(pendingStorageKey);
  } catch { /* storage may be disabled */ }
}

export function redirectToLogin() {
  if(redirectingToLogin)return;
  redirectingToLogin=true;
  window.location.assign(pageUrl('/login'));
}

export function sessionToken() {
  if (!isPages) return '';
  checkSessionStorage();
  let session;
  try { session = JSON.parse(sessionStorage.getItem(sessionKey)); } catch { clearSession(); }
  if (!session || !/^[A-Za-z0-9_-]{20,256}$/.test(session.token) || !(Date.parse(session.expiresAt)>Date.now())) {
    clearSession();
    const error = new Error('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
    error.code='AUTH_REQUIRED'; throw error;
  }
  return session.token;
}

export async function requestApi(path, options={}) {
  const url = apiUrl(path);
  const headers = new Headers(options.headers);
  if (isPages) {
    checkSessionStorage();
    if (path !== '/api/auth/token') {
      try { headers.set('Authorization','Bearer '+sessionToken()); }
      catch(error) {
        if(error.code==='AUTH_REQUIRED') redirectToLogin();
        throw error;
      }
    }
  }
  const response = await fetch(url, {...options, headers, credentials:isPages?'omit':'same-origin', redirect:'error'});
  if (isPages && response.status===401 && path!=='/api/auth/token') {
    clearSession(); redirectToLogin();
  }
  return response;
}

export function loginAvailable() {
  if (!isPages) return;
  if (!config.apiOrigin) throw new Error('Dịch vụ chưa được kết nối. Vui lòng liên hệ Admin.');
  checkSessionStorage();
}
