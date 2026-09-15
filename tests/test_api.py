from datetime import timedelta
from io import BytesIO
from pathlib import Path
import sqlite3
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sitecare.app import create_app
from sitecare.rules import JST, default_sites, iso, now_utc, parse_time
from sitecare.storage import transaction
from conftest import (state, upload, calibrate, alignment_payload, event_payload,
                      record, alert_payload, image_bytes)


def test_first_setup_and_login_required(tmp_path):
    with TestClient(create_app(tmp_path, testing=True)) as c:
        assert c.get('/').status_code == 200
        assert c.get('/api/patients').status_code == 401
        b = c.get('/api/bootstrap').json()
        assert b['setup_needed'] and b['csrf']
        assert c.post('/api/setup', json={}).status_code == 403


def test_setup_cannot_repeat(client):
    r = client.post('/api/setup', json={'username':'other','display_name':'Other',
                                       'password':'Long-test-password123'})
    assert r.status_code == 409


def test_security_headers_and_csrf_origin(client):
    r = client.get('/')
    assert r.headers['cache-control'] == 'no-store'
    assert r.headers['x-frame-options'] == 'DENY'
    assert "script-src 'self'" in r.headers['content-security-policy']
    assert client.post('/api/heartbeat', json={}, headers={'origin':'https://attacker.example'}).status_code == 403
    assert client.post('/api/heartbeat', json={}, headers={'x-csrf-token':'wrong'}).status_code == 403
    assert client.get('/', headers={'host': 'untrusted.example'}).status_code == 403


def test_patient_creation_id_unique_and_defaults(client, patient_id):
    data = state(client, patient_id)
    assert len(data['sites']) == 14 and not data['candidates']
    assert data['patient']['version'] == 1
    r = client.post('/api/patients', json={'code':'TEST-001','alias':'Duplicate',
                                          'start_at': iso(now_utc())})
    assert r.status_code == 409


def test_optimistic_conflict_does_not_overwrite(client, patient_id):
    v = state(client, patient_id)['patient']['version']
    assert client.patch(f'/api/patients/{patient_id}', json={'version':v,'alias':'First'}).status_code == 200
    r = client.patch(f'/api/patients/{patient_id}', json={'version':v,'alias':'Stale'})
    assert r.status_code == 409 and r.json()['code'] == 'version_conflict'
    assert state(client, patient_id)['patient']['alias'] == 'First'


def test_photo_metadata_stripped_and_authenticated(client, patient_id):
    exif = Image.Exif(); exif[270] = 'sensitive metadata'; exif[274] = 6
    pid = upload(client, patient_id, raw=image_bytes((1200,1000), exif))
    d = state(client, patient_id)['photos'][0]
    assert (d['width'],d['height']) == (1000,1200)
    assert 'filename' not in d
    r = client.get(d['url'])
    image = Image.open(BytesIO(r.content))
    assert image.size == (1000,1200) and not image.getexif()
    assert client.get('/data/sitecare.sqlite3').status_code == 404
    with TestClient(client.app) as unauthenticated:
        assert unauthenticated.get(f'/api/photos/{pid}/image').status_code == 401


@pytest.mark.parametrize('raw', [b'<html>not an image</html>', image_bytes((100,100))])
def test_invalid_or_too_small_upload_rejected(client, patient_id, raw):
    r = client.post(f'/api/patients/{patient_id}/photos',
             data={'version':1,'consent':'true','captured_at':iso(now_utc())},
             files={'photo':('bad.jpg',raw,'image/jpeg')})
    assert r.status_code == 400
    assert not state(client, patient_id)['photos']


def test_uncalibrated_photo_cannot_record(client, patient_id):
    pid = upload(client, patient_id)
    r = record(client, patient_id, pid)
    assert r.status_code == 422 and r.json()['code'] == 'calibration_required'


def test_server_derives_scale_from_ruler_ignoring_client_ppm(client, patient_id, photo_id):
    d = state(client, patient_id)
    assert d['photos'][0]['alignment']['ppm'] == 30
    assert d['candidates'] == [1,2,3]


def test_alignment_requires_ruler_points_and_confirmation(client, patient_id):
    pid = upload(client, patient_id)
    d = alignment_payload(client, patient_id); d['alignment']['calibration'] = None
    assert client.post(f'/api/photos/{pid}/alignment', json=d).status_code == 400
    d = alignment_payload(client, patient_id); d['confirmed'] = False
    assert client.post(f'/api/photos/{pid}/alignment', json=d).status_code == 400


