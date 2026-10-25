import {requestApi} from './transport.js';

let closeActive=null;
export function openPdfPreview(report,parent,admin=false,onClose=()=>{}) {
  closeActive?.();
  const node=(tag,text='',className='',owner=null)=>{
    const element=document.createElement(tag);element.textContent=text;element.className=className;owner?.append(element);return element;
  };
  const root=node('section','','report-pdf-preview',parent);root.setAttribute('aria-label','Xem trước PDF');
  const toolbar=node('div','','report-pdf-toolbar',root);
  const button=(text,action)=>{const element=node('button',text,'secondary',toolbar);element.type='button';element.addEventListener('click',action);return element;};
  const previous=button('Trang trước PDF',()=>render(currentPage-1));
  const next=button('Trang sau PDF',()=>render(currentPage+1));
  button('Đóng xem trước',close);
  const status=node('p','Đang tải PDF…','report-pdf-status',root);status.setAttribute('role','status');
  const scroll=node('div','','report-pdf-scroll',root);
  const canvas=node('canvas','','',scroll);canvas.setAttribute('aria-label','Trang PDF gốc');canvas.width=canvas.height=0;
  const controller=new AbortController();
  let alive=true,stale=false,timedOut=false,task=null,pdf=null,renderTask=null,currentPage=1,generation=0;
  let timer=null;
  previous.disabled=next.disabled=true;
  const observer=new MutationObserver(()=>{if(!root.isConnected)close();});
  observer.observe(document.body,{childList:true,subtree:true});
  function close() {
    if(!alive)return;alive=false;clearTimeout(timer);controller.abort();observer.disconnect();
    generation++;renderTask?.cancel();task?.destroy()?.catch(()=>{});
    window.removeEventListener('pagehide',close);canvas.width=canvas.height=0;root.remove();
    if(closeActive===close)closeActive=null;onClose();
  }
  async function render(number) {
    if(!alive || stale || !pdf || number<1 || number>pdf.numPages)return;
    const token=++generation,oldRender=renderTask;oldRender?.cancel();
    try {
      if(oldRender){try{await oldRender.promise;}catch{}}
      const page=await pdf.getPage(number);if(!alive || token!==generation)return;
      const original=page.getViewport({scale:1});
      const width=Math.max(100,Math.min(scroll.clientWidth,900));
      const scale=Math.min(width/original.width,Math.sqrt(4_000_000/(original.width*original.height)));
      const viewport=page.getViewport({scale});canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
      renderTask=page.render({canvasContext:canvas.getContext('2d'),viewport});
      await renderTask.promise;if(!alive || token!==generation)return;
      currentPage=number;canvas.dataset.page=String(number);
      previous.disabled=number<=1;next.disabled=number>=pdf.numPages;status.textContent=`Trang ${number} / ${pdf.numPages}`;
    }catch(error){if(alive && token===generation && error.name!=='RenderingCancelledException')status.textContent='Không thể hiển thị trang PDF. Bạn vẫn có thể tải file.';}
  }
  async function load() {
    timer=setTimeout(()=>{timedOut=true;controller.abort();},30000);
    try {
      const path=`/api/${admin?'admin/':''}weekly-reports/${encodeURIComponent(report.id)}/file?expected_revision=${encodeURIComponent(report.revision)}`;
      const response=await requestApi(path,{signal:controller.signal});
      if(!response.ok){
        let error;try{error=await response.json();}catch{}
        if(error?.code==='STALE_REVISION'){
          stale=true;status.textContent='PDF đã được thay thế. Vui lòng tải lại danh sách báo cáo.';return;
        }
        throw new Error('PDF_UNAVAILABLE');
      }
      if(!(response.headers.get('Content-Type')||'').startsWith('application/pdf'))throw new Error('PDF_UNAVAILABLE');
      const reader=response.body.getReader(),parts=[];let size=0;
      while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;
        if(size>10_000_000){await reader.cancel();throw new Error('PDF_TOO_LARGE');}parts.push(value);}
      clearTimeout(timer);if(!alive)return;
      const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}
      const pdfjs=await import('../vendor/pdfjs/pdf.mjs');if(!alive)return;
      pdfjs.GlobalWorkerOptions.workerSrc=new URL('../vendor/pdfjs/pdf.worker.mjs',import.meta.url).href;
      const vendor=new URL('../vendor/pdfjs/',import.meta.url).href;
      task=pdfjs.getDocument({data:bytes,isEvalSupported:false,useWasm:false,disableFontFace:true,
        cMapUrl:vendor+'cmaps/',cMapPacked:true,standardFontDataUrl:vendor+'standard_fonts/',
        maxImageSize:8_000_000,canvasMaxAreaInBytes:16_000_000});
      pdf=await task.promise;if(alive)await render(1);
    }catch(error){
      if(alive && !stale)status.textContent=timedOut?'Tải PDF quá thời gian chờ. Vui lòng đóng và mở lại.':error.name==='PasswordException'?'PDF có mật khẩu. Bạn có thể tải file để mở riêng.':'Không thể hiển thị PDF. Bạn vẫn có thể tải file.';
    }finally{clearTimeout(timer);}
  }
  window.addEventListener('pagehide',close);closeActive=close;load();return close;
}
