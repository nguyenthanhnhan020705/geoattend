import {message} from './api.js';
import {requestApi,pageUrl} from './transport.js';
import {fileBlob,downloadBlob} from './file-downloads.js';

const el = id=>document.getElementById(id);
let initialized = false, optionsKey = '';

export function updateExportFilters(data) {
  if (!initialized) {
    el('export-to').value = data.work_date;
    const start = new Date(data.work_date+'T00:00:00Z');
    start.setUTCDate(start.getUTCDate()-6);
    el('export-from').value = start.toISOString().slice(0,10);
    initialized = true;
    el('export-attendance').disabled = false;
  }
  const key = JSON.stringify(data.items.map(user=>[user.id,user.full_name,user.username]));
  if (key !== optionsKey) {
    const selected = el('export-user').value;
    const all = document.createElement('option'); all.value=''; all.textContent='Tất cả nhân viên';
    el('export-user').replaceChildren(all);
    for (const user of data.items) {
      const option = document.createElement('option');
      option.value = user.id; option.textContent = user.full_name+' · '+user.username;
      el('export-user').append(option);
    }
    if (data.items.some(user=>user.id===selected)) el('export-user').value=selected;
    optionsKey=key;
  }
}

el('attendance-export-form').addEventListener('submit', async event=>{
  event.preventDefault();
  const button = el('export-attendance');
  if (button.disabled || !initialized) return;
  const start = el('export-from').value, end = el('export-to').value;
  const days = (Date.parse(end)-Date.parse(start))/86400000;
  if (!start || !end || !Number.isFinite(days) || days<0 || days>=366) {
    message('export-message','Chọn khoảng ngày hợp lệ, tối đa 366 ngày.'); return;
  }
  const params = new URLSearchParams({from:start,to:end});
  if (el('export-user').value) params.set('user_id',el('export-user').value);
  button.disabled=true; button.textContent='Đang xuất…';
  el('attendance-export-form').setAttribute('aria-busy','true');
  message('export-message','Đang chuẩn bị file Excel…');
  const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),30000);
  try {
    const response=await requestApi('/api/admin/attendance/export?'+params,{signal:controller.signal});
    if (!response.ok) {
      const error=await response.json();
      if (response.status===401) window.location.assign(pageUrl('/login'));
      throw new Error(error.message || 'Không thể xuất Excel.');
    }
    const blob=await fileBlob(response,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    downloadBlob(blob,`geoattend_${start}_${end}.xlsx`);
    message('export-message','Đã tải file Excel.',true);
  } catch (error) {
    message('export-message',error.name==='AbortError'?'Xuất Excel quá thời gian chờ. Vui lòng thử lại.':error.message || 'Không thể kết nối. Vui lòng thử lại.');
  } finally {
    clearTimeout(timeout); button.disabled=false; button.textContent='Xuất Excel';
    el('attendance-export-form').removeAttribute('aria-busy');
  }
});