def test_record_locks_site_photo_layout_and_schedules_72_hours(client, patient_id, photo_id):
    when = iso(now_utc())
    r = record(client, patient_id, photo_id, occurred_at=when)
    assert r.status_code == 200, r.text
    d = state(client, patient_id)
    assert d['states'][0]['status'] == 'resting'
    assert d['events'][0]['actor'] == 'Test nurse'
    assert d['events'][0]['x'] == 0 and d['events'][0]['y'] == -6
    assert d['photos'][0]['locked'] and d['layout_locked']
    assert parse_time(d['appointment']['due_at']) == parse_time(when)+timedelta(days=3)
    assert client.post(f'/api/photos/{photo_id}/alignment', json=alignment_payload(client, patient_id)).status_code == 409
    assert client.post(f'/api/patients/{patient_id}/layout', json={'version':d['patient']['version'],
                       'sites':default_sites()}).status_code == 409


def test_duplicate_click_idempotent(client, patient_id, photo_id):
    d = event_payload(client, patient_id, photo_id)
    r1 = client.post(f'/api/patients/{patient_id}/events', json=d)
    r2 = client.post(f'/api/patients/{patient_id}/events', json=d)
    assert r1.status_code == r2.status_code == 200
    assert r1.json()['id'] == r2.json()['id'] and r2.json()['duplicate']
    assert len(state(client, patient_id)['events']) == 1


def test_same_photo_disallows_second_new_procedure(client, patient_id, photo_id):
    assert record(client, patient_id, photo_id).status_code == 200
    r = record(client, patient_id, photo_id, x=0,y=6)
    assert r.status_code == 422 and r.json()['code'] == 'fresh_photo_required'


def test_new_photo_preserves_history_and_site_lock(client, patient_id, photo_id):
    assert record(client, patient_id, photo_id).status_code == 200
    pid2 = calibrate(client, patient_id, upload(client, patient_id))
    r = record(client, patient_id, pid2)
    assert r.status_code == 422 and r.json()['code'] == 'point_blocked'
    d = state(client, patient_id)
    assert len(d['photos']) == 2 and len(d['events']) == 1
    assert record(client, patient_id, pid2, x=0,y=6).status_code == 200


def test_actual_point_nearest_number_and_2point5_guard(client, patient_id, photo_id):
    # Point is closer to number 1, not its exact nominal centre.
    first = record(client, patient_id, photo_id, x=2.2,y=-5.5)
    assert first.status_code == 200 and first.json()['site_number'] == 1
    pid2 = calibrate(client, patient_id, upload(client, patient_id))
    r = record(client, patient_id, pid2, x=3.4,y=-4.8)
    assert r.status_code == 422
    assert any(v['code']=='near_recent' for v in r.json()['reasons'])
    s = client.post(f'/api/patients/{patient_id}/screen-point', json={'x':3.4,'y':-4.8}).json()
    assert s['number'] == 2 and s['status'] == 'resting'


def test_navel_cannot_record(client, patient_id, photo_id):
    r = record(client, patient_id, photo_id, x=0,y=4.99)
    assert r.status_code == 422
    assert any(v['code']=='navel' for v in r.json()['reasons'])


def test_history_records_noncompliance_without_authorizing_it(client, patient_id, photo_id):
    r = record(client, patient_id, photo_id, kind='history', x=0,y=1,
               occurred_at=iso(now_utc()-timedelta(days=2)),
               exception_reason='Transferred from a previous paper record.')
    assert r.status_code == 200, r.text
    d = state(client, patient_id)
    assert d['events'][0]['kind'] == 'history'
    assert any(v['code']=='navel' for v in d['events'][0]['warnings'])


def test_older_history_does_not_move_due_backward(client, patient_id, photo_id):
    assert record(client, patient_id, photo_id).status_code == 200
    before = state(client, patient_id)['appointment']['due_at']
    r = record(client, patient_id, photo_id, kind='history', x=0,y=6,
               occurred_at=iso(now_utc()-timedelta(days=6)), exception_reason='Paper chart migration.')
    assert r.status_code == 200
    assert state(client, patient_id)['appointment']['due_at'] == before


