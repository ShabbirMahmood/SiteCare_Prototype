"""Integration coverage for application time, separate from authentication time."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from sitecare.app import create_app
from sitecare.clock import clock_offset, now_utc, system_now
from sitecare.rules import iso, parse_time, default_sites
from sitecare.storage import transaction
from conftest import state, upload, calibrate, record, alert_payload


def change_clock(client, when=None):
    config = client.get('/api/clock').json()
    r = client.post('/api/clock', json={
        'mode': 'manual' if when else 'system', 'now': when,
        'revision': config['revision']})
    assert r.status_code == 200, r.text
    return r.json()


def test_clock_defaults_to_system_and_advances(monkeypatch):
    import sitecare.clock as clock
    actual = system_now()
    monkeypatch.setattr(clock, 'system_now', lambda: actual)
    assert now_utc() == actual
    token = clock_offset.set(86400)
    try:
        assert now_utc() == actual + timedelta(days=1)
        actual += timedelta(seconds=10)
        assert now_utc() == actual + timedelta(days=1)
    finally:
        clock_offset.reset(token)


def test_api_candidate_recovery_reinserts_fifth_site(client, patient_id, photo_id):
    second = default_sites()[1]
    assert record(client, patient_id, photo_id, x=second['x'], y=second['y']).status_code == 200
    for _ in range(2):
        r = client.post(f'/api/patients/{patient_id}/alerts', json=alert_payload(
            client, patient_id, photo_id, x=0, y=6))
        assert r.status_code == 200, r.text
        aid = r.json()['id']
        assert state(client, patient_id)['candidates'] == [3, 4, 6]
        r = client.post(f'/api/alerts/{aid}/resolve', json={
            'version': state(client, patient_id)['patient']['version'],
            'healed_confirmed': True, 'note': 'Recovered for demonstration.'})
        assert r.status_code == 200, r.text
        assert state(client, patient_id)['candidates'] == [3, 4, 5]


def test_manual_clock_drives_rest_freshness_calendar_and_reset(client, patient_id, photo_id):
    client.post("/api/settings", json={"keep_calibration": False, "revision": 0})
    before = system_now()
    assert record(client, patient_id, photo_id, occurred_at=iso(before)).status_code == 200
    d = state(client, patient_id)
    saved_event = d['events'][0]
    chosen = before + timedelta(days=13)
    config = change_clock(client, iso(chosen))
    assert config['mode'] == 'manual'
    assert abs((parse_time(config['now']) - chosen).total_seconds()) < 3
    assert client.get('/api/patients').status_code == 200  # No session expiry from date jump.
    d = state(client, patient_id)
    assert d['states'][0]['rest_seconds'] == 0
    assert d['states'][0]['status'] == 'unverified'  # Old photo is correctly stale.
    assert d['events'][0] == saved_event  # Date changes do not rewrite records.
    assert client.get('/api/patients').json()['patients'][0]['overdue']
    calendar = client.get('/api/appointments').json()
    assert calendar['month'] == (chosen + timedelta(hours=9)).strftime('%Y-%m')
    current_photo = calibrate(client, patient_id, upload(client, patient_id, capture=iso(chosen)))
    d = state(client, patient_id)
    assert d['current_photo_id'] == current_photo
    assert d['states'][0]['status'] == 'eligible'
    assert record(client, patient_id, current_photo, x=6, y=0,
                  occurred_at=iso(chosen)).status_code == 200
    due = state(client, patient_id)['appointment']['due_at']
    assert due == iso(chosen + timedelta(days=3))
    change_clock(client)
    d = state(client, patient_id)
    assert d['current_photo_id'] == photo_id  # Future visit photo is not selected on return.
    assert d['states'][0]['status'] == 'resting'
    assert d['states'][2]['last_used_at'] is None  # Future event is retained, but not applied.
    assert d['appointment']['due_at'] == iso(before + timedelta(days=3))
    assert len(d['events']) == 2


def test_backward_clock_excludes_future_events_and_alerts(client, patient_id, photo_id):
    before = system_now()
    assert record(client, patient_id, photo_id, occurred_at=iso(before)).status_code == 200
    r = client.post(f'/api/patients/{patient_id}/alerts', json=alert_payload(
        client, patient_id, photo_id, x=0, y=6, observed_at=iso(before)))
    aid = r.json()['id']
    change_clock(client, iso(before - timedelta(days=1)))
    d = state(client, patient_id)
    assert d['states'][0]['rest_seconds'] == 0
    assert d['states'][4]['status'] != 'blocked'
    assert not client.get('/api/patients').json()['patients'][0]['active_alerts']
    assert d['appointment']['due_at'] == d['patient']['start_at']
    assert not any(e['kind'] == 'completed' for e in client.get('/api/appointments').json()['items'])
    r = client.post(f'/api/alerts/{aid}/resolve', json={
        'version':d['patient']['version'], 'healed_confirmed':True, 'note':'Recovery'})
    assert r.status_code == 422  # Never create recovery before observation.


def test_clock_persists_and_does_not_leak_to_another_app(client, tmp_path):
    chosen = '2032-04-01T00:30:00+09:00'
    change_clock(client, chosen)
    with TestClient(create_app(client.app.state.data_dir, testing=True)) as restarted:
        restarted.cookies.update(client.cookies)
        d = restarted.get('/api/clock').json()
        assert d['mode'] == 'manual'
        assert abs((parse_time(d['now']) - parse_time(chosen)).total_seconds()) < 5
    with TestClient(create_app(tmp_path / 'separate', testing=True)) as separate:
        d = separate.get('/api/bootstrap').json()
        assert d['clock']['mode'] == 'system'
        assert abs((parse_time(d['now']) - system_now()).total_seconds()) < 3


def test_stale_clock_and_patient_edits_are_rejected(client, patient_id):
    previous = state(client, patient_id)['patient']['version']
    clock = client.get('/api/clock').json()
    change_clock(client, '2030-03-01T09:00:00+09:00')
    r = client.patch(f'/api/patients/{patient_id}', json={'version':previous,'alias':'Stale'})
    assert r.status_code == 409
    r = client.post('/api/clock', json={'mode':'system','revision':clock['revision']})
    assert r.status_code == 409
    r = client.post('/api/heartbeat', headers={'x-clock-revision':str(clock['revision'])})
    assert r.status_code == 409 and r.json()['code'] == 'clock_conflict'


@pytest.mark.parametrize('value', ['bad', '2030-01-01T10:00:00', '2200-01-01T00:00:00Z', None])
def test_invalid_clock_input_is_rejected(client, value):
    r = client.post('/api/clock', json={'mode':'manual','now':value,'revision':0})
    assert r.status_code == 400
    assert client.get('/api/clock').json()['mode'] == 'system'


def test_manual_clock_keeps_real_idle_expiry(client):
    change_clock(client, '2040-01-01T00:00:00Z')
    with transaction(client.app.state.data_dir, True) as db:
        db.execute('UPDATE sessions SET touched_at=?', (iso(system_now()-timedelta(minutes=31)),))
    assert client.get('/api/patients').status_code == 401


def test_nurse_cannot_change_shared_clock(client):
    assert client.post('/api/users',json={'username':'nurse','display_name':'Nurse',
        'password':'Nurse-password-123','role':'nurse'}).status_code == 200
    client.post('/api/logout',json={})
    client.headers['x-csrf-token']=client.get('/api/bootstrap').json()['csrf']
    login=client.post('/api/login',json={'username':'nurse','password':'Nurse-password-123'})
    client.headers['x-csrf-token']=login.json()['csrf']
    assert client.get('/api/clock').status_code == 200
    assert client.post('/api/clock',json={'mode':'system','revision':0}).status_code == 403
