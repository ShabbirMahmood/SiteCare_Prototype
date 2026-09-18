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
 alignment_json TEXT NOT NULL, verified INTEGER NOT NULL DEFAULT 0,
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
        if db.execute("SELECT version FROM schema_info").fetchone()[0] != 1:
            raise RuntimeError("Unsupported database version. Preserve your data and contact the developer.")


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
    db.execute("INSERT INTO audit(at,actor,patient_id,action,entity,detail_json) VALUES(?,?,?,?,?,?)",
               (iso(now_utc()), actor, patient_id, action, entity, json.dumps(detail, ensure_ascii=False)))


def decode_photo(photo: dict | None) -> dict | None:
    if photo:
        photo = dict(photo)
        photo["alignment"] = json.loads(photo.pop("alignment_json"))
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
