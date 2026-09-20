export const state = { user: null, csrf: '', lang: localStorage.getItem('sitecare-language') || 'ja', now: null, clock: null, clockAnchor: null, settings: null };
export const appNow = () => state.clockAnchor ? state.clockAnchor.now + performance.now() - state.clockAnchor.received : Date.now();
export function syncClock(response) {
  const now = Date.parse(response.headers.get('X-SiteCare-Now'));
  const revision = Number(response.headers.get('X-SiteCare-Clock-Revision'));
  if (!Number.isFinite(now) || (state.clock && revision < state.clock.revision)) return;
  const changed = state.clock && state.clock.revision !== revision;
  state.clock = {mode: response.headers.get('X-SiteCare-Clock-Mode'), revision};
  state.clockAnchor = {now, received: performance.now()};
  state.now = new Date(now).toISOString();
  if (changed) window.dispatchEvent(new Event('clockchanged'));
}
export function syncSettings(response) {
  const raw = response.headers.get('X-SiteCare-Settings-Revision');
  if (raw === null) return;
  const revision = Number(raw);
  if (!Number.isFinite(revision) || (state.settings && revision < state.settings.revision)) return;
  const changed = state.settings && state.settings.revision !== revision;
  state.settings = {keep_calibration: response.headers.get('X-SiteCare-Keep-Calibration') === '1', revision};
  if (changed) window.dispatchEvent(new Event('settingschanged'));
}
export const t = (en, ja) => state.lang === 'ja' ? (ja || en) : en;
export const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
export const jstInput = (value = appNow()) => new Date(new Date(value).getTime() + 9 * 3600000).toISOString().slice(0, 16);
export const toISO = value => value ? `${value}:00+09:00` : '';
export const dayKey = (value = appNow()) => new Date(new Date(value).getTime() + 9 * 3600000).toISOString().slice(0, 10);
export const fmt = (value, options = {}) => value ? new Intl.DateTimeFormat(state.lang === 'ja' ? 'ja-JP' : 'en-GB', {
  timeZone: 'Asia/Tokyo', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false, ...options
}).format(new Date(value)) : '—';
export const shortTime = value => value ? new Intl.DateTimeFormat('ja-JP', {timeZone:'Asia/Tokyo', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hour12:false}).format(new Date(value)) : '';
export function countdown(until, now = appNow()) {
  if (!until) return '—';
  const mins = Math.max(0, Math.ceil((new Date(until).getTime() - new Date(now).getTime()) / 60000));
  if (!mins) return t('Rest Period Complete', '休止期間終了');
  const days = Math.floor(mins / 1440), hours = Math.floor(mins % 1440 / 60), minutes = mins % 60;
  return days ? `${days}${t('d','日')} ${hours}${t('h','時間')}` : `${hours}${t('h','時間')} ${minutes}${t('m','分')}`;
}
export function icon(name, size = 20) {
  const paths = {
    dashboard: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    patients: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.87M15 3.13a4 4 0 0 1 0 7.75"/><circle cx="9" cy="7" r="4"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18m-13 5h2m4 0h2"/>',
    shield: '<path d="M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7Z"/><path d="m8 12 3 3 5-6"/>',
    settings: '<path d="M12 3v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1M5.6 18.4l2.1-2.1m8.6-8.6 2.1-2.1"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4m0 3v.01"/>',
    plus: '<path d="M12 5v14M5 12h14"/>', close: '<path d="m6 6 12 12M6 18 18 6"/>',
    upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 16v4h16v-4"/>',
    camera: '<path d="M14.5 4h-5L7 7H3a1 1 0 0 0-1 1v11h20V8a1 1 0 0 0-1-1h-4Z"/><circle cx="12" cy="13" r="4"/>',
    arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>', chevron: '<path d="m9 5 7 7-7 7"/>',
    back: '<path d="M19 12H5m5-5-5 5 5 5"/>',
    search: '<circle cx="10.5" cy="10.5" r="7"/><path d="m16 16 5 5"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    alert: '<path d="m12 3 10 18H2Z"/><path d="M12 9v5m0 3v.01"/>',
    pin: '<circle cx="12" cy="10" r="3"/><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/>',
    logout: '<path d="M9 4H3v16h6m5-12 4 4-4 4m-7-4h14"/>',
    download: '<path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    move: '<path d="M12 2v20M2 12h20M8 6l4-4 4 4M8 18l4 4 4-4M6 8l-4 4 4 4m12-8 4 4-4 4"/>',
    target: '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/>',
    ruler: '<path d="m3 16 13-13 5 5L8 21Z"/><path d="m6 13 3 3m0-6 3 3m0-6 3 3m0-6 3 3"/>',
    hand: '<path d="M8 12V5a2 2 0 0 1 4 0v7-8a2 2 0 0 1 4 0v9-6a2 2 0 0 1 4 0v8c0 5-3 7-7 7-3 0-5-2-7-5l-3-5a2 2 0 0 1 3-2l2 2Z"/>',
    minus: '<path d="M5 12h14"/>',
    reset: '<path d="M3 10a9 9 0 1 1 1 7M3 4v6h6"/>',
    history: '<path d="M3 10a9 9 0 1 1 1 7M3 4v6h6m3-3v5l3 2"/>',
    edit: '<path d="m16 3 5 5-13 13H3v-5Z"/><path d="m13 6 5 5"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    folder: '<path d="M3 5h7l2 3h9v13H3Z"/>',
  };
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.pin}</svg>`;
}
export function toast(message, error = false) {
  const node = $('#toast'); node.textContent = message; node.className = `show ${error ? 'error' : ''}`;
  clearTimeout(node.timer); node.timer = setTimeout(() => node.className = '', error ? 7000 : 4000);
}
export async function api(path, {method = 'GET', data, form, activity = true} = {}) {
  const headers = {'X-User-Activity': activity ? '1' : '0'};
  if (method !== 'GET') headers['X-CSRF-Token'] = state.csrf;
  if (method !== 'GET' && state.clock) headers['X-Clock-Revision'] = $('#dialog[open] form')?.dataset.clockRevision ?? String(state.clock.revision);
  if (method !== 'GET' && state.settings) headers['X-Settings-Revision'] = $('#dialog[open] form')?.dataset.settingsRevision ?? String(state.settings.revision);
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  let response;
  try { response = await fetch(path, {method, headers, body: form || (data !== undefined ? JSON.stringify(data) : undefined), credentials: 'same-origin', cache: 'no-store'}); }
  catch { throw new Error(t('The local server is unavailable. Keep the SiteCare terminal open and retry.', 'ローカルサーバーに接続できません。SiteCare の起動ウィンドウを確認してください。')); }
  syncClock(response);
  syncSettings(response);
  const result = await response.json().catch(() => ({error: t('The server could not complete this request.', '処理に失敗しました。')}));
  if (!response.ok) {
    if (response.status === 401 && !path.includes('/login')) window.dispatchEvent(new Event('authlost'));
    const message = result.code === 'version_conflict' ? t('Another window changed this patient. Refresh before saving. Your edit was not applied.', '別の画面で更新されています。再読み込み後に保存してください。変更は未保存です。') : result.error;
    const error = new Error(message); error.code = result.code; error.details = result; throw error;
  }
  return result;
}
export function field(label, input, help = '') { return `<label class="field"><span>${label}</span>${input}${help ? `<small>${help}</small>` : ''}</label>`; }
export function input(name, value = '', type = 'text', attrs = '') { return `<input name="${name}" type="${type}" value="${esc(value)}" ${attrs}>`; }
export function check(name, label, checked = false) { return `<label class="check"><input type="checkbox" name="${name}" ${checked?'checked':''}> <span>${label}</span></label>`; }
export function openDialog({title, body, submit = t('Save','保存'), onSubmit, onOpen, danger = false, wide = false}) {
  const dialog = $('#dialog');
  if (dialog.open) dialog.close();
  dialog.className = wide ? 'wide' : '';
  dialog.innerHTML = `<div class="dialog-head"><h2 id="dialog-title">${title}</h2><button type="button" class="icon-button close-dialog" aria-label="${t('Close','閉じる')}">${icon('close')}</button></div>
    <form class="dialog-form"><div class="dialog-body">${body}<div class="form-error hidden" role="alert"></div></div>
    <div class="dialog-foot"><button type="button" class="button secondary close-dialog">${t('Cancel','キャンセル')}</button>${onSubmit ? `<button type="submit" class="button ${danger?'danger':'primary'}">${submit}</button>` : ''}</div></form>`;
  $$('.close-dialog', dialog).forEach(b => b.addEventListener('click', () => dialog.close()));
  const form = $('form', dialog);
  if (state.clock) form.dataset.clockRevision = String(state.clock.revision);
  if (state.settings) form.dataset.settingsRevision = String(state.settings.revision);
  form.addEventListener('submit', async event => {
    event.preventDefault(); if (!onSubmit) return;
    const button = $('button[type=submit]', form), error = $('.form-error', form);
    button.disabled = true; error.classList.add('hidden');
    try { await onSubmit(new FormData(form), form); dialog.close(); }
    catch (e) { error.textContent = e.message; error.classList.remove('hidden'); }
    finally { button.disabled = false; }
  });
  dialog.showModal();
  if (onOpen) onOpen(form);
  return dialog;
}
export const typeLabel = type => ({
  redness: t('Redness','発赤'), hardness:t('Hardening','硬結'), pain:t('Pain / Tenderness','痛み・圧痛'),
  swelling:t('Swelling','腫脹'), bruising:t('Bruising','皮下出血'), leakage:t('Leakage','液漏れ'), other:t('Other / Avoid Area','その他・使用禁止部位')
})[type] || type;
export const roleLabel = role => ({admin:t('Administrator','管理者'),nurse:t('Nurse','看護師')})[role] || role;
export const severityLabel = severity => ({mild:t('Mild','軽度'),moderate:t('Moderate','中等度'),severe:t('Severe','重度')})[severity] || severity;
export const statusLabel = value => ({eligible:t('Rule-Eligible','条件適合'),resting:t('Resting','休止中'),blocked:t('Do Not Use','使用不可'),unverified:t('Verify Photo','写真確認待ち')})[value] || value;
export const badge = (value, label = '') => `<span class="badge ${value}"><span class="status-dot"></span>${label || statusLabel(value)}</span>`;
export function reasonLabel(reason) {
  switch(reason.code) {
    case 'site_rest': return t(`Site ${reason.site} is resting until ${fmt(reason.until)}.`, `部位 ${reason.site}：${fmt(reason.until)} まで休止中。`);
    case 'near_recent': return t(`Only ${reason.distance_cm} cm from recent puncture #${reason.event_id}; minimum 2.5 cm.`, `直近の穿刺 #${reason.event_id} から ${reason.distance_cm} cm（2.5 cm以上必要）。`);
    case 'active_alert': return t(`Active skin alert: ${reason.types.map(typeLabel).join(', ')}.`, `皮膚注意部位：${reason.types.map(typeLabel).join('・')}。`);
    case 'recurrence_review': return t(`${reason.count} related episodes in 90 days. Review required.`, `90日以内に関連する皮膚所見 ${reason.count} 件。再評価が必要です。`);
    case 'navel': return t(`Only ${reason.distance_cm} cm from the navel; minimum 5 cm.`, `臍から ${reason.distance_cm} cm（5 cm以上必要）。`);
    case 'outside_photo': return t('This point is outside the photograph.', '写真の範囲外です。');
    case 'photo_unverified': return t('A current calibrated and verified photograph is required.', '現在の写真の校正と位置確認が必要です。');
    default: return reason.code;
  }
}
export function appointmentBadge(appt, overdue = false) {
  if (overdue) return badge('blocked', t('Overdue','期限超過'));
  return badge(appt?.status === 'confirmed' ? 'eligible' : 'unverified', appt?.status === 'confirmed' ? t('Confirmed','確定') : t('Suggested','提案'));
}
