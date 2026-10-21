import {loadAccount} from './api.js';

export function reportDate(value) {
  const [year,month,day]=value.split('-');return `${day}/${month}/${year}`;
}
export function reportWeek(start,end) { return `${reportDate(start)} – ${reportDate(end)}`; }
export function reportLine(tag,text,parent,className='') {
  const node=document.createElement(tag);node.textContent=text;node.className=className;parent.append(node);return node;
}
export function reportLinks(report,parent,admin=false) {
  const links=document.createElement('div');links.className='report-actions';parent.append(links);
  const url=`/api/${admin?'admin/':''}weekly-reports/${encodeURIComponent(report.id)}/file`;
  const view=reportLine('a','Xem PDF',links);view.href=url;view.target='_blank';view.rel='noopener';
  const download=reportLine('a','Tải PDF',links);download.href=url+'?download=true';
}
export function reportDetails(report,parent,admin=false) {
  reportLine('p',report.filename,parent,'report-filename');
  reportLine('p',`${(report.size_bytes/1_000_000).toLocaleString('vi-VN',{maximumFractionDigits:2})} MB · Nộp lúc ${new Date(report.submitted_at).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'})} (giờ Việt Nam)`,parent,'muted');
  reportLinks(report,parent,admin);
}

export async function uploadReport(pending) {
  const account=await loadAccount();
  if(account.id!==pending.accountId || account.role!=='USER') {
    const error=new Error('Tài khoản đã thay đổi. Vui lòng tải lại trang sau khi đăng nhập đúng tài khoản.');
    error.code='ACCOUNT_CHANGED';throw error;
  }
  const params=new URLSearchParams({request_id:pending.request_id,expected_revision:String(pending.expected_revision)});
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),60000);
  let response,data;
  try {
    response=await fetch(`/api/weekly-reports/${pending.week_start}?${params}`,{
      method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/pdf','X-CSRF-Token':account.csrf_token,'X-Report-Filename':encodeURIComponent(pending.filename)},
      body:pending.file,signal:controller.signal,
    });
    data=await response.json();
  }catch {
    throw new Error('Chưa xác nhận được kết quả nộp. Giữ trang này và bấm Gửi lại báo cáo để kiểm tra an toàn.');
  }finally{clearTimeout(timer);}
  if(!response.ok) {
    const error=new Error(data.message || 'Không thể nộp báo cáo.');
    if(response.status<500)error.code=data.code;
    throw error;
  }
  return data;
}
