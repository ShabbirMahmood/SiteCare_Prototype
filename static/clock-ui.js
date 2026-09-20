import {state,t,$,api,appNow,fmt,jstInput,toISO,openDialog,field,input,toast,icon} from './ui.js';

export function updateClockDisplay(){
  const bar = $('#application-clock');
  if (!bar) return;
  const manual = state.clock?.mode === 'manual';
  bar.classList.toggle('manual', manual);
  $('#clock-mode',bar).textContent = manual ? t('Demo Date','デモ日時') : t('System Date','システム日時');
  $('#clock-time',bar).textContent = `${fmt(appNow(),{year:'numeric',second:'2-digit'})} JST`;
  const dateChip = $('.topbar .date-chip');
  if (dateChip) dateChip.innerHTML = `${icon('calendar',15)}${fmt(appNow(),{year:'numeric',hour:undefined,minute:undefined})} · JST`;
  const keep = $('#keep-calibration');
  if (keep && !keep.disabled) keep.checked = Boolean(state.settings?.keep_calibration);
  const status = $('#calibration-policy');
  if (status) status.textContent = state.settings?.keep_calibration
    ? t('Verified photos can be reused beyond 24 hours. New uploads require calibration.','確認済み写真は24時間後も再利用できます。新しい写真は校正が必要です。')
    : t('24-hour photo limit. New visit photos require calibration.','写真の有効期限は24時間です。新しい訪問写真は校正が必要です。');
}

export async function changeCalibrationPolicy(event){
  const checkbox = event.currentTarget, enabled = checkbox.checked;
  checkbox.disabled = true;
  try {
    await api('/api/settings',{method:'POST',data:{keep_calibration:enabled,revision:state.settings.revision}});
    localStorage.setItem('sitecare-settings-changed',String(Date.now()));
    toast(enabled?t('Keep Calibration enabled for all patients.','全患者で校正の保持を有効にしました。'):t('Keep Calibration disabled. The 24-hour photo limit applies now.','校正の保持を無効にしました。24時間の有効期限が直ちに適用されます。'));
  } catch(error) {toast(error.message,true);}
  finally {checkbox.disabled=false;checkbox.checked=Boolean(state.settings?.keep_calibration);updateClockDisplay();}
}

export async function clockDialog(){
  try {
    const clock = await api('/api/clock',{activity:false});
    openDialog({title:t('Application Date & Time','アプリの日時'),submit:t('Apply Date','日時を適用'),
      body:`<p>${t('This date is shared by every patient and open window. The clock continues running from the time you choose and is remembered after a restart.','この日時は全患者・全画面で共通です。選択した日時から時計が進み、再起動後も保持されます。')}</p>
        ${field(t('Clock Mode','時計モード'),`<select name="mode"><option value="system" ${clock.mode==='system'?'selected':''}>${t('Use System Date','システム日時を使用')}</option><option value="manual" ${clock.mode==='manual'?'selected':''}>${t('Choose Demonstration Date','デモ日時を指定')}</option></select>`)}
        ${field(t('Demonstration Date And Time (JST)','デモ日時（日本時間）'),input('now',jstInput(),'datetime-local','min="2000-01-01T09:00" max="2100-12-31T23:59" required'))}
        <p>${t('Countdowns, candidates, photo freshness, appointments, calendars and new-entry times use this clock. Existing records keep their saved dates. With Keep Calibration off, moving forward beyond 24 hours requires a new calibrated photo. With it on, an existing verified photo remains usable.','休止時間・候補・写真の有効期限・予約・カレンダー・新規入力はこの時計を使用します。既存記録の日時は変わりません。「校正を保持」がオフの場合、撮影後24時間を超えると新しい校正済み写真が必要です。オンの場合は確認済み写真を引き続き使用できます。')}</p>`,
      onOpen:form=>{
        const mode = $('[name=mode]',form), date = $('[name=now]',form);
        const toggle=()=>{date.disabled=mode.value==='system';};
        mode.addEventListener('change',toggle); toggle();
      },
      onSubmit:async f=>{
        await api('/api/clock',{method:'POST',data:{mode:f.get('mode'),now:toISO(f.get('now')),revision:clock.revision}});
        localStorage.setItem('sitecare-clock-changed',String(Date.now()));
        toast(t('Application date updated.','アプリの日時を更新しました。'));
      }});
  } catch(e){toast(e.message,true);}
}
