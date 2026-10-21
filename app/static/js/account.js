import {apiFetch, loadAccount, bindForm, bindLogout, message} from './api.js';
import {pageUrl, clearSession} from './transport.js';
import {requirePageAccount} from './page-session.js';
await requirePageAccount();
bindLogout();
try {
  const account = await loadAccount();
  const home = pageUrl(account.role === 'ADMIN' ? '/admin/users' : '/user');
  document.getElementById('home').href = home;
  document.getElementById('back').href = home;
} catch (error) { message('message',error.message); }
bindForm('password-form','message',async (data, form) => {
  if (data.get('new_password') !== data.get('confirm')) throw new Error('Mật khẩu xác nhận không khớp.');
  await apiFetch('/api/auth/change-password',{method:'POST',body:JSON.stringify({current_password:data.get('current_password'),new_password:data.get('new_password')})});
  form.reset(); clearSession(); window.location.assign(pageUrl('/login'));
});
