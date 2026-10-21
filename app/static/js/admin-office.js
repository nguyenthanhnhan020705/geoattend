import {loadAccount,apiFetch,bindLogout,message} from './api.js';
import {requirePageAccount} from './page-session.js';
await requirePageAccount('ADMIN');
import {attachBackground} from './office-map-background.js';
bindLogout();
const el=id=>document.getElementById(id);
let revision=0,rings=[[]],active=0,map=null,polygon=null,markers=[],dirty=false,previewed=false,busy=false;
let backgroundConfig=null,detachBackground=null;

function setBusy(value) {
  busy=value;el('office-form').setAttribute('aria-busy',String(value));
  for(const node of el('office-form').elements)node.disabled=value;
  el('reload-office').disabled=value;
  el('draw-office').disabled=value || !map;
  el('retry-map').disabled=value || !map;
  for(const marker of markers){if(value)marker.dragging.disable();else marker.dragging.enable();}
  el('save-office').disabled=value || !previewed;
}

function markChanged() {
  dirty=true;previewed=false;el('save-office').disabled=true;
  el('draft-state').textContent='Có thay đổi chưa lưu. Xem trước rồi lưu để áp dụng.';
}

function draw() {
  if (!map) return;
  if (polygon) map.removeLayer(polygon);
  for (const marker of markers) map.removeLayer(marker);
  markers=[];
  const coords=rings.map(ring=>ring.map(([lon,lat])=>[lat,lon]));
  if (coords[0].length>=3) polygon=L.polygon(coords.filter(r=>r.length>=3),{color:'#18786a',weight:3}).addTo(map);
  rings[active].forEach(([lon,lat],index)=>{
    const marker=L.marker([lat,lon],{draggable:true,icon:L.divIcon({className:'vertex-marker',html:String(index+1),iconSize:[26,26],iconAnchor:[13,13]})}).addTo(map);
    marker.on('dragend',()=>{const point=marker.getLatLng();rings[active][index]=[point.lng,point.lat];markChanged();render();});markers.push(marker);
  });
}

function render() {
  el('ring-select').replaceChildren();
  rings.forEach((_,index)=>{const option=document.createElement('option');option.value=String(index);option.textContent=index===0?'Ranh giới ngoài':`Vùng loại trừ ${index}`;el('ring-select').append(option);});
  el('ring-select').value=String(active);el('remove-hole').hidden=active===0;
  el('vertices-list').replaceChildren();
  rings[active].forEach(([lon,lat],index)=>{
    const row=document.createElement('li');const fields=document.createElement('div');fields.className='vertex-fields';
    for (const [label,value,axis,min,max] of [['Vĩ độ',lat,1,-90,90],['Kinh độ',lon,0,-180,180]]) {
      const wrap=document.createElement('label');wrap.textContent=label+' '+(index+1);
      const input=document.createElement('input');input.type='number';input.step='any';input.min=String(min);input.max=String(max);input.value=String(value);input.required=true;
      input.addEventListener('change',()=>{if(!input.validity.valid || !Number.isFinite(Number(input.value)))return;rings[active][index][axis]=Number(input.value);markChanged();draw();});wrap.append(input);fields.append(wrap);
    }
    const remove=document.createElement('button');remove.type='button';remove.className='text-button';remove.textContent='Xóa';remove.setAttribute('aria-label','Xóa đỉnh '+(index+1));
    remove.addEventListener('click',()=>{rings[active].splice(index,1);markChanged();render();});row.append(fields,remove);el('vertices-list').append(row);
  });draw();
}

function geometry() {
  if(rings.some(r=>r.length<3))throw new Error('Mỗi đường biên cần ít nhất 3 đỉnh.');
  return {type:'Polygon',coordinates:rings.map(r=>[...r.map(p=>[...p]),[...r[0]]])};
}

