import {apiFetch,bindLogout,message} from './api.js';
import {requirePageAccount} from './page-session.js';
await requirePageAccount('ADMIN');
import {reportWeek,reportLine,reportDetails} from './reports-api.js';
const el=id=>document.getElementById(id);
const labels={SUBMITTED:'Đã nộp',PENDING:'Chưa nộp',OVERDUE:'Quá hạn chưa nộp',NOT_APPLICABLE:'Không áp dụng'};
let page=1,generation=0;
function monday(value){const day=new Date(value+'T00:00:00Z');day.setUTCDate(day.getUTCDate()-(day.getUTCDay()+6)%7);return day.toISOString().slice(0,10);}
async function load() {
  const token=++generation;
  const params=new URLSearchParams({page:String(page),page_size:'20'});
  if(el('filter-week').value)params.set('week_start',monday(el('filter-week').value));
  if(el('filter-user').value)params.set('user_id',el('filter-user').value);
  message('report-message','Đang tải…');
  try{
    const data=await apiFetch('/api/admin/weekly-reports?'+params);
    if(token!==generation)return;
    el('filter-week').value=data.week_start;
    el('admin-report-week').textContent='Tuần '+reportWeek(data.week_start,data.week_end);
    el('reports-list').replaceChildren();
    for(const item of data.items){
      const row=reportLine('li','',el('reports-list'));
      reportLine('h3',`${item.full_name} · ${item.username}`,row);
      if(!item.is_active)reportLine('p','Tài khoản bị khóa',row,'muted');
      reportLine('span',labels[item.status],row,'pill');
      if(item.report)reportDetails(item.report,row,true);
    }
    el('reports-page').textContent=`${data.page} / ${Math.max(1,Math.ceil(data.total/20))}`;
    el('reports-prev').disabled=data.page<=1;el('reports-next').disabled=data.page*20>=data.total;
    message('report-message',data.total?'':'Không có nhân viên trong bộ lọc này.');
  }catch(error){if(token===generation)message('report-message',error.message);}
}
el('report-filter').addEventListener('submit',event=>{event.preventDefault();page=1;load();});
el('reports-prev').addEventListener('click',()=>{if(page>1){page--;load();}});
el('reports-next').addEventListener('click',()=>{page++;load();});
bindLogout('report-message');
try{
  const users=await apiFetch('/api/admin/users');
  for(const user of users.items){const option=reportLine('option',`${user.full_name} · ${user.username}`,el('filter-user'));option.value=user.id;}
  await load();
}catch(error){message('report-message',error.message);}
