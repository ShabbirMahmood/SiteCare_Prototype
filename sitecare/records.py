"""Patient-specific flow-rate history, appointment rules and report summaries.

Rates are mL/h. Period averages are arithmetic means of recorded rates, never
delivered volumes: the prototype does not record infusion start/stop times.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import timedelta

from .rules import JST, event_applies, iso, now_utc, parse_time
from .storage import one


def previous_dosage(db, patient_id, at=None, exclude_id=None):
    at = iso(at or now_utc())
    return one(db, "SELECT * FROM events WHERE patient_id=? AND occurred_at<=? "
               "AND (voided_at IS NULL OR voided_at>?) AND dosage_rate IS NOT NULL "
               "AND id!=? AND (?=0 OR occurred_at<? OR id<?) ORDER BY occurred_at DESC,id DESC LIMIT 1",
               (patient_id, at, at, exclude_id or -1, exclude_id or 0, at, exclude_id or 0))


def dosage_status(rate, previous):
    delta = round(rate - previous, 6)
    return "increased" if delta > 0 else "decreased" if delta < 0 else "unchanged"


def dosage_settings(db, p):
    last = previous_dosage(db, p["id"])
    rate = last["dosage_rate"] if last else 0.15
    category = last["dosage_category"] if last else "standard"
    pending = bool(p["dosage_pending"])
    selected = p["dosage_rate"] if pending else rate
    return {"category": p["dosage_category"] if pending else category, "rate": selected,
            "step": p["dosage_step"], "reason": p["dosage_reason"] if pending else "",
            "previous_rate": rate, "previous_event_id": last["id"] if last else None,
            "status": dosage_status(selected, rate), "pending": pending}


def appointment_settings(p):
    return {"mode": p["appointment_mode"], "days": p["appointment_days"],
            "weekdays": json.loads(p["appointment_weekdays"])}


def next_due(p, last_time):
    settings = appointment_settings(p)
    if last_time:
        anchor = parse_time(last_time).astimezone(JST)
        if settings["mode"] == "days":
            return iso(anchor + timedelta(days=settings["days"]))
        start = 1  # The next visit is strictly after the puncture's calendar day.
    else:
        anchor = parse_time(p["start_at"]).astimezone(JST)
        if settings["mode"] == "days":
            return iso(anchor)  # Initial appointment entered at patient creation.
        start = 0
    for offset in range(start, start + 7):
        candidate = anchor + timedelta(days=offset)
        if candidate.weekday() in settings["weekdays"]:
            return iso(candidate)
    raise ValueError("At least one appointment weekday is required")


def make_report(events, alerts, view, period, site, as_of):
    def matches(value):
        local = parse_time(value).astimezone(JST)
        return view == "total" or local.strftime("%Y-%m" if view == "month" else "%Y") == period

    all_valid = [e for e in events if event_applies(e, as_of) and matches(e["occurred_at"])]
    valid = [e for e in all_valid if not site or e["site_number"] == site]
    measured = [e for e in valid if e.get("dosage_rate") is not None]
    groups = defaultdict(list)
    for e in sorted(measured, key=lambda e: (e["occurred_at"], e["id"])):
        local = parse_time(e["occurred_at"]).astimezone(JST)
        key = str(e["id"]) if view == "month" else local.strftime("%Y-%m" if view == "year" else "%Y")
        groups[key].append(e)
    points = []
    for key, group in groups.items():
        values = [e["dosage_rate"] for e in group]
        points.append({"key": key, "at": group[0]["occurred_at"], "count": len(values),
                       "rate": round(sum(values) / len(values), 6), "min": min(values), "max": max(values),
                       "site_number": group[0]["site_number"] if view == "month" else site,
                       "event_ids": [e["id"] for e in group]})
    observed = [a for a in alerts if parse_time(a["observed_at"]) <= as_of and matches(a["observed_at"])
                and (not a.get("voided_at") or parse_time(a["voided_at"]) > as_of)]
    counts = [{"site": n, "count": sum(a["site_number"] == n for a in observed)} for n in range(1, 15)]
    site_summary = []
    for n in range(1, 15):
        values = [e["dosage_rate"] for e in all_valid if e["site_number"] == n and e.get("dosage_rate") is not None]
        site_summary.append({"site": n, "count": len(values),
                             "average": round(sum(values) / len(values), 6) if values else None,
                             "min": min(values) if values else None, "max": max(values) if values else None})
    return {"view": view, "period": period, "site": site, "points": points, "block_counts": counts,
            "site_summary": site_summary, "events": valid, "missing_dosage_count": len(valid) - len(measured),
            "aggregation": "recorded_rate" if view == "month" else "arithmetic_mean", "unit": "mL/h"}


ACTION_LABELS = {
    "patient.created": "Patient Created", "patient.updated": "Patient Profile Updated",
    "patient.deleted": "Patient Deleted", "patient.csv_exported": "Patient CSV Exported",
    "photo.uploaded": "Photo Uploaded", "photo.aligned": "Photo Alignment Saved",
    "photo.alignment_saved": "Photo Alignment Saved", "layout.updated": "Site Layout Updated",
    "photo.alignment_verified": "Photo Alignment Verified", "layout.reset_to_default": "Default Site Layout Restored",
    "auth.login": "Signed In", "installation.setup": "Workspace Created", "password.reset": "Password Reset",
    "puncture.recorded": "Puncture Recorded", "puncture.voided": "Puncture Deleted From Active Records",
    "puncture.updated": "Puncture Corrected", "skin.alert_created": "Skin Alert Recorded",
    "skin.recovery_confirmed": "Skin Recovery Confirmed", "skin.updated": "Skin Alert Corrected",
    "skin.voided": "Skin Alert Deleted From Active Records", "dosage.updated": "Dosage Preset Updated",
    "appointment.rule_updated": "Appointment Suggestion Updated", "appointment.confirmed": "Appointment Confirmed",
    "settings.changed": "Calibration Setting Changed", "clock.changed": "Application Date Changed",
    "user.created": "User Created", "user.deleted": "Nurse Account Deleted", "backup.exported": "Backup Exported",
}


def describe_audit(row):
    d = row["detail"]
    action = row["action"]
    label = ACTION_LABELS.get(action, action.replace(".", " ").replace("_", " ").title())
    lines = []
    before, after = d.get("before", {}), d.get("after", {})
    names = {"alias": "Display Name", "notes": "Care Notes", "therapy": "Therapy", "active": "Active Patient",
             "dosage_rate": "Flow Rate (mL/h)", "dosage_category": "Dosage Category", "dosage_reason": "Dosage Reason",
             "site_number": "Site", "occurred_at": "Puncture Time", "note": "Note", "observed_at": "Observation Time",
             "width_cm": "Width (cm)", "height_cm": "Height (cm)", "severity": "Severity", "x": "X (cm)", "y": "Y (cm)",
             "keep_calibration": "Keep Calibration", "rate": "Flow Rate (mL/h)", "category": "Category",
             "mode": "Mode", "days": "Days", "weekdays": "Weekdays", "step": "Step (mL/h)"}
    names.update({"cx": "Navel Image X", "cy": "Navel Image Y", "ppm": "Pixels Per cm", "angle": "Photo Rotation",
                  "now": "Application Date", "types_json": "Observations", "voided_at": "Deleted At"})
    def readable(key, value):
        if value is None:
            return "—"
        if key == "types_json":
            return ", ".join(json.loads(value))
        if key == "weekdays":
            return ", ".join(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][n] for n in value) or "None"
        if key in ("active", "keep_calibration"):
            return "On" if value else "Off"
        if key == "mode":
            return {"days": "Count Days", "weekdays": "Assign Days From Week", "system": "System Date", "manual": "Demo Date"}.get(value, value)
        if key in ("category", "dosage_category"):
            return str(value).title()
        if key in ("now", "occurred_at", "observed_at", "voided_at"):
            return parse_time(value).astimezone(JST).strftime("%Y-%m-%d %H:%M:%S JST")
        return str(value)
    if isinstance(before, dict) and isinstance(after, dict):
        for key, name in names.items():
            if key in after and before.get(key) != after[key]:
                lines.append(f"{name}: {readable(key, before.get(key))} → {readable(key, after[key])}")
    if action.startswith("layout.") and isinstance(before, list) and isinstance(after, list):
        old = {p["number"]: p for p in before}
        for p in after:
            prior = old.get(p["number"])
            if prior != p:
                lines.append(f"Site {p['number']}: ({prior['x']}, {prior['y']}) → ({p['x']}, {p['y']}) cm" if prior else f"Site {p['number']} Added")
    for key, name in (("site_number", "Site"), ("occurred_at", "Puncture Time"), ("scheduled_at", "Appointment"),
                      ("reason", "Reason"), ("note", "Note"), ("username", "Username"), ("code", "Patient ID"),
                      ("width_cm", "Width (cm)"), ("height_cm", "Height (cm)"), ("dosage_rate", "Flow Rate (mL/h)")):
        if d.get(key) is not None and d.get(key) != "":
            value = parse_time(d[key]).astimezone(JST).strftime("%Y-%m-%d %H:%M:%S JST") if key in ("occurred_at", "scheduled_at") else d[key]
            lines.append(f"{name}: {value}")
    if d.get("types"):
        lines.append("Observations: " + ", ".join(d["types"]))
    if d.get("captured_at"):
        lines.append("Photo Captured: " + parse_time(d["captured_at"]).astimezone(JST).strftime("%Y-%m-%d %H:%M:%S JST"))
    if not lines:
        lines = [label + (f" · Record {row['entity']}" if str(row["entity"]).isdigit() else "")]
    return {"action_label": label, "summary": "; ".join(lines[:2]), "changes": lines}
