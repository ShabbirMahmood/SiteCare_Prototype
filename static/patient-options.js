import {t,esc,$,$$,api,openDialog,field,input,toast} from './ui.js';

export const doseNumber = value => value == null ? '—' : Number(value).toFixed(6).replace(/0+$/,'').replace(/\.$/,'');
export const doseCategory = value => ({higher:t('Higher','高用量'),standard:t('Standard','標準'),lower:t('Lower','低用量')})[value] || '—';
export const doseStatus = (rate,previous) => Math.abs(rate-previous)<0.0000005?'unchanged':rate>previous?'increased':'decreased';
export const doseBadge = status => `<strong class="dose-status ${status}">${({increased:t('Increased','増量'),decreased:t('Decreased','減量'),unchanged:t('Unchanged','変更なし')})[status]||'—'}</strong>`;

export function doseFields(dose,editable=true){
  return `<div class="dosage-card"><fieldset class="option-fieldset"><legend>${t('Drug Dosage Category','投与量区分')}</legend><div class="check-grid">${['higher','standard','lower'].map(c=>`<label class="check"><input type="radio" name="dosage_category" value="${c}" ${dose.category===c?'checked':''} ${editable?'':'disabled'} required><span>${doseCategory(c)}</span></label>`).join('')}</div></fieldset>
    <div class="dose-controls">${field(t('Drug Dosage Amount (mL/h)','投与速度（mL/h）'),input('dosage_rate',dose.rate,'number',`required min="0" max="1000" step="0.000001" ${editable?'':'readonly'}`))}${editable?`<button type="button" class="button secondary dose-minus" aria-label="${t('Decrease Dosage','投与速度を減らす')}">−</button>${field(t('Step (mL/h)','増減幅（mL/h）'),input('dosage_step',dose.step,'number','required min="0.000001" max="1000" step="0.000001"'))}<button type="button" class="button secondary dose-plus" aria-label="${t('Increase Dosage','投与速度を増やす')}">+</button>`:''}</div>
    <div class="spaced"><span class="small">${dose.previous_event_id===null?t('Initial Default Rate','初期設定速度'):t('Previous Recorded Rate','前回の記録速度')}: <span class="previous-dose">${doseNumber(dose.previous_rate)}</span> mL/h</span><span class="dose-comparison" role="status">${doseBadge(dose.status)}</span></div>
    ${field(t('Reason For Increase Or Decrease','増量・減量の理由'),`<textarea name="dosage_reason" maxlength="2000" ${editable?'':'readonly'}>${esc(dose.reason)}</textarea>`)}
    </div>`;
}

export function bindDoseFields(form,dose){
  const rate=$('[name=dosage_rate]',form), reason=$('[name=dosage_reason]',form);
  let previous=dose.previous_rate;
  const update=()=>{const status=doseStatus(Number(rate.value),previous);$('.dose-comparison',form).innerHTML=rate.value===''?t('Not Recorded','未記録'):doseBadge(status);reason.required=rate.value!==''&&status!=='unchanged';};
  rate.addEventListener('input',update);
  for(const [selector,sign] of [['.dose-minus',-1],['.dose-plus',1]]){
    $(selector,form)?.addEventListener('click',()=>{const step=$('[name=dosage_step]',form);if(!step.reportValidity()||!rate.reportValidity())return;rate.value=Math.max(0,Math.min(1000,Math.round((Number(rate.value)+sign*Number(step.value))*1e6)/1e6));update();});
  }
  update();
  return value=>{previous=value;$('.previous-dose',form).textContent=doseNumber(value);update();};
}

export function dosageDialog(data,onDone){
  const dose=data.dosage;
  openDialog({title:t('Drug Dosage','投与速度'),body:`<p><strong>${esc(data.patient.code)}</strong> · ${esc(data.patient.alias)}</p>${doseFields(dose)}<p class="small">${t('Save a preset for this patient. It becomes a recorded rate when a completed puncture is saved.','この患者の設定を保存します。実施済みの穿刺を保存した時点で投与速度の記録になります。')}</p>`,submit:t('Save Dosage Preset','投与速度設定を保存'),onOpen:form=>bindDoseFields(form,dose),onSubmit:async f=>{
    await api(`/api/patients/${data.patient.id}/dosage`,{method:'POST',data:{version:data.patient.version,category:f.get('dosage_category'),rate:Number(f.get('dosage_rate')),step:Number(f.get('dosage_step')),reason:f.get('dosage_reason')}});
    await onDone();toast(t('Patient dosage preset saved.','患者の投与速度設定を保存しました。'));
  }});
}

export function appointmentRuleDialog(data,onDone){
  const s=data.appointment_settings, days=t(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],['月曜日','火曜日','水曜日','木曜日','金曜日','土曜日','日曜日']);
  openDialog({title:t('Next Appointment Suggestion Category','次回予約の提案方法'),body:`<p><strong>${esc(data.patient.code)}</strong> · ${esc(data.patient.alias)}</p>
    <fieldset class="option-fieldset"><legend>${t('Choose One Method','方法を1つ選択')}</legend>${[['days',t('Count Days','日数で指定')],['weekdays',t('Assign Days From Week','曜日で指定')]].map(([v,l])=>`<label class="check"><input type="radio" name="mode" value="${v}" ${s.mode===v?'checked':''}><span>${l}</span></label>`).join('')}</fieldset>
    ${field(t('Days After The Previous Puncture','前回の穿刺からの日数'),input('days',s.days,'number','required min="1" max="365" step="1"'))}
    <fieldset class="option-fieldset weekdays"><legend>${t('Weekdays — Select One Or More','曜日（複数選択可）')}</legend><div class="check-grid">${days.map((d,i)=>`<label class="check"><input type="checkbox" name="weekdays" value="${i}" ${s.weekdays.includes(i)?'checked':''}><span>${d}</span></label>`).join('')}</div></fieldset>
    <p class="small">${t('Only the next visit is suggested. Weekday mode uses the next selected weekday after the puncture date, at the same Japan time. Before the first puncture, the initial appointment date is the starting point. Saving replaces the current suggestion or confirmation.','次回1件のみを提案します。曜日指定では穿刺日の翌日以降で最も近い選択曜日の同時刻（日本時間）を使用します。初回穿刺前は登録した初回予定日を基準にします。保存すると現在の提案・確定予約を置き換えます。')}</p>`,onOpen:form=>{
      const toggle=()=>{const mode=$('[name=mode]:checked',form).value;$('[name=days]',form).disabled=mode!=='days';$('.weekdays',form).disabled=mode!=='weekdays';};$$('[name=mode]',form).forEach(e=>e.addEventListener('change',toggle));toggle();
    },onSubmit:async f=>{
      await api(`/api/patients/${data.patient.id}/appointment-settings`,{method:'POST',data:{version:data.patient.version,mode:f.get('mode'),days:Number(f.get('days')||3),weekdays:f.getAll('weekdays').map(Number)}});
      await onDone();toast(t('Next appointment suggestion updated.','次回予約の提案を更新しました。'));
    }});
}
