import {loadAccount} from './api.js';
import {requestApi,isPages} from './transport.js';
import {downloadBlob,fileBlob} from './file-downloads.js';
import {mountSummary} from './pdf-summary-viewer.js?v=admin-summary-20261024';
import {openPdfPreview} from './pdf-preview.js?v=inline-preview-20261024';

export function reportDate(value) {
  const [year,month,day]=value.split('-');return `${day}/${month}/${year}`;
}
export function reportWeek(start,end) { return `${reportDate(start)} – ${reportDate(end)}`; }
export function reportLine(tag,text,parent,className='') {
  const node=document.createElement(tag);node.textContent=text;node.className=className;parent.append(node);return node;
}
export function reportLinks(report,parent,admin=false,previewParent=parent) {
  const links=document.createElement('div');links.className='report-actions';parent.append(links);
  const url=`/api/${admin?'admin/':''}weekly-reports/${encodeURIComponent(report.id)}/file`;
  const download=reportLine('a','Tải PDF',links);download.href=url+'?download=true';
  const view=reportLine('a','Xem trước PDF',links);view.href='#';view.setAttribute('aria-expanded','false');
  let closePreview=null;
  view.addEventListener('click',event=>{
    event.preventDefault();
    if(closePreview){closePreview();return;}
    view.setAttribute('aria-expanded','true');
    closePreview=openPdfPreview(report,previewParent,admin,()=>{closePreview=null;view.setAttribute('aria-expanded','false');});
  });
  if(isPages) {
    const notice=reportLine('p','',links,'message');notice.setAttribute('role','status');
    for(const link of [download]) {
      link.href='#';link.removeAttribute('target');
      let busy=false;
      link.addEventListener('click',async event=>{
        event.preventDefault();if(busy)return;busy=true;
        link.setAttribute('aria-disabled','true');notice.textContent='Đang tải PDF…';
        try {
          const blob=await fetchReportFile(report.id,{admin,download:true});
          downloadBlob(blob,report.filename);notice.textContent='';
        } catch(error) {notice.textContent=error.message;}
        finally {busy=false;link.removeAttribute('aria-disabled');}
      });
    }
  }
}

export async function fetchReportFile(reportId,{admin=false,download=false}={}) {
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),30000);
  try {
    const response=await requestApi(`/api/${admin?'admin/':''}weekly-reports/${encodeURIComponent(reportId)}/file${download?'?download=true':''}`,{signal:controller.signal});
    return await fileBlob(response,'application/pdf');
  } catch(error) {
    if(controller.signal.aborted)throw new Error('Tải PDF quá thời gian chờ. Vui lòng thử lại.');
    throw error;
  } finally {clearTimeout(timer);}
}
export function reportDetails(report,parent,admin=false) {
  const layout=admin?reportLine('div','',parent,'report-summary-layout'):parent;
  const details=admin?reportLine('div','',layout,'report-file-details'):layout;
  reportLine('p',report.filename,details,'report-filename');
  reportLine('p',`${(report.size_bytes/1_000_000).toLocaleString('vi-VN',{maximumFractionDigits:2})} MB · Nộp lúc ${new Date(report.submitted_at).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'})} (giờ Việt Nam)`,details,'muted');
  reportLinks(report,details,admin,parent);
  if(admin)mountSummary(report,layout,true);
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
    response=await requestApi(`/api/weekly-reports/${pending.week_start}?${params}`,{
      method:'PUT',headers:{'Content-Type':'application/pdf','X-CSRF-Token':account.csrf_token,'X-Report-Filename':encodeURIComponent(pending.filename)},
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
