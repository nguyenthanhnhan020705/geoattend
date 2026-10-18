import {apiFetch,loadAccount,bindLogout,message} from './api.js';
import {uploadReport,reportWeek,reportLine,reportDetails} from './reports-api.js';
import {refreshReportNotices,startReportNotices} from './report-notices.js';

const el=id=>document.getElementById(id);
let current=null,accountId=null,pending=null,busy=false,page=1,historyGeneration=0;
function render(data) {
  if(current && data.week_start!==current.week_start && !pending) {
    el('report-file').value='';el('selected-file').textContent='';
    message('report-message','Đã sang tuần mới. Hãy chọn lại file cho tuần đang hiển thị.');
  }
  current=data;
  el('report-week').textContent='Tuần '+reportWeek(data.week_start,data.week_end);
  el('report-deadline').textContent='Hạn nộp: hết Chủ nhật '+reportWeek(data.week_start,data.week_end).split(' – ')[1]+' (giờ Việt Nam).';
  el('current-report').replaceChildren();
  if(data.report){reportLine('strong','Đã nộp báo cáo tuần này',el('current-report'));reportDetails(data.report,el('current-report'));}
  else reportLine('p','Bạn chưa nộp báo cáo tuần này.',el('current-report'),'muted');
  controls();
}
function controls() {
  el('submit-report').disabled=busy || !!pending || !current || !accountId;
  el('submit-report').textContent=current?.report?'Thay thế báo cáo':'Nộp báo cáo';
  el('report-file').disabled=busy || !!pending;
  el('retry-report').hidden=!pending;el('retry-report').disabled=busy;
  el('report-form').setAttribute('aria-busy',String(busy));
}
async function history() {
  const token=++historyGeneration;
  try{
    const data=await apiFetch(`/api/weekly-reports?page=${page}&page_size=20`);
    if(token!==historyGeneration)return;
    el('report-history').replaceChildren();
    for(const item of data.items){const row=reportLine('li','',el('report-history'));reportLine('h3','Tuần '+reportWeek(item.week_start,item.week_end),row);reportDetails(item,row);}
    el('history-page').textContent=`${data.page} / ${Math.max(1,Math.ceil(data.total/20))}`;
    el('history-prev').disabled=data.page<=1;el('history-next').disabled=data.page*20>=data.total;
    message('history-message',data.total?'':'Chưa có báo cáo đã nộp.');
  }catch(error){if(token===historyGeneration)message('history-message',error.message);}
}
async function refresh() {const data=await refreshReportNotices();if(data)render(data);await history();}
async function send() {
  if(!pending || busy)return;
  busy=true;controls();message('report-message','Đang gửi báo cáo…');
  try{
    await uploadReport(pending);
    pending=null;el('report-file').value='';el('selected-file').textContent='';
    message('report-message','Đã nộp báo cáo thành công.',true);
  }catch(error){
    if(error.code){
      pending=null;el('report-file').value='';el('selected-file').textContent='';
      if(error.code==='ACCOUNT_CHANGED')accountId=null;
    }
    message('report-message',error.message);
  }
  finally{busy=false;controls();}
  try{await refresh();}catch(error){message('notice-error',error.message);}
}
el('report-file').addEventListener('change',()=>{
  const file=el('report-file').files[0];
  el('selected-file').textContent=file?`${file.name} · ${(file.size/1_000_000).toLocaleString('vi-VN',{maximumFractionDigits:2})} MB`:'';
});
el('report-form').addEventListener('submit',async event=>{
  event.preventDefault();if(busy || pending || !current)return;
  const file=el('report-file').files[0];
  if(!file || !/\.pdf$/i.test(file.name) || !file.size || file.size>current.max_bytes){message('report-message','Vui lòng chọn một file PDF hợp lệ, tối đa 10 MB.');return;}
  const intended=current;
  busy=true;controls();
  try{
    const data=await refreshReportNotices();if(!data)return;
    render(data);
    if(data.week_start!==intended.week_start || (data.report?.revision || 0)!==(intended.report?.revision || 0)) {
      message('report-message','Tuần hoặc báo cáo đã thay đổi. Hãy kiểm tra thông tin mới rồi nộp lại.');return;
    }
    if(data.report && !confirm('Thay thế PDF đã nộp của tuần này bằng file mới?'))return;
    pending={accountId,week_start:data.week_start,expected_revision:data.report?.revision || 0,request_id:crypto.randomUUID(),filename:file.name,file};
  }catch(error){message('report-message',error.message);}
  finally{busy=false;controls();}
  await send();
});
el('retry-report').addEventListener('click',send);
el('reload-reports').addEventListener('click',()=>refresh().catch(e=>message('notice-error',e.message)));
el('history-prev').addEventListener('click',()=>{if(page>1){page--;history();}});
el('history-next').addEventListener('click',()=>{page++;history();});
bindLogout('report-message');
try{const account=await loadAccount();accountId=account.id;startReportNotices(render);await history();}
catch(error){message('report-message',error.message);}
