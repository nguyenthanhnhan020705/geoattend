import {loadAccount, bindLogout, message, apiFetch} from './api.js';
import {requirePageAccount} from './page-session.js';
import {pendingStorageKey} from './transport.js';
await requirePageAccount('USER');
bindLogout();
const el = id => document.getElementById(id);
const labels = {NOT_STARTED:'Trạng thái: Chưa bắt đầu', WORKING_REMOTE:'Đang làm Remote', WORKING_OFFICE:'Đang làm tại văn phòng', CHECKED_OUT:'Đã Check-out', LUNCH_BREAK:'Đang nghỉ trưa', MORNING_LEAVE:'Đang nghỉ buổi sáng', FULL_DAY_LEAVE:'Nghỉ cả ngày'};
const clock = value => new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date(value));
let current = null, pending = null, busy = false, historyPage = 1, historyQuery = null, accountId = null;
let reasonPanel = null, leaveKind = null;
let historyGeneration = 0;
const pendingKey = pendingStorageKey;
const officeActions = ['START_OFFICE','CANCEL_LEAVE_START_OFFICE','SWITCH_OFFICE'];
const remoteActions = ['START_REMOTE','CANCEL_LEAVE_START_REMOTE','SWITCH_REMOTE'];
const isOffice = action => officeActions.includes(action);
const available = actions => actions.find(action => current?.allowed_actions.includes(action));

function controls() {
  const allowed = current?.allowed_actions || [];
  const working = ['WORKING_OFFICE','WORKING_REMOTE'].includes(current?.status);
  const morning = current?.status==='MORNING_LEAVE';
  const resuming = current?.status==='LUNCH_BREAK' || morning;
  const afternoon = current?.lunch_taken || current?.morning_leave;
  const remote = working ? undefined : available(remoteActions), office = working ? undefined : available(officeActions);
  el('attendance-choices').hidden = working || !!current?.day_finished;
  el('attendance-choices').classList.toggle('is-resuming',resuming);
  el('choose-remote').textContent = morning?'TIẾP TỤC BUỔI CHIỀU REMOTE':resuming?'TIẾP TỤC REMOTE':'CHECK-IN REMOTE';
  el('choose-leave').hidden = resuming;
  const leave = allowed.some(action=>['MORNING_LEAVE','FULL_DAY_LEAVE'].includes(action));
  const earlyCheckout = allowed.includes('CHECK_OUT') && !afternoon;
  if ((reasonPanel==='remote' && !remote) || (reasonPanel==='leave' && !leave) || (reasonPanel==='checkout' && !earlyCheckout)) reasonPanel=null;
  el('reason-panel').hidden = !reasonPanel;
  el('reason-heading').textContent = reasonPanel==='checkout'?'Check-out sớm':reasonPanel==='leave'?'Xin nghỉ':'Check-in Remote';
  el('checkout-form').hidden = reasonPanel!=='checkout';
  el('checkout-reason').disabled = busy || !!pending;
  el('checkout-form').querySelector('button').disabled = busy || !!pending;
  el('check-out').setAttribute('aria-expanded',String(reasonPanel==='checkout'));
  el('check-out').setAttribute('aria-controls','reason-panel');
  el('remote-form').hidden = reasonPanel!=='remote';
  el('choose-remote').disabled = busy || !!pending || !remote;
  el('choose-leave').disabled = busy || !!pending || !leave;
  el('close-reason').disabled = busy || !!pending;
  el('choose-remote').setAttribute('aria-expanded',String(reasonPanel==='remote'));
  el('choose-leave').setAttribute('aria-expanded',String(reasonPanel==='leave'));
  el('remote-form').querySelector('button').textContent = remote==='CANCEL_LEAVE_START_REMOTE'?'Hủy nghỉ và bắt đầu Remote':remote==='SWITCH_REMOTE'?'Chuyển sang Remote':resuming?'Tiếp tục Remote':'Bắt đầu Remote';
  el('check-out').hidden = !allowed.includes('CHECK_OUT');
  el('check-out').textContent = afternoon?'CHECK-OUT':'CHECK-OUT SỚM';
  el('start-office').textContent = morning?'TIẾP TỤC BUỔI CHIỀU OFFICE':office==='CANCEL_LEAVE_START_OFFICE'?'Hủy nghỉ và bắt đầu Office':resuming?'TIẾP TỤC OFFICE':'CHECK-IN OFFICE';
  el('gps-note').hidden = !office;
  el('start-lunch').hidden = !allowed.includes('START_LUNCH') || !!afternoon;
  el('start-lunch').textContent = 'NGHỈ TRƯA';
  el('leave-form').hidden = reasonPanel!=='leave';
  el('morning-leave').hidden = !allowed.includes('MORNING_LEAVE');
  el('full-day-leave').hidden = !allowed.includes('FULL_DAY_LEAVE');
  el('leave-fields').hidden = !leaveKind;
  el('morning-leave').setAttribute('aria-pressed',String(leaveKind==='MORNING_LEAVE'));
  el('full-day-leave').setAttribute('aria-pressed',String(leaveKind==='FULL_DAY_LEAVE'));
  el('confirm-leave').textContent = leaveKind==='MORNING_LEAVE'?'Xác nhận nghỉ buổi sáng':'Xác nhận nghỉ cả ngày';
  for (const id of ['start-lunch','morning-leave','full-day-leave','leave-reason','confirm-leave']) el(id).disabled = busy || !!pending;
  el('start-office').disabled = busy || !!pending || !office;
  el('retry-action').hidden = !pending;
  el('remote-form').querySelector('button').disabled = busy || !!pending;
  el('remote-reason').disabled = busy || !!pending;
  el('check-out').disabled = busy || !!pending;
  el('retry-action').disabled = busy;
}

