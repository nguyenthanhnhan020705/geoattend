import {loadAccount, bindLogout, message, apiFetch} from './api.js';
bindLogout();
const el = id => document.getElementById(id);
const labels = {NOT_STARTED:'Chưa bắt đầu', WORKING_REMOTE:'Đang làm Remote', WORKING_OFFICE:'Đang làm tại văn phòng', CHECKED_OUT:'Đã Check-out', LUNCH_BREAK:'Đang nghỉ trưa', MORNING_LEAVE:'Nghỉ buổi sáng', FULL_DAY_LEAVE:'Nghỉ cả ngày'};
const eventLabels = {WORK_START:'Bắt đầu làm việc', WORK_END:'Kết thúc phiên', DAY_END:'Kết thúc ngày', LUNCH_START:'Nghỉ trưa', MORNING_LEAVE:'Nghỉ buổi sáng', FULL_DAY_LEAVE:'Nghỉ cả ngày', LEAVE_CANCELLED:'Hủy nghỉ'};
const clock = value => new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date(value));
let current = null, pending = null, busy = false, historyPage = 1, historyQuery = null, accountId = null;
const pendingKey = 'geoattend.pendingAttendance';
const officeActions = ['START_OFFICE','CANCEL_LEAVE_START_OFFICE','SWITCH_OFFICE'];
const remoteActions = ['START_REMOTE','CANCEL_LEAVE_START_REMOTE','SWITCH_REMOTE'];
const isOffice = action => officeActions.includes(action);
const available = actions => actions.find(action => current?.allowed_actions.includes(action));

function controls() {
  const allowed = current?.allowed_actions || [];
  const remote = available(remoteActions), office = available(officeActions);
  el('remote-form').hidden = !remote;
  el('remote-form').querySelector('button').textContent = remote==='CANCEL_LEAVE_START_REMOTE'?'Hủy nghỉ và bắt đầu Remote':remote==='SWITCH_REMOTE'?'Chuyển sang Remote':current?.status==='LUNCH_BREAK'?'Tiếp tục Remote':'Bắt đầu Remote';
  el('check-out').hidden = !allowed.includes('CHECK_OUT');
  el('start-office').hidden = !office;
  el('start-office').textContent = office==='CANCEL_LEAVE_START_OFFICE'?'Hủy nghỉ và bắt đầu Office':office==='SWITCH_OFFICE'?'Chuyển sang Office':current?.status==='LUNCH_BREAK'?'Tiếp tục Office':'Check-in Office';
  el('gps-note').hidden = !office;
  el('start-lunch').hidden = !allowed.includes('START_LUNCH');
  el('leave-form').hidden = !allowed.some(action=>['MORNING_LEAVE','FULL_DAY_LEAVE'].includes(action));
  el('morning-leave').hidden = !allowed.includes('MORNING_LEAVE');
  el('full-day-leave').hidden = !allowed.includes('FULL_DAY_LEAVE');
  for (const id of ['start-lunch','morning-leave','full-day-leave','leave-reason']) el(id).disabled = busy || !!pending;
  el('start-office').disabled = busy || !!pending;
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
  if (pending && !isOffice(pending.body.action)) sessionStorage.setItem(pendingKey,JSON.stringify(pending));
  else sessionStorage.removeItem(pendingKey);
}

async function sendPending() {
  if (!pending || busy) return;
  busy = true; controls(); message('message','Đang gửi…');
  try {
    await apiFetch('/api/attendance/actions',{method:'POST',body:JSON.stringify(pending.body)});
    pending = null; savePending();
    el('remote-reason').value = '';
    el('leave-reason').value = '';
    message('message','Đã ghi nhận thao tác.',true);
  } catch (error) {
    if (error.code && error.code !== 'DATABASE_UNAVAILABLE' && error.code !== 'INCONSISTENT_ATTENDANCE') {
      pending = null; savePending(); message('message',error.message);
    } else message('message','Chưa xác nhận được kết quả. Bấm “Gửi lại thao tác” để kiểm tra và gửi lại an toàn.');
  } finally { busy = false; controls(); }
  try { await refreshStatus(); await loadHistory(historyQuery,historyPage); }
  catch (error) { message('message','Chưa tải được dữ liệu mới: '+error.message); }
}

