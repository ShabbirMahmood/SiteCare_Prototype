"""Patient deletion is administrative, explicit, isolated, and durable."""
import sqlite3
from io import BytesIO
from pathlib import Path
import zipfile

import pytest

from sitecare.rules import iso, now_utc
from sitecare.storage import transaction, initialize, create_backup
from conftest import state, upload, calibrate, record, alert_payload


def delete(client, patient_id, **overrides):
    p = state(client, patient_id)['patient']
    data = {'version':p['version'], 'confirm_code':p['code'], 'reason':'Remove test profile.'}
    data.update(overrides)
    return client.request('DELETE', f'/api/patients/{patient_id}', json=data)


def create_patient(client, code='OTHER'):
    r = client.post('/api/patients', json={'code':code, 'alias':code, 'start_at':iso(now_utc())})
    assert r.status_code == 200, r.text
    return r.json()['id']


def photo_path(client, photo_id):
    with transaction(client.app.state.data_dir) as db:
        name = db.execute('SELECT filename FROM photos WHERE id=?', (photo_id,)).fetchone()[0]
    return client.app.state.data_dir / 'photos' / name


def test_delete_removes_all_patient_records_and_files_only_for_target(client, patient_id, photo_id):
    assert record(client, patient_id, photo_id).status_code == 200
    assert client.post(f'/api/patients/{patient_id}/alerts', json=alert_payload(client,patient_id,photo_id)).status_code == 200
    d = state(client, patient_id)
    assert client.post(f'/api/patients/{patient_id}/reviews', json={
        'version':d['patient']['version'], 'site_number':1, 'confirmed':True, 'note':'Test review'}).status_code == 200
    target_file = photo_path(client, photo_id)
    second_photo = upload(client, patient_id)
    second_file = photo_path(client, second_photo)
    other = create_patient(client)
    other_photo = upload(client, other)
    other_file = photo_path(client, other_photo)
    r = delete(client, patient_id)
    assert r.status_code == 200, r.text
    assert not r.json()['photo_cleanup_pending']
    assert not target_file.exists() and not second_file.exists()
    assert other_file.exists()
    assert client.get(f'/api/patients/{patient_id}').status_code == 404
    assert client.get(f'/api/photos/{photo_id}/image').status_code == 404
    assert client.get(f'/api/patients/{patient_id}/export.csv').status_code == 404
    assert [p['id'] for p in client.get('/api/patients').json()['patients']] == [other]
    assert all(e['patient_id'] != patient_id for e in client.get('/api/appointments').json()['items'])
    with transaction(client.app.state.data_dir) as db:
        for table in ('sites','photos','events','complications','reviews','appointments'):
            assert db.execute(f'SELECT COUNT(*) FROM {table} WHERE patient_id=?',(patient_id,)).fetchone()[0] == 0
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    audit = client.get(f'/api/audit?patient_id={patient_id}').json()['items']
    deleted = next(a for a in audit if a['action']=='patient.deleted')
    assert deleted['detail']['code']=='TEST-001'
    assert deleted['detail']['removed']['photos']==2
    assert deleted['detail']['removed']['events']==1
    assert any(a['action']=='patient.created' for a in audit)
    backup = zipfile.ZipFile(BytesIO(client.get('/api/backup').content))
    assert 'data/photos/'+target_file.name not in backup.namelist()
    assert 'data/photos/'+other_file.name in backup.namelist()


@pytest.mark.parametrize('overrides', [{'confirm_code':''}, {'confirm_code':'OTHER'}, {'version':0}])
def test_confirmation_and_version_fail_without_deleting(client, patient_id, photo_id, overrides):
    target = photo_path(client, photo_id)
    r = delete(client, patient_id, **overrides)
    assert r.status_code in (400,409,422)
    assert client.get(f'/api/patients/{patient_id}').status_code == 200
    assert target.exists()


def test_stale_delete_requires_reviewing_updated_patient(client, patient_id):
    version = state(client, patient_id)['patient']['version']
    client.patch(f'/api/patients/{patient_id}',json={'version':version,'alias':'Updated patient'})
    r = delete(client, patient_id, version=version)
    assert r.status_code == 409
    assert state(client, patient_id)['patient']['alias']=='Updated patient'


