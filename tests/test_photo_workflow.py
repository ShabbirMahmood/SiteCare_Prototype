"""Visit-specific layouts, patient photo labels and retained calibration."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from sitecare.app import create_app
from sitecare.clock import system_now
from sitecare.rules import default_sites, iso
from sitecare.storage import initialize, transaction
from conftest import state, upload, calibrate, record, alert_payload
from test_clock import change_clock


def keep(client, enabled):
    config = client.get('/api/settings').json()
    result = client.post('/api/settings', json={
        'keep_calibration': enabled, 'revision': config['revision']})
    assert result.status_code == 200, result.text
    return result.json()


def save_layout(client, pid, photo_id, sites=None, **overrides):
    data = {'version': state(client, pid)['patient']['version'], 'photo_id': photo_id}
    data.update({'sites': sites} if sites else {'reset_to_default': True})
    data.update(overrides)
    return client.post(f'/api/patients/{pid}/layout', json=data)


def test_photo_numbers_are_patient_specific_and_stable(client, patient_id):
    other = client.post('/api/patients', json={'code': 'OTHER', 'alias': 'Other',
                                             'start_at': iso(system_now())}).json()['id']
    a1 = upload(client, patient_id)
    b1 = upload(client, other)
    a2 = upload(client, patient_id)
    b2 = upload(client, other)
    assert {p['id']: p['number'] for p in state(client, patient_id)['photos']} == {a1: 1, a2: 2}
    assert {p['id']: p['number'] for p in state(client, other)['photos']} == {b1: 1, b2: 2}
    a3 = upload(client, patient_id)
    assert {p['id']: p['number'] for p in state(client, patient_id)['photos']} == {a1: 1, a2: 2, a3: 3}
    assert len({a1, b1, a2, b2, a3}) == 5
    with TestClient(create_app(client.app.state.data_dir, testing=True)) as restarted:
        restarted.cookies.update(client.cookies)
        assert restarted.get(f'/api/patients/{patient_id}').json()['photos'][0]['number'] == 3


@pytest.mark.parametrize('record_kind', ['puncture', 'skin'])
def test_new_photo_layout_edit_preserves_old_photo_and_records(client, patient_id, photo_id, record_kind):
    if record_kind == 'puncture':
        assert record(client, patient_id, photo_id).status_code == 200
    else:
        assert client.post(f'/api/patients/{patient_id}/alerts',
                           json=alert_payload(client, patient_id, photo_id)).status_code == 200
    before = state(client, patient_id)
    assert before['layout_locked']
    new_photo = upload(client, patient_id)
    assert not state(client, patient_id)['layout_locked']
    custom = default_sites()
    custom[0]['y'] = -8
    response = save_layout(client, patient_id, new_photo, custom)
    assert response.status_code == 200, response.text
    after = state(client, patient_id)
    assert after['sites'] == custom
    old = next(p for p in after['photos'] if p['id'] == photo_id)
    assert old['sites'] == default_sites()
    assert old['alignment'] == before['photos'][0]['alignment']
    assert after['events'] == before['events'] and after['alerts'] == before['alerts']
    assert save_layout(client, patient_id, photo_id).status_code == 409
    assert save_layout(client, patient_id, new_photo).status_code == 200
    assert state(client, patient_id)['photos'][0]['sites'] == default_sites()
    assert not state(client, patient_id)['photos'][0]['verified']


def test_history_uses_source_photo_layout_and_clock_selects_snapshot(client, patient_id, photo_id):
    original = state(client, patient_id)['photos'][0]
    future = system_now() + timedelta(days=3)
    change_clock(client, iso(future))
    new_photo = upload(client, patient_id, capture=iso(future))
    custom = default_sites()
    custom[0]['y'] = -15  # Near the old site 1 point, site 2 is now closer.
    assert save_layout(client, patient_id, new_photo, custom).status_code == 200
    response = record(client, patient_id, photo_id, kind='history',
                      exception_reason='Historical source photo layout.',
                      occurred_at=original['captured_at'], x=0, y=-6)
    assert response.status_code == 200, response.text
    assert response.json()['site_number'] == 1
    selected = client.post(f'/api/patients/{patient_id}/screen-point',
                           json={'photo_id': photo_id, 'x': 0, 'y': -6}).json()
    assert selected['number'] == 1
    change_clock(client)
    assert state(client, patient_id)['sites'] == default_sites()
    change_clock(client, iso(future + timedelta(minutes=1)))
    assert state(client, patient_id)['sites'] == custom


def test_keep_calibration_reuses_old_photo_and_off_restores_age_limit(client, patient_id, photo_id):
    assert client.get('/api/settings').json() == {'keep_calibration': False, 'revision': 0}
    first_time = system_now()
    assert record(client, patient_id, photo_id, occurred_at=iso(first_time)).status_code == 200
    later = first_time + timedelta(days=3)
    change_clock(client, iso(later))
    assert not state(client, patient_id)['candidates']
    config = keep(client, True)
    assert config['keep_calibration']
    assert state(client, patient_id)['candidates'] == [2, 3, 4]
    next_site = default_sites()[1]
    result = record(client, patient_id, photo_id, occurred_at=iso(later),
                    x=next_site['x'], y=next_site['y'])
    assert result.status_code == 200, result.text
    # Reuse does not remove rest or skin restrictions.
    assert record(client, patient_id, photo_id, occurred_at=iso(later)).status_code == 422
    alert = client.post(f'/api/patients/{patient_id}/alerts', json=alert_payload(
        client, patient_id, photo_id, x=6, y=0, observed_at=iso(later)))
    assert alert.status_code == 200, alert.text
    assert state(client, patient_id)['states'][2]['status'] == 'blocked'
    keep(client, False)
    assert not state(client, patient_id)['candidates']
    result = record(client, patient_id, photo_id, occurred_at=iso(later), x=0, y=6)
    assert result.status_code == 422 and result.json()['code'] == 'fresh_photo_required'


def test_keep_calibration_requires_new_upload_verification_and_rejects_future_photo(client, patient_id, photo_id):
    keep(client, True)
    later = system_now() + timedelta(days=2)
    change_clock(client, iso(later))
    assert state(client, patient_id)['candidates']
    new_photo = upload(client, patient_id, capture=iso(later))
    assert not state(client, patient_id)['candidates']
    assert record(client, patient_id, new_photo, occurred_at=iso(later)).status_code == 422
    calibrate(client, patient_id, new_photo)
    assert state(client, patient_id)['candidates']
    change_clock(client, iso(system_now() - timedelta(days=2)))
    assert state(client, patient_id)['current_photo_id'] is None
    assert not state(client, patient_id)['candidates']


def test_settings_persist_are_isolated_and_invalidate_stale_writes(client, patient_id, tmp_path):
    previous = state(client, patient_id)['patient']['version']
    keep(client, True)
    assert client.patch(f'/api/patients/{patient_id}',
                        json={'version': previous, 'alias': 'Stale'}).status_code == 409
    response = client.post('/api/settings', json={'keep_calibration': False, 'revision': 0})
    assert response.status_code == 409
    response = client.post('/api/heartbeat', headers={'x-settings-revision': '0'})
    assert response.status_code == 409 and response.json()['code'] == 'settings_conflict'
    with TestClient(create_app(client.app.state.data_dir, testing=True)) as restarted:
        restarted.cookies.update(client.cookies)
        response = restarted.get('/api/settings')
        assert response.json()['keep_calibration']
        assert response.headers['X-SiteCare-Keep-Calibration'] == '1'
    with TestClient(create_app(tmp_path / 'separate', testing=True)) as separate:
        assert not separate.get('/api/bootstrap').json()['settings']['keep_calibration']
    entry = next(a for a in client.get('/api/audit').json()['items'] if a['action'] == 'settings.changed')
    assert not entry['detail']['before']['keep_calibration'] and entry['detail']['after']['keep_calibration']


def test_keep_calibration_requires_admin_and_csrf(client):
    data = {'keep_calibration': True, 'revision': 0}
    assert client.post('/api/settings', json=data, headers={'x-csrf-token': 'wrong'}).status_code == 403
    assert client.post('/api/settings', json={'keep_calibration': 'true', 'revision': 0}).status_code == 400
    assert client.post('/api/users', json={'username': 'nurse', 'display_name': 'Nurse',
        'password': 'Synthetic-nurse-123', 'role': 'nurse'}).status_code == 200
    with TestClient(client.app) as nurse:
        nurse.headers['x-csrf-token'] = nurse.get('/api/bootstrap').json()['csrf']
        response = nurse.post('/api/login', json={'username': 'nurse', 'password': 'Synthetic-nurse-123'})
        nurse.headers['x-csrf-token'] = response.json()['csrf']
        assert nurse.get('/api/settings').status_code == 200
        assert nurse.post('/api/settings', json=data).status_code == 403


def test_existing_database_gets_photo_snapshots_without_changing_history(client, patient_id, photo_id):
    assert record(client, patient_id, photo_id).status_code == 200
    before = state(client, patient_id)
    folder = client.app.state.data_dir
    with transaction(folder, True) as db:
        db.execute('ALTER TABLE photos DROP COLUMN sites_json')
        db.execute('DROP TABLE app_settings')
    initialize(folder)
    after = state(client, patient_id)
    assert after['events'] == before['events']
    assert after['photos'][0]['sites'] == default_sites()
    assert not client.get('/api/settings').json()['keep_calibration']
    # Reopening must not overwrite a photo's already saved snapshot.
    with transaction(folder, True) as db:
        db.execute('UPDATE sites SET y=-8 WHERE patient_id=? AND number=1', (patient_id,))
    initialize(folder)
    assert state(client, patient_id)['photos'][0]['sites'] == default_sites()