@pytest.mark.parametrize('overrides', [
    {'occurred_at':iso(now_utc()+timedelta(days=1))},
    {'identity_checked':False}, {'clinical_checked':False}, {'point_checked':False},
    {'kind':'history','exception_reason':''}, {'x':'NaN'}, {'kind':[]},
])
def test_invalid_event_input_rejected(client, patient_id, photo_id, overrides):
    r = record(client, patient_id, photo_id, **overrides)
    assert r.status_code == 400


def test_fresh_photo_check_and_minute_rounding(client, patient_id):
    pid = calibrate(client, patient_id, upload(client, patient_id,
                    capture=iso(now_utc()-timedelta(days=2))))
    r = record(client, patient_id, pid)
    assert r.status_code == 422 and r.json()['code'] == 'fresh_photo_required'
    pid2 = calibrate(client, patient_id, upload(client, patient_id, capture=iso(now_utc())))
    r = record(client, patient_id, pid2, occurred_at=iso(now_utc().replace(second=0,microsecond=0)))
    assert r.status_code == 200, r.text


def test_foreign_patient_photo_not_accepted(client, patient_id, photo_id):
    r = client.post('/api/patients', json={'code':'OTHER','alias':'Other synthetic',
                                          'start_at':iso(now_utc())})
    other = r.json()['id']
    assert record(client, other, photo_id).status_code == 422


def test_layout_validation_and_customization(client, patient_id):
    sites = default_sites(); sites[0]['y'] = -4
    r = client.post(f'/api/patients/{patient_id}/layout', json={'version':1,'sites':sites})
    assert r.status_code == 400
    sites = default_sites(); sites[0]['y'] = -7
    r = client.post(f'/api/patients/{patient_id}/layout', json={'version':1,'sites':sites})
    assert r.status_code == 200
    assert state(client, patient_id)['sites'][0]['y'] == -7


def test_active_alert_resolution_is_explicit(client, patient_id, photo_id):
    r = client.post(f'/api/patients/{patient_id}/alerts',json=alert_payload(client, patient_id, photo_id))
    assert r.status_code == 200, r.text
    aid = r.json()['id']; d = state(client, patient_id)
    assert d['states'][0]['status'] == 'blocked'
    assert record(client, patient_id, photo_id).status_code == 422
    r = client.post(f'/api/alerts/{aid}/resolve', json={'version':d['patient']['version'],
                    'note':'Reviewed at bedside.'})
    assert r.status_code == 400
    r = client.post(f'/api/alerts/{aid}/resolve', json={'version':d['patient']['version'],
                    'note':'Full recovery confirmed at bedside.','healed_confirmed':True})
    assert r.status_code == 200
    assert state(client, patient_id)['states'][0]['status'] == 'eligible'


@pytest.mark.parametrize('types', [[], ['unknown'], [{}]])
def test_unknown_or_malformed_complication_type_rejected(client, patient_id, photo_id, types):
    r = client.post(f'/api/patients/{patient_id}/alerts',
                   json=alert_payload(client, patient_id, photo_id, types=types))
    assert r.status_code == 400


def test_resolving_repeated_alerts_unblocks_without_review(client, patient_id, photo_id):
    for _ in range(2):
        assert client.post(f'/api/patients/{patient_id}/alerts',
                    json=alert_payload(client, patient_id, photo_id)).status_code == 200
    d = state(client, patient_id)
    assert not d['states'][0]['needs_review']
    assert not d['states'][0]['needs_review'] and d['states'][0]['status'] == 'blocked'

    for a in d['alerts']:
        r = client.post(f"/api/alerts/{a['id']}/resolve", json={
            'version': state(client, patient_id)['patient']['version'],
            'healed_confirmed': True, 'note': 'Recovered.'})
        assert r.status_code == 200
    d = state(client, patient_id)
    assert d['states'][0]['status'] == 'eligible'
    assert not d['states'][0]['needs_review']


def test_reschedule_does_not_change_protocol_due(client, patient_id, photo_id):
    assert record(client, patient_id, photo_id).status_code == 200
    d = state(client, patient_id); due = d['appointment']['due_at']
    r = client.post(f'/api/patients/{patient_id}/appointment', json={
        'version':d['patient']['version'],'scheduled_at':iso(parse_time(due)+timedelta(hours=2)),
        'reason':'Staff review: scheduling adjustment.'})
    assert r.status_code == 200, r.text
    d = state(client, patient_id)
    assert d['appointment']['due_at'] == due
    assert d['appointment']['scheduled_at'] != due


