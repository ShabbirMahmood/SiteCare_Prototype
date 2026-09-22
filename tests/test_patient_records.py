"""Synthetic-only integration tests for patient options and report integrity."""
import csv
import io
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from conftest import alert_payload, event_payload, record, state, upload
from sitecare.app import create_app
from sitecare.records import make_report, next_due
from sitecare.rules import JST, default_sites, inside_alert, iso, now_utc, parse_time
from sitecare.storage import initialize, transaction


def version(client, pid):
    return state(client, pid)["patient"]["version"]


def set_dose(client, pid, rate=.15, reason="", category="standard", step=.01, **extra):
    return client.post(f"/api/patients/{pid}/dosage", json={"version": version(client, pid),
                       "rate": rate, "category": category, "step": step, "reason": reason, **extra})


def test_ellipse_boundaries_do_not_use_bounding_circle():
    ellipse = {"x": 0, "y": 0, "radius": 2, "width_cm": 4, "height_cm": .3}
    assert inside_alert({"x": 2, "y": 0}, ellipse)
    assert inside_alert({"x": 0, "y": .15}, ellipse)
    assert not inside_alert({"x": 0, "y": .16}, ellipse)
    assert not inside_alert({"x": 1.5, "y": .14}, ellipse)


def test_elliptical_alert_and_separate_pain_tenderness(client, patient_id, photo_id):
    a = alert_payload(client, patient_id, photo_id, width_cm=4, height_cm=.3, types=["pain", "tenderness"])
    response = client.post(f"/api/patients/{patient_id}/alerts", json=a)
    assert response.status_code == 200, response.text
    saved = state(client, patient_id)["alerts"][0]
    assert (saved["width_cm"], saved["height_cm"]) == (4, .3)
    assert saved["types"] == ["pain", "tenderness"]
    inside = client.post(f"/api/patients/{patient_id}/screen-point", json={"x": 1.9, "y": -6}).json()
    outside = client.post(f"/api/patients/{patient_id}/screen-point", json={"x": 0, "y": -5.8}).json()
    assert any(r["code"] == "active_alert" for r in inside["reasons"])
    assert not any(r["code"] == "active_alert" for r in outside["reasons"])


@pytest.mark.parametrize("width,height", [(0, .3), (.3, 0), (-1, .3), (31, .3), ("NaN", .3), (.3, None)])
def test_invalid_ellipse_dimensions(client, patient_id, photo_id, width, height):
    response = client.post(f"/api/patients/{patient_id}/alerts", json=alert_payload(
        client, patient_id, photo_id, width_cm=width, height_cm=height))
    assert response.status_code == 400


def test_dose_preset_is_patient_specific_and_only_recorded_on_completion(client, patient_id, photo_id):
    assert state(client, patient_id)["dosage"]["rate"] == .15
    assert set_dose(client, patient_id, .17).status_code == 400  # Reason is required.
    assert set_dose(client, patient_id, .17, "Adjusted documented rate", "higher", .02).status_code == 200
    before = state(client, patient_id)
    assert not before["events"] and before["dosage"]["status"] == "increased"
    other = client.post("/api/patients", json={"code": "SECOND", "alias": "Other", "start_at": iso(now_utc())}).json()["id"]
    assert state(client, other)["dosage"]["rate"] == .15
    payload = event_payload(client, patient_id, photo_id)
    payload.pop("point_checked"); payload.pop("clinical_checked")
    response = client.post(f"/api/patients/{patient_id}/events", json=payload)
    assert response.status_code == 200, response.text
    after = state(client, patient_id)
    assert after["events"][0]["dosage_rate"] == .17
    assert after["events"][0]["dosage_category"] == "higher"
    assert after["events"][0]["dosage_previous_rate"] == .15
    assert after["events"][0]["dosage_status"] == "increased"
    assert after["dosage"]["rate"] == .17 and after["dosage"]["status"] == "unchanged"
    assert not after["dosage"]["pending"] and after["dosage"]["step"] == .02
    assert set_dose(client, patient_id, .14, "Documented decrease", "lower").status_code == 200
    assert state(client, patient_id)["dosage"]["status"] == "decreased"
    assert record(client, patient_id, photo_id, x=0, y=6).status_code == 200
    assert state(client, patient_id)["dosage"]["rate"] == .14
    # Login/restart does not reset patient settings or recorded defaults.
    with TestClient(create_app(client.app.state.data_dir, testing=True)) as restarted:
        restarted.cookies.update(client.cookies)
        assert state(restarted, patient_id)["dosage"]["rate"] == .14


