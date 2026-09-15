"""Synthetic-only fixtures. Never read actual patient photographs."""
from datetime import timedelta
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from sitecare.app import create_app
from sitecare.rules import iso, now_utc


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path, testing=True)
    with TestClient(app) as c:
        bootstrap = c.get('/api/bootstrap').json()
        c.headers['x-csrf-token'] = bootstrap['csrf']
        r = c.post('/api/setup', json={'username': 'admin', 'display_name': 'Test nurse',
                                     'password': 'Test-password-123!'})
        assert r.status_code == 200, r.text
        c.headers['x-csrf-token'] = r.json()['csrf']
        yield c


@pytest.fixture
def patient_id(client):
    r = client.post('/api/patients', json={'code': 'TEST-001', 'alias': 'Synthetic patient',
                    'start_at': iso(now_utc() + timedelta(days=1))})
    assert r.status_code == 200, r.text
    return r.json()['id']


def state(client, patient_id):
    r = client.get(f'/api/patients/{patient_id}')
    assert r.status_code == 200, r.text
    return r.json()


def image_bytes(size=(1200, 1000), exif=None):
    out = BytesIO()
    args = {'exif': exif} if exif is not None else {}
    Image.new('RGB', size, '#dfc2a4').save(out, 'JPEG', **args)
    return out.getvalue()


def upload(client, patient_id, *, capture=None, raw=None):
    data = state(client, patient_id)
    r = client.post(f'/api/patients/{patient_id}/photos',
                    data={'version': data['patient']['version'], 'consent': 'true',
                          'captured_at': capture or iso(now_utc() - timedelta(minutes=2))},
                    files={'photo': ('synthetic.jpg', raw or image_bytes(), 'image/jpeg')})
    assert r.status_code == 200, r.text
    return r.json()['id']


def alignment_payload(client, patient_id):
    return {'version': state(client, patient_id)['patient']['version'], 'confirmed': True,
            'alignment': {'cx': 600, 'cy': 520, 'angle': 0, 'ppm': 9999,
                          'calibration': {'a': {'x': 180, 'y': 800},
                                          'b': {'x': 480, 'y': 800}, 'length_cm': 10}}}


def calibrate(client, patient_id, photo_id):
    r = client.post(f'/api/photos/{photo_id}/alignment',
                    json=alignment_payload(client, patient_id))
    assert r.status_code == 200, r.text
    return photo_id


@pytest.fixture
def photo_id(client, patient_id):
    return calibrate(client, patient_id, upload(client, patient_id))


def event_payload(client, patient_id, photo_id, **overrides):
    data = {'version': state(client, patient_id)['patient']['version'], 'photo_id': photo_id,
            'request_key': str(uuid4()), 'kind': 'procedure', 'x': 0, 'y': -6,
            'occurred_at': iso(now_utc()), 'identity_checked': True, 'point_checked': True,
            'clinical_checked': True, 'note': 'Synthetic test event'}
    data.update(overrides)
    return data


def record(client, patient_id, photo_id, **overrides):
    return client.post(f'/api/patients/{patient_id}/events',
                       json=event_payload(client, patient_id, photo_id, **overrides))


def alert_payload(client, patient_id, photo_id, **overrides):
    data = {'version': state(client, patient_id)['patient']['version'], 'photo_id': photo_id,
            'x': 0, 'y': -6, 'radius': 1, 'observed_at': iso(now_utc() - timedelta(minutes=1)),
            'types': ['redness'], 'severity': 'mild', 'note': 'Synthetic observation'}
    data.update(overrides)
    return data
