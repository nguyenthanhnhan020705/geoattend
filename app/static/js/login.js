import {apiFetch, bindForm} from './api.js';
bindForm('login-form','message', async (data, form) => {
  const account = await apiFetch('/api/auth/login', {method:'POST',body:JSON.stringify({username:data.get('username'),password:data.get('password')})});
  form.querySelector('[name="password"]').value = '';
  window.location.assign(account.role === 'ADMIN' ? '/admin/users' : '/user');
});
