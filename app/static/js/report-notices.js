import {apiFetch} from './api.js';
import {reportLine,reportWeek} from './reports-api.js';

let generation=0;
export async function refreshReportNotices() {
  const token=++generation;
  const data=await apiFetch('/api/weekly-reports/status');
  if(token!==generation)return null;
  const root=document.querySelector('[data-report-notices]');
  root.replaceChildren();
  for(const notice of data.notices) {
    const box=reportLine('div','',root,'report-notice');
    reportLine('strong',notice.message,box);
    reportLine('p','Tuần '+reportWeek(notice.week_start,notice.week_end),box,'muted');
  }
  return data;
}

export function startReportNotices(onStatus=()=>{}) {
  let timer,stopped=false;
  const root=document.querySelector('[data-report-notices]');
  const errorNode=document.getElementById('notice-error');
  async function refresh() {
    if(stopped || document.hidden)return;
    clearTimeout(timer);
    let delay=60000;
    try {
      const data=await refreshReportNotices();
      if(data){
        if(errorNode)errorNode.textContent='';
        onStatus(data);
        const server=Date.parse(data.server_time);
        const untilMidnight=86400000-((server+7*3600000)%86400000);
        delay=Math.min(60000,Math.max(1000,untilMidnight+100));
      }
    }catch(error) {
      if(errorNode)errorNode.textContent='Chưa tải được thông tin báo cáo tuần: '+error.message;
      root.dataset.stale='true';
    }finally{if(!stopped)timer=setTimeout(refresh,delay);}
  }
  const visible=()=>{if(!document.hidden)refresh();else clearTimeout(timer);};
  document.addEventListener('visibilitychange',visible);
  window.addEventListener('focus',refresh);window.addEventListener('pageshow',refresh);
  window.addEventListener('pagehide',()=>clearTimeout(timer));
  refresh();
  return ()=>{stopped=true;clearTimeout(timer);document.removeEventListener('visibilitychange',visible);window.removeEventListener('focus',refresh);window.removeEventListener('pageshow',refresh);};
}
