import {apiFetch,bindLogout} from './api.js';
import {openEmployeeHistory} from './admin-history.js';
import {attachBackground} from './office-map-background.js';

const el=id=>document.getElementById(id);
const labels={NOT_STARTED:'Chưa bắt đầu',WORKING_OFFICE:'Đang làm tại văn phòng',WORKING_REMOTE:'Đang làm Remote',LUNCH_BREAK:'Đang nghỉ trưa',MORNING_LEAVE:'Nghỉ buổi sáng',FULL_DAY_LEAVE:'Nghỉ cả ngày',CHECKED_OUT:'Đã Check-out'};
const time=value=>new Intl.DateTimeFormat('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour:'2-digit',minute:'2-digit',second:'2-digit'}).format(new Date(value));
let map,layers,detach,lastData,backgroundKey;

function node(tag,text,parent) {
  const child=document.createElement(tag);child.textContent=text;
  if(parent)parent.append(child);return child;
}
function historyButton(item,parent) {
  const button=node('button','Lịch sử',parent);button.type='button';button.className='secondary';
  button.addEventListener('click',()=>openEmployeeHistory(item));
}
function startBackground(data) {
  if(!map)return;
  detach?.();
  detach=attachBackground(map,data.office.map,el('tile-message'),{readOnly:true});
  backgroundKey=JSON.stringify(data.office.map);
}
function renderMap(data) {
  try {
    if(!map){
      map=L.map('onsite-map').setView([10.77,106.7],11);
      layers=L.layerGroup().addTo(map);
    }
    if(backgroundKey!==JSON.stringify(data.office.map))startBackground(data);
    layers.clearLayers();
    const bounds=[];
    if(data.office.geom){
      const fence=L.geoJSON(data.office.geom,{style:{color:'#18786a',weight:2}}).addTo(layers);
      bounds.push(fence.getBounds());
    }
    for(const item of data.onsite){
      const gps=item.location;
      if(gps?.status!=='available' || !Number.isFinite(gps.latitude) || !Number.isFinite(gps.longitude))continue;
      const icon=node('span','●');icon.className='onsite-dot';
      const marker=L.marker([gps.latitude,gps.longitude],{icon:L.divIcon({html:icon,className:'onsite-marker',iconSize:[24,24]}),title:item.full_name}).addTo(layers);
      const name=node('span',item.full_name);
      marker.bindTooltip(name,{permanent:true,direction:'top'});
      const popup=node('div','');
      node('strong',item.full_name,popup);node('p',labels[item.status],popup);
      node('p',`Check-in: ${time(item.open_session.start_time)}`,popup);
      node('p',`GPS đã xác minh · Sai số ${gps.accuracy_m ?? '—'} m`,popup);
      historyButton(item,popup);marker.bindPopup(popup);
      bounds.push(L.latLngBounds([gps.latitude,gps.longitude],[gps.latitude,gps.longitude]));
    }
    if(bounds.length && !el('onsite-map').dataset.fitted){
      const combined=bounds[0];for(const bound of bounds.slice(1))combined.extend(bound);
      map.fitBounds(combined,{padding:[28,28],maxZoom:17});el('onsite-map').dataset.fitted='true';
    }
  }catch{el('tile-message').textContent='Không tải được bản đồ. Danh sách và lịch sử vẫn dùng được. Bấm Tải lại bản đồ để thử lại.';}
}
function render(data) {
  lastData=data;
  el('total-users').textContent=data.total_users;
  el('snapshot-time').textContent=`Ngày ${data.work_date} · Cập nhật ${time(data.as_of)} (giờ Việt Nam)`;
  el('status-cards').replaceChildren();
  for(const [status,label] of Object.entries(labels)){
    const card=node('div','',el('status-cards'));card.className='status-card';card.dataset.status=status;
    node('span',label,card);node('strong',String(data.counts[status]),card).className='status-count';
  }
  el('dashboard-users').replaceChildren();
  for(const item of data.items){
    const row=node('li','',el('dashboard-users'));
    const info=node('div','',row);info.className='user-info';
    node('strong',item.full_name,info);node('span',`${item.username} · ${labels[item.status]}`,info);
    if(!item.is_active)node('span','Tài khoản bị khóa',info);
    if(item.open_session){
      node('span',`Check-in: ${time(item.open_session.start_time)}`,info);
      if(item.open_session.start_reason)node('span',item.open_session.start_reason,info);
    }
    const onsite=data.onsite.find(person=>person.id===item.id);
    if(onsite?.location?.status==='expired')node('span','Dữ liệu vị trí đã hết hạn lưu',info);
    else if(item.status==='WORKING_OFFICE' && !onsite?.location)node('span','Không có dữ liệu vị trí để đặt Marker',info);
    historyButton(item,row);
  }
  el('empty-users').hidden=data.items.length>0;
  renderMap(data);
}
async function load() {
  try{render(await apiFetch('/api/admin/dashboard'));el('dashboard-message').textContent='';}
  catch(error){el('dashboard-message').textContent=error.message;}
}
el('reload-dashboard').addEventListener('click',load);
el('retry-map').addEventListener('click',()=>{if(lastData){startBackground(lastData);renderMap(lastData);}});
bindLogout('dashboard-message');
load();
