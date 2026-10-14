let csrf = '';
export async function apiFetch(path, options = {}) {
  const method = options.method || 'GET';
  if (method !== 'GET' && path !== '/api/auth/login' && !csrf) await loadAccount();
  const headers = {...options.headers};
  if (options.body) headers['Content-Type'] = 'application/json';
  if (method !== 'GET' && csrf) headers['X-CSRF-Token'] = csrf;
  let response;
  try { response = await fetch(path, {...options, headers, credentials: 'same-origin'}); }
  catch { throw new Error('Không thể kết nối. Kiểm tra mạng và thử lại.'); }
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    if (response.status === 401 && data.code === 'AUTH_REQUIRED') window.location.assign('/login');
    const error = new Error(data.message || 'Không thể thực hiện thao tác.');
    error.code = data.code;
    throw error;
  }
  if (data?.csrf_token) csrf = data.csrf_token;
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
    try { await apiFetch('/api/auth/logout', {method:'POST'}); window.location.assign('/login'); }
    catch (error) { message(messageId, error.message); document.getElementById('logout').disabled = false; }
  });
}
