// Authenticated files are fetched as blobs; credentials never enter a URL.
export function downloadBlob(blob, filename) {
  const url=URL.createObjectURL(blob), link=document.createElement('a');
  link.href=url; link.download=filename;
  document.body.append(link); link.click(); link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),60000);
}

export function openPdf(blob, reserved=null) {
  const popup=reserved;
  if (!popup || popup.closed) { downloadBlob(blob,'weekly-report.pdf'); return; }
  const url=URL.createObjectURL(blob);
  popup.opener=null;
  popup.location.replace(url);
  const timer=setInterval(()=>{if(popup.closed){URL.revokeObjectURL(url);clearInterval(timer);}},1000);
  window.addEventListener('pagehide',()=>{URL.revokeObjectURL(url);clearInterval(timer);},{once:true});
}

export async function fileBlob(response, expectedType) {
  if (!response.ok) {
    let data;
    try { data=await response.json(); } catch { /* proxy error may not be JSON */ }
    throw new Error(data?.message || 'Không thể tải file. Vui lòng thử lại.');
  }
  if (!(response.headers.get('Content-Type') || '').toLowerCase().startsWith(expectedType)) {
    throw new Error('Máy chủ không trả về file hợp lệ. Vui lòng thử lại.');
  }
  return response.blob();
}