def test_only_admin_can_delete_and_csrf_is_enforced(client, patient_id, photo_id):
    p = state(client, patient_id)['patient']
    payload = {'version':p['version'],'confirm_code':p['code']}
    assert client.request('DELETE',f'/api/patients/{patient_id}',json=payload,
                          headers={'x-csrf-token':'wrong'}).status_code == 403
    assert client.post('/api/users',json={'username':'nurse','display_name':'Nurse',
        'password':'Nurse-password-123','role':'nurse'}).status_code == 200
    client.post('/api/logout',json={})
    client.headers['x-csrf-token']=client.get('/api/bootstrap').json()['csrf']
    assert client.request('DELETE',f'/api/patients/{patient_id}',json=payload).status_code == 401
    login=client.post('/api/login',json={'username':'nurse','password':'Nurse-password-123'})
    client.headers['x-csrf-token']=login.json()['csrf']
    assert client.request('DELETE',f'/api/patients/{patient_id}',json=payload).status_code == 403
    assert client.get(f'/api/photos/{photo_id}/image').status_code == 200


def test_deleted_ids_are_not_reused_for_new_records(client, patient_id, photo_id):
    event_id = record(client,patient_id,photo_id).json()['id']
    alert_id = client.post(f'/api/patients/{patient_id}/alerts',json=alert_payload(client,patient_id,photo_id)).json()['id']
    assert delete(client, patient_id).status_code == 200
    replacement = create_patient(client, 'TEST-001')
    replacement_photo = calibrate(client,replacement,upload(client,replacement))
    replacement_event = record(client,replacement,replacement_photo).json()['id']
    replacement_alert = client.post(f'/api/patients/{replacement}/alerts',json=alert_payload(client,replacement,replacement_photo)).json()['id']
    assert replacement > patient_id and replacement_photo > photo_id
    assert replacement_event > event_id and replacement_alert > alert_id
    assert client.get(f'/api/patients/{patient_id}').status_code == 404
    assert client.get(f'/api/photos/{photo_id}/image').status_code == 404


def test_photo_removal_failure_is_queued_and_retried_on_restart(client, patient_id, photo_id, monkeypatch):
    target = photo_path(client,photo_id)
    original = Path.unlink
    def locked(path, *args, **kwargs):
        if path == target:
            raise PermissionError('Photo in use')
        return original(path,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path,'unlink',locked)
        r = delete(client,patient_id)
    assert r.status_code == 200 and r.json()['photo_cleanup_pending']
    assert target.exists()
    assert client.get(f'/api/photos/{photo_id}/image').status_code == 404
    initialize(client.app.state.data_dir)
    assert not target.exists()


def test_failed_transaction_keeps_database_and_photo_intact(client, patient_id, photo_id):
    target=photo_path(client,photo_id)
    with transaction(client.app.state.data_dir,True) as db:
        db.execute("CREATE TRIGGER fail_delete BEFORE DELETE ON patients BEGIN SELECT RAISE(ABORT,'test rollback'); END")
    assert delete(client,patient_id).status_code == 409
    assert state(client,patient_id)['photos'][0]['id'] == photo_id
    assert target.exists()
    with transaction(client.app.state.data_dir) as db:
        assert db.execute('SELECT COUNT(*) FROM pending_photo_deletions').fetchone()[0] == 0


def test_delete_empty_profile_and_repeat_request(client, patient_id):
    assert delete(client,patient_id).status_code == 200
    assert client.request('DELETE',f'/api/patients/{patient_id}',json={
        'version':1,'confirm_code':'TEST-001'}).status_code == 404


def test_demo_can_be_loaded_after_deleting_its_primary_patient(client):
    first=client.post('/api/demo').json()['id']
    assert delete(client,first).status_code == 200
    r=client.post('/api/demo')
    assert r.status_code == 200, r.text
    assert r.json()['id'] > first
    assert len(client.get('/api/patients').json()['patients']) == 3


def test_backup_holds_write_lock_until_photos_are_copied(client,patient_id,photo_id,tmp_path,monkeypatch):
    original=zipfile.ZipFile.write
    checked=[]
    def write(archive, filename, *args, **kwargs):
        if Path(filename).suffix == '.jpg':
            db=sqlite3.connect(client.app.state.data_dir/'sitecare.sqlite3',timeout=0)
            try:
                with pytest.raises(sqlite3.OperationalError,match='locked'):
                    db.execute('BEGIN IMMEDIATE')
                checked.append(True)
            finally:
                db.close()
        return original(archive,filename,*args,**kwargs)
    monkeypatch.setattr(zipfile.ZipFile,'write',write)
    output=create_backup(client.app.state.data_dir,tmp_path/'backup.zip')
    assert checked and zipfile.is_zipfile(output)
