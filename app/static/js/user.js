import {loadAccount, bindLogout, message, apiFetch} from './api.js';
bindLogout();
const el = id => document.getElementById(id);
const labels = {NOT_STARTED:'Chưa bắt đầu', WORKING_REMOTE:'Đang làm Remote', WORKING_OFFICE:'Đang làm tại văn phòng', CHECKED_OUT:'Đã Check-out', LUNCH_BREAK:'Đang nghỉ trưa', MORNING_LEAVE:'Nghỉ buổi sáng', FULL_DAY_LEAVE:'Nghỉ cả ngày'};
const eventLabels = {WORK_START:'Bắt đầu làm việc', WORK_END:'Kết thúc phiên', DAY_END:'Kết thúc ngày', LUNCH_START:'Nghỉ trưa', MORNING_LEAVE:'Nghỉ buổi sáng', FULL_DAY_LEAVE:'Nghỉ cả ngày', LEAVE_CANCELLED:'Hủy nghỉ'};
const clock = value => new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date(value));
let current = null, pending = null, busy = false, historyPage = 1, historyQuery = null, accountId = null;
const pendingKey = 'geoattend.pendingAttendance';

function controls() {
  const allowed = current?.allowed_actions || [];
  el('remote-form').hidden = !allowed.includes('START_REMOTE');
  el('check-out').hidden = !allowed.includes('CHECK_OUT');
  el('retry-action').hidden = !pending;
  el('remote-form').querySelector('button').disabled = busy || !!pending;
  el('remote-reason').disabled = busy || !!pending;
  el('check-out').disabled = busy || !!pending;
  el('retry-action').disabled = busy;
}

async function refreshStatus() {
  const data = await apiFetch('/api/attendance/status'); current = data;
  el('work-date').textContent = data.work_date + ' · Giờ Việt Nam';
  el('attendance-status').textContent = labels[data.status] || data.status;
  el('session-info').textContent = data.open_session ? `Bắt đầu lúc ${clock(data.open_session.start_time)} · ${data.open_session.start_reason || ''}` : 'Hiện không có phiên đang mở.';
  el('day-notice').textContent = data.allowed_actions.length ? '' : 'Hiện chưa có thao tác khả dụng. Ngày làm việc kết thúc lúc 20:00.';
  controls();
}

function savePending() {
  // Exact payload survives ambiguous responses/reloads in this account/tab.
  // No GPS or auth token is stored here.
  if (pending) sessionStorage.setItem(pendingKey,JSON.stringify(pending));
  else sessionStorage.removeItem(pendingKey);
}

async function sendPending() {
  if (!pending || busy) return;
  busy = true; controls(); message('message','Đang gửi…');
  let completed = false;
  try {
    await apiFetch('/api/attendance/actions',{method:'POST',body:JSON.stringify(pending.body)});
    pending = null; savePending(); completed = true;
    el('remote-reason').value = '';
    message('message','Đã ghi nhận thao tác.',true);
  } catch (error) {
    if (error.code && error.code !== 'DATABASE_UNAVAILABLE' && error.code !== 'INCONSISTENT_ATTENDANCE') {
      pending = null; savePending(); message('message',error.message);
    } else message('message','Chưa xác nhận được kết quả. Bấm “Gửi lại thao tác” để kiểm tra và gửi lại an toàn.');
  } finally { busy = false; controls(); }
  try { await refreshStatus(); if (completed) await loadHistory(historyQuery,historyPage); }
  catch (error) { message('message','Chưa tải được dữ liệu mới: '+error.message); }
}

function submit(action, reason) {
  if (!current || pending || busy) return;
  pending = {accountId,body:{request_id:crypto.randomUUID(),expected_revision:current.revision,action,...(reason !== undefined ? {reason} : {})}};
  savePending(); sendPending();
}

function line(tag, text, parent, className='') {
  const node = document.createElement(tag); node.textContent = text;
  if (className) node.className = className;
  parent.append(node); return node;
}

async function loadHistory(query, page=1) {
  if (!query) return;
  if (query.from > query.to) throw new Error('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.');
  const params = new URLSearchParams({...query,page:String(page),page_size:'20'});
  const data = await apiFetch('/api/attendance/history?'+params);
  historyQuery = query; historyPage = page; el('history-list').replaceChildren();
  if (!data.items.length) line('p','Chưa có lịch sử trong khoảng ngày này.',el('history-list'),'muted');
  for (const day of data.items) {
    const section = document.createElement('section'); section.className = 'history-day';
    line('h3',day.work_date+' · '+(labels[day.status] || day.status),section);
    for (const session of day.sessions) {
      const ending = session.end_time ? clock(session.end_time) : 'Đang mở';
      line('p',`${session.work_mode==='REMOTE'?'Remote':'Office'} · ${clock(session.start_time)} → ${ending}`,section);
      if (session.start_reason) line('p',session.start_reason,section,'muted');
      if (session.end_source==='SYSTEM') line('p','Hệ thống tự đóng lúc 20:00; không phải giờ kết thúc thực tế.',section,'system-note');
    }
    const events = document.createElement('ul'); events.className='timeline';
    for (const event of day.events) line('li',`${clock(event.event_time)} · ${eventLabels[event.event_type] || event.event_type}${event.source==='SYSTEM'?' · Hệ thống':''}${event.reason?' · '+event.reason:''}`,events);
    section.append(events); el('history-list').append(section);
  }
  el('history-page').textContent = `${page} / ${Math.max(1,Math.ceil(data.total/20))}`;
  el('history-prev').disabled = page<=1; el('history-next').disabled = page*20>=data.total;
  message('history-message','');
}

el('remote-form').addEventListener('submit', event => { event.preventDefault(); submit('START_REMOTE',el('remote-reason').value.trim()); });
el('check-out').addEventListener('click',()=>submit('CHECK_OUT'));
el('retry-action').addEventListener('click',sendPending);
el('refresh-status').addEventListener('click',()=>refreshStatus().catch(error=>message('message',error.message)));
el('history-form').addEventListener('submit',event=>{event.preventDefault(); loadHistory({from:el('history-from').value,to:el('history-to').value}).catch(error=>message('history-message',error.message));});
el('history-prev').addEventListener('click',()=>loadHistory(historyQuery,historyPage-1).catch(error=>message('history-message',error.message)));
el('history-next').addEventListener('click',()=>loadHistory(historyQuery,historyPage+1).catch(error=>message('history-message',error.message)));
try {
  const account = await loadAccount(); accountId=account.id;
  el('full-name').textContent = account.full_name; el('account-username').textContent = account.username;
  const saved = sessionStorage.getItem(pendingKey);
  if (saved) {
    try { const value=JSON.parse(saved); if (value.accountId===accountId) pending=value; else sessionStorage.removeItem(pendingKey); }
    catch { sessionStorage.removeItem(pendingKey); }
  }
  await refreshStatus();
  if (pending) message('message','Có thao tác chưa xác nhận. Bấm “Gửi lại thao tác” để kiểm tra kết quả.');
  el('history-to').value = current.work_date;
  const start = new Date(current.work_date+'T00:00:00Z'); start.setUTCDate(start.getUTCDate()-6);
  el('history-from').value = start.toISOString().slice(0,10);
  await loadHistory({from:el('history-from').value,to:current.work_date});
} catch (error) { message('message',error.message); }
setInterval(()=>{if(!document.hidden && !busy) refreshStatus().catch(error=>message('message',error.message));},60000);
window.addEventListener('focus',()=>{if(!busy) refreshStatus().catch(error=>message('message',error.message));});