@pytest.mark.parametrize("field,value", [("rate", -1), ("rate", "NaN"), ("step", 0), ("step", True), ("category", "invalid")])
def test_dosage_validation(client, patient_id, field, value):
    assert set_dose(client, patient_id, **{field: value}).status_code == 400


def test_dose_stale_version_and_failed_puncture_do_not_commit(client, patient_id, photo_id):
    old = version(client, patient_id)
    assert set_dose(client, patient_id, .2, "Increase reason").status_code == 200
    assert client.post(f"/api/patients/{patient_id}/dosage", json={"version": old, "rate": .4, "step": .01,
                       "category": "higher", "reason": "Stale change"}).status_code == 409
    assert record(client, patient_id, photo_id, x=0, y=0).status_code == 422
    data = state(client, patient_id)
    assert not data["events"] and data["dosage"]["pending"]


def test_historical_dose_does_not_replace_current_default(client, patient_id, photo_id):
    assert set_dose(client, patient_id, .2, "Latest rate").status_code == 200
    assert record(client, patient_id, photo_id).status_code == 200
    r = record(client, patient_id, photo_id, kind="history", occurred_at=iso(now_utc()-timedelta(days=40)),
               exception_reason="Earlier paper record", dosage_rate=.1, dosage_category="lower", dosage_reason="Earlier rate")
    assert r.status_code == 200, r.text
    assert state(client, patient_id)["dosage"]["rate"] == .2


def test_appointment_day_and_weekday_rules(client, patient_id, photo_id):
    when = iso(now_utc())
    assert record(client, patient_id, photo_id, occurred_at=when).status_code == 200
    response = client.post(f"/api/patients/{patient_id}/appointment-settings", json={"version": version(client, patient_id),
                           "mode": "days", "days": 5, "weekdays": [0, 2]})
    assert response.status_code == 200
    data = state(client, patient_id)
    assert data["appointment_settings"] == {"mode": "days", "days": 5, "weekdays": []}
    assert data["appointment"]["due_at"] == iso(parse_time(when)+timedelta(days=5))
    weekday = parse_time(when).astimezone(JST).weekday()
    response = client.post(f"/api/patients/{patient_id}/appointment-settings", json={"version": version(client, patient_id),
                           "mode": "weekdays", "weekdays": [weekday], "days": 99})
    assert response.status_code == 200
    assert state(client, patient_id)["appointment"]["due_at"] == iso(parse_time(when)+timedelta(days=7))
    items = client.get("/api/appointments").json()["items"]
    assert sum(i["next"] for i in items) == 1
    assert not any(i["kind"] == "projection" for i in items)
    assert client.post(f"/api/patients/{patient_id}/appointment-settings", json={"version": version(client, patient_id),
                       "mode": "weekdays", "weekdays": []}).status_code == 400


def test_weekday_rule_uses_japan_day_and_first_appointment_anchor():
    p = {"appointment_mode": "weekdays", "appointment_days": 3, "appointment_weekdays": "[0, 2, 4]",
         "start_at": "2026-09-20T15:30:00Z"}  # Monday 00:30 JST.
    assert next_due(p, None) == "2026-09-20T15:30:00Z"
    assert next_due(p, p["start_at"]) == "2026-09-22T15:30:00Z"  # Wednesday.


def test_reporting_averages_and_missing_values_jst_boundary():
    dates = ["2026-08-31T15:00:00Z", "2026-09-10T10:00:00Z", "2026-09-12T10:00:00Z", "2026-10-01T00:00:00Z"]
    events = [{"id": i+1, "site_number": 1 if i<2 else 2, "occurred_at": date, "voided_at": None,
               "dosage_rate": [.1,.3,None,.9][i]} for i,date in enumerate(dates)]
    as_of = parse_time("2026-12-31T00:00:00Z")
    month = make_report(events, [], "month", "2026-09", 0, as_of)
    assert [p["rate"] for p in month["points"]] == [.1,.3]
    assert month["missing_dosage_count"] == 1
    year = make_report(events, [], "year", "2026", 0, as_of)
    assert [p["rate"] for p in year["points"]] == [.2,.9]
    total = make_report(events, [], "total", "", 0, as_of)
    assert total["points"][0]["rate"] == pytest.approx(1.3/3, abs=1e-6)
    assert make_report(events, [], "month", "2026-09", 2, as_of)["missing_dosage_count"] == 1


