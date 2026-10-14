import {loadAccount, bindLogout, message} from './api.js';
bindLogout();
try {
  const account = await loadAccount();
  document.getElementById('full-name').textContent = account.full_name;
  document.getElementById('account-username').textContent = account.username;
} catch (error) { message('message',error.message); }
