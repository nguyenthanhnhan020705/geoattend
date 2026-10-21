import {requestApi, pageUrl, clearSession, isPages, saveSession, redirectToLogin} from './transport.js';
let csrf = '';
export async function apiFetch(path, options = {}) {
  const method = options.method || 'GET';
  const loggingIn = path === '/api/auth/login' || path === '/api/auth/token';
  if (method !== 'GET' && !loggingIn && !csrf) await loadAccount();
  const headers = {...options.headers};
  if (options.body) headers['Content-Type'] = 'application/json';
  if (method !== 'GET' && csrf) headers['X-CSRF-Token'] = csrf;
  let response, data;
  const controller = new AbortController();
  const timer = setTimeout(()=>controller.abort(),15000);
  const signal = options.signal ? AbortSignal.any([options.signal,controller.signal]) : controller.signal;
  try {
    response = await requestApi(path, {...options, headers,signal});
    data = response.status === 204 ? null : await response.json();
  } catch (error) {
    if (error.code==='AUTH_REQUIRED') throw error;
    // Keep network/timeout errors without a definitive API code: attendance
    // retries must preserve the UUID when a server may have committed.
    throw new Error(controller.signal.aborted ? 'Yêu cầu quá thời gian chờ. Kiểm tra kết nối và thử tải lại; thao tác vừa lưu có thể đã được ghi nhận.' : 'Không thể kết nối. Kiểm tra mạng và thử lại.');
  } finally {clearTimeout(timer);}
  if (!response.ok) {
    if (response.status === 401 && data.code === 'AUTH_REQUIRED') redirectToLogin();
    const error = new Error(data.message || 'Không thể thực hiện thao tác.');
    error.code = data.code;
    throw error;
  }
  if (data?.csrf_token) csrf = data.csrf_token;
  if (isPages && path==='/api/auth/token') saveSession(data.access_token,data.expires_at);
  return data;
}
export async function loadAccount() { return apiFetch('/api/auth/me'); }
export function message(id, text, success = false) {
  const node = document.getElementById(id);
  node.textContent = text;
  node.classList.toggle('success', success);
}
export function bindForm(id, messageId, action) {
  const form = document.getElementById(id);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const button = form.querySelector('[type="submit"]');
    if (button.disabled) return;
    button.disabled = true;
    form.setAttribute('aria-busy', 'true');
    message(messageId, '');
    try { await action(new FormData(form), form); }
    catch (error) { message(messageId, error.message); }
    finally { button.disabled = false; form.removeAttribute('aria-busy'); }
  });
}
export function bindLogout(messageId = 'message') {
  document.getElementById('logout')?.addEventListener('click', async event => {
    event.currentTarget.disabled = true;
    try { await apiFetch('/api/auth/logout', {method:'POST'}); clearSession({discardPending:true}); csrf=''; redirectToLogin(); }
    catch (error) { message(messageId, error.message); document.getElementById('logout').disabled = false; }
  });
}