def test_snapshot_recovery_and_trouble_counts(client, patient_id, photo_id):
    observed = now_utc()-timedelta(seconds=40)
    response = client.post(f"/api/patients/{patient_id}/alerts", json=alert_payload(
        client, patient_id, photo_id, observed_at=iso(observed), width_cm=.3, height_cm=.6))
    aid = response.json()["id"]
    before = client.get(f"/api/patients/{patient_id}/snapshot", params={"at": iso(observed-timedelta(seconds=10)), "photo_id": photo_id})
    assert before.status_code == 200 and before.json()["alerts"] == []
    during = client.get(f"/api/patients/{patient_id}/snapshot", params={"at": iso(observed+timedelta(seconds=10)), "photo_id": photo_id}).json()
    assert during["alerts"][0]["id"] == aid and during["alerts"][0]["height_cm"] == .6
    assert client.post(f"/api/alerts/{aid}/resolve", json={"version": version(client, patient_id),
        "healed_confirmed": True, "note": "Recovered"}).status_code == 200
    current = client.get(f"/api/patients/{patient_id}/snapshot", params={"at": iso(now_utc()), "photo_id": photo_id}).json()
    assert not current["alerts"]
    report = client.get(f"/api/patients/{patient_id}/records?view=total").json()
    assert report["report"]["block_counts"][0]["count"] == 1  # Recovery does not erase the episode.
    assert client.post(f"/api/alerts/{aid}/void", json={"version": version(client, patient_id), "reason": "Duplicate"}).status_code == 200
    report = client.get(f"/api/patients/{patient_id}/records?view=total").json()
    assert report["report"]["block_counts"][0]["count"] == 0
    assert report["alerts"][0]["voided_at"] and report["revisions"]


def test_corrections_audit_export_and_photo_retention(client, patient_id, photo_id):
    response = record(client, patient_id, photo_id)
    eid = response.json()["id"]
    response = client.patch(f"/api/events/{eid}", json={"version": version(client, patient_id), "dosage_rate": .25,
                            "dosage_reason": "Corrected from source", "reason": "Transcription error", "note": "Correct note"})
    assert response.status_code == 200, response.text
    d = client.get(f"/api/patients/{patient_id}/records?view=total").json()
    assert d["report"]["points"][0]["rate"] == .25
    assert state(client, patient_id)["dosage"]["rate"] == .25
    revision = client.get(f"/api/patients/{patient_id}/revisions/{d['revisions'][0]['id']}").json()
    assert revision["before"]["dosage_rate"] == .15 and revision["after"]["dosage_rate"] == .25
    audit = client.get("/api/audit").json()["items"][0]
    assert audit["patient_code"] == "TEST-001" and audit["patient_exists"]
    assert "0.15" in " ".join(audit["changes"]) and "0.25" in " ".join(audit["changes"])
    exported = list(csv.DictReader(io.StringIO(client.get(f"/api/patients/{patient_id}/export.csv").text.lstrip('\ufeff'))))
    assert exported[0]["dosage_rate_ml_per_hour"] == "0.25"
    assert client.request("DELETE", f"/api/photos/{photo_id}", json={"version": version(client, patient_id), "reason": "Remove"}).status_code == 409


def test_nurse_deletion_revokes_session_and_preserves_records(client, patient_id, photo_id):
    uid = client.post('/api/users', json={"username": "nurse-delete", "display_name": "Nurse Example",
        "password": "Synthetic-nurse-123", "role": "nurse"}).json()["id"]
    with TestClient(client.app) as nurse:
        nurse.headers['x-csrf-token'] = nurse.get('/api/bootstrap').json()['csrf']
        login = nurse.post('/api/login', json={"username": "nurse-delete", "password": "Synthetic-nurse-123"}).json()
        nurse.headers['x-csrf-token'] = login['csrf']
        assert record(nurse, patient_id, photo_id).status_code == 200
        eid = state(nurse, patient_id)["events"][0]["id"]
        assert nurse.patch(f"/api/events/{eid}", json={"version": version(nurse, patient_id), "reason": "Correction"}).status_code == 403
        assert nurse.get(f"/api/patients/{patient_id}/records").status_code == 200
        assert client.request("DELETE", f"/api/users/{uid}", json={"confirm_username": "wrong"}).status_code == 400
        assert client.request("DELETE", f"/api/users/{uid}", json={"confirm_username": "nurse-delete"}).status_code == 200
        assert nurse.get(f"/api/patients/{patient_id}/records").status_code == 401
    assert state(client, patient_id)["events"][0]["actor"] == "Nurse Example"