def test_void_keeps_original_and_recalculates_due(client, patient_id, photo_id):
    original_start = state(client, patient_id)['patient']['start_at']
    eid = record(client, patient_id, photo_id).json()['id']
    r = client.post(f'/api/events/{eid}/void', json={
        'version':state(client, patient_id)['patient']['version'], 'reason':'Mistaken synthetic entry.'})
    assert r.status_code == 200
    d = state(client, patient_id)
    assert len(d['events']) == 1 and d['events'][0]['voided_at']
    assert d['appointment']['due_at'] == original_start
    assert d['states'][0]['status'] == 'eligible'


def test_calendar_has_next_and_forecasts_distinguished(client, patient_id):
    month = now_utc().strftime('%Y-%m')
    r = client.get('/api/appointments', params={'month':month})
    assert r.status_code == 200, r.text
    d = r.json()
    assert parse_time(d['grid_start']+'T00:00:00+09:00').astimezone(JST).weekday() == 0
    assert any(i.get('next') is True for i in d['items'])
    assert any(i.get('kind') == 'projection' for i in d['items'])


def test_inactive_patient_cannot_record(client, patient_id, photo_id):
    d = state(client, patient_id)
    assert client.patch(f'/api/patients/{patient_id}',json={'version':d['patient']['version'],
                                                        'active':False}).status_code == 200
    assert not state(client, patient_id)['candidates']
    assert record(client, patient_id, photo_id).status_code == 422


def test_demo_seed_is_synthetic_and_idempotent(client):
    first = client.post('/api/demo',json={}); second = client.post('/api/demo',json={})
    assert first.status_code == second.status_code == 200
    assert first.json()['id'] == second.json()['id']
    ps = client.get('/api/patients').json()['patients']
    assert len(ps) == 3 and all(p['demo'] for p in ps)
    d = state(client, first.json()['id'])
    assert d['candidates'] == [5,6,7]
    assert d['states'][3]['status'] == 'blocked'


def test_csv_export_formula_injection_guard(client, patient_id, photo_id):
    assert record(client, patient_id, photo_id, note='=HYPERLINK("test")').status_code == 200
    r = client.get(f'/api/patients/{patient_id}/export.csv')
    assert r.status_code == 200 and r.content.startswith(b'\xef\xbb\xbf')
    assert "'=HYPERLINK" in r.content.decode('utf-8-sig')


def test_backup_contains_consistent_database_photos_no_live_sessions(client, patient_id, photo_id, tmp_path):
    assert record(client, patient_id, photo_id).status_code == 200
    r = client.get('/api/backup')
    assert r.status_code == 200, r.text[:200]
    z = zipfile.ZipFile(BytesIO(r.content))
    assert 'data/sitecare.sqlite3' in z.namelist()
    assert any(n.startswith('data/photos/') for n in z.namelist())
    extracted = tmp_path/'extracted'; z.extractall(extracted)
    db = sqlite3.connect(extracted/'data/sitecare.sqlite3')
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] == 0
    assert db.execute('SELECT COUNT(*) FROM events').fetchone()[0] == 1
    db.close()
    assert client.get('/api/patients').status_code == 200


def test_nurse_account_cannot_access_admin_functions(client):
    r = client.post('/api/users', json={'username':'nurse','display_name':'Another nurse',
                                      'password':'Another-password-123','role':'nurse'})
    assert r.status_code == 200, r.text
    assert client.post('/api/logout',json={}).status_code == 200
    b = client.get('/api/bootstrap').json(); client.headers['x-csrf-token']=b['csrf']
    r = client.post('/api/login', json={'username':'nurse','password':'Another-password-123'})
    assert r.status_code == 200; client.headers['x-csrf-token']=r.json()['csrf']
    assert client.get('/api/patients').status_code == 200
    for path in ('/api/backup','/api/audit','/api/users'):
        assert client.get(path).status_code == 403
    assert client.post('/api/demo',json={}).status_code == 403


def test_idle_session_expiry_and_background_poll_not_keepalive(client):
    with transaction(client.app.state.data_dir, True) as db:
        db.execute('UPDATE sessions SET touched_at=?', (iso(now_utc()-timedelta(minutes=31)),))
    assert client.get('/api/patients',headers={'x-user-activity':'0'}).status_code == 401
