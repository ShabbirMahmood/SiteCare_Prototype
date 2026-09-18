import {appNow,state,t,esc,$,$$,api,icon,toast,fmt,shortTime,dayKey,jstInput,toISO,countdown,openDialog,field,input,check,badge,statusLabel,typeLabel,reasonLabel,appointmentBadge} from './ui.js';

const clone = value => JSON.parse(JSON.stringify(value));
const radialDistance = (a,b) => Math.hypot(a.x-b.x,a.y-b.y);
function toImage(p,a){const r=a.angle*Math.PI/180;return{x:a.cx+a.ppm*(p.x*Math.cos(r)-p.y*Math.sin(r)),y:a.cy+a.ppm*(p.x*Math.sin(r)+p.y*Math.cos(r))};}
function fromImage(p,a){const r=a.angle*Math.PI/180,dx=p.x-a.cx,dy=p.y-a.cy;return{x:(dx*Math.cos(r)+dy*Math.sin(r))/a.ppm,y:(-dx*Math.sin(r)+dy*Math.cos(r))/a.ppm};}
const colors={eligible:['#309878','#72caa3'],resting:['#356fbd','#78a9ed'],blocked:['#bc4a57','#e99aa2'],unverified:['#7f9299','#c4cfd4']};

export async function mountWorkspace(root,patientId,callbacks){
  const w={root,pid:patientId,closed:false,data:null,photo:null,a:null,sites:[],dirty:false,layoutDirty:false,mode:'inspect',
    view:{x:-18,y:-14,w:36,h:28},selected:null,point:null,assessment:null,tab:'sites',calPoints:[],draft:null,
    showHalos:true,photoOpacity:1,conflict:false,offline:false,clockRevision:state.clock?.revision};
  const serverNow=appNow;
  const eventApplies=e=>new Date(e.occurred_at).getTime()<=serverNow()&&(!e.voided_at||new Date(e.voided_at).getTime()>serverNow());
  const alertActive=a=>new Date(a.observed_at).getTime()<=serverNow()&&(!a.resolved_at||new Date(a.resolved_at).getTime()>serverNow());
  const isLatest=()=>w.photo&&w.photo.id===w.data.current_photo_id;
  const fresh=()=>w.photo&&serverNow()-new Date(w.photo.captured_at).getTime()<=24*3600000&&serverNow()>=new Date(w.photo.captured_at).getTime();
  const verified=()=>w.photo?.verified&&!w.dirty&&!w.layoutDirty;
  const editable=()=>w.photo&&isLatest()&&!w.photo.locked;
  const clearReady=()=>w.clockRevision===state.clock?.revision&&verified()&&fresh()&&isLatest()&&w.data.patient.active&&!w.conflict;
  const actualDone=()=>w.data.events.some(e=>e.photo_id===w.photo?.id&&e.kind==='procedure'&&!e.voided_at);
  const selectedState=()=>w.assessment||w.data.states.find(s=>s.number===w.selected);
  const modeLabels={inspect:t('Inspect','部位確認'),pan:t('Pan view','表示移動'),move:t('Move photo','写真移動'),navel:t('Navel','臍'),calibrate:t('Ruler','定規'),mark:t('Exact point','実際の点'),alert:t('Draw alert','注意領域'),layout:t('Edit 14 sites','14部位調整')};

  async function reload({latest=false,keepSelection=true}={}){
    const photoId=w.photo?.id, previousPoint=w.point?{...w.point}:null;
    const data=await api(`/api/patients/${w.pid}`);if(w.closed)return;
    w.data=data;w.clockRevision=state.clock?.revision;w.photo=(!latest&&data.photos.find(p=>p.id===photoId))||data.photos.find(p=>p.id===data.current_photo_id)||data.photos[0]||null;
    w.a=w.photo?clone(w.photo.alignment):null;w.basePPM=w.a?.ppm;w.sites=clone(data.sites);w.dirty=false;w.layoutDirty=false;w.conflict=false;w.mode='inspect';w.calPoints=[];w.draft=null;
    if(!keepSelection){w.selected=null;w.point=null;w.assessment=null;}
    else if(w.selected){w.point=previousPoint;w.assessment=null;}
    if(latest)w.view={x:-18,y:-14,w:36,h:28};
    render();
    if(w.selected&&w.point&&keepSelection){try{w.assessment=await api(`/api/patients/${w.pid}/screen-point`,{method:'POST',data:w.point});if(!w.closed)renderAside();}catch{}}
  }
  async function chooseSite(n){
    const s=w.sites.find(s=>s.number===n);w.selected=n;w.point={x:s.x,y:s.y};w.assessment=w.data.states.find(s=>s.number===n);w.mode='inspect';w.draft=null;updateTools();draw();renderAside();
  }
  function markDirty(){w.dirty=true;w.assessment=null;updateAlignmentStatus();renderAside();}
  function updateAlignmentStatus(){
    const elem=$('#alignment-state',root);if(!elem)return;
    const okay=verified();elem.innerHTML=badge(okay?'eligible':'unverified',okay?t('Alignment verified','位置確認済み'):t('Alignment required','位置確認が必要'));
    const save=$('#verify-alignment',root);if(save)save.disabled=!editable();
    const tag=$('#photo-tag',root);if(tag){tag.className=`float-tag ${!okay?'warning':''}`;tag.textContent=!isLatest()?t('OLDER PHOTO · CURRENT RESTRICTIONS','過去の写真・現在の制限を表示'):!okay?t('UNCALIBRATED / UNSAVED · DO NOT USE','未校正・未保存：使用不可'):!fresh()?t('PHOTO OVER 24 HOURS OLD','撮影後24時間経過'):w.photo.demo?t('SYNTHETIC DEMO · NOT A PATIENT','模式図デモ・実患者ではありません'):t('CALIBRATED ESTIMATE · VERIFY ON BODY','校正済み推定値・身体で確認');}
    const scale=$('#scale-readout',root);if(scale)scale.textContent=w.a?`${w.a.ppm.toFixed(1)} px/cm ${w.a.calibration?'✓':t('(uncalibrated)','（未校正）')}`:'—';
  }
  function render(){
    const p=w.data.patient;
    $('#breadcrumb').innerHTML=`<button class="button ghost small-button" id="back-patients">${t('Patients','患者一覧')}</button>${icon('chevron',12)}<span class="mono">${esc(p.code)}</span>`;
    $('#back-patients').addEventListener('click',()=>callbacks.go('patients'));
    const prev=w.photo&&w.data.photos.find(ph=>ph.id<w.photo.id&&ph.verified);
    root.innerHTML=`<div class="page-head"><div><div class="eyebrow">${t('PATIENT WORKSPACE','患者ワークスペース')}</div><div class="row"><h1>${esc(p.alias)}</h1>${p.demo?'<span class="demo-tag">SYNTHETIC DEMO</span>':''}</div><p><span class="chip-id">${esc(p.code)}</span> ${esc(p.therapy||t('Puncture-site rotation','穿刺部位ローテーション'))} ${!p.active?badge('blocked',t('Inactive','管理終了')):''}</p></div><div class="page-actions"><button class="button secondary" id="edit-profile">${icon('edit',16)}${t('Profile','プロフィール')}</button><a class="button secondary" href="/api/patients/${w.pid}/export.csv" title="${t('Export includes sensitive patient data','機微な患者データを含みます')}">${icon('download',16)}CSV</a><button class="button primary" id="upload-photo">${icon('camera',17)}${t('New visit photo','今回の写真を追加')}</button></div></div>
    <div class="progress-strip"><span class="step ${w.photo?'done':''}"><em>1</em>${t('Upload photo','写真追加')}</span><span class="line"></span><span class="step ${w.photo?.verified?'done':''}"><em>2</em>${t('Align & calibrate','位置・校正確認')}</span><span class="line"></span><span class="step"><em>3</em>${t('Review skin & point','皮膚・位置確認')}</span><span class="line"></span><span class="step"><em>4</em>${t('Record puncture','穿刺を記録')}</span></div>
    <div id="conflict-banner" class="notice danger mb-16 hidden">${icon('alert',18)}<span>${t('Another window updated this patient. Reload before continuing.','別の画面で更新されました。再読み込みしてください。')}</span><button class="button secondary small-button" id="conflict-reload">${t('Reload','再読み込み')}</button></div>
    <div class="workspace-grid"><div class="workspace-main stack"><section class="card canvas-card"><div class="canvas-heading"><div class="row"><h2>${t('Abdominal site map','腹部の穿刺部位マップ')}</h2><span id="alignment-state"></span></div>${w.data.photos.length?`<select id="photo-select" class="photo-select" aria-label="${t('Photo history','写真履歴')}">${w.data.photos.map((ph,i)=>`<option value="${ph.id}" ${ph.id===w.photo?.id?'selected':''}>${ph.id===w.data.current_photo_id?t('Current · ','現在・'):''}${fmt(ph.captured_at)} · #${ph.id}</option>`).join('')}</select>`:''}</div>
    ${w.photo?`<div class="canvas-toolbar">${[['inspect','eye'],['pan','hand'],['move','move'],['navel','target'],['calibrate','ruler'],['mark','pin'],['alert','alert']].map(([mode,ic])=>`<button class="tool-button ${mode==='alert'?'red':''}" data-mode="${mode}" ${['move','navel','calibrate'].includes(mode)&&!editable()?'disabled':''} title="${modeLabels[mode]}">${icon(ic,17)}<span>${modeLabels[mode]}</span></button>`).join('')}${!w.data.layout_locked?`<button class="tool-button" data-mode="layout">${icon('edit',16)}<span>${modeLabels.layout}</span></button>`:''}</div>
    <div class="tool-hint" id="tool-hint"></div><div class="canvas-stage"><svg class="map-svg" id="site-map" viewBox="-18 -14 36 28" role="group" aria-label="${t('Interactive 14-site abdominal map. Use the numbered buttons or the accessible status table.','14部位の腹部マップ。番号ボタンまたは右側の表から操作できます。')}"><defs><marker id="flow-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#468c76"/></marker><pattern id="navel-hatch" width=".5" height=".5" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><line x1="0" y1="0" x2="0" y2=".5" stroke="#b98139" stroke-width=".04" opacity=".35"/></pattern></defs><image id="abdomen-photo" href="${w.photo.url}" x="0" y="0" width="${w.photo.width}" height="${w.photo.height}" preserveAspectRatio="none"/><g id="map-layer"></g><g id="tool-layer"></g></svg>
    <div class="canvas-floating"><div class="float-tag" id="photo-tag"></div><div class="float-tag">${t('PATIENT RIGHT ←  HEAD UP  → PATIENT LEFT','患者の右 ← 頭側が上 → 患者の左')}</div></div><div class="canvas-coordinates">${t('Navel-centred map · estimated cm','臍を原点とするマップ・推定cm')}</div><div class="view-controls"><button class="icon-button" id="zoom-out" aria-label="${t('Zoom out','縮小')}">${icon('minus',17)}</button><span id="zoom-level">100%</span><button class="icon-button" id="zoom-in" aria-label="${t('Zoom in','拡大')}">${icon('plus',17)}</button><button class="icon-button" id="zoom-fit" aria-label="${t('Reset view','表示リセット')}">${icon('reset',16)}</button></div></div>
    <div class="canvas-legend"><div class="legend-items">${[['green',t('Rule-eligible','条件適合')],['blue',t('12-day rest','12日間休止')],['red',t('Do not use','使用不可')],['gray',t('Unverified','未確認')]].map(([c,l])=>`<span class="legend-item"><span class="legend-swatch ${c}"></span>${l}</span>`).join('')}</div><label class="photo-opacity">${t('Photo','写真')}<input id="photo-opacity" type="range" min="40" max="100" value="${w.photoOpacity*100}" aria-label="${t('Photo opacity','写真の不透明度')}"></label></div>
    <div class="alignment-panel"><div class="spaced"><div class="small strong">${w.photo.locked?t('Alignment locked to saved records','保存済み記録の位置合わせを固定'):t('Photo alignment controls','写真の位置合わせ')}</div><span class="small mono muted" id="scale-readout"></span></div>
    ${editable()?`<div class="alignment-inputs mt-16">${field(t('Photo size','写真サイズ'),'<input id="photo-size" type="range" min="30" max="250" value="100">',t('Resizing clears ruler calibration.','サイズ変更後は再校正が必要です。'))}${field(t('Photo rotation','写真回転'),`<div class="row"><input id="photo-angle" type="range" min="-180" max="180" step=".1" value="${w.a.angle}" style="flex:1"><output id="angle-value" class="small mono">${w.a.angle.toFixed(1)}°</output></div>`)}</div><div class="row mt-16"><button class="button primary small-button" id="verify-alignment">${icon('check',15)}${t('Verify & save alignment','確認して位置を保存')}</button><button class="button secondary small-button" id="discard-alignment">${t('Discard changes','変更を破棄')}</button>${!w.data.layout_locked?`<button class="button secondary small-button" id="save-layout">${t('Save 14-site layout','14部位配置を保存')}</button>`:''}</div>`:`<p class="small muted mt-16">${t('Saved photo geometry cannot be changed after a record references it. Upload and verify a new photo for another visit.','記録に紐づく写真の位置合わせは変更できません。次の訪問では新しい写真を追加して確認してください。')}</p>`}
    ${prev?`<div class="reference-preview"><img src="${prev.url}" alt="${t('Previous verified photo for manual landmark comparison','目印の比較用：前回確認済み写真')}"><div><strong class="small">${t('Previous reference photo','前回の参考写真')}</strong><p>${fmt(prev.captured_at)} JST<br>${t('Compare landmarks and previous puncture marks. This is not automatic registration.','目印と過去の穿刺痕を比較してください。自動位置合わせではありません。')}</p></div></div>`:''}</div>`:
    `<div class="photo-empty"><div class="photo-empty-inner"><div class="empty-icon">${icon('camera',35)}</div><h3>${t('Start with an abdominal photo','腹部の写真から始めましょう')}</h3><p>${t('Include the navel, visible landmarks and a measured ruler segment. Your 14-site overlay will appear above the photo.','臍・位置合わせの目印・定規を写してください。写真の上に14部位のレイヤーを表示します。')}</p><button class="button primary" id="upload-first">${icon('upload',17)}${t('Upload photograph','写真をアップロード')}</button></div></div>`}</section>
    <div class="notice warning slim">${icon('shield',17)}<span>${t('Photo distances are estimates, not verified skin-surface measurements. The nurse must check the actual skin and distances. Green does not mean clinically safe.','写真の距離は推定で、皮膚表面の実測値ではありません。看護師が皮膚と実際の距離を確認してください。緑色は安全を保証しません。')}</span></div></div><aside class="workspace-aside" id="workspace-aside"></aside></div>`;
    $('#upload-photo').addEventListener('click',uploadDialog);$('#upload-first')?.addEventListener('click',uploadDialog);
    $('#edit-profile').addEventListener('click',()=>callbacks.editProfile(w.data.patient,()=>reload()));
    $('#conflict-reload').addEventListener('click',()=>reload().catch(e=>toast(e.message,true)));
    if(w.photo){bindCanvas();updateAlignmentStatus();updateTools();draw();}
    renderAside();
  }
  function renderAside(){
    const aside=$('#workspace-aside',root);if(!aside)return;
    const candidates=clearReady()?w.data.candidates:[],saved=selectedState(),s=saved&&saved.status==='eligible'&&!clearReady()?{...saved,status:'unverified'}:saved,ap=w.data.appointment;
    const overdue=ap&&new Date(ap.due_at).getTime()<serverNow();
    aside.innerHTML=`<section class="card candidate-card"><div class="spaced"><h2>${t('Candidate sites','穿刺部位の候補')}</h2>${icon('shield',17)}</div><p>${t('Up to 3 rule-screened options. Nurse assessment is required for every point.','設定条件に適合した最大3部位。すべての候補で看護師の評価が必要です。')}</p>${candidates.length?`<div class="candidate-list">${candidates.map(n=>`<button class="candidate-button" data-candidate="${n}"><strong>${n}</strong><span>${t('Review site','部位を確認')}</span></button>`).join('')}</div>`:`<div class="candidate-none">${t('No verified candidates. Review alignment, photo age and restrictions.','確認済み候補なし。位置・撮影日時・制限を確認してください。')}</div>`}</section>
    <section class="card site-detail">${s?`<div class="site-detail-head"><div class="site-number-big">${s.number}</div><div><h2>${t(`Site ${s.number}`,`部位 ${s.number}`)}</h2><span class="small muted">${t('Nearest numbered location','最も近い番号の部位')}</span></div></div>${badge(s.status)}
      <dl class="detail-grid"><div><dt>${t('Last used (JST)','前回使用（日本時間）')}</dt><dd>${fmt(s.last_used_at)}</dd></div><div><dt>${t('Rest remaining','休止期間の残り')}</dt><dd>${s.unlock_at?countdown(s.unlock_at,serverNow()):'—'}</dd></div><div><dt>${t('Rest ends (JST)','休止終了（日本時間）')}</dt><dd>${fmt(s.unlock_at)}</dd></div><div><dt>${t('Navel distance (estimate)','臍からの距離（推定）')}</dt><dd>${s.navel_distance_cm} cm</dd></div></dl>
      <div class="metric-line"><span>${t('Actual point, relative to navel','実際の点（臍から）')}</span><strong class="mono">${w.point?.x.toFixed(2)}, ${w.point?.y.toFixed(2)} cm</strong></div>
      ${s.reasons?.length?`<div class="detail-reasons">${s.reasons.map(r=>`<div class="detail-reason">${esc(reasonLabel(r))}</div>`).join('')}</div>`:''}
      ${w.dirty||w.layoutDirty?`<div class="notice warning slim mt-16">${t('Save and verify alignment before recording.','位置合わせを確認・保存してから記録してください。')}</div>`:''}
      ${actualDone()?`<div class="notice slim mt-16">${t('A procedure is already recorded on this photo. Use a new visit photo for the next procedure.','この写真には穿刺記録があります。次回は新しい写真を追加してください。')}</div>`:''}
      <button class="button primary full mt-16" id="record-puncture" ${clearReady()&&s.status==='eligible'&&!actualDone()?'':'disabled'}>${icon('plus',16)}${t('Record completed puncture','実施済みの穿刺を記録')}</button>
      <div class="row mt-16"><button class="button secondary small-button" id="history-puncture" ${verified()?'':'disabled'}>${t('Add historical record','過去の記録を追加')}</button>${s.needs_review?`<button class="button ghost small-button" id="review-recurrence">${t('Review recurring issue','反復所見の再評価')}</button>`:''}</div>`:
      `<div class="empty-state" style="padding:16px 2px"><div class="empty-icon">${icon('target',25)}</div><h3 style="font-size:18px">${t('Select a site','部位を選択')}</h3><p style="margin-bottom:0">${t('Tap a number on the photo, a candidate, or a row in the status table. Use Exact point to mark the real puncture location.','写真の番号、候補、または状態表を選択します。「実際の点」で穿刺位置を指定します。')}</p></div>`}</section>
    <section class="card side-records"><div class="side-tabs">${[['sites',t('Site status','部位状態')],['history',t('History','穿刺履歴')],['skin',t('Skin alerts','皮膚所見')]].map(([v,l])=>`<button class="side-tab ${w.tab===v?'active':''}" data-tab="${v}">${l}</button>`).join('')}</div><div id="side-tab-content"></div></section>
    <section class="card mini-cal-card"><div class="mini-calendar"><div class="mini-cal-head"><span>${t('Visit calendar','訪問カレンダー')}</span><span class="muted">${fmt(serverNow(),{year:'numeric',month:'short',day:undefined,hour:undefined,minute:undefined})}</span></div>${miniCalendar()}<div class="legend-items mt-16"><span class="legend-item"><span class="legend-swatch blue"></span>${t('Puncture','穿刺')}</span><span class="legend-item"><span class="legend-swatch green"></span>${t('Next visit','次回')}</span></div></div><div class="card-body" style="padding-top:0"><div class="spaced"><strong class="small">${t('Next appointment','次回予約')}</strong>${appointmentBadge(ap,overdue)}</div><p class="mt-16 small strong">${fmt(ap?.scheduled_at)} JST</p>${ap?.scheduled_at!==ap?.due_at?`<p class="small muted">${t('Protocol due:','予定期限：')} ${fmt(ap?.due_at)}</p>`:''}<button class="button secondary full mt-16" id="edit-appointment">${icon('calendar',15)}${t('Confirm / change time','日時の確認・変更')}</button></div></section>`;
    $$('[data-candidate]',aside).forEach(b=>b.addEventListener('click',()=>chooseSite(Number(b.dataset.candidate))));
    $$('[data-tab]',aside).forEach(b=>b.addEventListener('click',()=>{w.tab=b.dataset.tab;renderAside();}));
    $('#record-puncture')?.addEventListener('click',()=>recordDialog(false));$('#history-puncture')?.addEventListener('click',()=>recordDialog(true));
    $('#review-recurrence')?.addEventListener('click',reviewDialog);
    $('#edit-appointment')?.addEventListener('click',()=>callbacks.editAppointment({...w.data.patient,appointment:w.data.appointment},()=>reload()));
    renderTab();
  }
  function renderTab(){
    const node=$('#side-tab-content',root);if(!node)return;
    if(w.tab==='sites'){
      node.innerHTML=`<div class="side-table-scroll"><table class="site-table"><thead><tr><th>${t('Site','部位')}</th><th>${t('Status','状態')}</th><th>${t('Rest / last use','残り・前回使用')}</th></tr></thead><tbody>${w.data.states.map(s=>`<tr class="clickable-row ${s.number===w.selected?'selected-row':''}" data-site-row="${s.number}" tabindex="0"><td>${String(s.number).padStart(2,'0')}</td><td>${badge(s.status)}</td><td><div class="small">${s.unlock_at?countdown(s.unlock_at,serverNow()):'—'}</div><div class="sub">${s.last_used_at?shortTime(s.last_used_at):t('Not recorded','記録なし')}</div></td></tr>`).join('')}</tbody></table></div>`;
      $$('[data-site-row]',node).forEach(row=>{row.addEventListener('click',()=>chooseSite(Number(row.dataset.siteRow)));row.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();chooseSite(Number(row.dataset.siteRow));}});});
    }else if(w.tab==='history'){
      node.innerHTML=`<div class="history-scroll">${w.data.events.length?w.data.events.map(e=>`<article class="history-card"><div class="spaced"><span class="title ${e.voided_at?'voided':''}">${t('Site','部位')} ${e.site_number} · ${fmt(e.occurred_at)}</span>${e.kind==='history'?`<span class="badge unverified">${t('History','過去')}</span>`:''}</div><p class="description">${esc(e.actor)} · (${e.x.toFixed(2)}, ${e.y.toFixed(2)}) cm<br>${esc(e.note||'')}${e.voided_at?`<br>${t('Voided:','取消：')} ${esc(e.void_reason)}`:''}${e.exception_reason?`<br>${esc(e.exception_reason)}`:''}</p>${e.warnings.length?`<div class="detail-reason mt-16">${e.warnings.map(r=>esc(reasonLabel(r))).join('<br>')}</div>`:''}<div class="row mt-16"><button class="button ghost small-button" data-history-photo="${e.photo_id}">${t('Source photo','記録写真')}</button>${state.user.role==='admin'&&!e.voided_at?`<button class="button ghost small-button" data-void="${e.id}">${t('Correct / void','記録を取消')}</button>`:''}</div></article>`).join(''):`<div class="card-body"><p class="small">${t('No punctures recorded yet.','穿刺記録はまだありません。')}</p></div>`}</div>`;
      $$('[data-void]',node).forEach(b=>b.addEventListener('click',()=>voidDialog(Number(b.dataset.void))));
      $$('[data-history-photo]',node).forEach(b=>b.addEventListener('click',()=>switchPhoto(Number(b.dataset.historyPhoto))));
    }else{
      node.innerHTML=`<div class="history-scroll">${w.data.alerts.length?w.data.alerts.map(a=>`<article class="history-card"><div class="spaced"><span class="title">${t('Site','部位')} ${a.site_number} · ${a.types.map(typeLabel).join(' / ')}</span>${badge(a.resolved_at?'eligible':'blocked',a.resolved_at?t('Recovered','回復済み'):t('Active','未回復'))}</div><p class="description">${fmt(a.observed_at)} JST · ${esc(a.actor)}<br>${t('Radius','半径')} ${a.radius.toFixed(1)} cm · ${esc(a.severity)}${a.note?`<br>${esc(a.note)}`:''}${a.resolved_at?`<br>${t('Recovery:','回復確認：')} ${fmt(a.resolved_at)} · ${esc(a.resolution_note)}`:''}</p>${!a.resolved_at?`<button class="button secondary small-button mt-16" data-resolve="${a.id}">${t('Confirm full recovery','完全回復を確認')}</button>`:''}</article>`).join(''):`<div class="card-body"><p class="small">${t('No skin observations yet. Choose Draw alert to mark an area.','皮膚所見はまだありません。「注意領域」で部位を指定します。')}</p></div>`}</div>`;
      $$('[data-resolve]',node).forEach(b=>b.addEventListener('click',()=>resolveDialog(Number(b.dataset.resolve))));
    }
  }
  function miniCalendar(){
    const month=dayKey(serverNow()).slice(0,7),first=new Date(`${month}-01T00:00:00+09:00`),weekday=(first.getUTCDay()+1)%7; // Correct weekday calculated explicitly in JST below.
    const utcDate=new Date(`${month}-01T00:00:00Z`),startOffset=(utcDate.getUTCDay()+6)%7;
    const used=new Set(w.data.events.filter(eventApplies).map(e=>dayKey(e.occurred_at))),due=dayKey(w.data.appointment?.scheduled_at||serverNow());
    return `<div class="mini-cal-grid">${t(['M','T','W','T','F','S','S'],['月','火','水','木','金','土','日']).map(s=>`<div class="mini-day label">${s}</div>`).join('')}${Array.from({length:35+((new Date(Date.UTC(Number(month.slice(0,4)),Number(month.slice(5)),0)).getUTCDate()+startOffset>35)?7:0)},(_,i)=>{const d=new Date(utcDate);d.setUTCDate(1-startOffset+i);const key=d.toISOString().slice(0,10);return `<div class="mini-day ${key.slice(0,7)!==month?'off':''} ${used.has(key)?'used':''} ${key===due?'due':''} ${key===dayKey(serverNow())?'today':''}" title="${key}">${d.getUTCDate()}</div>`;}).join('')}</div>`;
  }
  function draw(){
    const svg=$('#site-map',root);if(!svg||!w.a)return;
    svg.setAttribute('viewBox',`${w.view.x} ${w.view.y} ${w.view.w} ${w.view.h}`);svg.dataset.mode=w.mode;
    const image=$('#abdomen-photo',svg);image.setAttribute('transform',`scale(${1/w.a.ppm}) rotate(${-w.a.angle}) translate(${-w.a.cx} ${-w.a.cy})`);image.setAttribute('opacity',w.photoOpacity);
    const initialSvgScale=svg.getScreenCTM()?.a||20,hitRadius=Math.max(.96,22/initialSvgScale),font=.56;
    const connectors=w.sites.slice(0,8).map(s=>`<line x1="0" y1="0" x2="${s.x}" y2="${s.y}" stroke="#a47b6e" stroke-width=".055" stroke-dasharray=".23 .2" opacity=".58"/>`).join('');
    const active=w.data.alerts.filter(alertActive).map(a=>`<g><circle cx="${a.x}" cy="${a.y}" r="${a.radius}" fill="#e0747f" fill-opacity=".29" stroke="#bd4d5a" stroke-width=".075"/><text x="${a.x}" y="${a.y-a.radius-.25}" class="point-label" font-size=".50" fill="#9b3745" text-anchor="middle">${esc(a.types.map(typeLabel).join(' / '))}</text></g>`).join('');
    const events=w.data.events.filter(eventApplies).map(e=>{const recent=serverNow()-new Date(e.occurred_at).getTime()<12*86400000;return `<g>${recent&&w.showHalos?`<circle cx="${e.x}" cy="${e.y}" r="2.5" fill="#8aafea" fill-opacity=".055" stroke="#467bc2" stroke-opacity=".35" stroke-width=".045" stroke-dasharray=".16 .17"/>`:''}<circle cx="${e.x}" cy="${e.y}" r=".14" fill="${recent?'#245aaa':'#797f7a'}" stroke="white" stroke-width=".05"/><title>#${e.id} · ${fmt(e.occurred_at)} JST · ${esc(e.actor)}</title></g>`;}).join('');
    const nodes=w.sites.map(s=>{
      const saved=w.data.states.find(v=>v.number===s.number),isReady=clearReady();
      const status=saved.status==='eligible'&&!isReady?'unverified':saved.status;
      const [stroke,fill]=colors[status],selected=w.selected===s.number;
      const label=saved.unlock_at?countdown(saved.unlock_at,serverNow()):status==='blocked'?t('Blocked','使用不可'):'';
      return `<g class="site-touch" data-site="${s.number}" role="button" tabindex="0" aria-label="${t('Site','部位')} ${s.number}: ${statusLabel(status)} ${esc(label)}"><title>${t('Site','部位')} ${s.number} · ${statusLabel(status)}${saved.last_used_at?' · '+fmt(saved.last_used_at):''}</title>
        <circle cx="${s.x}" cy="${s.y}" r="${hitRadius}" fill="transparent" stroke="none"/>
        ${selected?`<circle cx="${s.x}" cy="${s.y}" r=".95" fill="none" stroke="#184843" stroke-width=".09"/>`:''}
        <circle class="site-ring" cx="${s.x}" cy="${s.y}" r=".73" fill="${fill}" fill-opacity=".60" stroke="${stroke}" stroke-width=".09"/>
        <text x="${s.x}" y="${s.y+.20}" text-anchor="middle" font-size="${font}" font-family="inherit" font-weight="750" fill="${status==='blocked'?'#843444':'#143f43'}" pointer-events="none">${s.number}</text>
        ${label?`<text x="${s.x}" y="${s.y+1.22}" text-anchor="middle" font-size=".49" class="site-label">${esc(label)}</text>`:''}
        ${saved.last_used_at?`<text x="${s.x}" y="${s.y+1.76}" text-anchor="middle" font-size=".43" class="point-label" fill="#3b5368">${shortTime(saved.last_used_at)}</text>`:''}</g>`;
    }).join('');
    $('#map-layer',svg).innerHTML=`${connectors}<circle cx="0" cy="0" r="5" fill="url(#navel-hatch)" stroke="#a87535" stroke-opacity=".75" stroke-dasharray=".17 .15" stroke-width=".055"/>
      <path d="M 2.5 -7.3 A 7.7 7.7 0 0 1 7.3 -2.5" fill="none" stroke="#468c76" stroke-opacity=".65" stroke-width=".10" marker-end="url(#flow-arrow)"/>
      <path d="M -2.5 7.3 A 7.7 7.7 0 0 1 -7.3 2.5" fill="none" stroke="#468c76" stroke-opacity=".65" stroke-width=".10" marker-end="url(#flow-arrow)"/>
      <path d="M 12 -7 Q 15 0 12 7" fill="none" stroke="#468c76" stroke-opacity=".65" stroke-width=".12" marker-end="url(#flow-arrow)"/>
      <path d="M -12 7 Q -15 0 -12 -7" fill="none" stroke="#468c76" stroke-opacity=".65" stroke-width=".12" marker-end="url(#flow-arrow)"/>
      <circle cx="0" cy="0" r=".2" fill="#876e58"/><path d="M-.45 0H.45M0 -.45V.45" stroke="#765e4b" stroke-width=".05"/>
      <text x="0" y="2.4" text-anchor="middle" font-size=".50" class="point-label" fill="#96713d">${t('NAVEL EXCLUSION','臍の周囲は使用不可')}</text><text x="0" y="3.1" text-anchor="middle" font-size=".56" class="point-label" fill="#96713d">${t('5 cm radius','半径 5 cm')}</text>
      ${active}${events}${nodes}`;
    let tool='';
    if(w.point){const p=w.point;tool+=`<path d="M${p.x-.55} ${p.y}H${p.x+.55} M${p.x} ${p.y-.55}V${p.y+.55}" stroke="#193c52" stroke-width=".065" pointer-events="none"/><circle cx="${p.x}" cy="${p.y}" r=".31" fill="none" stroke="#fff" stroke-width=".05" pointer-events="none"/>`;}
    if(w.calPoints.length){const ps=w.calPoints.map(p=>fromImage(p,w.a));tool+=ps.map(p=>`<circle cx="${p.x}" cy="${p.y}" r=".18" fill="#fff" stroke="#175e8b" stroke-width=".065"/>`).join('');if(ps.length===2)tool+=`<line x1="${ps[0].x}" y1="${ps[0].y}" x2="${ps[1].x}" y2="${ps[1].y}" stroke="#175e8b" stroke-width=".065"/>`;}
    if(w.draft)tool+=`<circle cx="${w.draft.x}" cy="${w.draft.y}" r="${w.draft.radius}" fill="#e47780" fill-opacity=".26" stroke="#b54457" stroke-dasharray=".16 .10" stroke-width=".08"/>`;
    $('#tool-layer',svg).innerHTML=tool;
    $('#zoom-level',root).textContent=`${Math.round(36/w.view.w*100)}%`;
  }
  function updateTools(){
    if(!w.photo)return;
    $$('[data-mode]',root).filter(n=>n.tagName==='BUTTON').forEach(b=>b.classList.toggle('active',b.dataset.mode===w.mode));
    const hints={
      inspect:t('Tap a numbered site to view its status. Dates and restrictions stay attached to the patient map.','番号を選択して状態を確認します。日時と制限は患者マップに紐づいて保持されます。'),
      pan:t('Drag to pan the whole view. Use + / − or the mouse wheel to inspect; stored geometry does not change.','ドラッグで表示全体を移動。＋/－やホイールで拡大しても記録座標は変わりません。'),
      move:t('Drag the photograph beneath the fixed overlay. Align the actual navel with the central crosshair.','固定レイヤーの下で写真をドラッグ。実際の臍を中央の十字に合わせます。'),
      navel:t('Tap the actual navel on the photo. The photograph will move so the navel is at the map centre.','写真上の実際の臍をタップ。臍がマップ中央にくるよう写真が移動します。'),
      calibrate:w.calPoints.length===1?t('Tap the second ruler mark. Use a known 2–30 cm segment in the same skin plane.','定規の2点目をタップ。皮膚と同じ平面の2～30cmの長さを使用します。'):t('Tap two marks on a ruler in the image, then enter the actual distance in centimetres.','写真の定規上の2点をタップし、実際の距離をcmで入力します。'),
      mark:t('Tap the exact puncture point. The nearest chart number is assigned automatically; the exact point is stored too.','実際の穿刺点をタップ。最も近い番号を自動割り当てし、座標も保存します。'),
      alert:t('Drag from the centre to the edge of the affected area to draw a red circle. Choose its observations next.','注意部位の中心から端までドラッグして赤い円を描き、所見を選択します。'),
      layout:t('Drag numbered sites to personalize the initial layout. Minimum: 5 cm from navel, 2.5 cm between sites. Save layout separately.','番号をドラッグして初回の配置を調整。臍から5cm・部位間2.5cm以上が必要です。配置を別途保存します。')};
    $('#tool-hint',root).innerHTML=`${icon(w.mode==='calibrate'?'ruler':w.mode==='alert'?'alert':'target',15)}<span>${hints[w.mode]}</span>`;
    $('#site-map').dataset.mode=w.mode;
  }
  function setMode(mode){
    if(['move','navel','calibrate'].includes(mode)&&!editable())return;
    if(['mark','alert'].includes(mode)&&!verified()){toast(t('Calibrate, verify and save this photo first.','先に校正・位置確認をして保存してください。'),true);return;}
    if(mode==='alert'&&!clearReady()){toast(t('Use the latest, current photo to mark skin concerns.','最新の写真を使って皮膚所見を記録してください。'),true);return;}
    w.mode=mode;w.calPoints=[];w.draft=null;updateTools();draw();
  }
  function svgPoint(event){const svg=$('#site-map'),p=svg.createSVGPoint();p.x=event.clientX;p.y=event.clientY;return p.matrixTransform(svg.getScreenCTM().inverse());}
  function bindCanvas(){
    $$('button[data-mode]',root).forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mode)));
    $('#photo-select')?.addEventListener('change',e=>switchPhoto(Number(e.target.value)));
    $('#photo-opacity').addEventListener('input',e=>{w.photoOpacity=Number(e.target.value)/100;draw();});
    $('#photo-size')?.addEventListener('input',e=>{w.a.ppm=w.basePPM*100/Number(e.target.value);w.a.calibration=null;w.calPoints=[];markDirty();draw();});
    $('#photo-angle')?.addEventListener('input',e=>{w.a.angle=Number(e.target.value);$('#angle-value').textContent=`${w.a.angle.toFixed(1)}°`;markDirty();draw();});
    $('#verify-alignment')?.addEventListener('click',verifyDialog);$('#discard-alignment')?.addEventListener('click',()=>reload().catch(e=>toast(e.message,true)));$('#save-layout')?.addEventListener('click',saveLayout);
    const zoom=scale=>{const next=Math.max(10,Math.min(60,w.view.w*scale)),factor=next/w.view.w,cx=w.view.x+w.view.w/2,cy=w.view.y+w.view.h/2;w.view={x:cx-next/2,y:cy-w.view.h*factor/2,w:next,h:w.view.h*factor};draw();};
    $('#zoom-in').addEventListener('click',()=>zoom(.82));$('#zoom-out').addEventListener('click',()=>zoom(1.22));$('#zoom-fit').addEventListener('click',()=>{w.view={x:-18,y:-14,w:36,h:28};draw();});
    const svg=$('#site-map');
    svg.addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY>0?1.08:.92);},{passive:false});
    svg.addEventListener('keydown',e=>{const g=e.target.closest('[data-site]');if(g&&(e.key==='Enter'||e.key===' ')){e.preventDefault();chooseSite(Number(g.dataset.site));}});
    svg.addEventListener('pointerdown',e=>{
      if(e.button!==0&&e.pointerType==='mouse')return;
      const p=svgPoint(e),site=e.target.closest('[data-site]')?.dataset.site;
      w.drag={id:e.pointerId,start:{x:p.x,y:p.y},clientX:e.clientX,clientY:e.clientY,scale:svg.getScreenCTM().a,
        initialA:clone(w.a),initialView:{...w.view},site:site?Number(site):null,moved:false};
      if(w.mode==='layout'&&site){w.drag.original={...w.sites.find(s=>s.number===Number(site))};}
      svg.setPointerCapture(e.pointerId);e.preventDefault();
      if(w.mode==='alert'){w.draft={x:p.x,y:p.y,radius:.3};draw();}
    });
    svg.addEventListener('pointermove',e=>{
      const d=w.drag;if(!d||d.id!==e.pointerId)return;
      const dx=(e.clientX-d.clientX)/d.scale,dy=(e.clientY-d.clientY)/d.scale;
      if(Math.hypot(e.clientX-d.clientX,e.clientY-d.clientY)>3)d.moved=true;
      if(w.mode==='pan'){w.view.x=d.initialView.x-dx;w.view.y=d.initialView.y-dy;draw();}
      else if(w.mode==='move'&&editable()){
        const r=d.initialA.angle*Math.PI/180;w.a.cx=d.initialA.cx-d.initialA.ppm*(dx*Math.cos(r)-dy*Math.sin(r));w.a.cy=d.initialA.cy-d.initialA.ppm*(dx*Math.sin(r)+dy*Math.cos(r));w.dirty=true;draw();
      }else if(w.mode==='alert'){w.draft.radius=Math.min(15,Math.max(.3,Math.hypot(dx,dy)));draw();}
      else if(w.mode==='layout'&&d.original&&!w.data.layout_locked){const s=w.sites.find(s=>s.number===d.site);s.x=d.original.x+dx;s.y=d.original.y+dy;w.layoutDirty=true;draw();}
    });
    svg.addEventListener('pointerup',async e=>{
      const d=w.drag;if(!d||d.id!==e.pointerId)return;w.drag=null;try{svg.releasePointerCapture(e.pointerId);}catch{}
      const p=svgPoint(e);
      try{
        if(w.mode==='move'&&d.moved){markDirty();}
        else if(w.mode==='layout'&&d.moved){updateAlignmentStatus();renderAside();}
        else if(w.mode==='navel'){
          const actual=toImage(p,w.a);w.a.cx=actual.x;w.a.cy=actual.y;w.mode='move';markDirty();updateTools();draw();
        }else if(w.mode==='calibrate'){
          const actual=toImage(p,w.a);
          if(actual.x<0||actual.y<0||actual.x>w.photo.width||actual.y>w.photo.height){toast(t('Choose ruler marks inside the photograph.','写真内の定規を指定してください。'),true);return;}
          w.calPoints.push(actual);draw();updateTools();if(w.calPoints.length===2)calibrationDialog();
        }else if(w.mode==='mark'){
          w.point={x:Number(p.x.toFixed(5)),y:Number(p.y.toFixed(5))};w.assessment=await api(`/api/patients/${w.pid}/screen-point`,{method:'POST',data:w.point});w.selected=w.assessment.number;draw();renderAside();
        }else if(w.mode==='alert'){alertDialog();}
        else if(w.mode==='inspect'&&d.site&&!d.moved){chooseSite(d.site);}
      }catch(error){toast(error.message,true);}
    });
    svg.addEventListener('pointercancel',()=>{w.drag=null;w.draft=null;draw();});
  }
  function switchPhoto(id){
    if((w.dirty||w.layoutDirty)&&!window.confirm(t('Discard unsaved alignment/layout edits?','未保存の位置・配置変更を破棄しますか？'))){$('#photo-select').value=w.photo.id;return;}
    w.photo=w.data.photos.find(p=>p.id===id)||w.data.photos[0];w.a=clone(w.photo.alignment);w.basePPM=w.a.ppm;w.dirty=false;w.layoutDirty=false;w.sites=clone(w.data.sites);w.calPoints=[];w.draft=null;w.mode='inspect';render();
  }
  function calibrationDialog(){
    const [a,b]=w.calPoints;
    const dialog=openDialog({title:t('Set image scale','画像の縮尺を設定'),body:`<p>${t('Enter the real distance between the two ruler marks, not an estimated distance on the body. Keep the ruler in the same plane as the photographed skin.','2点間の定規の実際の距離を入力します。身体上の推測値ではありません。定規は撮影する皮膚と同じ平面に置いてください。')}</p>
      ${field(t('Known ruler distance (cm)','定規の実際の距離（cm）'),input('length_cm',10,'number','required min="2" max="30" step="0.1"'))}<div class="notice warning">${t('Calibration estimates scale only. Perspective and curved-skin errors remain.','校正は縮尺の推定のみです。遠近や皮膚の曲面による誤差は残ります。')}</div>`,submit:t('Apply calibration','校正を適用'),onSubmit:async f=>{
        const length=Number(f.get('length_cm')),pixels=radialDistance(a,b),ppm=pixels/length;
        if(pixels<30||ppm<5||ppm>600)throw new Error(t('Ruler marks are too close or the scale is invalid. Choose a longer, clearly visible reference.','定規の2点が近すぎるか、縮尺が不正です。より長く鮮明な定規区間を選んでください。'));
        w.a.calibration={a,b,length_cm:length};w.a.ppm=ppm;w.basePPM=ppm;$('#photo-size').value=100;w.mode='move';markDirty();updateTools();draw();toast(t('Scale calibrated. Verify and save the alignment.','縮尺を校正しました。位置合わせを確認して保存してください。'));
      }});
    dialog.addEventListener('close',()=>{w.calPoints=[];updateTools();draw();},{once:true});
  }
  function verifyDialog(){
    if(!w.a.calibration){toast(t('Use Ruler to calibrate a known distance before saving.','「定規」で実際の長さを校正してから保存してください。'),true);return;}
    if(w.layoutDirty){toast(t('Save the 14-site layout first, then verify photo alignment.','先に14部位配置を保存してから、写真の位置を確認してください。'),true);return;}
    openDialog({title:t('Verify photo alignment','写真の位置合わせを確認'),body:`<p><strong>${esc(w.data.patient.code)}</strong> · ${esc(w.data.patient.alias)}</p><div class="notice mb-16">${icon('ruler',17)}<span>${t('Reference:','基準：')} ${w.a.calibration.length_cm} cm · ${w.a.ppm.toFixed(2)} px/cm</span></div>
      ${check('identity',t('This is the correct patient and photograph.','患者と写真が一致していることを確認しました。'))}
      ${check('navel',t('The origin is on the actual navel; the image is not mirrored and head direction is correct.','原点は実際の臍に一致し、鏡像ではなく、頭側の向きが正しいことを確認しました。'))}
      ${check('scale',t('Ruler marks, centimetres and the same-skin-plane scale were checked.','定規の2点・cm・皮膚と同じ平面の縮尺を確認しました。'))}
      ${check('history',t('Skin is visible; landmarks and historical puncture marks were compared. I understand this 2-D alignment is approximate.','皮膚が見え、目印と過去の穿刺痕を比較しました。2次元位置合わせは推定と理解しています。'))}`,
      submit:t('Verify & save','確認して保存'),onSubmit:async f=>{
        if(!['identity','navel','scale','history'].every(k=>f.has(k)))throw new Error(t('Complete all four checks.','4項目すべてを確認してください。'));
        await api(`/api/photos/${w.photo.id}/alignment`,{method:'POST',data:{version:w.data.patient.version,alignment:w.a,confirmed:true}});await reload();toast(t('Alignment verified and saved.','位置合わせを確認・保存しました。'));
      }});
  }
  async function saveLayout(){
    try{
      const unsavedAlignment=clone(w.a),wasDirty=w.dirty;
      await api(`/api/patients/${w.pid}/layout`,{method:'POST',data:{version:w.data.patient.version,sites:w.sites}});
      await reload();if(wasDirty){w.a=unsavedAlignment;w.dirty=true;w.basePPM=w.a.ppm;updateAlignmentStatus();draw();renderAside();}
      toast(t('14-site layout saved. Verify the photo alignment next.','14部位配置を保存しました。写真の位置合わせも確認してください。'));
    }catch(e){toast(e.message,true);}
  }
  function uploadDialog(){
    openDialog({title:t('Add a visit photograph','訪問写真を追加'),submit:t('Upload photo','写真を追加'),body:`<p><strong>${esc(w.data.patient.code)}</strong> · ${esc(w.data.patient.alias)}</p>
      ${field(t('Abdominal photograph','腹部写真'),'<input type="file" name="photo" accept="image/jpeg,image/png" capture="environment" required>',t('JPEG / PNG · maximum 16 MB and 32 MP · include navel and ruler. HEIC must be converted first.','JPEG/PNG・16MB/32MP以下・臍と定規を撮影。HEICは事前変換が必要です。'))}
      ${field(t('Actual capture time (JST)','実際の撮影日時（日本時間）'),input('captured_at',jstInput(serverNow()),'datetime-local','required'))}
      ${check('consent',t('I am authorized to use this image and confirm the correct patient. I am using appropriate synthetic/de-identified data for prototype evaluation.','写真利用の許可と正しい患者を確認しました。試作評価に適切な架空・匿名化データを使用しています。'))}
      <div class="notice warning">${icon('ruler',17)}<span>${t('Every new photo starts unverified. Alignment and ruler calibration are required again. Existing points and restrictions are kept.','新しい写真は未確認状態から開始します。毎回、位置合わせと定規校正が必要です。過去の点と制限は保持されます。')}</span></div>`,
      onSubmit:async f=>{if(!f.has('consent'))throw new Error(t('Confirm authorized image use.','写真利用の許可を確認してください。'));const form=new FormData();form.append('photo',f.get('photo'));form.append('captured_at',toISO(f.get('captured_at')));form.append('version',String(w.data.patient.version));form.append('consent','true');await api(`/api/patients/${w.pid}/photos`,{method:'POST',form});await reload({latest:true,keepSelection:false});setMode('move');toast(t('Photo uploaded. Set navel, ruler scale and verify alignment.','写真を追加しました。臍・定規を合わせて位置を確認してください。'));}});
  }
  function recordDialog(history){
    const s=selectedState(),point={...w.point},requestKey=crypto.randomUUID();
    openDialog({title:history?t('Record a previous puncture','過去の穿刺を記録'):t('Record completed puncture','実施済みの穿刺を記録'),submit:t('Save puncture record','穿刺記録を保存'),body:`<p><strong>${esc(w.data.patient.code)}</strong> · ${esc(w.data.patient.alias)}</p>
      <div class="notice ${history?'warning':''} mb-16">${icon(history?'history':'pin',18)}<span>${history?t('Documentation of an already-performed puncture only. Rule conflicts are retained as warnings; this does not authorize a new puncture.','実施済みの事実を記録する機能です。条件違反は警告付きで残ります。新たな穿刺を許可するものではありません。'):t('Document the actual completed procedure, not a future plan. No drug or dose is prescribed by this app.','実際に完了した穿刺を記録します。将来の予定ではありません。薬剤・投与量はこのアプリでは指示しません。')}</span></div>
      <div class="form-grid">${field(t('Nearest chart number','最も近い番号'),input('site_display',s.number,'text','readonly'))}${field(t('Puncture date & time (JST)','穿刺日時（日本時間）'),input('occurred_at',jstInput(serverNow()),'datetime-local','required'))}</div>
      <div class="metric-line"><span>${t('Exact point from navel','臍からの正確な記録座標')}</span><strong class="mono">x=${point.x.toFixed(3)}, y=${point.y.toFixed(3)} cm</strong></div>
      ${history?field(t('Historical record explanation','過去記録の説明'),'<textarea name="exception_reason" required minlength="8" maxlength="2000"></textarea>',t('Include the source and any uncertain or exceptional circumstances. At least 8 characters.','情報源・不確実性・例外事項を8文字以上で記録してください。')):''}
      ${field(t('Procedure note','穿刺メモ'),'<textarea name="note" maxlength="2000"></textarea>')}
      ${check('identity_checked',t(`I verified patient ${esc(w.data.patient.code)} and the correct record.`,`患者 ${esc(w.data.patient.code)} と記録の一致を確認しました。`))}
      ${check('point_checked',t('The crosshair matches the actual puncture point, not just an approximate chart button.','十字が実際の穿刺点に一致しており、単なる番号ボタンの概位置ではないことを確認しました。'))}
      ${check('clinical_checked',history?t('I reviewed the source record, skin history, geometry and any rule conflicts.','情報源、皮膚履歴、位置、条件との矛盾を確認しました。'):t('The actual skin was assessed and physical 5 cm / 2.5 cm distances were checked; the site was not chosen from photo colour alone.','皮膚を実際に評価し、5cm/2.5cmの距離を身体で確認しました。写真の色だけで部位を選んでいません。'))}
      <p class="small mt-16">${t('Recorded by:','記録者：')} <strong>${esc(state.user.display_name)}</strong></p>`,onSubmit:async f=>{
        if(!f.has('point_checked'))throw new Error(t('Confirm the exact physical point.','実際の穿刺点を確認してください。'));
        const data={...Object.fromEntries(f),...point,photo_id:w.photo.id,version:w.data.patient.version,kind:history?'history':'procedure',
          identity_checked:f.has('identity_checked'),clinical_checked:f.has('clinical_checked'),point_checked:true,occurred_at:toISO(f.get('occurred_at')),request_key:requestKey};
        await api(`/api/patients/${w.pid}/events`,{method:'POST',data});await reload();toast(t('Puncture saved. Rest period and next visit updated.','穿刺記録を保存し、休止期間と次回予定を更新しました。'));
      }});
  }
  function alertDialog(){
    const draft={...w.draft};
    const dialog=openDialog({title:t('Mark a skin concern','皮膚注意部位を記録'),submit:t('Save red alert area','赤い注意領域を保存'),body:`<div class="alert-area-preview"><span>${t('No-use region until recovery','回復確認まで使用不可')}</span><strong>${t('Circular region','円形の領域')}</strong></div>
      <div class="form-grid">${field(t('Radius (cm)','半径（cm）'),input('radius',draft.radius.toFixed(2),'number','required min="0.3" max="15" step="0.01"'))}${field(t('Observed time (JST)','所見の確認日時（日本時間）'),input('observed_at',jstInput(serverNow()),'datetime-local','required'))}</div>
      <div class="field"><span>${t('Observation type — select all that apply','所見の種類（複数選択可）')}</span><div class="check-grid">${['redness','hardness','pain','swelling','bruising','leakage','other'].map(type=>`<label class="check"><input type="checkbox" name="types" value="${type}"><span>${typeLabel(type)}</span></label>`).join('')}</div></div>
      ${field(t('Recorded severity','観察された程度'),`<select name="severity"><option value="mild">${t('Mild','軽度')}</option><option value="moderate">${t('Moderate','中等度')}</option><option value="severe">${t('Severe','重度')}</option></select>`)}
      ${field(t('Assessment / reason to avoid','評価・使用禁止の理由'),'<textarea name="note" maxlength="2000"></textarea>')}
      <div class="notice warning">${t('This app does not diagnose or grade complications automatically. Significant or worsening findings require the treating team’s assessment; do not wait for a countdown.','このアプリは所見の診断や程度判定を自動で行いません。重大・悪化する所見は医療チームで評価し、カウントダウンの終了を待たないでください。')}</div>`,onOpen:form=>{
        $('input[name=radius]',form).addEventListener('input',e=>{const n=Number(e.target.value);if(n>=.3&&n<=15){w.draft.radius=n;draw();}});
      },onSubmit:async f=>{
        const types=f.getAll('types');if(!types.length)throw new Error(t('Select at least one observation type.','所見を1つ以上選択してください。'));
        await api(`/api/patients/${w.pid}/alerts`,{method:'POST',data:{x:draft.x,y:draft.y,radius:Number(f.get('radius')),types,
          severity:f.get('severity'),observed_at:toISO(f.get('observed_at')),note:f.get('note'),photo_id:w.photo.id,version:w.data.patient.version}});
        w.tab='skin';await reload();toast(t('Skin area blocked until recovery is recorded.','回復確認まで使用不可として記録しました。'));
      }});
    dialog.addEventListener('close',()=>{w.draft=null;draw();},{once:true});
  }
  function resolveDialog(alertId){
    const a=w.data.alerts.find(a=>a.id===alertId);
    openDialog({title:t('Confirm full skin recovery','皮膚の完全回復を確認'),body:`<p>${t('Site','部位')} ${a.site_number} · ${a.types.map(typeLabel).join(' / ')}</p><div class="notice warning mb-16">${t('Recovery is a clinical assessment, never inferred from elapsed days or photo colour. Resolving this alert clears its restriction immediately; no recurring-episode review is required. A separate 12-day rest may still apply.','回復は臨床評価により確認し、日数や写真の色から推測しません。回復を記録すると、この注意領域の制限は直ちに解除され、反復所見の再評価は不要です。別の12日間休止は引き続き適用される場合があります。')}</div>
      ${field(t('Recovery assessment and findings','回復評価と所見'),'<textarea name="note" required maxlength="2000"></textarea>')}
      ${check('healed_confirmed',t('I assessed the skin at the bedside and confirm that this area has fully recovered.','現場で皮膚を評価し、この領域が完全に回復したことを確認しました。'))}`,submit:t('Record recovery','回復を記録'),onSubmit:async f=>{await api(`/api/alerts/${alertId}/resolve`,{method:'POST',data:{version:w.data.patient.version,note:f.get('note'),healed_confirmed:f.has('healed_confirmed')}});await reload();toast(t('Recovery recorded. Other restrictions remain in force.','回復を記録しました。他の制限は引き続き適用されます。'));}});
  }
  function reviewDialog(){
    const n=w.selected;
    openDialog({title:t('Review recurring skin concern','反復する皮膚所見を再評価'),body:`<p>${t('Site','部位')} ${n}</p><div class="notice warning mb-16">${t('Two or more related observations within 90 days triggered this prototype review hold. Review does not resolve active skin alerts or shorten rest periods.','90日以内に関連所見が2件以上あり、試作ルールにより再評価待ちです。再評価しても未回復の注意領域や休止期間は解除されません。')}</div>
      ${field(t('Bedside assessment and review note','現場での評価・再評価記録'),'<textarea name="note" required maxlength="2000"></textarea>')}
      ${check('confirmed',t('I reviewed the recurring issue and documented my assessment.','反復所見を再評価し、その結果を記録しました。'))}`,submit:t('Save review','再評価を保存'),onSubmit:async f=>{await api(`/api/patients/${w.pid}/reviews`,{method:'POST',data:{version:w.data.patient.version,site_number:n,note:f.get('note'),confirmed:f.has('confirmed')}});await reload();toast(t('Review recorded. Active skin alerts and rest remain protected.','再評価を記録しました。未回復の注意と休止期間は保持されます。'));}});
  }
  function voidDialog(eventId){
    openDialog({title:t('Void an incorrect puncture record','誤った穿刺記録を取消'),danger:true,body:`<div class="notice danger mb-16">${t('Only correct a factual documentation error. Do not use this to shorten a genuine rest period. The original entry and this correction remain in history and the audit log.','記録の事実誤りを修正する場合のみ使用してください。実際の休止期間を短縮するために使用しないでください。元の記録と取消は履歴・監査に残ります。')}</div>${field(t('Correction reason','取消理由'),'<textarea name="reason" required maxlength="2000"></textarea>')}`,submit:t('Void record','記録を取消'),onSubmit:async f=>{await api(`/api/events/${eventId}/void`,{method:'POST',data:{version:w.data.patient.version,reason:f.get('reason')}});await reload();toast(t('Record voided with an audit entry.','監査記録を残して取消しました。'));}});
  }
  await reload({latest:true,keepSelection:false});
  const tick=setInterval(()=>{if(w.closed||document.hidden)return;draw();if(!$('#dialog').open)renderAside();},30000);
  const poll=setInterval(async()=>{
    if(w.closed||document.hidden)return;
    try{const data=await api(`/api/patients/${w.pid}`,{activity:false});if(w.closed)return;
      if(data.patient.version!==w.data.patient.version){w.conflict=true;$('#conflict-banner',root)?.classList.remove('hidden');renderAside();return;}
      w.data.states=data.states;w.data.candidates=data.candidates;w.offline=false;draw();if(!$('#dialog').open)renderAside();
    }catch(e){if(!w.closed&&!w.offline){w.offline=true;toast(e.message,true);}}
  },60000);
  const beforeUnload=e=>{if(w.dirty||w.layoutDirty){e.preventDefault();e.returnValue='';}};
  window.addEventListener('beforeunload',beforeUnload);
  const dispose=()=>{w.closed=true;clearInterval(tick);clearInterval(poll);window.removeEventListener('beforeunload',beforeUnload);};
  dispose.hasDraft=()=>w.dirty||w.layoutDirty;
  return dispose;
}
