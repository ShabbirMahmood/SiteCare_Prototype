"""Optional synthetic records. Never includes any of the user's supplied photos."""
from __future__ import annotations
import json
from datetime import timedelta
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .rules import default_sites, iso, now_utc
from .storage import audit, one


def demo_image(path: Path):
    """A clearly labelled, schematic teaching surface, not a real patient image."""
    image = Image.new("RGB", (1200, 1000), "#e8edef")
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((90, 75, 1110, 950), radius=140, fill="#e3c7ab", outline="#c3a68e", width=3)
    d.rounded_rectangle((140, 30, 1060, 180), radius=40, fill="#33474a")
    d.rounded_rectangle((120, 860, 1080, 1000), radius=40, fill="#4c6266")
    d.arc((200, 215, 1000, 500), 10, 170, fill="#c3a88f", width=3)
    d.arc((200, 430, 1000, 765), 10, 170, fill="#c3a88f", width=3)
    d.ellipse((588, 509, 612, 531), fill="#967d69", outline="#745f50", width=2)
    # Visible 10 cm reference: endpoints (180,800) and (480,800), 30 px/cm.
    d.rounded_rectangle((165, 767, 500, 836), radius=5, fill="#fffdf3", outline="#9eaaad", width=2)
    d.line((180, 800, 480, 800), fill="#3b4d50", width=3)
    for i in range(11):
        x = 180 + i * 30
        d.line((x, 790, x, 816), fill="#3b4d50", width=2)
        d.text((x - 5, 772), str(i), fill="#263e42")
    d.text((405, 819), "10 cm", fill="#263e42")
    d.rounded_rectangle((410, 91, 790, 130), radius=8, fill="#eef5f3")
    d.text((435, 104), "SYNTHETIC DEMO - NOT A PATIENT", fill="#193b3c")
    image.save(path, "JPEG", quality=94)


def seed_demo(db, data_dir: Path, actor: str) -> int:
    from .app import sync_appointment
    existing = one(db, "SELECT id FROM patients WHERE code='DEMO-001'")
    if existing:
        return existing["id"]
    now = now_utc().replace(microsecond=0)
    pid = db.execute("INSERT INTO patients(code,alias,notes,therapy,start_at,demo,created_at) VALUES(?,?,?,?,?,1,?)",
                     ("DEMO-001", "Demo patient A / デモ患者 A",
                      "Synthetic training data only. The reference ruler is 10 cm. No actual patient data.",
                      "Medication-neutral demonstration", iso(now - timedelta(days=2)), iso(now))).lastrowid
    sites = default_sites()
    db.executemany("INSERT INTO sites VALUES(?,?,?,?)", [(pid, s["number"], s["x"], s["y"]) for s in sites])
    filename = "synthetic-demo-001.jpg"
    demo_image(data_dir / "photos" / filename)
    alignment = {"cx": 600, "cy": 520, "ppm": 30, "angle": 0,
                 "calibration": {"a": {"x": 180, "y": 800}, "b": {"x": 480, "y": 800}, "length_cm": 10}}
    photoid = db.execute("INSERT INTO photos(patient_id,filename,width,height,captured_at,uploaded_at,alignment_json,"
                        "verified,verified_at,verified_by,locked,demo) VALUES(?,?,1200,1000,?,?,?,1,?,?,1,1)",
                        (pid, filename, iso(now), iso(now), json.dumps(alignment), iso(now), actor)).lastrowid
    for n, ago in [(1, 2), (2, 5), (3, 8), (8, 11)]:
        s = sites[n - 1]
        db.execute("INSERT INTO events(patient_id,photo_id,site_number,x,y,occurred_at,recorded_at,actor,note,kind,"
                   "exception_reason,alignment_json,request_key) VALUES(?,?,?,?,?,?,?,?,?,'history',?,?,?)",
                   (pid, photoid, n, s["x"], s["y"], iso(now - timedelta(days=ago)), iso(now), actor,
                    "Synthetic historical example", "Seeded fictional example for interface testing.",
                    json.dumps(alignment), f"demo-{pid}-{n}"))
    s = sites[3]
    for ago, resolved in [(30, 24), (2, None)]:
        db.execute("INSERT INTO complications(patient_id,photo_id,site_number,x,y,radius,types_json,severity,"
                   "observed_at,recorded_at,actor,note,alignment_json,resolved_at,resolved_by,resolution_note) "
                   "VALUES(?,?,?,?,?,1.5,?,'mild',?,?,?,?,?,?,?,?)",
                   (pid, photoid, 4, s["x"], s["y"], json.dumps(["redness", "hardness"]),
                    iso(now - timedelta(days=ago)), iso(now), actor, "Synthetic skin-observation example.",
                    json.dumps(alignment), iso(now - timedelta(days=resolved)) if resolved else None,
                    actor if resolved else None, "Fictional recovery assessment." if resolved else None))
    sync_appointment(db, pid)
    for code, label, offset in [("DEMO-002", "Demo patient B / デモ患者 B", -1),
                                ("DEMO-003", "Demo patient C / デモ患者 C", 3)]:
        p = db.execute("INSERT INTO patients(code,alias,notes,start_at,demo,created_at) VALUES(?,?,?, ?,1,?)",
                       (code, label, "Synthetic patient. Upload a test image to start mapping.",
                        iso(now + timedelta(days=offset)), iso(now))).lastrowid
        db.executemany("INSERT INTO sites VALUES(?,?,?,?)", [(p, s["number"], s["x"], s["y"]) for s in sites])
        sync_appointment(db, p)
    audit(db, actor, "demo.created", str(pid), {"synthetic_only": True}, pid)
    return pid