async function refreshStatus() {
  const data = await apiFetch('/api/attendance/status'); current = data;
  el('work-date').textContent = data.work_date + ' · Giờ Việt Nam';
  el('attendance-status').textContent = data.morning_leave && data.status==='WORKING_OFFICE'?'Đang làm việc tại văn phòng':data.morning_leave && data.status==='WORKING_REMOTE'?'Đang làm việc Remote':labels[data.status] || data.status;
  el('session-info').textContent = data.open_session ? `Bắt đầu lúc ${clock(data.open_session.start_time)} · ${data.open_session.start_reason || ''}` : '';
  el('day-notice').textContent = data.day_finished ? 'Ngày làm việc đã kết thúc. Có thể bắt đầu lại vào ngày mai.' : data.allowed_actions.length ? '' : 'Hiện chưa có thao tác khả dụng. Ngày làm việc kết thúc lúc 20:00.';
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
    reasonPanel = null;
    leaveKind = null;
    el('remote-reason').value = '';
    el('leave-reason').value = '';
    el('checkout-reason').value = '';
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

function historyDay(day) {
  const section = document.createElement('section'); section.className = 'history-day';
  const modes = ['OFFICE','REMOTE'].filter(mode=>day.sessions.some(session=>session.work_mode===mode));
  const summary = modes.length ? 'GHI NHẬN ĐÃ LÀM VIỆC '+modes.join(' VÀ ')
    : day.status==='FULL_DAY_LEAVE' ? 'NGHỈ CẢ NGÀY'
    : day.status==='MORNING_LEAVE' ? 'NGHỈ BUỔI SÁNG' : 'CHƯA CÓ GHI NHẬN LÀM VIỆC';
  line('h3',day.work_date+' · '+summary,section);
  const entries = [];
  const lunches = day.events.filter(event=>event.event_type==='LUNCH_START');
  const usedLunches = new Set();
  for (const event of day.events) {
    if (['MORNING_LEAVE','FULL_DAY_LEAVE','LEAVE_CANCELLED','DAY_END'].includes(event.event_type)) {
      const label = {MORNING_LEAVE:'Nghỉ buổi sáng',FULL_DAY_LEAVE:'Nghỉ cả ngày',LEAVE_CANCELLED:'Hủy nghỉ',DAY_END:'Hệ thống kết thúc ngày'}[event.event_type];
      entries.push({time:event.event_time,label,reason:event.reason,system:event.source==='SYSTEM'});
    }
  }
  for (const session of day.sessions) {
    const mode = session.work_mode==='OFFICE'?'Office':'Remote';
    entries.push({time:session.start_time,label:'Check-in'+(modes.length>1?' '+mode:'')});
    if (!session.end_time) continue;
    // Lunch closes a session too: show that moment once, as "Nghỉ trưa".
    const lunch = lunches.find(event=>!usedLunches.has(event.id) && Date.parse(event.event_time)===Date.parse(session.end_time));
    if (lunch) usedLunches.add(lunch.id);
    entries.push({time:session.end_time,label:lunch?'Nghỉ trưa':session.end_source==='SYSTEM'?'Hệ thống tự đóng':'Check-out',system:session.end_source==='SYSTEM'});
  }
  const timeline = document.createElement('ol'); timeline.className = 'personal-timeline';
  const formatTime = new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit'});
  entries.sort((a,b)=>Date.parse(a.time)-Date.parse(b.time));
  for (const entry of entries) {
    const item = line('li','',timeline);
    const time = line('time',formatTime.format(new Date(entry.time)),item);
    time.dateTime = entry.time;
    line('span',' · '+entry.label,item);
    if (entry.reason) line('p',entry.reason,item,'muted');
  }
  section.append(timeline);
  if (day.sessions.some(session=>!session.end_time)) line('p','Đang làm việc',section,'history-current');
  if (entries.some(entry=>entry.system)) line('p','Mốc hệ thống đóng, không phải giờ kết thúc thực tế.',section,'system-note');
  return section;
}

async function loadHistory(query, page=1) {
  if (!query || !el('personal-history').open) return;
  const generation=++historyGeneration;
  if (query.from > query.to) throw new Error('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.');
  historyQuery = query; historyPage = page;
  const params = new URLSearchParams({...query,page:String(page),page_size:'20'});
  message('history-message','Đang tải…');
  let data;
  try { data = await apiFetch('/api/attendance/history?'+params); }
  catch (error) { if (generation===historyGeneration && el('personal-history').open) throw error; return; }
  if (generation!==historyGeneration || !el('personal-history').open) return;
  el('history-list').replaceChildren();
  if (!data.items.length) line('p','Chưa có lịch sử trong khoảng ngày này.',el('history-list'),'muted');
  for (const day of data.items) el('history-list').append(historyDay(day));
  el('history-page').textContent = `${page} / ${Math.max(1,Math.ceil(data.total/20))}`;
  el('history-prev').disabled = page<=1; el('history-next').disabled = page*20>=data.total;
  message('history-message','');
}

function openReason(panel) {
  if (!current || busy || pending) return;
  reasonPanel=panel;controls();
  el(panel==='checkout'?'checkout-reason':panel==='remote'?'remote-reason':leaveKind?'leave-reason':'morning-leave').focus();
}
el('choose-remote').addEventListener('click',()=>openReason('remote'));
el('choose-leave').addEventListener('click',()=>openReason('leave'));
el('close-reason').addEventListener('click',()=>{const previous=reasonPanel;reasonPanel=null;controls();el(previous==='checkout'?'check-out':previous==='remote'?'choose-remote':'choose-leave').focus();});
el('remote-form').addEventListener('submit', event => { event.preventDefault(); const action=available(remoteActions); if(action)submit(action,el('remote-reason').value.trim()); });
for(const id of ['morning-leave','full-day-leave']) el(id).addEventListener('click',()=>{
  if(busy || pending)return;
  leaveKind=el(id).value;controls();el('leave-reason').focus();
});
el('leave-form').addEventListener('submit', event => {
  event.preventDefault();const reason=el('leave-reason').value.trim();
  if(!reason){message('message','Vui lòng nhập lý do nghỉ.');el('leave-reason').focus();return;}
  if(current?.allowed_actions.includes(leaveKind))submit(leaveKind,reason);
});
el('start-lunch').addEventListener('click',()=>submit('START_LUNCH'));
el('check-out').addEventListener('click',()=>current?.lunch_taken || current?.morning_leave?submit('CHECK_OUT'):openReason('checkout'));
el('checkout-form').addEventListener('submit',event=>{
  event.preventDefault();
  const reason=el('checkout-reason').value.trim();
  if(!reason){message('message','Vui lòng nhập lý do Check-out sớm.');el('checkout-reason').focus();return;}
  if(current?.allowed_actions.includes('CHECK_OUT') && !current.lunch_taken && !current.morning_leave)submit('CHECK_OUT',reason);
});
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
el('personal-history').addEventListener('toggle',()=>{
  if (el('personal-history').open) loadHistory(historyQuery,historyPage).catch(error=>message('history-message',error.message));
  else historyGeneration++;
});
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
  historyQuery={from:el('history-from').value,to:current.work_date};
  await loadHistory(historyQuery);
} catch (error) { message('message',error.message); }
setInterval(()=>{if(!document.hidden && !busy) refreshAll().catch(error=>message('message',error.message));},60000);
window.addEventListener('focus',()=>{if(!busy) refreshAll().catch(error=>message('message',error.message));});
