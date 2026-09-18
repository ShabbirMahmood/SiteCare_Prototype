"""FastAPI routes for the SiteCare local prototype.

No external services are contacted. All rule checks are repeated on the server.
This application is intentionally restricted to the loopback interface.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import secrets
import sqlite3
import threading
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.background import BackgroundTask

from . import __version__
from .clock import clock_offset, system_now, read_clock, describe_clock
from .rules import (JST, CHANGE_DAYS, PHOTO_VALID_HOURS, assess_point, body_to_image,
                    default_sites, distance, iso, nearest_site, now_utc, parse_time,
                    photo_ready, policy_info, relevant_complications, screen_sites,
                    event_applies, alert_active)
from .security import password_hash, password_matches, token_hash
from .storage import (audit, create_backup, decode_photo, initialize, one,
                      patient_records, rows, transaction)

ROOT = Path(__file__).resolve().parent.parent
MAX_UPLOAD = 16 * 1024 * 1024
MAX_PIXELS = 32_000_000
COMPLICATION_TYPES = {"redness", "hardness", "pain", "swelling", "bruising", "leakage", "other"}


class AppError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "invalid", **details):
        self.message, self.status, self.code, self.details = message, status, code, details


def text(value, label: str, maximum: int = 2000, required: bool = False) -> str:
    if not isinstance(value, str):
        raise AppError(f"{label}: text is required.")
    value = value.strip()
    if len(value) > maximum or (required and not value):
        raise AppError(f"{label}: enter {'1 to ' if required else 'up to '}{maximum} characters.")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in value):
        raise AppError(f"{label}: invalid control characters.")
    return value


def number(value, label: str, low: float, high: float) -> float:
    if isinstance(value, bool):
        raise AppError(f"{label}: a number is required.")
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise AppError(f"{label}: a number is required.") from None
    if not math.isfinite(v) or not low <= v <= high:
        raise AppError(f"{label}: must be between {low} and {high}.")
    return v


def integer(value, label: str, low: int = 1, high: int = 2_147_483_647) -> int:
    v = number(value, label, low, high)
    if int(v) != v:
        raise AppError(f"{label}: a whole number is required.")
    return int(v)


def timestamp(value, label: str, not_future: bool = False) -> str:
    try:
        dt = parse_time(value)
    except ValueError as exc:
        raise AppError(f"{label}: {exc}") from None
    if dt.year < 2000 or dt.year > 2100:
        raise AppError(f"{label}: date is outside the prototype's 2000–2100 range.")
    if not_future and dt > now_utc():
        raise AppError(f"{label}: a completed observation/procedure cannot be in the future.", code="future_record")
    return iso(dt)


async def payload(request: Request) -> dict:
    if not request.headers.get("content-type", "").lower().startswith("application/json"):
        raise AppError("Send JSON data.", 415)
    try:
        data = await request.json()
    except Exception:
        raise AppError("Invalid JSON data.") from None
    if not isinstance(data, dict):
        raise AppError("A JSON object is required.")
    return data


def require(request: Request, admin: bool = False) -> dict:
    user = getattr(request.state, "user", None)
    if not user:
        raise AppError("Please sign in again. Your session may have expired.", 401, "login_required")
    if admin and user["role"] != "admin":
        raise AppError("An administrator account is required.", 403, "admin_required")
    return user


def patient(db, patient_id: int, expected_version=None) -> dict:
    p = one(db, "SELECT * FROM patients WHERE id=?", (patient_id,))
    if not p:
        raise AppError("Patient not found.", 404)
    if expected_version is not None and p["version"] != integer(expected_version, "Record version"):
        raise AppError("This patient was changed in another window. Refresh before saving; your edit was not applied.",
                       409, "version_conflict")
    return p


def check_version(db, patient_id: int, data: dict) -> dict:
    if "version" not in data:
        raise AppError("A record version is required. Refresh the patient page.", 409, "version_conflict")
    return patient(db, patient_id, data["version"])


def bump(db, patient_id: int):
    db.execute("UPDATE patients SET version=version+1 WHERE id=?", (patient_id,))


def appointment_due(db, p):
    at = iso(now_utc())
    last = one(db, "SELECT occurred_at FROM events WHERE patient_id=? AND occurred_at<=? "
                   "AND (voided_at IS NULL OR voided_at>?) ORDER BY occurred_at DESC,id DESC LIMIT 1",
               (p["id"], at, at))
    return iso(parse_time(last["occurred_at"]) + timedelta(days=CHANGE_DAYS)) if last else p["start_at"]


def effective_appointment(db, p):
    existing = one(db, "SELECT * FROM appointments WHERE patient_id=?", (p["id"],))
    due = appointment_due(db, p)
    if existing and existing["due_at"] == due and parse_time(existing["updated_at"]) <= now_utc():
        return existing
    # Previewing a different date must not erase saved appointment confirmations.
    return {"patient_id": p["id"], "due_at": due, "scheduled_at": due,
            "status": "suggested", "reason": "", "updated_at": iso(now_utc())}


def sync_appointment(db, patient_id: int, *, force: bool = False):
    p = patient(db, patient_id)
    due = appointment_due(db, p)
    existing = one(db, "SELECT * FROM appointments WHERE patient_id=?", (patient_id,))
    if not existing or existing["due_at"] != due or force:
        db.execute("INSERT INTO appointments(patient_id,due_at,scheduled_at,status,reason,updated_at) "
                   "VALUES(?,?,?,'suggested','',?) ON CONFLICT(patient_id) DO UPDATE SET "
                   "due_at=excluded.due_at, scheduled_at=excluded.scheduled_at, status='suggested', "
                   "reason='', updated_at=excluded.updated_at", (patient_id, due, due, iso(now_utc())))


def latest_photo(db, patient_id: int) -> dict | None:
    return decode_photo(one(db, "SELECT * FROM photos WHERE patient_id=? AND captured_at<=? ORDER BY id DESC LIMIT 1",
                            (patient_id, iso(now_utc()))))


def workspace(db, patient_id: int) -> dict:
    p = patient(db, patient_id)
    sites, events, alerts, reviews = patient_records(db, patient_id)
    photos = [decode_photo(r) for r in rows(db, "SELECT * FROM photos WHERE patient_id=? ORDER BY id DESC", (patient_id,))]
    current_photo = latest_photo(db, patient_id)
    states, candidates = screen_sites(sites, events, alerts, reviews, current_photo, now_utc())
    return {"patient": p, "sites": sites, "events": events, "alerts": alerts, "reviews": reviews,
            "photos": photos, "states": states, "candidates": candidates if p["active"] else [],
            "current_photo_id": current_photo["id"] if current_photo else None,
            "appointment": effective_appointment(db, p),
            "now": iso(now_utc()), "policy": policy_info(),
            "layout_locked": bool(events or alerts)}


def summaries(db) -> list[dict]:
    result = []
    for p in rows(db, "SELECT * FROM patients ORDER BY active DESC,code COLLATE NOCASE"):
        sites, events, alerts, reviews = patient_records(db, p["id"])
        photo = latest_photo(db, p["id"])
        states, candidates = screen_sites(sites, events, alerts, reviews, photo, now_utc())
        appt = effective_appointment(db, p)
        result.append({**p, "appointment": appt, "eligible_count": sum(s["status"] == "eligible" for s in states),
                       "resting_count": sum(s["status"] == "resting" for s in states),
                       "active_alerts": sum(alert_active(a, now_utc()) for a in alerts),
                       "review_count": sum(s["needs_review"] for s in states),
                       "photo_count": db.execute("SELECT COUNT(*) FROM photos WHERE patient_id=?", (p["id"],)).fetchone()[0],
                       "last_used_at": next((e["occurred_at"] for e in events if event_applies(e, now_utc())), None),
                       "candidates": candidates if p["active"] else [],
                       "overdue": bool(p["active"] and appt and parse_time(appt["due_at"]) < now_utc())})
    return result


def create_app(data_dir: Path | None = None, *, testing: bool = False) -> FastAPI:
    data_dir = Path(data_dir or ROOT / "data").resolve()
    initialize(data_dir)
    app = FastAPI(title="SiteCare local prototype", version=__version__,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.data_dir = data_dir
    attempts: dict[tuple, list[float]] = {}
    attempts_lock = threading.Lock()

    @app.exception_handler(AppError)
    async def app_error(request, exc: AppError):
        return JSONResponse({"error": exc.message, "code": exc.code, **exc.details}, status_code=exc.status)

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity_error(request, exc):
        return JSONResponse({"error": "A unique ID is already in use, or a related record is invalid.", "code": "duplicate"}, status_code=409)

    @app.exception_handler(sqlite3.OperationalError)
    async def database_error(request, exc):
        return JSONResponse({"error": "The local database could not complete this operation. Check free disk space, close competing windows, then retry.",
                             "code": "database_error"}, status_code=503)

    @app.middleware("http")
    async def local_security(request: Request, call_next):
        host = request.url.hostname
        allowed_hosts = {"127.0.0.1", "localhost", "::1"} | ({"testserver"} if testing else set())
        if host not in allowed_hosts:
            return JSONResponse({"error": "This prototype only accepts localhost requests."}, status_code=403)
        try:
            content_length = int(request.headers.get("content-length", "0") or 0)
        except ValueError:
            return JSONResponse({"error": "Invalid content length."}, status_code=400)
        if content_length < 0:
            return JSONResponse({"error": "Invalid content length."}, status_code=400)
        if content_length > MAX_UPLOAD + 1024 * 1024:
            return JSONResponse({"error": "Upload is too large. Use an image smaller than 16 MB."}, status_code=413)
        request.state.user = None
        request.state.session_hash = None
        request.state.csrf = None
        token = request.cookies.get("sitecare_session", "")
        if token and len(token) <= 200:
            with transaction(data_dir) as db:
                session = one(db, "SELECT * FROM sessions WHERE token_hash=?", (token_hash(token),))
                if session and (system_now() - parse_time(session["touched_at"]) < timedelta(minutes=30)
                                and system_now() - parse_time(session["created_at"]) < timedelta(hours=8)):
                    request.state.session_hash = session["token_hash"]
                    request.state.csrf = session["csrf"]
                    if session["user_id"]:
                        request.state.user = one(db, "SELECT id,username,display_name,role FROM users WHERE id=?", (session["user_id"],))
                    # Only explicit activity refreshes idle timeout. Background polls do not.
                    if request.headers.get("x-user-activity") == "1":
                        db.execute("UPDATE sessions SET touched_at=? WHERE token_hash=?", (iso(system_now()), session["token_hash"]))
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            expected_origin = f"{request.url.scheme}://{request.url.netloc}"
            if origin and origin != expected_origin:
                return JSONResponse({"error": "Cross-origin writes are not allowed.", "code": "csrf"}, status_code=403)
            if not request.state.csrf or not secrets.compare_digest(request.headers.get("x-csrf-token", ""), request.state.csrf):
                return JSONResponse({"error": "Security token expired. Refresh the page and sign in again.", "code": "csrf"}, status_code=403)
            revision = request.headers.get("x-clock-revision")
            if revision is not None and revision != str(request.state.clock["revision"]):
                return JSONResponse({"error": "The application date changed in another window. Refresh before saving.",
                                     "code": "clock_conflict"}, status_code=409)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; connect-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        return response

    @app.middleware("http")
    async def application_clock(request: Request, call_next):
        with transaction(data_dir) as db:
            request.state.clock = read_clock(db)
        context = clock_offset.set(request.state.clock["offset_seconds"] or 0)
        try:
            response = await call_next(request)
            clock = describe_clock(request.state.clock)
            response.headers["X-SiteCare-Now"] = clock["now"]
            response.headers["X-SiteCare-Clock-Mode"] = clock["mode"]
            response.headers["X-SiteCare-Clock-Revision"] = str(clock["revision"])
            return response
        finally:
            clock_offset.reset(context)

    def new_session(db, user_id: int | None = None) -> tuple[str, str]:
        token, csrf = secrets.token_urlsafe(40), secrets.token_urlsafe(32)
        now = iso(system_now())
        db.execute("DELETE FROM sessions WHERE touched_at<? OR created_at<?",
                   (iso(system_now() - timedelta(minutes=30)), iso(system_now() - timedelta(hours=8))))
        db.execute("INSERT INTO sessions VALUES(?,?,?,?,?)", (token_hash(token), csrf, user_id, now, now))
        return token, csrf

    def session_response(data: dict, token: str) -> JSONResponse:
        response = JSONResponse(data)
        response.set_cookie("sitecare_session", token, httponly=True, samesite="strict", path="/", max_age=8 * 3600)
        return response

    @app.get("/api/bootstrap")
    def bootstrap(request: Request):
        with transaction(data_dir, True) as db:
            needs_setup = db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
            token = None
            csrf = request.state.csrf
            if not request.state.session_hash:
                token, csrf = new_session(db)
            data = {"user": request.state.user, "setup_needed": needs_setup, "csrf": csrf,
                    "version": __version__, "now": iso(now_utc()), "policy": policy_info(),
                    "clock": describe_clock(request.state.clock)}
            return session_response(data, token) if token else data

    @app.get("/api/clock")
    def get_clock(request: Request):
        require(request)
        return describe_clock(request.state.clock)

    @app.post("/api/clock")
    async def set_clock(request: Request):
        user = require(request, True)
        data = await payload(request)
        mode = data.get("mode")
        if mode not in ("system", "manual"):
            raise AppError("Choose system or manual date mode.")
        selected = timestamp(data.get("now"), "Demonstration date") if mode == "manual" else None
        offset = (parse_time(selected) - system_now()).total_seconds() if selected else None
        revision = integer(data.get("revision"), "Clock version", 0)
        with transaction(data_dir, True) as db:
            before = read_clock(db)
            if before["revision"] != revision:
                raise AppError("The application date changed in another window. Refresh before saving.", 409, "clock_conflict")
            db.execute("UPDATE app_clock SET offset_seconds=?,selected_at=?,revision=revision+1 WHERE id=1",
                       (offset, selected))
            # Existing patient forms must reload under the new date before saving.
            db.execute("UPDATE patients SET version=version+1")
            request.state.clock = read_clock(db)
            clock_offset.set(offset or 0)
            audit(db, user["display_name"], "clock.changed", "application",
                  {"before": before, "after": request.state.clock, "system_at": iso(system_now())})
        return describe_clock(request.state.clock)

    @app.post("/api/setup")
    async def setup(request: Request):
        data = await payload(request)
        username = text(data.get("username"), "Username", 60, True)
        display = text(data.get("display_name"), "Name", 100, True)
        pw = text(data.get("password"), "Password", 128, True)
        if len(pw) < 12:
            raise AppError("Use a password with at least 12 characters.")
        with transaction(data_dir, True) as db:
            if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                raise AppError("Setup has already been completed.", 409)
            uid = db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,'admin',?)",
                             (username, display, password_hash(pw), iso(now_utc()))).lastrowid
            db.execute("DELETE FROM sessions WHERE token_hash=?", (request.state.session_hash,))
            token, csrf = new_session(db, uid)
            audit(db, display, "installation.setup", "users", {})
            user = one(db, "SELECT id,username,display_name,role FROM users WHERE id=?", (uid,))
        return session_response({"user": user, "csrf": csrf}, token)

    @app.post("/api/login")
    async def login(request: Request):
        data = await payload(request)
        username = text(data.get("username"), "Username", 60, True)
        pw = text(data.get("password"), "Password", 128, True)
        key = (request.client.host if request.client else "local", username.lower())
        with attempts_lock:
            recent = [v for v in attempts.get(key, []) if time.monotonic() - v < 15 * 60]
            if len(recent) >= 5:
                raise AppError("Too many attempts. Wait 15 minutes before trying again.", 429, "rate_limited")
            attempts[key] = recent + [time.monotonic()]
        with transaction(data_dir, True) as db:
            user = one(db, "SELECT * FROM users WHERE username=?", (username,))
            # Constant work for an unknown username reduces trivial timing leakage.
            valid = password_matches(pw, user["password_hash"]) if user else password_matches(pw, password_hash("not-a-valid-password"))
            if not user or not valid:
                raise AppError("Username or password is incorrect.", 401, "bad_login")
            db.execute("DELETE FROM sessions WHERE token_hash=?", (request.state.session_hash,))
            token, csrf = new_session(db, user["id"])
            audit(db, user["display_name"], "auth.login", str(user["id"]), {})
            user.pop("password_hash")
        with attempts_lock:
            attempts.pop(key, None)
        return session_response({"user": user, "csrf": csrf}, token)

    @app.post("/api/logout")
    def logout(request: Request):
        with transaction(data_dir, True) as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (request.state.session_hash,))
        response = JSONResponse({"ok": True})
        response.delete_cookie("sitecare_session", path="/")
        return response

    @app.post("/api/heartbeat")
    def heartbeat(request: Request):
        require(request)
        return {"ok": True}

    @app.get("/api/patients")
    def get_patients(request: Request):
        require(request)
        with transaction(data_dir) as db:
            return {"patients": summaries(db), "now": iso(now_utc())}

    @app.post("/api/patients")
    async def add_patient(request: Request):
        user = require(request)
        data = await payload(request)
        code = text(data.get("code"), "Patient ID", 64, True)
        alias = text(data.get("alias"), "Display label", 100, True)
        start = timestamp(data.get("start_at"), "First appointment")
        with transaction(data_dir, True) as db:
            pid = db.execute("INSERT INTO patients(code,alias,notes,therapy,start_at,created_at) VALUES(?,?,?,?,?,?)",
                             (code, alias, text(data.get("notes", ""), "Notes"),
                              text(data.get("therapy", ""), "Therapy", 150), start, iso(now_utc()))).lastrowid
            db.executemany("INSERT INTO sites(patient_id,number,x,y) VALUES(?,?,?,?)",
                           [(pid, s["number"], s["x"], s["y"]) for s in default_sites()])
            sync_appointment(db, pid)
            audit(db, user["display_name"], "patient.created", str(pid), {"code": code}, pid)
        return {"id": pid}

    @app.get("/api/patients/{patient_id}")
    def get_patient(request: Request, patient_id: int):
        require(request)
        with transaction(data_dir) as db:
            return workspace(db, patient_id)

    @app.patch("/api/patients/{patient_id}")
    async def edit_patient(request: Request, patient_id: int):
        user = require(request)
        data = await payload(request)
        with transaction(data_dir, True) as db:
            p = check_version(db, patient_id, data)
            active = data.get("active", bool(p["active"]))
            if not isinstance(active, bool):
                raise AppError("Active must be true or false.")
            updated = {"alias": text(data.get("alias", p["alias"]), "Display label", 100, True),
                       "notes": text(data.get("notes", p["notes"]), "Notes"),
                       "therapy": text(data.get("therapy", p["therapy"]), "Therapy", 150), "active": active}
            db.execute("UPDATE patients SET alias=?,notes=?,therapy=?,active=? WHERE id=?",
                       (*updated.values(), patient_id))
            bump(db, patient_id)
            audit(db, user["display_name"], "patient.updated", str(patient_id), {"before": p, "after": updated}, patient_id)
        return {"ok": True}

    @app.post("/api/patients/{patient_id}/photos")
    async def upload_photo(request: Request, patient_id: int):
        user = require(request)
        form = await request.form(max_files=1, max_fields=6, max_part_size=MAX_UPLOAD)
        upload = form.get("photo")
        if not upload or not hasattr(upload, "read"):
            raise AppError("Choose a JPEG or PNG photograph.")
        raw = await upload.read(MAX_UPLOAD + 1)
        if len(raw) > MAX_UPLOAD:
            raise AppError("Photograph exceeds 16 MB.", 413)
        captured = timestamp(form.get("captured_at"), "Photo capture time", True)
        version = integer(form.get("version"), "Record version")
        if form.get("consent") != "true":
            raise AppError("Confirm authorized use of this photograph.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as image:
                    if image.format not in {"JPEG", "PNG"}:
                        raise AppError("Only actual JPEG and PNG files are supported. Convert HEIC to JPEG first.")
                    if image.width * image.height > MAX_PIXELS or min(image.size) < 200:
                        raise AppError("Use an image at least 200 pixels per side and no more than 32 megapixels.")
                    image.load()
                    oriented = ImageOps.exif_transpose(image)
                    if oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info:
                        rgba = oriented.convert("RGBA")
                        clean = Image.new("RGB", rgba.size, "white")
                        clean.paste(rgba, mask=rgba.getchannel("A"))
                    else:
                        clean = oriented.convert("RGB")
                    clean.thumbnail((2560, 2560), Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    # A fresh image prevents EXIF/GPS/comments from being copied.
                    sanitized = Image.new("RGB", clean.size)
                    sanitized.paste(clean)
                    sanitized.save(output, "JPEG", quality=92)
                    width, height = clean.size
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise AppError("The file is not a supported, readable photograph.") from None
        filename = secrets.token_hex(20) + ".jpg"
        path = data_dir / "photos" / filename
        try:
            with transaction(data_dir, True) as db:
                p = patient(db, patient_id, version)
                alignment = {"cx": width / 2, "cy": height / 2, "ppm": width / 36,
                             "angle": 0, "calibration": None}
                path.write_bytes(output.getvalue())
                photo_id = db.execute("INSERT INTO photos(patient_id,filename,width,height,captured_at,uploaded_at,alignment_json) "
                                      "VALUES(?,?,?,?,?,?,?)", (patient_id, filename, width, height, captured,
                                                              iso(now_utc()), json.dumps(alignment))).lastrowid
                bump(db, patient_id)
                audit(db, user["display_name"], "photo.uploaded", str(photo_id),
                      {"width": width, "height": height, "captured_at": captured}, patient_id)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return {"id": photo_id}

    @app.get("/api/photos/{photo_id}/image")
    def get_photo(request: Request, photo_id: int):
        require(request)
        with transaction(data_dir) as db:
            p = one(db, "SELECT filename FROM photos WHERE id=?", (photo_id,))
        if not p:
            raise AppError("Photo not found.", 404)
        path = data_dir / "photos" / p["filename"]
        if not path.is_file():
            raise AppError("Photo file is missing. Restore it from your backup.", 404)
        return FileResponse(path, media_type="image/jpeg")

    @app.post("/api/photos/{photo_id}/alignment")
    async def align_photo(request: Request, photo_id: int):
        user = require(request)
        data = await payload(request)
        with transaction(data_dir, True) as db:
            photo = one(db, "SELECT * FROM photos WHERE id=?", (photo_id,))
            if not photo:
                raise AppError("Photo not found.", 404)
            pid = photo["patient_id"]
            check_version(db, pid, data)
            if photo["locked"]:
                raise AppError("This photo is linked to a clinical record. Its alignment is locked. Upload a new photo.", 409, "photo_locked")
            a = data.get("alignment")
            if not isinstance(a, dict):
                raise AppError("Alignment data is required.")
            cx = number(a.get("cx"), "Navel X", 0, photo["width"])
            cy = number(a.get("cy"), "Navel Y", 0, photo["height"])
            angle = number(a.get("angle"), "Rotation", -180, 180)
            cal = a.get("calibration")
            if not isinstance(cal, dict) or not all(isinstance(cal.get(k), dict) for k in ("a", "b")):
                raise AppError("Calibrate with two ruler points and their known distance first.", code="calibration_required")
            points = [{"x": number(cal[k].get("x"), "Ruler X", 0, photo["width"]),
                       "y": number(cal[k].get("y"), "Ruler Y", 0, photo["height"])} for k in ("a", "b")]
            length = number(cal.get("length_cm"), "Ruler length", 2, 30)
            pixels = distance(points[0], points[1])
            if pixels < 30:
                raise AppError("The ruler reference is too small in this image. Use a longer visible segment.")
            ppm = pixels / length
            if not 5 <= ppm <= 600:
                raise AppError("Calibration scale looks invalid. Recheck the ruler endpoints and centimetres.")
            if data.get("confirmed") is not True:
                raise AppError("Confirm navel, orientation, scale, skin visibility and historical-point alignment.")
            alignment = {"cx": cx, "cy": cy, "angle": angle, "ppm": ppm,
                         "calibration": {"a": points[0], "b": points[1], "length_cm": length}}
            db.execute("UPDATE photos SET alignment_json=?,verified=1,verified_at=?,verified_by=? WHERE id=?",
                       (json.dumps(alignment), iso(now_utc()), user["display_name"], photo_id))
            bump(db, pid)
            audit(db, user["display_name"], "photo.alignment_verified", str(photo_id),
                  {"before": json.loads(photo["alignment_json"]), "after": alignment}, pid)
        return {"ok": True}

    @app.post("/api/patients/{patient_id}/layout")
    async def edit_layout(request: Request, patient_id: int):
        user = require(request)
        data = await payload(request)
        incoming = data.get("sites")
        if not isinstance(incoming, list) or len(incoming) != 14:
            raise AppError("Exactly 14 numbered sites are required.")
        sites = [{"number": integer(s.get("number"), "Site number", 1, 14),
                  "x": number(s.get("x"), "X (cm)", -30, 30),
                  "y": number(s.get("y"), "Y (cm)", -30, 30)} for s in incoming if isinstance(s, dict)]
        if len(sites) != 14 or {s["number"] for s in sites} != set(range(1, 15)):
            raise AppError("Each number 1–14 must occur exactly once.")
        for i, s in enumerate(sites):
            if math.hypot(s["x"], s["y"]) < 5 - 1e-8:
                raise AppError(f"Site {s['number']} is less than 5 cm from the navel.")
            for other in sites[i + 1:]:
                if distance(s, other) < 2.5 - 1e-8:
                    raise AppError(f"Sites {s['number']} and {other['number']} are less than 2.5 cm apart.")
        with transaction(data_dir, True) as db:
            check_version(db, patient_id, data)
            if db.execute("SELECT 1 FROM events WHERE patient_id=? UNION SELECT 1 FROM complications WHERE patient_id=? LIMIT 1",
                          (patient_id, patient_id)).fetchone():
                raise AppError("The numbered layout is frozen after the first puncture or skin record. Align new photographs instead.", 409)
            old = rows(db, "SELECT number,x,y FROM sites WHERE patient_id=?", (patient_id,))
            for s in sites:
                db.execute("UPDATE sites SET x=?,y=? WHERE patient_id=? AND number=?", (s["x"], s["y"], patient_id, s["number"]))
            bump(db, patient_id)
            audit(db, user["display_name"], "layout.updated", str(patient_id), {"before": old, "after": sites}, patient_id)
        return {"ok": True}

    @app.post("/api/patients/{patient_id}/screen-point")
    async def screen_point(request: Request, patient_id: int):
        require(request)
        data = await payload(request)
        point = {"x": number(data.get("x"), "X", -40, 40), "y": number(data.get("y"), "Y", -40, 40)}
        with transaction(data_dir) as db:
            patient(db, patient_id)
            sites, events, alerts, reviews = patient_records(db, patient_id)
            n = nearest_site(point, sites)
            return assess_point(point, n, events, alerts, reviews, latest_photo(db, patient_id), now_utc())

    @app.post("/api/patients/{patient_id}/events")
    async def record_event(request: Request, patient_id: int):
        user = require(request)
        data = await payload(request)
        key = text(data.get("request_key"), "Request key", 100, True)
        occurred = timestamp(data.get("occurred_at"), "Puncture time", True)
        kind = data.get("kind", "procedure")
        if not isinstance(kind, str) or kind not in {"procedure", "history"}:
            raise AppError("Choose a new procedure or a historical record.")
        point = {"x": number(data.get("x"), "X", -40, 40), "y": number(data.get("y"), "Y", -40, 40)}
        if any(data.get(field) is not True for field in ("identity_checked", "point_checked", "clinical_checked")):
            raise AppError("Confirm patient identity, the exact puncture point, and bedside assessment/measurement before saving.")
        reason = text(data.get("exception_reason", ""), "Historical record explanation", 2000)
        if kind == "history" and len(reason) < 8:
            raise AppError("A historical record needs an explanation of at least 8 characters.")
        with transaction(data_dir, True) as db:
            existing = one(db, "SELECT id,patient_id FROM events WHERE request_key=?", (key,))
            if existing:
                if existing["patient_id"] != patient_id:
                    raise AppError("Request key is already in use.", 409)
                return {"id": existing["id"], "duplicate": True}
            p = check_version(db, patient_id, data)
            photo_id = integer(data.get("photo_id"), "Photo")
            raw_photo = one(db, "SELECT * FROM photos WHERE id=? AND patient_id=?", (photo_id, patient_id))
            photo = decode_photo(raw_photo)
            if not photo or not photo_ready(photo, now_utc(), freshness=False):
                raise AppError("Use a calibrated and verified photo.", 422, "calibration_required")
            latest = latest_photo(db, patient_id)
            if kind == "procedure":
                if not p["active"]:
                    raise AppError("This patient is inactive.", 422)
                if not latest or latest["id"] != photo_id or not photo_ready(photo, now_utc()):
                    raise AppError("Upload and verify a current photo (captured within 24 hours) for this visit.", 422, "fresh_photo_required")
                if now_utc() - parse_time(occurred) > timedelta(hours=24):
                    raise AppError("Older entries must use Historical record mode.", 422)
                if parse_time(occurred) < parse_time(photo["captured_at"]) - timedelta(minutes=5):
                    raise AppError("Procedure time predates this photograph. Use Historical record mode.", 422)
                if db.execute("SELECT 1 FROM events WHERE photo_id=? AND kind='procedure' AND voided_at IS NULL", (photo_id,)).fetchone():
                    raise AppError("A new procedure is already recorded on this photo. Upload a new visit photograph.", 422, "fresh_photo_required")
            sites, events, alerts, reviews = patient_records(db, patient_id)
            previous = [e for e in events if event_applies(e, now_utc())]
            if kind == "procedure" and previous and occurred < max(e["occurred_at"] for e in previous):
                raise AppError("Out-of-order entries must use Historical record mode.", 422)
            n = nearest_site(point, sites)
            # Photo freshness is checked against current server time above. Do not
            # compare it again to a procedure timestamp rounded to the minute.
            assessed = assess_point(point, n, events, alerts, reviews, photo,
                                    parse_time(occurred), freshness=False)
            if kind == "procedure" and assessed["status"] != "eligible":
                raise AppError("This point does not meet the configured checks. Select another point or record an already-performed event as history.",
                               422, "point_blocked", reasons=assessed["reasons"])
            # Historical records document what happened; warnings are preserved, not silently bypassed.
            eid = db.execute("INSERT INTO events(patient_id,photo_id,site_number,x,y,occurred_at,recorded_at,actor,note,kind,"
                             "exception_reason,warnings_json,alignment_json,request_key) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (patient_id, photo_id, n, point["x"], point["y"], occurred, iso(now_utc()), user["display_name"],
                              text(data.get("note", ""), "Note"), kind, reason, json.dumps(assessed["reasons"]),
                              raw_photo["alignment_json"], key)).lastrowid
            db.execute("UPDATE photos SET locked=1 WHERE id=?", (photo_id,))
            sync_appointment(db, patient_id)
            bump(db, patient_id)
            audit(db, user["display_name"], "puncture.recorded", str(eid),
                  {"site_number": n, "point": point, "occurred_at": occurred, "kind": kind,
                   "warnings": assessed["reasons"], "exception_reason": reason}, patient_id)
        return {"id": eid, "site_number": n}

    @app.post("/api/events/{event_id}/void")
    async def void_event(request: Request, event_id: int):
        user = require(request, True)
        data = await payload(request)
        reason = text(data.get("reason"), "Correction reason", 2000, True)
        with transaction(data_dir, True) as db:
            event = one(db, "SELECT * FROM events WHERE id=?", (event_id,))
            if not event:
                raise AppError("Record not found.", 404)
            check_version(db, event["patient_id"], data)
            if event["voided_at"]:
                raise AppError("This record has already been voided.", 409)
            if parse_time(event["occurred_at"]) > now_utc():
                raise AppError("The application date is earlier than this record. Change the date before voiding it.", 422)
            db.execute("UPDATE events SET voided_at=?,voided_by=?,void_reason=? WHERE id=?",
                       (iso(now_utc()), user["display_name"], reason, event_id))
            sync_appointment(db, event["patient_id"])
            bump(db, event["patient_id"])
            audit(db, user["display_name"], "puncture.voided", str(event_id), {"reason": reason}, event["patient_id"])
        return {"ok": True}

    @app.post("/api/patients/{patient_id}/alerts")
    async def add_alert(request: Request, patient_id: int):
        user = require(request)
        data = await payload(request)
        types = data.get("types")
        if not isinstance(types, list) or not types or any(not isinstance(t, str) or t not in COMPLICATION_TYPES for t in types):
            raise AppError("Select at least one supported complication type.")
        types = sorted(set(types))
        point = {"x": number(data.get("x"), "X", -40, 40), "y": number(data.get("y"), "Y", -40, 40)}
        radius = number(data.get("radius"), "Alert radius (cm)", 0.3, 15)
        severity = data.get("severity", "mild")
        if not isinstance(severity, str) or severity not in {"mild", "moderate", "severe"}:
            raise AppError("Choose a supported severity.")
        observed = timestamp(data.get("observed_at"), "Observation time", True)
        with transaction(data_dir, True) as db:
            check_version(db, patient_id, data)
            photo_id = integer(data.get("photo_id"), "Photo")
            raw = one(db, "SELECT * FROM photos WHERE id=? AND patient_id=?", (photo_id, patient_id))
            photo = decode_photo(raw)
            if not photo or not photo_ready(photo, now_utc()):
                raise AppError("A current, calibrated photo is required to mark a skin area.", 422)
            if latest_photo(db, patient_id)["id"] != photo_id:
                raise AppError("Use the latest photograph to mark a skin area.", 422)
            x, y = body_to_image(point["x"], point["y"], photo["alignment"])
            if not (0 <= x <= photo["width"] and 0 <= y <= photo["height"]):
                raise AppError("Place the alert centre on the photograph.")
            sites = rows(db, "SELECT number,x,y FROM sites WHERE patient_id=?", (patient_id,))
            n = nearest_site(point, sites)
            aid = db.execute("INSERT INTO complications(patient_id,photo_id,site_number,x,y,radius,types_json,severity,observed_at,"
                             "recorded_at,actor,note,alignment_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                             (patient_id, photo_id, n, point["x"], point["y"], radius, json.dumps(types), severity,
                              observed, iso(now_utc()), user["display_name"], text(data.get("note", ""), "Note"), raw["alignment_json"])).lastrowid
            db.execute("UPDATE photos SET locked=1 WHERE id=?", (photo_id,))
            bump(db, patient_id)
            audit(db, user["display_name"], "skin.alert_created", str(aid),
                  {"types": types, "point": point, "radius": radius, "severity": severity}, patient_id)
        return {"id": aid}

    @app.post("/api/alerts/{alert_id}/resolve")
    async def resolve_alert(request: Request, alert_id: int):
        user = require(request)
        data = await payload(request)
        if data.get("healed_confirmed") is not True:
            raise AppError("Explicitly confirm that the skin has fully recovered after bedside assessment.")
        note = text(data.get("note"), "Recovery assessment", 2000, True)
        with transaction(data_dir, True) as db:
            alert = one(db, "SELECT * FROM complications WHERE id=?", (alert_id,))
            if not alert:
                raise AppError("Alert not found.", 404)
            check_version(db, alert["patient_id"], data)
            if alert["resolved_at"]:
                raise AppError("This alert is already resolved.", 409)
            if parse_time(alert["observed_at"]) > now_utc():
                raise AppError("The application date is earlier than this observation. Change the date before resolving it.", 422)
            db.execute("UPDATE complications SET resolved_at=?,resolved_by=?,resolution_note=? WHERE id=?",
                       (iso(now_utc()), user["display_name"], note, alert_id))
            bump(db, alert["patient_id"])
            audit(db, user["display_name"], "skin.recovery_confirmed", str(alert_id), {"note": note}, alert["patient_id"])
        return {"ok": True}

    @app.post("/api/patients/{patient_id}/reviews")
    async def review_site(request: Request, patient_id: int):
        user = require(request)
        data = await payload(request)
        n = integer(data.get("site_number"), "Site", 1, 14)
        if data.get("confirmed") is not True:
            raise AppError("Confirm that the recurring skin issue was reviewed at the bedside.")
        note = text(data.get("note"), "Review note", 2000, True)
        with transaction(data_dir, True) as db:
            check_version(db, patient_id, data)
            sites, events, alerts, reviews = patient_records(db, patient_id)
            s = next(s for s in sites if s["number"] == n)
            episodes = relevant_complications(s, n, alerts, now_utc())
            through = max((a["id"] for a in episodes), default=0)
            db.execute("INSERT INTO reviews(patient_id,site_number,through_alert_id,reviewed_at,actor,note) VALUES(?,?,?,?,?,?) "
                       "ON CONFLICT(patient_id,site_number) DO UPDATE SET through_alert_id=excluded.through_alert_id,"
                       "reviewed_at=excluded.reviewed_at,actor=excluded.actor,note=excluded.note",
                       (patient_id, n, through, iso(now_utc()), user["display_name"], note))
            bump(db, patient_id)
            audit(db, user["display_name"], "skin.recurrence_reviewed", str(n), {"note": note, "through_alert_id": through}, patient_id)
        return {"ok": True}

    @app.post("/api/patients/{patient_id}/appointment")
    async def edit_appointment(request: Request, patient_id: int):
        user = require(request)
        data = await payload(request)
        scheduled = timestamp(data.get("scheduled_at"), "Appointment time")
        reason = text(data.get("reason", ""), "Schedule note", 2000)
        if parse_time(scheduled) < now_utc() - timedelta(minutes=1):
            raise AppError("Choose a future appointment time. The original due time remains visible if overdue.")
        with transaction(data_dir, True) as db:
            check_version(db, patient_id, data)
            sync_appointment(db, patient_id)
            appt = one(db, "SELECT * FROM appointments WHERE patient_id=?", (patient_id,))
            if scheduled != appt["due_at"] and not reason:
                raise AppError("Enter a reason when changing the suggested time.")
            db.execute("UPDATE appointments SET scheduled_at=?,status='confirmed',reason=?,updated_at=? WHERE patient_id=?",
                       (scheduled, reason, iso(now_utc()), patient_id))
            bump(db, patient_id)
            audit(db, user["display_name"], "appointment.confirmed", str(patient_id),
                  {"before": appt, "scheduled_at": scheduled, "reason": reason}, patient_id)
        return {"ok": True}

    @app.get("/api/appointments")
    def get_appointments(request: Request, month: str = ""):
        require(request)
        try:
            anchor = datetime.strptime(month, "%Y-%m").replace(tzinfo=JST) if month else now_utc().astimezone(JST).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            raise AppError("Choose a month in YYYY-MM format.") from None
        begin = anchor - timedelta(days=anchor.weekday())
        end = begin + timedelta(days=42)
        items = []
        with transaction(data_dir) as db:
            patients = summaries(db)
            for p in patients:
                if not p["active"]:
                    continue
                appt = p["appointment"]
                dt = parse_time(appt["scheduled_at"])
                base = {"patient_id": p["id"], "code": p["code"], "alias": p["alias"], "due_at": appt["due_at"]}
                # The next unresolved appointment is always retained, even when overdue.
                items.append({**base, "at": iso(dt), "kind": appt["status"], "overdue": p["overdue"], "next": True})
                if dt < end:
                    step = max(1, math.ceil((begin - dt).total_seconds() / (CHANGE_DAYS * 86400)))
                    while dt + timedelta(days=CHANGE_DAYS * step) < end:
                        future = dt + timedelta(days=CHANGE_DAYS * step)
                        if future >= begin:
                            items.append({**base, "at": iso(future), "kind": "projection", "overdue": False, "next": False})
                        step += 1
                for e in rows(db, "SELECT id,occurred_at,site_number FROM events WHERE patient_id=? "
                                  "AND (voided_at IS NULL OR voided_at>?) AND occurred_at<=? "
                                  "AND occurred_at>=? AND occurred_at<?",
                              (p["id"], iso(now_utc()), iso(now_utc()), iso(begin), iso(end))):
                    items.append({**base, "at": e["occurred_at"], "kind": "completed", "next": False,
                                  "site_number": e["site_number"], "overdue": False})
        return {"items": sorted(items, key=lambda i: i["at"]), "patients": patients, "now": iso(now_utc()),
                "month": anchor.strftime("%Y-%m"), "grid_start": begin.date().isoformat()}

    @app.get("/api/patients/{patient_id}/export.csv")
    def export_patient(request: Request, patient_id: int):
        user = require(request)
        with transaction(data_dir, True) as db:
            p = patient(db, patient_id)
            sites, events, alerts, reviews = patient_records(db, patient_id)
            audit(db, user["display_name"], "patient.csv_exported", str(patient_id), {}, patient_id)
        buf = io.StringIO(newline="")
        writer = csv.writer(buf)
        writer.writerow(["patient_id", "record_type", "site_number", "occurred_JST", "x_cm", "y_cm", "radius_cm",
                         "types", "actor", "note", "resolved_or_voided_JST", "historical_warning", "correction_note"])
        def safe(v):
            s = "" if v is None else str(v)
            return "'" + s if s.lstrip().startswith(("=", "+", "-", "@")) or s.startswith(("\t", "\r", "\n")) else s
        def local(v):
            return parse_time(v).astimezone(JST).isoformat() if v else ""
        for e in events:
            values = [p["code"], e["kind"], e["site_number"], local(e["occurred_at"]), e["x"], e["y"], "", "",
                      e["actor"], e["note"], local(e["voided_at"]), json.dumps(e["warnings"], ensure_ascii=False),
                      e["void_reason"] or e["exception_reason"]]
            writer.writerow([safe(v) for v in values])
        for a in alerts:
            values = [p["code"], "skin_alert", a["site_number"], local(a["observed_at"]), a["x"], a["y"], a["radius"],
                      ", ".join(a["types"]), a["actor"], a["note"], local(a["resolved_at"]), "", a["resolution_note"]]
            writer.writerow([safe(v) for v in values])
        return Response(("\ufeff" + buf.getvalue()).encode("utf-8"), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="sitecare-patient-{patient_id}.csv"'})

    @app.get("/api/audit")
    def get_audit(request: Request, patient_id: int | None = None):
        require(request, True)
        with transaction(data_dir) as db:
            query = "SELECT * FROM audit" + (" WHERE patient_id=?" if patient_id is not None else "") + " ORDER BY id DESC LIMIT 200"
            data = rows(db, query, (patient_id,) if patient_id is not None else ())
        for row in data:
            row["detail"] = json.loads(row.pop("detail_json"))
        return {"items": data, "limit": 200}

    @app.get("/api/users")
    def get_users(request: Request):
        require(request, True)
        with transaction(data_dir) as db:
            return {"users": rows(db, "SELECT id,username,display_name,role,created_at FROM users ORDER BY id")}

    @app.post("/api/users")
    async def add_user(request: Request):
        user = require(request, True)
        data = await payload(request)
        username = text(data.get("username"), "Username", 60, True)
        display = text(data.get("display_name"), "Name", 100, True)
        pw = text(data.get("password"), "Password", 128, True)
        if len(pw) < 12:
            raise AppError("Use a password with at least 12 characters.")
        role = data.get("role", "nurse")
        if not isinstance(role, str) or role not in {"nurse", "admin"}:
            raise AppError("Invalid role.")
        with transaction(data_dir, True) as db:
            uid = db.execute("INSERT INTO users(username,display_name,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                             (username, display, password_hash(pw), role, iso(now_utc()))).lastrowid
            audit(db, user["display_name"], "user.created", str(uid), {"username": username, "role": role})
        return {"id": uid}

    @app.get("/api/backup")
    def backup(request: Request):
        user = require(request, True)
        with transaction(data_dir, True) as db:
            audit(db, user["display_name"], "backup.exported", "database", {})
        tmp = TemporaryDirectory(prefix="sitecare-export-")
        try:
            target = Path(tmp.name) / "sitecare-backup.zip"
            create_backup(data_dir, target)
        except Exception:
            tmp.cleanup()
            raise
        return FileResponse(target, media_type="application/zip",
                            filename=f"sitecare-backup-{now_utc().strftime('%Y%m%dT%H%M%SZ')}.zip",
                            background=BackgroundTask(tmp.cleanup))

    @app.post("/api/demo")
    def add_demo(request: Request):
        user = require(request, True)
        from .demo import seed_demo
        with transaction(data_dir, True) as db:
            pid = seed_demo(db, data_dir, user["display_name"])
        return {"id": pid}

    @app.get("/")
    def index():
        return FileResponse(ROOT / "templates" / "index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    return app