def test_migration_keeps_old_rates_unknown_and_old_circle_geometry(client, patient_id, photo_id):
    assert record(client, patient_id, photo_id).status_code == 200
    assert client.post(f"/api/patients/{patient_id}/alerts", json=alert_payload(client, patient_id, photo_id)).status_code == 200
    with transaction(client.app.state.data_dir, True) as db:
        db.execute("UPDATE complications SET types_json='[\"pain\"]'")
        db.execute("UPDATE schema_info SET version=1")
        db.execute("UPDATE app_settings SET keep_calibration=0")
        for column in ("dosage_rate", "dosage_category", "dosage_previous_rate", "dosage_status", "dosage_reason"):
            db.execute(f"ALTER TABLE events DROP COLUMN {column}")
        db.execute("ALTER TABLE complications DROP COLUMN width_cm")
        db.execute("ALTER TABLE complications DROP COLUMN height_cm")
    initialize(client.app.state.data_dir)
    d = state(client, patient_id)
    assert d["events"][0]["dosage_rate"] is None
    assert d["alerts"][0]["width_cm"] == d["alerts"][0]["height_cm"] == 2
    assert d["alerts"][0]["types"] == ["pain_tenderness_legacy"]
    eid = d["events"][0]["id"]
    response = client.patch(f"/api/events/{eid}", json={"version": d["patient"]["version"],
        "reason": "Correct a note without inventing a dosage", "note": "Updated legacy note", "dosage_rate": ""})
    assert response.status_code == 200, response.text
    assert state(client, patient_id)["events"][0]["dosage_rate"] is None
    assert client.get('/api/settings').json()['keep_calibration']
    settings = client.get('/api/settings').json()
    assert client.post('/api/settings', json={"keep_calibration": False, "revision": settings["revision"]}).status_code == 200
    initialize(client.app.state.data_dir)
    assert not client.get('/api/settings').json()['keep_calibration']  # Choice survives later restarts.


def test_alert_correction_and_deleted_history_preserve_originals(client, patient_id, photo_id):
    aid = client.post(f"/api/patients/{patient_id}/alerts", json=alert_payload(
        client, patient_id, photo_id, width_cm=.3, height_cm=.3, types=["pain"])).json()["id"]
    r = client.patch(f"/api/alerts/{aid}", json={"version": version(client, patient_id), "width_cm": .8,
        "height_cm": .2, "types": ["tenderness"], "reason": "Correct measurement and observation"})
    assert r.status_code == 200, r.text
    d = client.get(f"/api/patients/{patient_id}/records").json()
    assert d["alerts"][0]["width_cm"] == .8
    revision = client.get(f"/api/patients/{patient_id}/revisions/{d['revisions'][0]['id']}").json()
    assert revision["before"]["types"] == ["pain"] and revision["after"]["types"] == ["tenderness"]
    stale = version(client, patient_id)-1
    assert client.patch(f"/api/alerts/{aid}", json={"version": stale, "reason": "Stale edit"}).status_code == 409


def test_dosage_context_uses_history_time_and_excludes_corrected_event(client, patient_id, photo_id):
    when = iso(now_utc()-timedelta(days=4))
    result = record(client, patient_id, photo_id, kind="history", occurred_at=when, exception_reason="Synthetic earlier record",
                    dosage_rate=.22, dosage_category="higher", dosage_reason="Known historical value")
    assert result.status_code == 200
    eid = result.json()["id"]
    r = client.get(f"/api/patients/{patient_id}/dosage-context", params={"at": iso(now_utc())}).json()
    assert r == {"previous_rate": .22, "previous_event_id": eid}
    r = client.get(f"/api/patients/{patient_id}/dosage-context", params={"at": when, "exclude_id": eid}).json()
    assert r == {"previous_rate": .15, "previous_event_id": None}
    later = record(client, patient_id, photo_id, kind="history", occurred_at=when,
                   exception_reason="Second synthetic record at the same time", dosage_rate=.24,
                   dosage_category="higher", dosage_reason="Second documented rate")
    assert later.status_code == 200, later.text
    r = client.get(f"/api/patients/{patient_id}/dosage-context", params={"at": when, "exclude_id": eid}).json()
    assert r == {"previous_rate": .15, "previous_event_id": None}
    r = client.get(f"/api/patients/{patient_id}/dosage-context", params={"at": when, "exclude_id": later.json()["id"]}).json()
    assert r == {"previous_rate": .22, "previous_event_id": eid}


def test_unused_photo_delete_and_deleted_patient_audit_links(client, patient_id):
    pid = upload(client, patient_id)
    r = client.request("DELETE", f"/api/photos/{pid}", json={"version": version(client, patient_id), "reason": "Wrong unused image"})
    assert r.status_code == 200
    assert not state(client, patient_id)["photos"]
    assert client.get(f"/api/photos/{pid}/image").status_code == 404
    r = client.request("DELETE", f"/api/patients/{patient_id}", json={"version": version(client, patient_id), "confirm_code": "TEST-001"})
    assert r.status_code == 200
    entries = client.get('/api/audit').json()['items']
    assert all(e['patient_code'] == 'TEST-001' and not e['patient_exists'] for e in entries if e['patient_id'] == patient_id)
