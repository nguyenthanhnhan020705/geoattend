// Leaflet owns the editor. The background layer loads independently so
// provider outages never leave the office form locked.
export function attachBackground(map, config, notice, {readOnly=false}={}) {
  const container=map.getContainer();let layer=null;
  const state=(value,text)=>{container.dataset.mapState=value;notice.textContent=readOnly ? (value==='ready'?'Bản đồ Onsite · Vị trí Check-in đã xác minh.':value==='loading'?'Đang tải bản đồ nền…':'Không tải được bản đồ nền. Bấm “Tải lại bản đồ”; danh sách và lịch sử vẫn dùng được.') : text;};
  state('loading','Đang tải bản đồ nền… Bạn vẫn có thể chỉnh sửa vùng.');
  const timer=setTimeout(()=>state('failed','Bản đồ nền quá thời gian chờ. Bấm “Tải lại bản đồ” hoặc kiểm tra kết nối; bản nháp vẫn được giữ.'),15000);
  const ready=()=>{clearTimeout(timer);state('ready','Bấm “Vẽ vùng”, sau đó bấm ít nhất 3 đỉnh quanh văn phòng và chọn “Xem trước”.');};
  const failed=()=>{clearTimeout(timer);state('failed','Không tải được bản đồ nền. Bấm “Tải lại bản đồ” để thử lại; bạn vẫn có thể chỉnh vùng bằng tọa độ.');};
  try {
    if(config.mode==='vector') {
      layer=L.maplibreGL({style:config.style_url,interactive:false,attributionControl:{customAttribution:'<a href="https://openfreemap.org/" target="_blank" rel="noopener noreferrer">OpenFreeMap</a> · © <a href="https://openmaptiles.org/" target="_blank" rel="noopener noreferrer">OpenMapTiles</a> · Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>'}}).addTo(map);
      const renderer=layer.getMaplibreMap();renderer.on('load',ready);renderer.on('error',failed);
    } else {
      const text=document.createElement('span');text.textContent=config.attribution;
      layer=L.tileLayer(config.tile_url,{attribution:text.innerHTML+' · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">Bản quyền bản đồ</a>',maxZoom:19}).addTo(map);
      layer.on('load',()=>{if(container.dataset.mapState!=='failed')ready();});layer.on('tileerror',failed);
    }
  } catch {failed();}
  return ()=>{clearTimeout(timer);if(layer && map.hasLayer(layer))map.removeLayer(layer);};
}
