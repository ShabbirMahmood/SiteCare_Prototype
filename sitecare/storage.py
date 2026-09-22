"""SQLite storage and durable snapshot backups; no database server required."""
from __future__ import annotations

import json
import sqlite3
import zipfile
from contextlib import contextmanager, closing
from pathlib import Path
from tempfile import TemporaryDirectory
from .rules import iso, now_utc

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS schema_info(version INTEGER NOT NULL);
INSERT INTO schema_info SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_info);
CREATE TABLE IF NOT EXISTS app_clock(
 id INTEGER PRIMARY KEY CHECK(id=1), offset_seconds REAL, selected_at TEXT,
 revision INTEGER NOT NULL DEFAULT 0);
INSERT OR IGNORE INTO app_clock(id) VALUES(1);
CREATE TABLE IF NOT EXISTS app_settings(
 id INTEGER PRIMARY KEY CHECK(id=1), keep_calibration INTEGER NOT NULL DEFAULT 1
 CHECK(keep_calibration IN (0,1)), revision INTEGER NOT NULL DEFAULT 0);
INSERT OR IGNORE INTO app_settings(id) VALUES(1);
CREATE TABLE IF NOT EXISTS id_sequences(name TEXT PRIMARY KEY, last_id INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS pending_photo_deletions(filename TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL,
 password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','nurse')), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(
 token_hash TEXT PRIMARY KEY, csrf TEXT NOT NULL, user_id INTEGER REFERENCES users(id),
 created_at TEXT NOT NULL, touched_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS patients(
 id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, alias TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
 therapy TEXT NOT NULL DEFAULT '', start_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
 version INTEGER NOT NULL DEFAULT 1, demo INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sites(
 patient_id INTEGER REFERENCES patients(id), number INTEGER CHECK(number BETWEEN 1 AND 14),
 x REAL NOT NULL, y REAL NOT NULL, PRIMARY KEY(patient_id, number));
CREATE TABLE IF NOT EXISTS photos(
 id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL REFERENCES patients(id), filename TEXT UNIQUE NOT NULL,
 width INTEGER NOT NULL, height INTEGER NOT NULL, captured_at TEXT NOT NULL, uploaded_at TEXT NOT NULL,
 alignment_json TEXT NOT NULL, sites_json TEXT, verified INTEGER NOT NULL DEFAULT 0,
 verified_at TEXT, verified_by TEXT, locked INTEGER NOT NULL DEFAULT 0, demo INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS events(
 id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL REFERENCES patients(id),
 photo_id INTEGER NOT NULL REFERENCES photos(id), site_number INTEGER NOT NULL,
 x REAL NOT NULL, y REAL NOT NULL, occurred_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
 actor TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL,
 exception_reason TEXT NOT NULL DEFAULT '', warnings_json TEXT NOT NULL DEFAULT '[]',
 alignment_json TEXT NOT NULL, request_key TEXT UNIQUE NOT NULL,
 voided_at TEXT, voided_by TEXT, void_reason TEXT);
CREATE INDEX IF NOT EXISTS events_patient_time ON events(patient_id, occurred_at);
CREATE TABLE IF NOT EXISTS complications(
 id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL REFERENCES patients(id),
 photo_id INTEGER NOT NULL REFERENCES photos(id), site_number INTEGER NOT NULL,
 x REAL NOT NULL, y REAL NOT NULL, radius REAL NOT NULL, types_json TEXT NOT NULL,
 severity TEXT NOT NULL, observed_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
 actor TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', alignment_json TEXT NOT NULL,
 resolved_at TEXT, resolved_by TEXT, resolution_note TEXT);
CREATE INDEX IF NOT EXISTS complications_patient ON complications(patient_id, observed_at);
CREATE TABLE IF NOT EXISTS reviews(
 patient_id INTEGER NOT NULL REFERENCES patients(id), site_number INTEGER NOT NULL,
 through_alert_id INTEGER NOT NULL, reviewed_at TEXT NOT NULL, actor TEXT NOT NULL, note TEXT NOT NULL,
 PRIMARY KEY(patient_id, site_number));
CREATE TABLE IF NOT EXISTS appointments(
 patient_id INTEGER PRIMARY KEY REFERENCES patients(id), due_at TEXT NOT NULL,
 scheduled_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'suggested', reason TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(
 id INTEGER PRIMARY KEY, at TEXT NOT NULL, actor TEXT NOT NULL, patient_id INTEGER,
 action TEXT NOT NULL, entity TEXT NOT NULL, detail_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS record_revisions(
 id INTEGER PRIMARY KEY, patient_id INTEGER NOT NULL REFERENCES patients(id),
 record_type TEXT NOT NULL, record_id INTEGER NOT NULL, changed_at TEXT NOT NULL,
 actor TEXT NOT NULL, reason TEXT NOT NULL, before_json TEXT NOT NULL, after_json TEXT NOT NULL);
"""


def connect(data_dir: Path) -> sqlite3.Connection:
    db = sqlite3.connect(data_dir / "sitecare.sqlite3", timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=15000")
    return db


def initialize(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "photos").mkdir(exist_ok=True)
    with closing(connect(data_dir)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)
        version = db.execute("SELECT version FROM schema_info").fetchone()[0]
        if version not in (1, 2):
            raise RuntimeError("Unsupported database version. Preserve your data and contact the developer.")
        additions = {
            "patients": {"dosage_category": "TEXT NOT NULL DEFAULT 'standard'", "dosage_rate": "REAL NOT NULL DEFAULT 0.15",
                         "dosage_step": "REAL NOT NULL DEFAULT 0.01", "dosage_reason": "TEXT NOT NULL DEFAULT ''",
                         "dosage_pending": "INTEGER NOT NULL DEFAULT 0", "appointment_mode": "TEXT NOT NULL DEFAULT 'days'",
                         "appointment_days": "INTEGER NOT NULL DEFAULT 3", "appointment_weekdays": "TEXT NOT NULL DEFAULT '[]'"},
            "events": {"dosage_category": "TEXT", "dosage_rate": "REAL", "dosage_previous_rate": "REAL",
                       "dosage_status": "TEXT", "dosage_reason": "TEXT NOT NULL DEFAULT ''"},
            "complications": {"width_cm": "REAL", "height_cm": "REAL", "voided_at": "TEXT",
                              "voided_by": "TEXT", "void_reason": "TEXT"},
            "audit": {"patient_code": "TEXT"},
        }
        for table, columns in additions.items():
            existing = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
            for name, definition in columns.items():
                if name not in existing:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        db.execute("UPDATE complications SET width_cm=radius*2,height_cm=radius*2 WHERE width_cm IS NULL")
        db.execute("UPDATE audit SET patient_code=(SELECT code FROM patients WHERE patients.id=audit.patient_id) "
                   "WHERE patient_code IS NULL AND patient_id IS NOT NULL")
        for entry in rows(db, "SELECT patient_id,detail_json FROM audit WHERE action='patient.deleted'"):
            code = json.loads(entry["detail_json"]).get("code")
            if code:
                db.execute("UPDATE audit SET patient_code=? WHERE patient_id=? AND patient_code IS NULL",
                           (code, entry["patient_id"]))
        if version == 1:
            # The previous UI combined pain/tenderness. Preserve that meaning;
            # new observations can distinguish the two without rewriting history.
            for row in rows(db, "SELECT id,types_json FROM complications"):
                types = json.loads(row["types_json"])
                if "pain" in types:
                    types = ["pain_tenderness_legacy" if value == "pain" else value for value in types]
                    db.execute("UPDATE complications SET types_json=? WHERE id=?", (json.dumps(types), row["id"]))
            # One-time upgrade requested for this installation; subsequent choices persist.
            db.execute("UPDATE app_settings SET keep_calibration=1,revision=revision+1 WHERE keep_calibration=0")
            db.execute("UPDATE schema_info SET version=2")
        # Earlier installations had one immutable layout per patient. Preserve it
        # on every existing photo before allowing edits on later visit photos.
        if "sites_json" not in {r[1] for r in db.execute("PRAGMA table_info(photos)")}:
            db.execute("ALTER TABLE photos ADD COLUMN sites_json TEXT")
        for photo in db.execute("SELECT id,patient_id FROM photos WHERE sites_json IS NULL").fetchall():
            sites = rows(db, "SELECT number,x,y FROM sites WHERE patient_id=? ORDER BY number", (photo["patient_id"],))
            db.execute("UPDATE photos SET sites_json=? WHERE id=?", (json.dumps(sites), photo["id"]))
        # Preserve ID high-water marks before any deletion, including older databases.
        for table in ("patients", "photos", "events", "complications"):
            highest = db.execute(f"SELECT COALESCE(MAX(id),0) FROM {table}").fetchone()[0]
            db.execute("INSERT INTO id_sequences VALUES(?,?) ON CONFLICT(name) DO UPDATE "
                       "SET last_id=MAX(last_id,excluded.last_id)", (table, highest))
        db.commit()
    cleanup_deleted_photos(data_dir)


def next_id(db, table: str) -> int:
    """IDs remain unique after deletion, so old links cannot address new records."""
    if table not in {"patients", "photos", "events", "complications"}:
        raise ValueError("Unsupported record type")
    highest = db.execute(f"SELECT COALESCE(MAX(id),0) FROM {table}").fetchone()[0]
    previous = db.execute("SELECT last_id FROM id_sequences WHERE name=?", (table,)).fetchone()
    value = max(highest, previous[0] if previous else 0) + 1
    db.execute("INSERT INTO id_sequences VALUES(?,?) ON CONFLICT(name) DO UPDATE "
               "SET last_id=excluded.last_id", (table, value))
    return value


def cleanup_deleted_photos(data_dir: Path) -> int:
    """Retry committed deletions. Failed file removals remain queued for restart."""
    photo_root = (data_dir / "photos").resolve()
    with transaction(data_dir, True) as db:
        for row in db.execute("SELECT filename FROM pending_photo_deletions").fetchall():
            filename = row[0]
            target = (photo_root / filename).resolve()
            if target.parent != photo_root or target.name != filename:
                continue
            if db.execute("SELECT 1 FROM photos WHERE filename=?", (filename,)).fetchone():
                continue
            try:
                target.unlink(missing_ok=True)
            except OSError:
                continue
            db.execute("DELETE FROM pending_photo_deletions WHERE filename=?", (filename,))
        return db.execute("SELECT COUNT(*) FROM pending_photo_deletions").fetchone()[0]


@contextmanager
def transaction(data_dir: Path, write: bool = False):
    db = connect(data_dir)
    try:
        if write:
            db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def rows(db: sqlite3.Connection, sql: str, args: tuple = ()) -> list[dict]:
    return [dict(r) for r in db.execute(sql, args).fetchall()]


def one(db: sqlite3.Connection, sql: str, args: tuple = ()) -> dict | None:
    r = db.execute(sql, args).fetchone()
    return dict(r) if r else None


def audit(db, actor: str, action: str, entity: str, detail: dict, patient_id: int | None = None):
    p = one(db, "SELECT code FROM patients WHERE id=?", (patient_id,)) if patient_id else None
    code = p["code"] if p else detail.get("code")
    db.execute("INSERT INTO audit(at,actor,patient_id,action,entity,detail_json,patient_code) VALUES(?,?,?,?,?,?,?)",
               (iso(now_utc()), actor, patient_id, action, entity, json.dumps(detail, ensure_ascii=False), code))


def decode_photo(photo: dict | None) -> dict | None:
    if photo:
        photo = dict(photo)
        photo["alignment"] = json.loads(photo.pop("alignment_json"))
        photo["sites"] = json.loads(photo.pop("sites_json", None) or "[]")
        photo["url"] = f"/api/photos/{photo['id']}/image"
        photo.pop("filename", None)
    return photo


def patient_records(db, patient_id: int) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    sites = rows(db, "SELECT number,x,y FROM sites WHERE patient_id=? ORDER BY number", (patient_id,))
    events = rows(db, "SELECT * FROM events WHERE patient_id=? ORDER BY occurred_at DESC,id DESC", (patient_id,))
    alerts = rows(db, "SELECT * FROM complications WHERE patient_id=? ORDER BY observed_at DESC,id DESC", (patient_id,))
    reviews = rows(db, "SELECT * FROM reviews WHERE patient_id=?", (patient_id,))
    for e in events:
        e["warnings"] = json.loads(e.pop("warnings_json"))
        e.pop("alignment_json", None)
        e.pop("request_key", None)
    for a in alerts:
        a["types"] = json.loads(a.pop("types_json"))
        a.pop("alignment_json", None)
    return sites, events, alerts, reviews


def create_backup(data_dir: Path, target: Path) -> Path:
    """Snapshot DB first, then copy the immutable photo files referenced by that DB.
    Login sessions are deliberately removed from the backup, not from the live DB.
    """
    # Coordinate with uploads/deletions, including maintenance in another process.
    # Use a separate read connection for backup; backing up a connection that owns
    # a write transaction can wait indefinitely.
    with transaction(data_dir, True):
        return _create_backup(data_dir, target)


def _create_backup(data_dir: Path, target: Path) -> Path:
    with TemporaryDirectory(prefix="sitecare-backup-") as tmp:
        snapshot = Path(tmp) / "sitecare.sqlite3"
        src, dest = connect(data_dir), sqlite3.connect(snapshot)
        try:
            src.backup(dest)
            dest.execute("DELETE FROM sessions")
            filenames = [r[0] for r in dest.execute("SELECT filename FROM photos")]
            dest.commit()
        finally:
            src.close()
            dest.close()
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(snapshot, "data/sitecare.sqlite3")
            for filename in filenames:
                z.write(data_dir / "photos" / filename, "data/photos/" + filename)
            z.writestr("RESTORE.txt", "Contains sensitive, UNENCRYPTED patient data. Stop SiteCare before restoring.\n"
                       "Back up the current data folder, replace it with the data folder from this archive, then restart.\n"
                       "Do not merge a restored database with an unrelated photos folder. Existing logins must sign in again.\n")
    return target
