import {apiFetch} from './api.js';

export function mountSummary(report,parent,admin=false) {
  const node=(tag,text='',className='',owner=null)=>{
    const el=document.createElement(tag);el.textContent=text;el.className=className;owner?.append(el);return el;
  };
  const root=node('section','','pdf-summary-viewer',parent);
  root.setAttribute('aria-label','Tóm tắt PDF');
  const button=(text,action,owner)=>{
    const el=node('button',text,'secondary',owner);el.type='button';el.addEventListener('click',action);return el;
  };
  const panel=node('div','','pdf-summary-panel',root);
  node('h3','Tóm tắt nội dung','',panel);
  const content=node('p','Đang tải trạng thái…','pdf-summary-text',panel);content.setAttribute('role','status');
  const retry=button('Tạo lại',retrySummary,panel);retry.hidden=true;
  const check=button('Kiểm tra trạng thái',()=>{deadline=Date.now()+120000;readSummary();},panel);check.hidden=true;
  const controller=new AbortController();
  let alive=true,stale=false;
  let timer=null,loadingSummary=false,lastState='',deadline=Date.now()+120000;
  const path=`/api/${admin?'admin/':''}weekly-reports/${encodeURIComponent(report.id)}`;
  const query=`?expected_revision=${encodeURIComponent(report.revision)}`;
  const observer=new MutationObserver(()=>{if(!root.isConnected)close();});
  observer.observe(document.body,{childList:true,subtree:true});
  function close() {
    if(!alive)return;alive=false;clearTimeout(timer);controller.abort();observer.disconnect();
    window.removeEventListener('pagehide',close);document.removeEventListener('visibilitychange',visible);
    root.remove();
  }
  function invalidate() {
    stale=true;clearTimeout(timer);controller.abort();retry.hidden=check.hidden=true;
    content.textContent='PDF đã thay đổi; bản tóm tắt đang mở không còn áp dụng.';
  }
  function schedule() {
    clearTimeout(timer);if(!alive || stale || document.hidden)return;
    if(['NOT_CREATED','PENDING','PROCESSING'].includes(lastState)){
      if(Date.now()<deadline)timer=setTimeout(readSummary,3000);
      else{check.hidden=false;content.textContent+=' Bạn có thể kiểm tra lại trạng thái sau.';}
    }
  }
  async function readSummary() {
    if(!alive || stale || loadingSummary || document.hidden)return;
    loadingSummary=true;clearTimeout(timer);
    try{
      const data=await apiFetch(path+'/summary'+query,{signal:controller.signal});
      if(!alive || stale)return;
      lastState=data.status;content.textContent=data.status==='COMPLETE'?data.summary:data.message;
      retry.hidden=!data.can_retry;check.hidden=true;schedule();
    }catch(error){if(alive && !stale){if(error.code==='STALE_REVISION')invalidate();else{content.textContent=error.message;retry.hidden=true;check.hidden=error.code==='AUTH_REQUIRED';}}}
    finally{loadingSummary=false;}
  }
  async function retrySummary() {
    if(!alive || stale || retry.disabled)return;
    retry.disabled=true;clearTimeout(timer);check.hidden=true;
    try {
      await apiFetch(path+'/summary'+query,{method:'POST',signal:controller.signal});
      deadline=Date.now()+120000;
    }catch(error){if(alive && error.code==='STALE_REVISION'){invalidate();return;}}
    finally{retry.disabled=false;}
    await readSummary();
  }
  function visible(){if(document.hidden)clearTimeout(timer);else if(['NOT_CREATED','PENDING','PROCESSING'].includes(lastState))readSummary();}
  window.addEventListener('pagehide',close);document.addEventListener('visibilitychange',visible);
  readSummary();
}