async function loadOffice() {
  setBusy(true);
  try {
  const data=await apiFetch('/api/admin/office');revision=data.revision;
  el('office-name').value=data.name;el('office-address').value=data.address;
  rings=data.geom?data.geom.coordinates.map(r=>r.slice(0,-1).map(p=>[...p])):[[]];active=0;dirty=false;previewed=false;
  el('office-revision').textContent='Phiên bản '+revision;el('save-office').disabled=true;
  el('draft-state').textContent=data.geom?'Đang hiển thị vùng đã lưu.':'Chưa cấu hình. Thêm ít nhất 3 đỉnh để tạo vùng.';
  if(!map) {
    map=L.map('office-map').setView([10.7769,106.7009],15);
    backgroundConfig=data.map;detachBackground=attachBackground(map,backgroundConfig,el('tile-message'));
    map.on('click',event=>{if(busy)return;rings[active].push([event.latlng.lng,event.latlng.lat]);markChanged();render();});
  }
  render();if(rings[0].length>=3)map.fitBounds(L.latLngBounds(rings[0].map(([lon,lat])=>[lat,lon])),{padding:[30,30],maxZoom:18});
  } finally {setBusy(false);}
}

el('ring-select').addEventListener('change',()=>{active=Number(el('ring-select').value);render();});
el('add-hole').addEventListener('click',()=>{rings.push([]);active=rings.length-1;markChanged();render();});
el('remove-hole').addEventListener('click',()=>{if(active===0)return;rings.splice(active,1);active=0;markChanged();render();});
el('add-vertex').addEventListener('click',()=>{
  const lat=Number(el('new-latitude').value),lon=Number(el('new-longitude').value);
  if(!el('new-latitude').value || !el('new-longitude').value || !Number.isFinite(lat) || !Number.isFinite(lon) || lat< -90 || lat>90 || lon< -180 || lon>180){message('message','Nhập vĩ độ và kinh độ hợp lệ.');return;}
  rings[active].push([lon,lat]);markChanged();render();if(rings[active].length===1 && map)map.setView([lat,lon],17);message('message','');
});
el('draw-office').addEventListener('click',()=>{
  if(busy || !map)return;
  if(rings.some(r=>r.length) && !confirm('Vẽ vùng mới sẽ bỏ vùng đang chỉnh sửa. Tiếp tục?'))return;
  rings=[[]];active=0;markChanged();render();message('message','Bấm ít nhất 3 đỉnh quanh văn phòng trên bản đồ, sau đó chọn “Xem trước”.',true);
});
el('retry-map').addEventListener('click',()=>{if(busy || !map || !backgroundConfig)return;if(detachBackground)detachBackground();detachBackground=attachBackground(map,backgroundConfig,el('tile-message'));});
el('office-name').addEventListener('input',markChanged);el('office-address').addEventListener('input',markChanged);
el('preview-office').addEventListener('click',()=>{try{geometry();draw();if(polygon)map.fitBounds(polygon.getBounds(),{padding:[30,30],maxZoom:18});previewed=true;el('save-office').disabled=false;message('message','Đang xem trước. Bấm lưu để Backend kiểm tra và áp dụng.',true);}catch(error){message('message',error.message);}});
el('reload-office').addEventListener('click',async()=>{if(busy)return;if(dirty && !confirm('Bỏ thay đổi chưa lưu và tải lại vùng mới nhất?'))return;try{await loadOffice();message('message','Đã tải bản đã lưu.',true);}catch(error){el('office-revision').textContent='Chưa tải được';message('message',error.message);}});
el('office-form').addEventListener('submit',async event=>{
  event.preventDefault();if(busy || !previewed)return;setBusy(true);
  try{
    const saved=await apiFetch('/api/admin/office',{method:'PUT',body:JSON.stringify({name:el('office-name').value.trim(),address:el('office-address').value.trim(),geom:geometry(),expected_revision:revision})});
    revision=saved.revision;dirty=false;previewed=false;el('office-revision').textContent='Phiên bản '+revision;el('draft-state').textContent='Vùng đã lưu. Chỉ ảnh hưởng những lần Check-in Office tiếp theo.';message('message','Đã lưu vùng văn phòng.',true);
  }catch(error){message('message',error.message);}
  finally{setBusy(false);}
});
setBusy(true);
try{await loadAccount();await loadOffice();}catch(error){el('office-revision').textContent='Chưa tải được';message('message',error.message);}finally{setBusy(false);}
