import {appNow,state,t,esc,$,$$,api,icon,toast,fmt,dayKey,jstInput,toISO,openDialog,field,input,check,badge,appointmentBadge} from './ui.js';
import {mountWorkspace} from './workspace.js';
import {clockDialog,updateClockDisplay} from './clock-ui.js';

let dispose = null, routeSequence = 0;
const go = path => { if (location.hash === `#${path}`) renderRoute(); else location.hash = path; };
const languageButton = () => `<button class="language-button" id="language">${state.lang==='ja'?'EN / 日本語':'日本語 / EN'}</button>`;

function bindLanguage(){
  $('#language')?.addEventListener('click', () => {
    state.lang = state.lang === 'ja' ? 'en' : 'ja';
    localStorage.setItem('sitecare-language', state.lang);
    document.documentElement.lang = state.lang;
    if (state.user) {shell(); renderRoute();} else loginPage(window.sitecareSetup);
  });
}
function shell(){
  document.documentElement.lang = state.lang;
  const nav = [['dashboard',t('Overview','ホーム')],['patients',t('Patients','患者一覧')],['calendar',t('Appointments','予約カレンダー')],
    ['history',t('Audit trail','監査ログ')],['settings',t('Settings & data','設定・データ')],['help',t('Workflow guide','使い方ガイド')]];
  $('#app').innerHTML = `<div class="app-shell"><aside class="sidebar"><div class="brand"><div class="brand-mark">S</div><div class="brand-text"><h2>SiteCare</h2><small>${t('PUNCTURE SITE WORKSPACE','穿刺部位管理ワークスペース')}</small></div></div>
    <nav><div class="nav-section">${t('WORKSPACE','ワークスペース')}</div>${nav.filter(([key])=>key!=='history'||state.user.role==='admin').map(([key,label])=>`<button class="nav-item" data-route="${key}" title="${label}">${icon(key)}<span class="nav-label">${label}</span></button>`).join('')}</nav>
    <div class="sidebar-bottom"><div class="local-card"><div class="row">${icon('shield',15)}${t('Stored on this computer','このPCに保存')}</div>${t('Local files. No cloud upload.','外部クラウドへの送信なし。')}</div>
    <div class="user-card"><div class="avatar">${esc(state.user.display_name.slice(0,2).toUpperCase())}</div><div class="user-info"><strong>${esc(state.user.display_name)}</strong><small>${state.user.role==='admin'?t('Administrator','管理者'):t('Nurse','看護師')}</small></div></div></div></aside>
    <div class="main-shell"><header class="topbar"><div class="topbar-path" id="breadcrumb">${t('Workspace','ワークスペース')}</div><div class="topbar-actions"><span class="environment-tag">PROTOTYPE</span><span class="date-chip">${icon('calendar',15)}${fmt(appNow(),{year:'numeric',month:'short',day:'numeric',hour:undefined,minute:undefined})} · JST</span>${languageButton()}<button class="icon-button logout-button" id="logout" aria-label="${t('Sign out','ログアウト')}">${icon('logout',18)}</button></div></header><div class="application-clock" id="application-clock"><div><strong id="clock-mode"></strong><span id="clock-time"></span></div>${state.user.role==='admin'?`<button class="button secondary small-button" id="change-clock">${icon('calendar',16)}${t('Change date','日時を変更')}</button>`:''}<span id="clock-pending" class="hidden">${t('Date changed. Finish or close your current edit to refresh this view.','日時が変更されました。編集中の画面を保存または閉じると更新されます。')}</span></div><main class="main-content" id="main"></main></div></div>`;
  $$('[data-route]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.route)));
  $('#logout').addEventListener('click',async()=>{try{await api('/api/logout',{method:'POST'});}catch{}state.user=null;if(dispose)dispose();await boot();});
  bindLanguage();
  $('#change-clock')?.addEventListener('click',clockDialog);
  updateClockDisplay();
}

function loginPage(setup){
  window.sitecareSetup = setup;
  document.documentElement.lang=state.lang;
  $('#app').innerHTML = `<div class="login-page"><section class="login-art"><div class="brand"><div class="brand-mark">S</div><div><h2>SiteCare</h2><small>PUNCTURE SITE WORKSPACE</small></div></div>
    <div class="eyebrow">${t('A clearer picture of every site','一つひとつの部位を、見える記録に')}</div><h1>${t('One patient.<br>One shared picture.<br>Every site, remembered.','患者ごとの写真で、<br>穿刺部位を<br>ひとつに管理。')}</h1>
    <p>${t('Replace the tracing sheet with a photo-aligned record of puncture sites, skin observations and upcoming visits.','透明フィルムの記録を、写真に重ねるデジタル記録へ。穿刺履歴、皮膚所見、次回予定を一画面で確認できます。')}</p>
    <svg class="login-visual" viewBox="0 0 320 200" aria-hidden="true"><rect x="20" y="10" width="280" height="180" rx="18" fill="#ffffffbb" stroke="#d1e3d9"/><circle cx="160" cy="100" r="46" fill="none" stroke="#c7dace" stroke-dasharray="5 5"/><path d="M70 52q-25 48 0 96m180-96q25 48 0 96" fill="none" stroke="#abc8b8" stroke-width="2"/><circle cx="160" cy="100" r="5" fill="#668a7c"/>${[[160,43,1,'#91b7e5'],[208,66,2,'#8ac8ab'],[224,113,3,'#91b7e5'],[182,154,4,'#d9989e'],[130,150,5,'#8ac8ab'],[101,98,6,'#8ac8ab']].map(([x,y,n,c])=>`<circle cx="${x}" cy="${y}" r="16" fill="${c}" fill-opacity=".5" stroke="${c}"/><text x="${x}" y="${y+4}" text-anchor="middle" fill="#41675b" font-family="sans-serif" font-size="12">${n}</text>`).join('')}</svg>
    <div class="art-footer">LOCAL-FIRST · JAPAN STANDARD TIME · HUMAN REVIEW</div></section>
    <section class="login-side"><div class="login-language">${languageButton()}</div><h2>${setup?t('Create your local workspace','初期設定'):t('Welcome back','ログイン')}</h2><p>${setup?t('Create the administrator account for this computer. There is no default password.','このPCで使用する管理者アカウントを作成します。初期パスワードはありません。'):t('Sign in to view your patient records.','アカウントにログインして患者記録を開きます。')}</p>
    <form id="login-form" class="login-form">${field(t('Username','ユーザー名'),input('username','','text','required maxlength="60" autocomplete="username"'))}
    ${setup?field(t('Your display name','記録者名'),input('display_name','','text','required maxlength="100" autocomplete="name"')):''}
    ${field(t('Password','パスワード'),input('password','','password',`required ${setup?'minlength="12"':''} maxlength="128" autocomplete="${setup?'new-password':'current-password'}"`),setup?t('At least 12 characters. Save it in a password manager.','12文字以上。安全に保管してください。'):'')}
    <div class="form-error hidden" role="alert"></div><button class="button primary full" type="submit">${setup?t('Create workspace','作成して開始'):t('Sign in','ログイン')}${icon('arrow',17)}</button></form>
    <div class="notice warning">${icon('alert',17)}<span>${t('Prototype for evaluation with synthetic or de-identified data. Not a validated medical device or a substitute for bedside assessment.','試作評価用です。架空・匿名化データを使用してください。医療機器として未検証であり、実際の皮膚評価に代わるものではありません。')}</span></div><div class="form-foot">${t('Your records stay in this installation’s data folder. No patient data is sent to an external service.','記録はこのPCの data フォルダーに保存されます。外部サービスへの患者データ送信はありません。')}</div></section></div>`;
  bindLanguage();
  $('#login-form').addEventListener('submit',async event=>{
    event.preventDefault();const form=event.currentTarget,b=$('button[type=submit]',form),err=$('.form-error',form);b.disabled=true;err.classList.add('hidden');
    try{const data=Object.fromEntries(new FormData(form)), result=await api(setup?'/api/setup':'/api/login',{method:'POST',data});state.user=result.user;state.csrf=result.csrf;shell();if(!location.hash)location.hash='dashboard';else renderRoute();}
    catch(e){err.textContent=e.message;err.classList.remove('hidden');}finally{b.disabled=false;}
  });
}

async function renderRoute(){
  if(!state.user)return;
  const sequence=++routeSequence;
  if(dispose){dispose();dispose=null;}
  const route=(location.hash.slice(1)||'dashboard'), main=$('#main');
  $$('[data-route]').forEach(b=>b.classList.toggle('active',b.dataset.route===(route.startsWith('patient/')?'patients':route)));
  main.innerHTML=`<div class="empty-state"><span class="muted">${t('Loading…','読み込み中…')}</span></div>`;
  const titles={dashboard:t('Overview','ホーム'),patients:t('Patients','患者一覧'),calendar:t('Appointments','予約カレンダー'),settings:t('Settings & data','設定・データ'),history:t('Audit trail','監査ログ'),help:t('Workflow guide','使い方ガイド')};
  $('#breadcrumb').innerHTML=`SiteCare ${icon('chevron',12)} <span>${titles[route]||t('Patient workspace','患者ワークスペース')}</span>`;
  try{
    if(route.startsWith('patient/')){
      const pid=Number(route.split('/')[1]);if(!Number.isInteger(pid)||pid<1)throw new Error(t('Patient not found.','患者が見つかりません。'));
      dispose=await mountWorkspace(main,pid,{go,editProfile,editAppointment});return;
    }
    if(route==='help'){renderHelp(main);return;}
    if(route==='settings'){await renderSettings(main);return;}
    if(route==='history'){await renderAudit(main);return;}
    if(route==='calendar'){await renderCalendar(main);return;}
    const result=await api('/api/patients'); if(sequence!==routeSequence)return;
    state.now=result.now;
    if(route==='patients')renderPatients(main,result.patients); else renderDashboard(main,result.patients);
  }catch(e){if(sequence===routeSequence)main.innerHTML=`<div class="card page-error"><div class="notice danger">${icon('alert')}<span>${esc(e.message)}</span></div><button class="button secondary mt-16" id="retry">${t('Retry','再試行')}</button></div>`;$('#retry')?.addEventListener('click',renderRoute);}
}

function addPatient(){
  openDialog({title:t('Create patient profile','患者プロフィールを作成'),submit:t('Create profile','プロフィール作成'),body:
    `<p>${t('Use your institution’s patient ID and a minimal display label. Avoid unnecessary identifying details in this prototype.','施設の患者IDと必要最小限の表示名を使用してください。この試作版に不要な個人情報を入れないでください。')}</p>
    <div class="form-grid">${field(t('Patient ID','患者ID'),input('code','','text','required maxlength="64" placeholder="P-0001"'))}${field(t('Display label','表示名'),input('alias','','text','required maxlength="100"'))}</div>
    ${field(t('Therapy / protocol label (optional)','治療・手順名（任意）'),input('therapy','','text','maxlength="150"'),t('Medication-neutral; no drug or dose recommendations.','薬剤や投与量の提案は行いません。'))}
    ${field(t('First appointment (JST)','初回予定日時（日本時間）'),input('start_at',jstInput(),'datetime-local','required'))}
    ${field(t('Care notes','ケアメモ'),'<textarea name="notes" maxlength="2000"></textarea>')}`,
    onSubmit:async f=>{const d=Object.fromEntries(f);d.start_at=toISO(d.start_at);const result=await api('/api/patients',{method:'POST',data:d});toast(t('Patient profile created.','患者プロフィールを作成しました。'));go(`patient/${result.id}`);}});
}
function editProfile(p,onDone){
  openDialog({title:t('Patient profile','患者プロフィール'),body:`<p><span class="chip-id">${esc(p.code)}</span> ${t('Patient ID is permanent in this prototype.','この試作版では患者IDは固定です。')}</p>
    ${field(t('Display label','表示名'),input('alias',p.alias,'text','required maxlength="100"'))}${field(t('Therapy / protocol label','治療・手順名'),input('therapy',p.therapy,'text','maxlength="150"'))}
    ${field(t('Care notes','ケアメモ'),`<textarea name="notes" maxlength="2000">${esc(p.notes)}</textarea>`)}${check('active',t('Active patient — include in appointment suggestions','管理中の患者として予約提案に含める'),p.active)}`,
    onSubmit:async f=>{await api(`/api/patients/${p.id}`,{method:'PATCH',data:{...Object.fromEntries(f),active:f.has('active'),version:p.version}});toast(t('Profile updated.','プロフィールを更新しました。'));await onDone();}});
}
function editAppointment(p,onDone){
  const ap=p.appointment;
  openDialog({title:t('Confirm next appointment','次回予約を確認'),body:`<p><strong>${esc(p.code)}</strong> · ${esc(p.alias)}</p>
    <div class="notice warning mb-16">${icon('clock',17)}<span>${t('Protocol due time:','手順上の予定期限：')} <strong>${fmt(ap.due_at)}</strong> JST.<br>${t('Moving an appointment does not change or clear this due time.','予約日時を変更しても、予定期限や期限超過の表示は消えません。')}</span></div>
    ${field(t('Scheduled date and time (JST)','予約日時（日本時間）'),input('scheduled_at',jstInput(new Date(ap.scheduled_at)>new Date(appNow())?ap.scheduled_at:appNow()+3600000),'datetime-local','required'))}
    ${field(t('Schedule change / confirmation note','変更理由・確認メモ'),'<textarea name="reason" maxlength="2000"></textarea>',t('Required when changing the suggested time.','提案日時から変更する場合は理由が必要です。'))}`,
    submit:t('Confirm appointment','予約を確定'),onSubmit:async f=>{await api(`/api/patients/${p.id}/appointment`,{method:'POST',data:{version:p.version,scheduled_at:toISO(f.get('scheduled_at')),reason:f.get('reason')}});toast(t('Appointment confirmed.','予約を確定しました。'));await onDone();}});
}
function bindOpenPatients(root){
  $$('[data-patient]',root).forEach(el=>{el.addEventListener('click',()=>go(`patient/${el.dataset.patient}`));if(el.tagName==='TR'){el.tabIndex=0;el.addEventListener('keydown',e=>{if(e.key==='Enter')go(`patient/${el.dataset.patient}`);});}});
}
function patientTable(patients,compact=false){
  if(!patients.length)return `<div class="empty-state"><div class="empty-icon">${icon('patients',28)}</div><h3>${t('Your first patient starts here','最初の患者を登録しましょう')}</h3><p>${t('Create a profile, upload an abdominal photo and align the 14-site map.','プロフィールを作成して腹部写真をアップロードし、14部位のマップを合わせます。')}</p><button class="button primary new-patient">${icon('plus',17)}${t('Create patient','患者を登録')}</button></div>`;
  return `<div class="table-wrap"><table><thead><tr><th>${t('Patient','患者')}</th><th>${t('Next visit · JST','次回予約・日本時間')}</th><th>${t('Skin review','皮膚所見')}</th>${compact?'':`<th>${t('Site availability','部位の状況')}</th>`}<th></th></tr></thead><tbody>${patients.map(p=>`<tr class="clickable-row" data-patient="${p.id}"><td><div class="patient-name"><div class="avatar square">${esc(p.code.slice(-2))}</div><div><div class="name">${esc(p.alias)}</div><div class="sub mono">${esc(p.code)} ${p.demo?`<span class="demo-tag">DEMO</span>`:''} ${!p.active?t('· Inactive','・管理終了'):''}</div></div></div></td>
    <td><div class="name nowrap">${fmt(p.appointment?.scheduled_at)}</div><div class="sub">${appointmentBadge(p.appointment,p.overdue)}</div></td><td>${p.active_alerts?badge('blocked',`${p.active_alerts} ${t('active','未回復')}`):badge('eligible',t('No active alerts','注意部位なし'))}${p.review_count?`<div class="sub">${t('Recurring issue review','反復所見の再評価')}</div>`:''}</td>
    ${compact?'':`<td><div class="status-grid">${Array.from({length:14},(_,i)=>`<span class="mini-site ${i<p.resting_count?'resting':i<p.resting_count+p.eligible_count?'eligible':'unverified'}"></span>`).join('')}</div><div class="sub">${p.eligible_count}/14 ${t('rule-eligible','条件適合')}</div></td>`}<td>${icon('chevron',15)}</td></tr>`).join('')}</tbody></table></div>`;
}
function renderPatients(main,patients){
  main.innerHTML=`<div class="page-head"><div><div class="eyebrow">${t('PATIENT DIRECTORY','患者管理')}</div><h1>${t('Patients','患者一覧')}</h1><p>${t('One persistent profile. A complete record across every visit.','患者ごとに一つのプロフィール。毎回の訪問記録を継続管理します。')}</p></div><button class="button primary new-patient">${icon('plus',18)}${t('Create patient','患者を登録')}</button></div>
    <div class="card"><div class="card-head"><div class="search-field">${icon('search',18)}<input id="patient-search" placeholder="${t('Search ID or display label…','ID・表示名で検索…')}" aria-label="${t('Search patients','患者検索')}"></div><span class="muted small">${patients.length} ${t('profiles','件')}</span></div><div id="patient-results">${patientTable(patients)}</div></div><p class="data-note">${t('Blue = 12-day rest. Red = active skin concern or review hold. Green = configured rules met; bedside assessment is still required.','青：12日間の休止。赤：未回復の皮膚所見・再評価待ち。緑：設定条件に適合（実際の皮膚評価は必要です）。')}</p>`;
  const bind=()=>{$$('.new-patient',main).forEach(b=>b.addEventListener('click',addPatient));bindOpenPatients(main);};bind();
  $('#patient-search').addEventListener('input',e=>{const q=e.target.value.toLowerCase();$('#patient-results').innerHTML=patientTable(patients.filter(p=>`${p.code} ${p.alias}`.toLowerCase().includes(q)));bindOpenPatients($('#patient-results'));$('.new-patient',$('#patient-results'))?.addEventListener('click',addPatient);});
}
async function loadDemo(){
  openDialog({title:t('Load synthetic demonstration','架空データを読み込む'),body:`<p>${t('This adds three fictional profiles and a schematic abdominal image. No supplied patient photographs are included. Demo data is clearly labelled.','架空の患者3件と模式図を追加します。提供された実患者の写真は含まれません。すべてデモとして表示されます。')}</p>`,submit:t('Load demo','デモを読み込む'),onSubmit:async()=>{const d=await api('/api/demo',{method:'POST'});go(`patient/${d.id}`);}});
}
function renderDashboard(main,patients){
  const active=patients.filter(p=>p.active),today=dayKey(),todayP=active.filter(p=>dayKey(p.appointment?.scheduled_at)===today),overdue=active.filter(p=>p.overdue),alerts=active.reduce((a,p)=>a+p.active_alerts,0);
  const upcoming=active.filter(p=>new Date(p.appointment.scheduled_at)>=new Date(appNow())).sort((a,b)=>a.appointment.scheduled_at.localeCompare(b.appointment.scheduled_at)), next=upcoming[0];
  const stats=[['calendar',t('Due today','本日の予定'),todayP.length,t(`${overdue.length} overdue to review`,`${overdue.length} 件の期限超過を確認`),''],['clock',t('Next 7 days','今後7日間'),upcoming.filter(p=>new Date(p.appointment.scheduled_at)-appNow()<7*86400000).length,t('Next unresolved visits','次回未実施の予約'),'blue'],['alert',t('Active skin alerts','未回復の皮膚所見'),alerts,t('Remain blocked until recovered','回復確認まで使用不可'),'red'],['patients',t('Active patients','管理中の患者'),active.length,t('Profiles stored locally','プロフィールをローカル保存'),'']];
  main.innerHTML=`<div class="page-head"><div><div class="eyebrow">${t('YOUR CARE WORKSPACE','ケアワークスペース')}</div><h1>${t('Today, at a glance','本日の状況')}</h1><p>${t('Keep track of every site, skin observation and upcoming visit.','穿刺部位、皮膚所見、次回予約をまとめて確認。')}</p></div><button class="button primary new-patient">${icon('plus',18)}${t('Create patient','患者を登録')}</button></div>
    <div class="stat-grid">${stats.map(([ic,label,count,foot,color])=>`<div class="card stat-card"><div class="stat-top"><span>${label}</span><span class="stat-icon ${color}">${icon(ic,18)}</span></div><div class="stat-value">${count}</div><div class="stat-foot">${foot}</div></div>`).join('')}</div>
    <div class="dashboard-grid"><div class="stack"><section class="card"><div class="card-head"><h2>${t('Patient workspace','患者ワークスペース')}</h2><button class="button ghost small-button" id="view-all">${t('View all','すべて見る')}${icon('arrow',15)}</button></div>${patientTable(patients.slice(0,8),true)}${patients.length?`<div class="table-footer">${t('Select a patient to open their photo and site map.','患者を選択すると写真と部位マップを開きます。')}</div>`:''}</section>
    <div class="notice warning">${icon('shield',19)}<span><strong>${t('Human review, always.','必ず看護師が確認。')}</strong> ${t('A green marker means the recorded rules are met, not that insertion is clinically safe. Check the actual skin, identity and physical distances.','緑色は記録上の条件適合を示すもので、穿刺の安全性を保証しません。皮膚、本人確認、実際の距離を確認してください。')}</span></div>
    ${!patients.length&&state.user.role==='admin'?`<div class="notice"><span>${t('Try the complete workflow without patient data.','実患者データなしで操作を試せます。')}</span><button class="button secondary small-button" id="demo-load">${t('Load demo','デモを読み込む')}</button></div>`:''}</div>
    <aside class="stack"><section class="card next-card"><div class="card-body"><div class="eyebrow">${t('NEXT SUGGESTED VISIT','次の訪問予定')}</div>${next?`<div class="spaced mt-16"><div><div class="next-day">${fmt(next.appointment.scheduled_at,{day:'numeric',month:undefined,hour:undefined,minute:undefined})}</div><div class="next-month">${fmt(next.appointment.scheduled_at,{month:'long',weekday:'long',day:undefined,hour:undefined,minute:undefined})}</div></div><div class="next-time">${fmt(next.appointment.scheduled_at,{month:undefined,day:undefined})}<small> JST</small></div></div><div class="next-detail"><h3>${esc(next.alias)}</h3><p class="small mono mt-16">${esc(next.code)}</p><button class="button primary full mt-16" data-patient="${next.id}">${t('Open patient','患者を開く')}${icon('arrow',16)}</button></div>`:`<p class="small mt-16">${t('New visits appear here after you create a profile or record a puncture.','患者登録・穿刺記録後に次の予定が表示されます。')}</p>`}</div></section>
    <section class="card"><div class="card-body"><h3>${t('Rotation at a glance','部位ローテーションの目安')}</h3>${[['3',t('Every 3 days','3日ごと'),t('Next visit suggestion','次回予定を自動提案')],['12',t('12-day rest','12日間の休止'),t('Exact date and time countdown','日時からカウントダウン')],['2.5',t('2.5 cm spacing','2.5 cm以上の間隔'),t('From sites used in the last 12 days','過去12日間の穿刺部位から')],['5',t('5 cm from navel','臍から5 cm以上'),t('Calibrated estimate; measure on body','校正値は推定・身体で計測')]].map(([n,title,sub])=>`<div class="step-rule"><div class="rule-number">${n}</div><div><strong>${title}</strong><p>${sub}</p></div></div>`).join('')}</div></section></aside></div>`;
  $$('.new-patient',main).forEach(b=>b.addEventListener('click',addPatient));$('#view-all').addEventListener('click',()=>go('patients'));$('#demo-load')?.addEventListener('click',loadDemo);bindOpenPatients(main);
}

async function renderCalendar(main,month=new Date(appNow()+9*3600000).toISOString().slice(0,7)){
  const result=await api(`/api/appointments?month=${month}`), patients=result.patients, today=dayKey(), actual=result.items.filter(i=>i.next), overdue=actual.filter(i=>i.overdue);
  const days=Array.from({length:42},(_,i)=>{const d=new Date(`${result.grid_start}T00:00:00+09:00`);d.setUTCDate(d.getUTCDate()+i);return dayKey(d);});
  main.innerHTML=`<div class="page-head"><div><div class="eyebrow">${t('VISIT PLANNING','訪問計画')}</div><h1>${t('Appointments','予約カレンダー')}</h1><p>${t('The next visit is suggested 72 hours after the latest recorded puncture.','最後の穿刺記録から72時間後を次回予定として提案します。')}</p></div><button class="button secondary" id="calendar-today">${t('This month','今月')}</button></div>
    ${overdue.length?`<div class="notice danger mb-16">${icon('alert',18)}<span><strong>${overdue.length} ${t('overdue visit(s)','件の期限超過')}</strong> · ${t('Unresolved due dates stay visible even when appointments are moved.','予約を移動しても、未実施の予定期限は保持されます。')}</span></div>`:''}
    <div class="calendar-layout"><section class="card calendar-card"><div class="calendar-head"><h2>${fmt(`${month}-01T12:00:00+09:00`,{year:'numeric',month:'long',day:undefined,hour:undefined,minute:undefined})}</h2><div class="row"><button class="icon-button" id="prev-month" aria-label="${t('Previous month','前月')}">${icon('back',18)}</button><input type="month" id="calendar-month" value="${month}" aria-label="${t('Month','月')}" style="min-height:33px;padding:5px;font-size:15px"><button class="icon-button" id="next-month" aria-label="${t('Next month','翌月')}">${icon('arrow',18)}</button></div></div>
    <div class="calendar-grid">${t(['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],['月','火','水','木','金','土','日']).map(d=>`<div class="calendar-weekday">${d}</div>`).join('')}${days.map(day=>{const items=result.items.filter(i=>dayKey(i.at)===day);return `<div class="calendar-cell ${day.slice(0,7)!==month?'off':''} ${day===today?'today':''}"><div class="day-number">${Number(day.slice(-2))}</div>${items.slice(0,5).map(i=>`<button class="calendar-event ${i.kind} ${i.overdue?'overdue':''}" data-appt="${i.patient_id}" title="${esc(i.alias)} · ${fmt(i.at)} · ${i.kind}">${fmt(i.at,{month:undefined,day:undefined})} ${esc(i.code)}${i.kind==='projection'?' ◌':''}${i.kind==='completed'?' ✓':''}</button>`).join('')}${items.length>5?`<small class="muted">+${items.length-5}</small>`:''}</div>`;}).join('')}</div>
    <div class="calendar-legend"><span><span class="legend-swatch green"></span>${t('Next appointment','次回予約')}</span><span><span class="projected-dot"></span>${t('3-day projection; not booked','3日間隔の予測・未予約')}</span><span><span class="legend-swatch blue"></span>${t('Recorded puncture','穿刺記録')}</span></div></section>
    <aside class="stack"><section class="card"><div class="card-head"><h2>${t('Next visits','次回予約一覧')}</h2><span class="small muted">JST</span></div>${actual.length?actual.sort((a,b)=>a.at.localeCompare(b.at)).map(i=>`<div class="day-agenda"><div class="spaced"><span class="time">${fmt(i.at)}</span>${i.overdue?badge('blocked',t('Overdue','期限超過')):''}</div><div class="name">${esc(i.alias)}</div><div class="small mono muted">${esc(i.code)}</div><div class="row mt-16"><button class="button secondary small-button" data-appt="${i.patient_id}">${t('Confirm / change','確認・変更')}</button><button class="button ghost small-button" data-patient="${i.patient_id}">${t('Open','開く')}${icon('arrow',13)}</button></div></div>`).join(''):`<div class="card-body"><p class="small">${t('Create a patient to start scheduling.','患者登録後に予定が表示されます。')}</p></div>`}</section>
    <div class="notice warning">${icon('clock',17)}<span>${t('Dashed entries are forecasts, not confirmed bookings. A new actual puncture resets the next due time. Earlier changes may be necessary under the treating team’s protocol.','点線は予測で、確定予約ではありません。新しい穿刺記録で次回期限が更新されます。医療チームの手順により早めの交換が必要な場合があります。')}</span></div></aside></div>`;
  const change=delta=>{const d=new Date(`${month}-01T12:00:00Z`);d.setUTCMonth(d.getUTCMonth()+delta);renderCalendar(main,d.toISOString().slice(0,7)).catch(e=>toast(e.message,true));};
  $('#prev-month').addEventListener('click',()=>change(-1));$('#next-month').addEventListener('click',()=>change(1));$('#calendar-today').addEventListener('click',()=>renderCalendar(main));$('#calendar-month').addEventListener('change',e=>{if(e.target.value)renderCalendar(main,e.target.value);});
  $$('[data-appt]',main).forEach(b=>b.addEventListener('click',()=>{const p=patients.find(p=>p.id===Number(b.dataset.appt));editAppointment(p,()=>renderCalendar(main,month));}));bindOpenPatients(main);
}

async function renderSettings(main){
  const admin=state.user.role==='admin',users=admin?(await api('/api/users')).users:[];
  main.innerHTML=`<div class="page-head"><div><div class="eyebrow">${t('LOCAL WORKSPACE','ローカルワークスペース')}</div><h1>${t('Settings & data','設定・データ')}</h1><p>${t('Simple local storage, named users and portable backups.','簡単なローカル保存、記録者アカウント、バックアップ。')}</p></div></div>
    <div class="settings-grid"><section class="card"><div class="card-head"><h2>${t('Your local data','ローカルデータ')}</h2>${icon('folder',20)}</div><div class="card-body"><p>${t('SQLite stores patient profiles, exact points, observations and audit records. Photographs are stored separately in the same data folder.','SQLiteにプロフィール、穿刺点、皮膚所見、監査記録を保存します。写真は同じ data フォルダー内に別ファイルとして保存されます。')}</p><div class="metric-line"><span>${t('Database','データベース')}</span><strong class="mono">data/sitecare.sqlite3</strong></div><div class="metric-line"><span>${t('Photographs','写真')}</span><strong class="mono">data/photos/</strong></div><div class="metric-line"><span>${t('Time zone','時間帯')}</span><strong>Japan · UTC+09:00</strong></div><div class="notice warning mt-16">${icon('shield',17)}<span>${t('Files and backups are not encrypted by the app. Use approved encrypted storage, restrict PC access, and keep patient data out of consumer sync folders.','アプリ自体は保存・バックアップを暗号化しません。承認済みの暗号化保存先とPCアクセス制限を使用し、一般向け同期フォルダーを避けてください。')}</span></div>${admin?`<button class="button primary full mt-16" id="backup-download">${icon('download',17)}${t('Download complete backup','完全バックアップを取得')}</button>`:''}<p class="small mt-16">${t('To restore: stop the app, preserve the current data folder, and replace it with the backup’s data folder. See START_HERE.html.','復元：アプリを終了し、現在の data フォルダーを保管してから、バックアップ内の data に置き換えます。START_HERE.html を参照。')}</p></div></section>
    <section class="card"><div class="card-head"><h2>${t('Configured screening rules','設定されている確認条件')}</h2>${icon('shield',20)}</div><div class="card-body">${[['3 days / 72 h',t('Next visit interval','次回訪問の間隔')],['12 days / 288 h',t('Rest from recorded insertion time','記録された穿刺時刻から休止')],['2.5 cm',t('Minimum distance from recent points','直近の穿刺点からの最小距離')],['5 cm',t('Minimum distance from navel','臍からの最小距離')],['24 hours',t('Current-photo freshness limit','最新写真の撮影経過時間')]].map(([v,k])=>`<div class="metric-line"><span>${k}</span><strong>${v}</strong></div>`).join('')}<p class="mt-16">${t('Rules are intentionally not adjustable during routine use. A developer and clinical lead must review policy changes in sitecare/rules.py. Resolved skin alerts do not require an additional recurrence review.','通常操作で条件は変更できません。変更は開発者と臨床責任者が sitecare/rules.py を確認して行います。回復済みの皮膚注意領域に追加の反復所見再評価は不要です。')}</p></div></section>
    ${admin?`<section class="card"><div class="card-head"><h2>${t('Nurse accounts','記録者アカウント')}</h2><button class="button secondary small-button" id="add-user">${icon('plus',14)}${t('Add user','追加')}</button></div><div class="table-wrap"><table><thead><tr><th>${t('Name','記録者名')}</th><th>${t('Username','ユーザー名')}</th><th>${t('Role','権限')}</th></tr></thead><tbody>${users.map(u=>`<tr><td>${esc(u.display_name)}</td><td class="mono">${esc(u.username)}</td><td>${esc(u.role)}</td></tr>`).join('')}</tbody></table></div><div class="card-body"><p class="small">${t('Password recovery is a local maintenance command:','パスワード再設定はローカルコマンドで行います：')}<br><code>python manage.py reset-password USERNAME</code></p></div></section>
    <section class="card"><div class="card-head"><h2>${t('Demonstration data','デモデータ')}</h2><span class="demo-tag">SYNTHETIC</span></div><div class="card-body"><p>${t('Load three fictional patients to explore the blue countdown, red skin region, candidate suggestions and appointment projections. The drawing is not a real abdomen photograph.','架空患者3件で、青いカウントダウン、赤い注意部位、候補提示、予約予測を確認できます。表示画像は模式図で、実患者の写真ではありません。')}</p><button class="button secondary" id="demo-load">${t('Load / open demo','デモを読み込む・開く')}${icon('arrow',16)}</button><p class="small mt-16">${t('Demo records persist, just like other records. For a clean trial, stop the app and run with a separate --data-dir.','デモ記録も保存されます。空の環境で試すにはアプリを終了して、別の --data-dir を指定してください。')}</p></div></section>`:''}</div>`;
  $('#backup-download')?.addEventListener('click',()=>openDialog({title:t('Download sensitive data','機微データのバックアップ'),body:`<p>${t('This archive includes all patient records, photos, user password hashes and the audit trail. It is NOT encrypted. Save it only to an approved secure location. Login sessions are excluded.','全患者記録・写真・パスワードハッシュ・監査記録が含まれます。暗号化されません。承認された安全な場所に保存してください。ログインセッションは含まれません。')}</p>`,submit:t('Download backup','バックアップ取得'),onSubmit:async()=>{window.location.href='/api/backup';}}));
  $('#demo-load')?.addEventListener('click',loadDemo);
  $('#add-user')?.addEventListener('click',()=>openDialog({title:t('Add nurse account','記録者アカウントを追加'),body:`${field(t('Username','ユーザー名'),input('username','','text','required maxlength="60"'))}${field(t('Display name','記録者名'),input('display_name','','text','required maxlength="100"'))}${field(t('Password','パスワード'),input('password','','password','required minlength="12" maxlength="128" autocomplete="new-password"'))}${field(t('Role','権限'),`<select name="role"><option value="nurse">${t('Nurse','看護師')}</option><option value="admin">${t('Administrator','管理者')}</option></select>`)}`,onSubmit:async f=>{await api('/api/users',{method:'POST',data:Object.fromEntries(f)});await renderSettings(main);toast(t('Account created.','アカウントを作成しました。'));}}));
}
async function renderAudit(main){
  const d=await api('/api/audit');
  main.innerHTML=`<div class="page-head"><div><div class="eyebrow">${t('ACCOUNTABILITY','記録の追跡')}</div><h1>${t('Audit trail','監査ログ')}</h1><p>${t('Latest 200 recorded changes. The local audit log is not tamper-proof.','最新200件の変更記録を表示します。ローカル監査ログは改ざん防止型ではありません。')}</p></div></div><section class="card"><div class="table-wrap"><table><thead><tr><th>JST</th><th>${t('Recorded by','記録者')}</th><th>${t('Action','操作')}</th><th>${t('Patient','患者')}</th><th>${t('Details','詳細')}</th></tr></thead><tbody>${d.items.map(a=>`<tr><td class="nowrap">${fmt(a.at)}</td><td>${esc(a.actor)}</td><td class="mono">${esc(a.action)}</td><td>${a.patient_id?`<button class="button ghost small-button" data-patient="${a.patient_id}">#${a.patient_id}</button>`:'—'}</td><td><details><summary class="small">${t('View changes','変更を見る')}</summary><div class="audit-detail">${esc(JSON.stringify(a.detail,null,2))}</div></details></td></tr>`).join('')}</tbody></table></div></section>`;bindOpenPatients(main);
}
function renderHelp(main){
  main.innerHTML=`<div class="page-head"><div><div class="eyebrow">${t('WORKFLOW GUIDE','操作ガイド')}</div><h1>${t('From photograph to record','写真から記録まで')}</h1><p>${t('A digital tracing sheet — with explicit limits and bedside review.','透明フィルムの記録をデジタル化。限界を理解し、現場で確認します。')}</p></div></div><div class="help-content"><div class="notice warning mb-16">${icon('alert',20)}<span>${t('Use this prototype only with synthetic or appropriately de-identified data. It has not been clinically validated and must not guide actual needle insertion.','架空または適切に匿名化したデータで評価してください。臨床検証されておらず、実際の穿刺判断に使用しないでください。')}</span></div><section class="card">
    <div class="help-section"><h2><span class="workflow-number">1</span>${t('Create a patient and upload a photo','患者を登録し、写真をアップロード')}</h2><p>${t('Use the same patient ID at each visit. Upload a JPEG or PNG abdominal photo with the navel, useful landmarks and a known-length ruler in the same skin plane visible. Use a consistent, front-facing, non-mirrored view and posture. Confirm authorized photo use. HEIC and video are not supported.','毎回同じ患者IDを使用します。臍・位置合わせに使う目印・皮膚と同じ平面の定規を写したJPEG/PNGをアップロードします。鏡像を避け、正面から同じ姿勢で撮影してください。写真利用の許可を確認します。HEIC・動画は非対応です。')}</p></div>
    <div class="help-section"><h2><span class="workflow-number">2</span>${t('Move the photo beneath the map','写真をマップに合わせる')}</h2><p>${t('Move photo: drag to shift the image beneath the fixed overlay. Navel: tap the actual navel to place it at the map origin. Photo size and rotation align the image; changing size clears calibration. Ruler: tap two visible ruler marks and enter their actual separation in centimetres. The app calculates pixels per centimetre. Use View zoom to inspect; it does not change measured coordinates.','「写真移動」で写真をドラッグし、固定レイヤーに合わせます。「臍」で実際の臍をタップして原点に合わせます。写真サイズ・回転で調整し、サイズ変更後は再校正します。「定規」で2点をタップし、実際の距離をcmで入力します。「表示ズーム」は確認用で、記録座標は変えません。')}</p><p>${t('Verify alignment after comparing visible historical puncture marks and stable body landmarks. Historical points are never moved independently to make a new photo fit. Once a photo is attached to a record, its saved alignment is locked; upload a new image to start another visit.','過去の穿刺痕と安定した目印を比較して位置合わせを確認します。新しい写真に合わせるために履歴点だけを移動しないでください。記録に紐づいた写真の位置合わせは固定されます。次の訪問では新しい写真を使用します。')}</p></div>
    <div class="help-section"><h2><span class="workflow-number">3</span>${t('Review the map and exact point','マップと実際の穿刺点を確認')}</h2><p>${t('Tap any of the 14 numbered buttons to inspect its status. Green means the configured checks are met; blue means a 12-day rest; red means an active alert or distance/visibility exclusion. Gray means the photo is not current and verified. Up to three rule-screened candidates are shown, not guaranteed-safe sites.','14個の番号をタップすると状態を確認できます。緑は設定条件に適合、青は12日間の休止、赤は皮膚注意・距離/表示範囲の制限です。灰色は最新写真の確認待ちです。候補は最大3部位で、安全性を保証するものではありません。')}</p><p>${t('Exact point: tap the actual location on the photo. The app assigns the nearest chart number and stores the exact point separately. It checks a 5 cm navel exclusion and 2.5 cm from every recorded puncture in the last 12 days, including points assigned to other numbers. A numbered site also rests for 12 days.','「実際の点」で写真上の位置をタップします。最も近い番号を割り当て、実際の座標も別に保存します。臍から5cm、過去12日間の全穿刺点から2.5cmを確認します。別番号の穿刺点も対象です。番号付き部位も12日間休止します。')}</p></div>
    <div class="help-section"><h2><span class="workflow-number">4</span>${t('Document, do not just toggle a colour','色の切り替えではなく、事実を記録')}</h2><p>${t('Record a completed puncture with its actual date/time, point and signed-in nurse. Confirm patient identity, the exact point, skin assessment and physical measurements. Future timestamps are rejected. Historical record mode documents an already-performed puncture, requires an explanation, and retains rule conflicts as warnings; it is never a recommendation to proceed.','実施済みの穿刺を実際の日時・位置・ログイン中の記録者名で記録します。本人、実際の点、皮膚状態、身体で計測した距離を確認してください。未来日時は記録できません。「過去の記録」では理由を入力し、条件に反した点も警告付きで残します。実施の推奨ではありません。')}</p><p>${t('An administrator can void an incorrect puncture with a reason; it remains visible in history and audit. There is no instant “make green” button.','誤った穿刺記録は管理者が理由付きで取消できます。履歴と監査には残ります。緑色に強制変更するボタンはありません。')}</p></div>
    <div class="help-section"><h2><span class="workflow-number">5</span>${t('Mark skin concerns','皮膚注意部位を記録')}</h2><p>${t('Draw alert: drag from the centre to the edge of a circular area, then choose one or more observations (redness, hardening, pain, swelling, bruising, leakage or other). Adjust its radius in centimetres. Use overlapping circles for an irregular area. Red areas persist until a nurse explicitly confirms full recovery and records an assessment. Resolved episodes do not trigger an additional review hold.','「注意領域」で中心から端へドラッグして円を描き、発赤・硬結・痛み・腫脹・皮下出血・液漏れ・その他を選択します。半径をcmで調整できます。不規則な形は複数の円で囲みます。完全回復を看護師が確認・記録するまで赤色が残ります。回復済みの所見による追加の再評価待ちはありません。')}</p></div>
    <div class="help-section"><h2><span class="workflow-number">6</span>${t('Plan, back up and protect','予定管理・バックアップ・保護')}</h2><p>${t('The next due time is the latest actual puncture plus 72 hours. Dashed calendar entries are 3-day forecasts, not bookings. Rescheduling does not erase an overdue due time. Back up the database and photographs together. Files are not encrypted by this app. Accounts expire after 30 minutes idle or 8 hours total; the server must be running for the interface to work. There are no email, SMS or background clinical alerts.','次回期限は最後の穿刺から72時間後です。点線は3日間隔の予測で、予約ではありません。予約変更で期限超過は消えません。データベースと写真はセットでバックアップします。アプリ自体はファイルを暗号化しません。30分無操作または8時間経過でログインが切れます。利用中はサーバーを起動してください。メール・SMS・バックグラウンドの臨床警告機能はありません。')}</p><h3>${t('Important measurement limitation','計測の重要な限界')}</h3><p>${t('A single 2-D photo cannot prove true surface distances or reliably track skin movement, folds, perspective, posture changes or tissue recovery. Calibration is approximate; this version has no 3-D reconstruction, automatic registration, computer-vision diagnosis or validated clinical safety margin. Manual verification does not remove these limitations.','単一の2次元写真では、真の皮膚表面距離、皮膚の移動、しわ、遠近、姿勢変化、回復を確実に判断できません。校正値は推定です。3次元復元、自動位置合わせ、画像診断、検証済み安全余裕はありません。手動確認でもこの限界はなくなりません。')}</p></div>
  </section></div>`;
}

async function boot(){
  try{const d=await api('/api/bootstrap',{activity:false});state.csrf=d.csrf;state.user=d.user;state.now=d.now;if(d.user){shell();renderRoute();}else loginPage(d.setup_needed);}
  catch(e){$('#app').innerHTML=`<div class="loading-screen"><h1>SiteCare</h1><p>${esc(e.message)}</p><button class="button secondary" id="boot-retry">${t('Retry','再試行')}</button></div>`;$('#boot-retry').addEventListener('click',boot);}
}
window.addEventListener('hashchange',renderRoute);
window.addEventListener('authlost',()=>{if(dispose)dispose();state.user=null;$('#dialog').close();boot();});
let lastHeartbeat=0, pendingClockRefresh=false;
function refreshClockView(){
  if(!state.user)return;
  updateClockDisplay();
  if(pendingClockRefresh){
    if($('#dialog').open||dispose?.hasDraft?.()){$('#clock-pending')?.classList.remove('hidden');return;}
    pendingClockRefresh=false;shell();renderRoute();
  }
}
window.addEventListener('clockchanged',()=>{pendingClockRefresh=true;setTimeout(refreshClockView,0);});
$('#dialog').addEventListener('close',refreshClockView);
setInterval(refreshClockView,1000);
const pollClock=()=>{if(state.user&&!document.hidden)api('/api/clock',{activity:false}).catch(()=>{});};
setInterval(pollClock,15000);
window.addEventListener('focus',pollClock);
window.addEventListener('storage',e=>{if(e.key==='sitecare-clock-changed')pollClock();});

window.addEventListener('pointerdown',()=>{if(state.user&&Date.now()-lastHeartbeat>60000){lastHeartbeat=Date.now();api('/api/heartbeat',{method:'POST'}).catch(()=>{});}},{passive:true});
boot();
