"""Deterministic rule screening. This is NOT a validated clinical measurement engine.

All coordinates use an approximate patient-relative 2-D plane in centimetres:
navel=(0,0), +x=photo right/patient left, +y=towards the feet. Clinical review and
physical measurement remain necessary even after image calibration.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import cos, sin, pi, hypot
from typing import Any
from .clock import now_utc
from .settings import keep_calibration

UTC = timezone.utc
JST = timezone(timedelta(hours=9), "JST")
REST_DAYS = 12
CHANGE_DAYS = 3
MIN_SPACING_CM = 2.5
NAVEL_RADIUS_CM = 5.0
PHOTO_VALID_HOURS = 24
RECURRENCE_DAYS = 90  # Prototype heuristic, not a clinical standard.
RECURRENCE_COUNT = 2
EPSILON = 1e-8


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 50:
        raise ValueError("A date and time with a timezone are required.")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise ValueError("Invalid date/time. Use an ISO timestamp with a timezone.") from None
    if dt.tzinfo is None:
        raise ValueError("Date/time must include a timezone (Japan: +09:00).")
    return dt.astimezone(UTC)


def default_sites() -> list[dict[str, Any]]:
    """Same numbering topology as the supplied chart, NOT its unscaled geometry."""
    sites = []
    for n in range(1, 9):
        angle = (n - 1) * pi / 4
        sites.append({"number": n, "x": round(6 * sin(angle), 6),
                      "y": round(-6 * cos(angle), 6)})
    outer = [(9, 9.5, -5.5), (10, 10.5, 0), (11, 9.5, 5.5),
             (12, -9.5, 5.5), (13, -10.5, 0), (14, -9.5, -5.5)]
    sites.extend({"number": n, "x": x, "y": y} for n, x, y in outer)
    return sites


def distance(a: dict, b: dict) -> float:
    return hypot(a["x"] - b["x"], a["y"] - b["y"])


def inside_alert(point: dict, alert: dict) -> bool:
    """Full width/height are diameters in the patient coordinate plane."""
    rx = (alert.get("width_cm") or alert["radius"] * 2) / 2
    ry = (alert.get("height_cm") or alert["radius"] * 2) / 2
    return ((point["x"] - alert["x"]) / rx) ** 2 + ((point["y"] - alert["y"]) / ry) ** 2 <= 1 + EPSILON


def body_to_image(x: float, y: float, alignment: dict) -> tuple[float, float]:
    r = alignment["angle"] * pi / 180
    p = alignment["ppm"]
    return (alignment["cx"] + p * (x * cos(r) - y * sin(r)),
            alignment["cy"] + p * (x * sin(r) + y * cos(r)))


def image_to_body(x: float, y: float, alignment: dict) -> tuple[float, float]:
    r = alignment["angle"] * pi / 180
    dx, dy = x - alignment["cx"], y - alignment["cy"]
    return ((dx * cos(r) + dy * sin(r)) / alignment["ppm"],
            (-dx * sin(r) + dy * cos(r)) / alignment["ppm"])


def in_photo(point: dict, photo: dict | None) -> bool:
    if not photo or not photo.get("alignment"):
        return False
    x, y = body_to_image(point["x"], point["y"], photo["alignment"])
    return 0 <= x <= photo["width"] and 0 <= y <= photo["height"]


def photo_ready(photo: dict | None, as_of: datetime, *, freshness: bool = True) -> bool:
    if not photo or not photo.get("verified") or not photo.get("alignment", {}).get("calibration"):
        return False
    if freshness:
        age = as_of - parse_time(photo["captured_at"])
        return age >= timedelta(0) and (keep_calibration.get() or age <= timedelta(hours=PHOTO_VALID_HOURS))
    return True


def nearest_site(point: dict, sites: list[dict]) -> int:
    return min(sites, key=lambda s: (distance(point, s), s["number"]))["number"]


def relevant_complications(point: dict, number: int, complications: list[dict],
                           as_of: datetime) -> list[dict]:
    return [c for c in complications
            if as_of - timedelta(days=RECURRENCE_DAYS) <= parse_time(c["observed_at"]) <= as_of
            and (not c.get("voided_at") or parse_time(c["voided_at"]) > as_of)
            and (c["site_number"] == number or inside_alert(point, c))]


def assess_point(point: dict, number: int, events: list[dict], complications: list[dict],
                 reviews: list[dict], photo: dict | None, as_of: datetime,
                 *, freshness: bool = True) -> dict:
    """Server-side screening; a site's lock and spatial-neighbour locks both apply.

    The 12-day window is half-open: an event at T blocks until, but not including,
    T+12*24h. An unresolved skin alert never expires automatically.
    """
    reasons: list[dict] = []
    locks: list[datetime] = []
    valid_events = [e for e in events if event_applies(e, as_of)]
    same = [e for e in valid_events if e["site_number"] == number]
    last = max(same, key=lambda e: e["occurred_at"]) if same else None
    for e in valid_events:
        until = parse_time(e["occurred_at"]) + timedelta(days=REST_DAYS)
        if until <= as_of:
            continue
        same_site = e["site_number"] == number
        nearby = distance(point, e) + EPSILON < MIN_SPACING_CM
        if same_site or nearby:
            locks.append(until)
            reasons.append({"code": "site_rest" if same_site else "near_recent",
                            "site": e["site_number"], "event_id": e["id"],
                            "distance_cm": round(distance(point, e), 2), "until": iso(until)})
    active = [c for c in complications
              if alert_active(c, as_of) and inside_alert(point, c)]
    for c in active:
        reasons.append({"code": "active_alert", "alert_id": c["id"], "types": c["types"]})
    past = relevant_complications(point, number, complications, as_of)
    latest_episode = max((c["id"] for c in past), default=0)
    recurrent = len(past) >= RECURRENCE_COUNT
    # Recurrence is informational: resolved episodes never impose another hold.
    needs_review = False
    navel_distance = hypot(point["x"], point["y"])
    if navel_distance + EPSILON < NAVEL_RADIUS_CM:
        reasons.append({"code": "navel", "distance_cm": round(navel_distance, 2)})
    if photo and not in_photo(point, photo):
        reasons.append({"code": "outside_photo"})
    ready = photo_ready(photo, as_of, freshness=freshness)
    if not ready:
        reasons.append({"code": "photo_unverified"})
    hard = any(r["code"] in {"active_alert", "navel", "outside_photo"} for r in reasons)
    status = "blocked" if hard else "resting" if locks else "unverified" if not ready else "eligible"
    unlock_at = iso(max(locks)) if locks else None
    return {"number": number, "x": point["x"], "y": point["y"], "status": status,
            "reasons": reasons, "unlock_at": unlock_at,
            "rest_seconds": max(0, int((max(locks) - as_of).total_seconds())) if locks else 0,
            "last_used_at": last["occurred_at"] if last else None,
            "navel_distance_cm": round(navel_distance, 2), "complication_count": len(past),
            "recurrent": recurrent, "needs_review": needs_review,
            "latest_episode": latest_episode}


def screen_sites(sites: list[dict], events: list[dict], complications: list[dict],
                 reviews: list[dict], photo: dict | None, as_of: datetime) -> tuple[list[dict], list[int]]:
    states = [assess_point(s, s["number"], events, complications, reviews, photo, as_of) for s in sites]
    previous = [e for e in events if event_applies(e, as_of)]
    last_number = max(previous, key=lambda e: e["occurred_at"])["site_number"] if previous else 0
    eligible = sorted((s for s in states if s["status"] == "eligible"),
                      key=lambda s: (s["number"] - last_number - 1) % 14)
    # Never invent candidates when fewer than three meet the configured checks.
    candidates = [s["number"] for s in eligible[:3]]
    return states, candidates


def event_applies(event: dict, as_of: datetime) -> bool:
    return (parse_time(event["occurred_at"]) <= as_of and
            (not event.get("voided_at") or parse_time(event["voided_at"]) > as_of))


def alert_active(alert: dict, as_of: datetime) -> bool:
    return (parse_time(alert["observed_at"]) <= as_of and
            (not alert.get("voided_at") or parse_time(alert["voided_at"]) > as_of) and
            (not alert.get("resolved_at") or parse_time(alert["resolved_at"]) > as_of))


def policy_info() -> dict:
    return {"rest_days": REST_DAYS, "change_days": CHANGE_DAYS,
            "minimum_spacing_cm": MIN_SPACING_CM, "navel_radius_cm": NAVEL_RADIUS_CM,
            "photo_valid_hours": PHOTO_VALID_HOURS, "keep_calibration": keep_calibration.get(), "recurrence_days": RECURRENCE_DAYS,
            "recurrence_count": RECURRENCE_COUNT, "timezone": "Asia/Tokyo (UTC+09:00)"}
