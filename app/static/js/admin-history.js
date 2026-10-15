import {apiFetch, message} from './api.js';

const el = id => document.getElementById(id);
const dialog = el('employee-history-dialog'), confirmation = el('delete-history-dialog');
const labels = {NOT_STARTED:'Chưa bắt đầu',WORKING_REMOTE:'Đang làm Remote',WORKING_OFFICE:'Đang làm tại văn phòng',CHECKED_OUT:'Đã Check-out',LUNCH_BREAK:'Đang nghỉ trưa',MORNING_LEAVE:'Nghỉ buổi sáng',FULL_DAY_LEAVE:'Nghỉ cả ngày'};
const events = {WORK_START:'Bắt đầu làm việc',WORK_END:'Kết thúc phiên',LUNCH_START:'Nghỉ trưa',MORNING_LEAVE:'Nghỉ buổi sáng',FULL_DAY_LEAVE:'Nghỉ cả ngày',LEAVE_CANCELLED:'Hủy nghỉ',DAY_END:'Kết thúc ngày'};
const clock = value => new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date(value));
let selected=null, page=1, total=0, loading=false, deleting=false, deletion=null, generation=0;

function line(parent,tag,text,className='') {
  const node=document.createElement(tag); node.textContent=text; node.className=className; parent.append(node); return node;
}

function controls() {
  for(const node of el('employee-history-filter').querySelectorAll('input,button'))node.disabled=loading;
  el('employee-history-prev').disabled=loading || page<=1;
  el('employee-history-next').disabled=loading || page*20>=total;
  el('confirm-history-delete').disabled=deleting || !deletion || el('confirm-history-username').value!==deletion.account.username;
  el('confirm-history-username').disabled=deleting;
  el('cancel-history-delete').disabled=deleting;
}

function render(data) {
  const list=el('employee-history-list'); list.replaceChildren();
  if(!data.items.length)line(list,'p','Chưa có lịch sử trong khoảng ngày này.','muted');
  for(const day of data.items) {
    const section=document.createElement('section');section.className='history-day';
    line(section,'h3',`${day.work_date} · ${labels[day.status] || day.status}`);
    for(const session of day.sessions) {
      line(section,'p',`${session.work_mode} · ${clock(session.start_time)} → ${session.end_time?clock(session.end_time):'Đang mở'}`);
      if(session.start_reason)line(section,'p',session.start_reason,'muted');
      if(session.end_reason)line(section,'p',session.end_reason,'muted');
      if(session.end_source==='SYSTEM')line(section,'p','Hệ thống tự đóng lúc 20:00; không phải giờ kết thúc thực tế.','system-note');
      if(session.location?.status==='available')line(section,'p',`GPS đã xác minh · ${session.location.latitude}, ${session.location.longitude} · Sai số ${session.location.accuracy_m} m`,'muted');
      if(session.location?.status==='expired')line(section,'p','Dữ liệu vị trí đã hết hạn lưu. Kết quả xác minh được giữ lại.','muted');
    }
    const timeline=document.createElement('ul');timeline.className='timeline';
    for(const event of day.events)line(timeline,'li',`${clock(event.event_time)} · ${events[event.event_type] || event.event_type}${event.source==='SYSTEM'?' · Hệ thống':''}${event.reason?' · '+event.reason:''}`);
    section.append(timeline);
    const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent='Xóa ngày này';
    const active=['WORKING_OFFICE','WORKING_REMOTE','LUNCH_BREAK'].includes(day.status) || day.sessions.some(session=>!session.end_time);
    button.disabled=active;
    button.addEventListener('click',()=>{
      deletion={account:{...selected},day:{id:day.id,revision:day.revision}};
      el('delete-history-target').textContent=`${selected.full_name} · ${selected.username} · ${day.work_date}`;
      el('confirm-history-username').value=''; message('delete-history-message','');controls();confirmation.showModal();
    });
    section.append(button);
    if(active)line(section,'p','Nhân viên cần Check-out trước khi xóa ngày này.','muted');
    list.append(section);
  }
  el('employee-history-page').textContent=`${page} / ${Math.max(1,Math.ceil(total/20))}`;
}

async function load(requested=1) {
  const account={...selected}, token=++generation;
  const from=el('employee-history-from').value, to=el('employee-history-to').value;
  if(from && to && from>to){message('employee-history-message','Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.');return;}
  loading=true;controls();message('employee-history-message','Đang tải…');
  try {
    const params=new URLSearchParams({page:String(requested),page_size:'20'});
    if(from)params.set('from',from);if(to)params.set('to',to);
    const data=await apiFetch(`/api/admin/users/${account.id}/history?${params}`);
    if(token!==generation)return;
    page=requested;total=data.total;
    if(!data.items.length && requested>1){await load(requested-1);return;}
    render(data);message('employee-history-message','');
  }catch(error){if(token===generation)message('employee-history-message',error.message);}
  finally{if(token===generation){loading=false;controls();}}
}

export function openEmployeeHistory(account) {
  selected={...account};page=1;total=0;
  el('employee-history-name').textContent=`${account.full_name} · ${account.username}`;
  el('employee-history-filter').reset();el('employee-history-list').replaceChildren();
  dialog.showModal();load();
}

el('close-employee-history').addEventListener('click',()=>dialog.close());
dialog.addEventListener('close',()=>{generation++;});
el('employee-history-filter').addEventListener('submit',event=>{event.preventDefault();if(!loading)load();});
el('employee-history-prev').addEventListener('click',()=>load(page-1));
el('employee-history-next').addEventListener('click',()=>load(page+1));
el('confirm-history-username').addEventListener('input',controls);
el('cancel-history-delete').addEventListener('click',()=>confirmation.close());
confirmation.addEventListener('cancel',event=>{if(deleting)event.preventDefault();});
el('delete-history-form').addEventListener('submit',async event=>{
  event.preventDefault();
  if(deleting || !deletion || el('confirm-history-username').value!==deletion.account.username)return;
  const target=deletion;deleting=true;controls();message('delete-history-message','Đang xóa…');
  try {
    await apiFetch(`/api/admin/users/${target.account.id}/history/${target.day.id}`,{method:'DELETE',body:JSON.stringify({expected_revision:target.day.revision,confirm_username:target.account.username})});
    confirmation.close();deletion=null;await load(page);
  }catch(error){message('delete-history-message',error.message);}
  finally{deleting=false;controls();}
});
