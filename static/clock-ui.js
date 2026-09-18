import {state,t,$,api,appNow,fmt,jstInput,toISO,openDialog,field,input,toast,icon} from './ui.js';

export function updateClockDisplay(){
  const bar = $('#application-clock');
  if (!bar) return;
  const manual = state.clock?.mode === 'manual';
  bar.classList.toggle('manual', manual);
  $('#clock-mode',bar).textContent = manual ? t('Demo date','デモ日時') : t('System date','システム日時');
  $('#clock-time',bar).textContent = `${fmt(appNow(),{year:'numeric',second:'2-digit'})} JST`;
  const dateChip = $('.topbar .date-chip');
  if (dateChip) dateChip.innerHTML = `${icon('calendar',15)}${fmt(appNow(),{year:'numeric',hour:undefined,minute:undefined})} · JST`;
}

export async function clockDialog(){
  try {
    const clock = await api('/api/clock',{activity:false});
    openDialog({title:t('Application date & time','アプリの日時'),submit:t('Apply date','日時を適用'),
      body:`<p>${t('This date is shared by every patient and open window. The clock continues running from the time you choose and is remembered after a restart.','この日時は全患者・全画面で共通です。選択した日時から時計が進み、再起動後も保持されます。')}</p>
        ${field(t('Clock mode','時計モード'),`<select name="mode"><option value="system" ${clock.mode==='system'?'selected':''}>${t('Use system date','システム日時を使用')}</option><option value="manual" ${clock.mode==='manual'?'selected':''}>${t('Choose demonstration date','デモ日時を指定')}</option></select>`)}
        ${field(t('Demonstration date and time (JST)','デモ日時（日本時間）'),input('now',jstInput(),'datetime-local','min="2000-01-01T09:00" max="2100-12-31T23:59" required'))}
        <p>${t('Countdowns, candidates, photo freshness, appointments, calendars and new-entry times use this clock. Existing records keep their saved dates. Moving forward may make a photo too old; upload a new demonstration photo for that visit.','休止時間・候補・写真の有効期限・予約・カレンダー・新規入力はこの時計を使用します。既存記録の日時は変わりません。日付を進めて写真が古くなった場合は、その訪問用のデモ写真を追加してください。')}</p>`,
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
