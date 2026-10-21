import {apiFetch, bindForm} from './api.js';
import {isPages, pageUrl, loginAvailable} from './transport.js';
try { loginAvailable(); } catch(error) {
  document.querySelector('#login-form button[type="submit"]').disabled=true;
  for (const input of document.querySelectorAll('#login-form input')) input.disabled=true;
  document.getElementById('message').textContent=error.message;
}
bindForm('login-form','message', async (data, form) => {
  loginAvailable();
  const account = await apiFetch(isPages?'/api/auth/token':'/api/auth/login', {method:'POST',body:JSON.stringify({username:data.get('username'),password:data.get('password')})});
  form.querySelector('[name="password"]').value = '';
  window.location.assign(pageUrl(account.role === 'ADMIN' ? '/admin/users' : '/user'));
});
