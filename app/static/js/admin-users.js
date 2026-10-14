import {apiFetch, loadAccount, bindForm, bindLogout, message} from './api.js';
const dialog = document.getElementById('reset-dialog');
let selected = null;
bindLogout('list-message');
function openReset(account) {
  selected = account; document.getElementById('reset-form').reset(); message('reset-message','');
  document.getElementById('reset-name').textContent = account.full_name + ' · ' + account.username;
  dialog.showModal(); document.getElementById('reset-password').focus();
}
document.getElementById('close-reset').addEventListener('click',() => dialog.close());
async function refresh() {
  const result = await apiFetch('/api/admin/users');
  const list = document.getElementById('users'); list.replaceChildren();
  document.getElementById('empty').hidden = result.items.length > 0;
  for (const account of result.items) {
    const row = document.createElement('li');
    const info = document.createElement('div'); info.className = 'user-info';
    const name = document.createElement('strong'); name.textContent = account.full_name;
    const username = document.createElement('span'); username.textContent = account.username;
    const button = document.createElement('button'); button.type = 'button'; button.className = 'secondary'; button.textContent = 'Cấp lại mật khẩu';
    button.addEventListener('click',() => openReset(account));
    info.append(name,username); row.append(info,button); list.append(row);
  }
}
document.getElementById('reload').addEventListener('click',async event => {
  event.currentTarget.disabled = true;
  try { await refresh(); message('list-message',''); }
  catch (error) { message('list-message',error.message); }
  finally { document.getElementById('reload').disabled = false; }
});
bindForm('create-form','message',async (data,form) => {
  const account = await apiFetch('/api/admin/users',{method:'POST',body:JSON.stringify({username:data.get('username'),full_name:data.get('full_name'),password:data.get('password')})});
  form.reset(); message('message','Đã tạo tài khoản ' + account.username + '. Hãy cấp thông tin đăng nhập cho nhân viên.',true);
  try { await refresh(); } catch { message('list-message','Tài khoản đã tạo, nhưng chưa tải lại được danh sách. Bấm Tải lại.'); }
});
bindForm('reset-form','reset-message',async (data,form) => {
  await apiFetch('/api/admin/users/' + selected.id + '/reset-password',{method:'POST',body:JSON.stringify({new_password:data.get('new_password')})});
  form.reset(); dialog.close(); message('list-message','Đã đặt lại mật khẩu cho ' + selected.username + '. Hãy cấp mật khẩu mới cho nhân viên.',true);
});
try { await loadAccount(); await refresh(); }
catch (error) { message('list-message',error.message); }
