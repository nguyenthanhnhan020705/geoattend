import {loadAccount} from './api.js';
import {requestApi} from './transport.js';

const image = document.getElementById('employee-avatar');
const picker = document.getElementById('avatar-file');
const button = document.getElementById('avatar-change');
const status = document.getElementById('avatar-message');

function display(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => { image.src = reader.result; resolve(); };
    reader.onerror = () => reject(new Error('Không đọc được ảnh. Vui lòng thử lại.'));
    reader.readAsDataURL(blob);
  });
}

async function responseError(response) {
  const data = await response.json().catch(() => ({}));
  throw new Error(data.message || 'Không thể cập nhật avatar. Vui lòng thử lại.');
}

async function restore() {
  try {
    const response = await requestApi('/api/account/avatar', {signal: AbortSignal.timeout(15000)});
    if (!response.ok) await responseError(response);
    if (response.status !== 204 && response.headers.get('Content-Type')?.startsWith('image/')) await display(await response.blob());
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
}

button.addEventListener('click', () => picker.click());
picker.addEventListener('change', async () => {
  const file = picker.files[0];
  if (!file) return;
  button.disabled = true;
  status.textContent = 'Đang tải ảnh…';
  try {
    if (file.size > 5_000_000) throw new Error('Ảnh đại diện tối đa 5 MB.');
    const account = await loadAccount();
    const response = await requestApi('/api/account/avatar', {
      method: 'PUT', body: file,
      headers: {'Content-Type': file.type || 'application/octet-stream', 'X-CSRF-Token': account.csrf_token},
      signal: AbortSignal.timeout(60000),
    });
    if (!response.ok) await responseError(response);
    await display(file);
    status.textContent = 'Đã cập nhật avatar.';
  } catch (error) { status.textContent = error.message; }
  finally { picker.value = ''; button.disabled = false; }
});
restore();
