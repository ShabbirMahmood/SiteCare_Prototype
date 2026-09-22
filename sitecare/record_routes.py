"""Patient preferences, longitudinal reports and auditable record corrections."""
from __future__ import annotations

import json
import re

from fastapi import Request

from .records import appointment_settings, dosage_settings, dosage_status, make_report, previous_dosage
from .rules import (JST, alert_active, assess_point, body_to_image, iso, nearest_site,
                    now_utc, parse_time)
from .storage import audit, cleanup_deleted_photos, decode_photo, one, patient_records, rows, transaction


def register_record_routes(app, data_dir):
    from .app import (AppError, COMPLICATION_TYPES, bump, check_version, integer, number,
                      patient, payload, require, sync_appointment, text, timestamp)

    def revision(db, kind, before, after, user, reason):
        db.execute("INSERT INTO record_revisions(patient_id,record_type,record_id,changed_at,actor,reason,before_json,after_json) "
                   "VALUES(?,?,?,?,?,?,?,?)", (before["patient_id"], kind, before["id"], iso(now_utc()), user["display_name"],
                   reason, json.dumps(before, ensure_ascii=False), json.dumps(after, ensure_ascii=False)))

    @app.get("/api/patients/{patient_id}/dosage-context")
    def get_dosage_context(request: Request, patient_id: int, at: str, exclude_id: int = 0):
        require(request)
        at = timestamp(at, "Puncture time", True)
        with transaction(data_dir) as db:
            patient(db, patient_id)
            previous = previous_dosage(db, patient_id, parse_time(at), exclude_id)
        return {"previous_rate": previous["dosage_rate"] if previous else .15,
                "previous_event_id": previous["id"] if previous else None}

    @app.post("/api/patients/{patient_id}/dosage")
    async def set_dosage(request: Request, patient_id: int):
        user = require(request)
        data = await payload(request)
        category = data.get("category")
        if category not in ("higher", "standard", "lower"):
            raise AppError("Choose one dosage category.")
        rate = number(data.get("rate"), "Drug Dosage Amount (mL/h)", 0, 1000)
        step = number(data.get("step"), "Step (mL/h)", 0.000001, 1000)
        with transaction(data_dir, True) as db:
            p = check_version(db, patient_id, data)
            before = dosage_settings(db, p)
            changed = dosage_status(rate, before["previous_rate"]) != "unchanged"
            reason = text(data.get("reason", ""), "Dosage change reason", 2000, required=changed)
            db.execute("UPDATE patients SET dosage_category=?,dosage_rate=?,dosage_step=?,dosage_reason=?,dosage_pending=1 WHERE id=?",
                       (category, rate, step, reason, patient_id))
            bump(db, patient_id)
            after = dosage_settings(db, patient(db, patient_id))
            audit(db, user["display_name"], "dosage.updated", str(patient_id), {"before": before, "after": after}, patient_id)
        return after

    @app.post("/api/patients/{patient_id}/appointment-settings")
    async def set_appointment_settings(request: Request, patient_id: int):
        user = require(request)
        data = await payload(request)
        mode = data.get("mode")
        if mode not in ("days", "weekdays"):
            raise AppError("Choose Count Days or Assign Days From Week.")
        days = integer(data.get("days", 3), "Days", 1, 365) if mode == "days" else 3
        weekdays = data.get("weekdays", []) if mode == "weekdays" else []
        if not isinstance(weekdays, list) or (mode == "weekdays" and not weekdays):
            raise AppError("Select at least one weekday.")
        weekdays = sorted({integer(n, "Weekday", 0, 6) for n in weekdays})
        with transaction(data_dir, True) as db:
            p = check_version(db, patient_id, data)
            before = appointment_settings(p)
            db.execute("UPDATE patients SET appointment_mode=?,appointment_days=?,appointment_weekdays=? WHERE id=?",
                       (mode, days, json.dumps(weekdays), patient_id))
            sync_appointment(db, patient_id, force=True)
            bump(db, patient_id)
            after = appointment_settings(patient(db, patient_id))
            audit(db, user["display_name"], "appointment.rule_updated", str(patient_id), {"before": before, "after": after}, patient_id)
        return after

    @app.get("/api/patients/{patient_id}/records")
    def get_records(request: Request, patient_id: int, view: str = "month", period: str = "", site: int = 0):
        require(request)
        if view not in ("month", "year", "total") or site not in range(15):
            raise AppError("Choose Month, Year or Total and a site from 1 to 14.")
        period = period or now_utc().astimezone(JST).strftime("%Y-%m" if view == "month" else "%Y")
        pattern = r"\d{4}-(0[1-9]|1[0-2])" if view == "month" else r"\d{4}"
        if view != "total" and not re.fullmatch(pattern, period):
            raise AppError("Choose a valid reporting period.")
        with transaction(data_dir) as db:
            p = patient(db, patient_id)
            _, events, alerts, _ = patient_records(db, patient_id)
            photos = [decode_photo(r) for r in rows(db, "SELECT * FROM photos WHERE patient_id=? ORDER BY id", (patient_id,))]
            for n, photo in enumerate(photos, 1):
                photo["number"] = n
                photo["record_count"] = sum(e["photo_id"] == photo["id"] for e in events) + sum(a["photo_id"] == photo["id"] for a in alerts)
            revisions = rows(db, "SELECT id,record_type,record_id,changed_at,actor,reason FROM record_revisions WHERE patient_id=? ORDER BY id DESC", (patient_id,))
            report = make_report(events, alerts, view, period, site, now_utc())
        return {"patient": p, "report": report, "events": events, "alerts": alerts,
                "photos": photos, "revisions": revisions, "now": iso(now_utc())}

    @app.get("/api/patients/{patient_id}/snapshot")
    def get_snapshot(request: Request, patient_id: int, at: str, photo_id: int = 0):
        require(request)
        at = timestamp(at, "Historical view time", True)
        moment = parse_time(at)
        with transaction(data_dir) as db:
            patient(db, patient_id)
            photo = decode_photo(one(db, "SELECT * FROM photos WHERE patient_id=? AND captured_at<=? "
                                      + ("AND id=? " if photo_id else "") + "ORDER BY id DESC LIMIT 1",
                                     (patient_id, at, photo_id) if photo_id else (patient_id, at)))
            if not photo:
                raise AppError("No photograph was available at this time. Choose a later time or a different photo.", 404)
            _, events, alerts, _ = patient_records(db, patient_id)
            # Apply the latest corrected facts to the selected clinical date.
            # Every original value is separately available in the revision history.
            active = [a for a in alerts if alert_active(a, moment)]
            punctures = [e for e in events if parse_time(e["occurred_at"]) <= moment
                         and (not e["voided_at"] or parse_time(e["voided_at"]) > moment)]
        return {"at": at, "photo": photo, "alerts": active, "events": punctures,
                "basis": "Corrected records, filtered by observation/recovery/deletion time"}

    @app.get("/api/patients/{patient_id}/revisions/{revision_id}")
    def get_revision(request: Request, patient_id: int, revision_id: int):
        require(request)
        with transaction(data_dir) as db:
            patient(db, patient_id)
            item = one(db, "SELECT * FROM record_revisions WHERE id=? AND patient_id=?", (revision_id, patient_id))
        if not item:
            raise AppError("Revision not found.", 404)
        for field in ("before", "after"):
            item[field] = json.loads(item.pop(field + "_json"))
            if "types_json" in item[field]:
                item[field]["types"] = json.loads(item[field].pop("types_json"))
            for hidden in ("request_key", "alignment_json", "warnings_json"):
                item[field].pop(hidden, None)
        return item

    @app.patch("/api/events/{event_id}")
    async def correct_event(request: Request, event_id: int):
        user = require(request, True)
        data = await payload(request)
        reason = text(data.get("reason"), "Correction reason", 2000, True)
        with transaction(data_dir, True) as db:
            before = one(db, "SELECT * FROM events WHERE id=?", (event_id,))
            if not before:
                raise AppError("Puncture record not found.", 404)
            check_version(db, before["patient_id"], data)
            if before["voided_at"]:
                raise AppError("A deleted record cannot be edited. Add a corrected historical record.", 409)
            occurred = timestamp(data.get("occurred_at", before["occurred_at"]), "Puncture time", True)
            point = {k: number(data.get(k, before[k]), k.upper(), -40, 40) for k in ("x", "y")}
            photo = decode_photo(one(db, "SELECT * FROM photos WHERE id=?", (before["photo_id"],)))
            n = nearest_site(point, photo["sites"])
            _, events, alerts, reviews = patient_records(db, before["patient_id"])
            assessed = assess_point(point, n, [e for e in events if e["id"] != event_id], alerts, reviews, photo,
                                    parse_time(occurred), freshness=False)
            raw_rate = data.get("dosage_rate", before["dosage_rate"])
            rate = None if raw_rate in (None, "") and before["dosage_rate"] is None else number(raw_rate, "Flow Rate (mL/h)", 0, 1000)
            category = data.get("dosage_category", before["dosage_category"] or "standard")
            if category not in ("higher", "standard", "lower"):
                raise AppError("Choose a valid dosage category.")
            previous = previous_dosage(db, before["patient_id"], parse_time(occurred), event_id)
            prior_rate = previous["dosage_rate"] if previous else 0.15
            status = dosage_status(rate, prior_rate) if rate is not None else None
            dose_reason = text(data.get("dosage_reason", before["dosage_reason"]), "Dosage reason", 2000,
                               status is not None and status != "unchanged")
            if rate is None:
                category = prior_rate = None
            note = text(data.get("note", before["note"]), "Note")
            db.execute("UPDATE events SET occurred_at=?,site_number=?,x=?,y=?,note=?,dosage_rate=?,dosage_category=?,"
                       "dosage_previous_rate=?,dosage_status=?,dosage_reason=?,warnings_json=? WHERE id=?",
                       (occurred, n, point["x"], point["y"], note, rate, category, prior_rate, status, dose_reason,
                        json.dumps(assessed["reasons"]), event_id))
            after = one(db, "SELECT * FROM events WHERE id=?", (event_id,))
            revision(db, "puncture", before, after, user, reason)
            sync_appointment(db, before["patient_id"])
            bump(db, before["patient_id"])
            audit(db, user["display_name"], "puncture.updated", str(event_id),
                  {"before": before, "after": after, "reason": reason}, before["patient_id"])
        return {"ok": True}

    @app.patch("/api/alerts/{alert_id}")
    async def correct_alert(request: Request, alert_id: int):
        user = require(request, True)
        data = await payload(request)
        reason = text(data.get("reason"), "Correction reason", 2000, True)
        with transaction(data_dir, True) as db:
            before = one(db, "SELECT * FROM complications WHERE id=?", (alert_id,))
            if not before:
                raise AppError("Alert not found.", 404)
            check_version(db, before["patient_id"], data)
            if before["voided_at"]:
                raise AppError("A deleted alert cannot be edited.", 409)
            observed = timestamp(data.get("observed_at", before["observed_at"]), "Observation time", True)
            if before["resolved_at"] and observed > before["resolved_at"]:
                raise AppError("Observation cannot be later than its recovery.")
            width = number(data.get("width_cm", before["width_cm"]), "Width (cm)", 0.01, 30)
            height = number(data.get("height_cm", before["height_cm"]), "Height (cm)", 0.01, 30)
            point = {k: number(data.get(k, before[k]), k.upper(), -40, 40) for k in ("x", "y")}
            types = data.get("types", json.loads(before["types_json"]))
            supported_types = COMPLICATION_TYPES | ({"pain_tenderness_legacy"} if "pain_tenderness_legacy" in json.loads(before["types_json"]) else set())
            if not isinstance(types, list) or not types or any(not isinstance(t, str) or t not in supported_types for t in types):
                raise AppError("Select a supported observation type.")
            severity = data.get("severity", before["severity"])
            if severity not in ("mild", "moderate", "severe"):
                raise AppError("Choose a valid severity.")
            photo = decode_photo(one(db, "SELECT * FROM photos WHERE id=?", (before["photo_id"],)))
            x, y = body_to_image(point["x"], point["y"], photo["alignment"])
            if not (0 <= x <= photo["width"] and 0 <= y <= photo["height"]):
                raise AppError("Place the centre on the source photo.")
            db.execute("UPDATE complications SET observed_at=?,width_cm=?,height_cm=?,radius=?,x=?,y=?,site_number=?,"
                       "types_json=?,severity=?,note=? WHERE id=?",
                       (observed, width, height, max(width, height) / 2, point["x"], point["y"], nearest_site(point, photo["sites"]),
                        json.dumps(sorted(set(types))), severity, text(data.get("note", before["note"]), "Note"), alert_id))
            after = one(db, "SELECT * FROM complications WHERE id=?", (alert_id,))
            revision(db, "skin", before, after, user, reason)
            bump(db, before["patient_id"])
            audit(db, user["display_name"], "skin.updated", str(alert_id), {"before": before, "after": after, "reason": reason}, before["patient_id"])
        return {"ok": True}

    @app.post("/api/alerts/{alert_id}/void")
    async def void_alert(request: Request, alert_id: int):
        user = require(request, True)
        data = await payload(request)
        reason = text(data.get("reason"), "Deletion reason", 2000, True)
        with transaction(data_dir, True) as db:
            before = one(db, "SELECT * FROM complications WHERE id=?", (alert_id,))
            if not before:
                raise AppError("Alert not found.", 404)
            check_version(db, before["patient_id"], data)
            if before["voided_at"]:
                raise AppError("Already deleted.", 409)
            if parse_time(before["observed_at"]) > now_utc():
                raise AppError("Change the application date before deleting this future record.")
            db.execute("UPDATE complications SET voided_at=?,voided_by=?,void_reason=? WHERE id=?",
                       (iso(now_utc()), user["display_name"], reason, alert_id))
            after = one(db, "SELECT * FROM complications WHERE id=?", (alert_id,))
            revision(db, "skin", before, after, user, reason)
            bump(db, before["patient_id"])
            audit(db, user["display_name"], "skin.voided", str(alert_id), {"reason": reason}, before["patient_id"])
        return {"ok": True}

    @app.delete("/api/photos/{photo_id}")
    async def delete_unused_photo(request: Request, photo_id: int):
        user = require(request, True)
        data = await payload(request)
        reason = text(data.get("reason"), "Deletion reason", 2000, True)
        with transaction(data_dir, True) as db:
            photo = one(db, "SELECT * FROM photos WHERE id=?", (photo_id,))
            if not photo:
                raise AppError("Photo not found.", 404)
            check_version(db, photo["patient_id"], data)
            for table in ("events", "complications"):
                if one(db, f"SELECT id FROM {table} WHERE photo_id=?", (photo_id,)):
                    raise AppError("This photograph supports saved records and must be retained with them.", 409)
            db.execute("INSERT OR IGNORE INTO pending_photo_deletions(filename) VALUES(?)", (photo["filename"],))
            db.execute("DELETE FROM photos WHERE id=?", (photo_id,))
            bump(db, photo["patient_id"])
            audit(db, user["display_name"], "photo.deleted", str(photo_id), {"reason": reason, "captured_at": photo["captured_at"]}, photo["patient_id"])
        try:
            pending = cleanup_deleted_photos(data_dir) > 0
        except OSError:
            pending = True
        return {"ok": True, "photo_cleanup_pending": pending}

    @app.delete("/api/users/{user_id}")
    async def delete_nurse(request: Request, user_id: int):
        user = require(request, True)
        data = await payload(request)
        with transaction(data_dir, True) as db:
            target = one(db, "SELECT id,username,display_name,role FROM users WHERE id=?", (user_id,))
            if not target:
                raise AppError("Account not found.", 404)
            if target["role"] != "nurse" or target["id"] == user["id"]:
                raise AppError("Only nurse accounts can be deleted here.", 403)
            if data.get("confirm_username") != target["username"]:
                raise AppError("Type the nurse username to confirm deletion.")
            db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            db.execute("DELETE FROM users WHERE id=?", (user_id,))
            audit(db, user["display_name"], "user.deleted", str(user_id), target)
        return {"ok": True}
