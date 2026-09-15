# Architecture and prototype assumptions

## Technology

- Backend: Python, FastAPI, Uvicorn.
- Interface: local HTML, CSS, and JavaScript modules; SVG-based overlay. No frontend compilation step.
- Storage: SQLite plus JPEG image files in the local data directory.
- Image processing: Pillow for validation, orientation handling, and sanitized image output.
- Runtime package pins: `requirements.txt`. Optional tests: `requirements-dev.txt`.

The normal launcher binds only to 127.0.0.1. There is deliberately no host option for LAN/internet exposure. The prototype is not a production deployment template.

## Source responsibilities

`run.py` starts the local server and opens the browser. `manage.py` provides local backup, database integrity/image-existence checks, and password reset. `sitecare/app.py` defines the application and API; `rules.py` implements deterministic screening and coordinate conversion; `storage.py` manages SQLite and backups; `security.py` provides credential helpers; `demo.py` generates fictional demo records and a schematic image.

`static/app.js` handles page-level UI, `workspace.js` the photograph/overlay workflow, and `ui.js` shared language and interface helpers. `templates/index.html` is served by the application; it must not be opened directly as a local HTML file.

## Geometry and time

The internal patient-relative two-dimensional plane uses centimetres, with navel=(0, 0), positive x toward image right/patient left, and positive y toward the feet. Alignment uses a navel location, one scale derived from a ruler, and rotation. This is a similarity transform, not anatomical image registration or a three-dimensional body-surface model.

The initial layout uses eight inner and six outer points. Its numbering is based on the supplied diagram, but its initial geometry is a prototype template. Save any patient-specific layout adjustments before adding clinical records. Layout/alignment locks preserve record interpretation afterward.

Dates are stored as timezone-aware UTC timestamps and displayed/entered in Japan Standard Time. Rest is 12 x 24 hours from the recorded puncture time; it is not based on calendar midnights. Appointments use 3 x 24 hours from the latest non-voided recorded puncture, or the initial due date when no puncture exists.

## Rule assumptions requiring clinical review

The supplied project brief is the source for a 12-day reuse restriction, 3-day procedure interval, at least 2.5 cm from punctures in the preceding 12 days, and at least 5 cm from the navel. This package does not independently establish their medical applicability. Confirm the actual medicine, device, approved protocol, and which event starts each clock.

The prototype conservatively restricts the whole assigned numbered site after use, in addition to exact-point spacing checks. Active complication circles remain blocking until recovery is recorded. Related observations over 90 days are retained as informational history, without a recurrence-review hold. The 24-hour latest-photo limit for new-procedure screening remains a prototype engineering setting.

The deterministic suggestion engine returns at most three rule-eligible numbered positions. It is not a model of tissue condition, wound recovery, drug absorption, or clinical risk. There is no automated diagnosis or image-based complication recognition.

## Persistence and security boundaries

SQLite records users, sessions, patients, layout coordinates, photographs and alignment metadata, events, complications, reviews, appointments, and audit entries. Photographs are separate local files. Passwords are hashed, authentication/CSRF checks are implemented, data endpoints require access checks, and optimistic record versions prevent silent competing writes.

These are prototype controls, not a security certification. A user with filesystem access can copy or alter local files; the audit table is not tamper-proof. Data and backups are not encrypted by the application. Backups include password hashes and patient data but omit active sessions. The application does not implement an institution's retention policy, encryption/key-management service, medical-device certification, hospital identity integration, or incident-response process.

Do not open the database through network shares, synchronize a live SQLite database between PCs, or expose the local service publicly. Do not disable system security controls to run this package. Obtain institution-approved clinical, technical, privacy, and security review before a real-data pilot.

## Advanced commands

From the project directory, use your `.venv` Python:

```text
python run.py --port 8001 --no-browser
python run.py --data-dir /absolute/path/to/separate-local-data
python manage.py check
python manage.py backup
python manage.py reset-password USERNAME
```

The word `python` above represents `.venv\Scripts\python.exe` on Windows or `.venv/bin/python` on macOS/Linux. When a custom data directory is used for the server, supply the same `--data-dir` to maintenance commands. Maintenance without that option defaults to the project's `data` folder.

The normal setup does not require any advanced flags. Do not modify rule constants casually: rule changes need versioning, tests, review of historical interpretation, and clinical approval.

## Not implemented / not certified

This package does not provide automated physical distance verification, automatic anatomical tracking across photographs, contour deformation, autonomous site selection, freehand alert polygons, medication dosing, outbound reminder messages, hospital-record integration, or validated clinical decision support. Multi-computer deployment, real-world clinical usability, and Windows/macOS installation have not been validated in the packaging environment.