function submit(action, reason, position=null, intended=current) {
  if (!current || pending || busy) return;
  pending = {accountId,body:{request_id:crypto.randomUUID(),expected_revision:intended.revision,expected_work_date:intended.work_date,action,...(reason !== undefined ? {reason} : {}),...(position || {})}};
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
      if(session.location?.status==='available') line('p',`GPS đã xác minh · ${session.location.latitude}, ${session.location.longitude} · Sai số ${session.location.accuracy_m} m`,section,'muted');
      if(session.location?.status==='expired') line('p','Dữ liệu vị trí đã hết hạn lưu. Kết quả xác minh được giữ lại.',section,'muted');
    }
    const events = document.createElement('ul'); events.className='timeline';
    for (const event of day.events) {
      const label = event.event_type==='DAY_END' && event.source==='SYSTEM' ? 'Hệ thống kết thúc ngày lúc 20:00; không phải giờ kết thúc thực tế.' : eventLabels[event.event_type] || event.event_type;
      line('li',`${clock(event.event_time)} · ${label}${event.source==='SYSTEM'?' · Hệ thống':''}${event.reason?' · '+event.reason:''}`,events);
    }
    section.append(events); el('history-list').append(section);
  }
  el('history-page').textContent = `${page} / ${Math.max(1,Math.ceil(data.total/20))}`;
  el('history-prev').disabled = page<=1; el('history-next').disabled = page*20>=data.total;
  message('history-message','');
}

el('remote-form').addEventListener('submit', event => { event.preventDefault(); const action=available(remoteActions); if(action)submit(action,el('remote-reason').value.trim()); });
el('leave-form').addEventListener('submit', event => { event.preventDefault(); const action=event.submitter?.value; if(current?.allowed_actions.includes(action))submit(action,el('leave-reason').value.trim()); });
el('start-lunch').addEventListener('click',()=>submit('START_LUNCH'));
el('check-out').addEventListener('click',()=>submit('CHECK_OUT'));
el('start-office').addEventListener('click',async()=>{
  if(!current || busy || pending)return;
  const action=available(officeActions);if(!action)return;
  const intended={...current};let position=null;busy=true;controls();message('message','Đang xác minh vị trí…');
  try{
    if(!navigator.geolocation)throw {code:2};
    const result=await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{enableHighAccuracy:true,timeout:15000,maximumAge:0}));
    position={latitude:result.coords.latitude,longitude:result.coords.longitude,accuracy_m:result.coords.accuracy};
  }catch(error){
    const text=error.code===1?'Bạn chưa cấp quyền vị trí. Cho phép GPS rồi thử lại, hoặc tự chọn Remote và nhập lý do.':error.code===3?'Lấy vị trí quá thời gian chờ. Hãy thử lại hoặc tự chọn Remote.':'Chưa lấy được vị trí. Kiểm tra GPS hoặc tự chọn Remote.';
    message('message',text);
  }finally{busy=false;controls();}
  if(position)submit(action,undefined,position,intended);
});
el('retry-action').addEventListener('click',sendPending);
async function refreshAll() { await refreshStatus(); await loadHistory(historyQuery,historyPage); }
el('refresh-status').addEventListener('click',()=>refreshAll().catch(error=>message('message',error.message)));
el('history-form').addEventListener('submit',event=>{event.preventDefault(); loadHistory({from:el('history-from').value,to:el('history-to').value}).catch(error=>message('history-message',error.message));});
el('history-prev').addEventListener('click',()=>loadHistory(historyQuery,historyPage-1).catch(error=>message('history-message',error.message)));
el('history-next').addEventListener('click',()=>loadHistory(historyQuery,historyPage+1).catch(error=>message('history-message',error.message)));
try {
  const account = await loadAccount(); accountId=account.id;
  el('full-name').textContent = account.full_name; el('account-username').textContent = account.username;
  const saved = sessionStorage.getItem(pendingKey);
  if (saved) {
    try { const value=JSON.parse(saved); if (value.accountId===accountId && value.body && !isOffice(value.body.action) && !['latitude','longitude','accuracy_m'].some(key=>key in value.body)) pending=value; else sessionStorage.removeItem(pendingKey); }
    catch { sessionStorage.removeItem(pendingKey); }
  }
  await refreshStatus();
  if (pending) message('message','Có thao tác chưa xác nhận. Bấm “Gửi lại thao tác” để kiểm tra kết quả.');
  el('history-to').value = current.work_date;
  const start = new Date(current.work_date+'T00:00:00Z'); start.setUTCDate(start.getUTCDate()-6);
  el('history-from').value = start.toISOString().slice(0,10);
  await loadHistory({from:el('history-from').value,to:current.work_date});
} catch (error) { message('message',error.message); }
setInterval(()=>{if(!document.hidden && !busy) refreshAll().catch(error=>message('message',error.message));},60000);
window.addEventListener('focus',()=>{if(!busy) refreshAll().catch(error=>message('message',error.message));});
