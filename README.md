# SiteCare Prototype

A local, bilingual web application for documenting abdominal puncture sites, reviewing a 14-site photo overlay, and planning visits.

**GitHub:** [ShabbirMahmood/SiteCare_Prototype](https://github.com/ShabbirMahmood/SiteCare_Prototype)

## Start

Open the project folder in VS Code and use a **Command Prompt** terminal. With Python 3.13 installed:

```bat
py -3.13 -m venv .venv
.venv\Scripts\activate
python.exe -m pip install -r requirements.txt
python.exe run.py
```

Open [SiteCare](http://127.0.0.1:8000/). On a fresh installation, create the administrator account; no account is built in. Stop the server with **Ctrl+C** in its terminal.

For an existing installation, activate its environment and run `python.exe run.py`. See [Setup Instructions](setup_instruction.md) for Python versions, account details, password resets, and port recovery.

## Features

- Patient profiles, photo numbering from #1 per patient, and a separate editable 14-site layout for each new photo.
- Manual alignment, ruler calibration, exact-point records, and skin-alert recovery.
- Up to three candidates in numbered rotation order, rest countdowns, and appointments.
- Shared demonstration date, administrator-controlled Keep Calibration, English/Japanese interface, and administrator patient deletion.
- Local accounts, audit history, patient CSV export, and database/photo backups.

## Architecture

```mermaid
flowchart LR
    Browser["Browser: HTML / CSS / JavaScript / SVG"] -->|"Local HTTP + JSON"| API["Uvicorn + FastAPI"]
    API --> Rules["Screening Rules + Clock + Settings"]
    API --> Security["Sessions + Roles + CSRF"]
    API --> Storage["SQLite Storage"]
    Storage --> DB[("data/sitecare.sqlite3")]
    API --> Photos["data/photos: Local JPEG Files"]
    Storage --> Backup["Backup ZIP: Database + Photos"]
```

## Workflow

```mermaid
flowchart LR
    A["Sign In"] --> B["Create / Open Patient"]
    B --> C["Upload Visit Photo"]
    C --> L["Edit / Save This Photo Layout"]
    L --> D["Align + Calibrate + Verify"]
    D --> E["Review Sites + Exact Point"]
    E --> F["Record Completed Puncture"]
    F --> G["Rest Countdown + Next Visit"]
    E --> H["Record Skin Alert"]
    H --> I["Confirm Recovery"]
    I --> E
```

## Photos and Calibration

Photo labels are local to each patient: patient A has **#1, #2, #3**, and patient B starts again at **#1**. They represent upload order, including existing photos. Internal database IDs stay unchanged so records continue to link to the correct image.

On every new photo, **Edit 14 Sites** and the four bottom controls are available: **Verify & Save Alignment**, **Discard Changes** (yellow), **Save 14-Site Layout** (red), and **Default Layout** (blue). Once a record uses that photo, its layout and alignment become read-only. A later upload gets its own editable copy; earlier images and records retain their saved geometry.

The administrator's **Keep Calibration** checkbox sits immediately beside **Change Date**:

| Setting | Behavior |
| --- | --- |
| Unchecked — default | The current photo must be within 24 hours of the application clock. A new procedure also needs a photo without an existing non-voided procedure record. |
| Checked | Reuse the latest verified photo beyond 24 hours and for later procedures. Its saved layout/alignment stay protected. |
| New photo uploaded | Calibrate and verify this new image in either mode. Calibration is never copied between different images. |

The setting applies to all patients, is saved across restarts, and takes effect when changed. Site rest, exact-point spacing, skin alerts and all other record checks still apply. **Change Date** affects photo age as well as countdowns and appointments.

## Everyday Operation

1. Sign in and open the existing patient profile for each visit.
2. Upload and prepare a new photo, or use an existing verified photo when Keep Calibration is enabled.
3. Review the three candidate suggestions and the exact point before documenting a completed procedure.
4. Record skin observations and explicitly confirm recovery when appropriate. Recovery returns an otherwise eligible site to its numbered candidate position immediately.
5. Save changes before closing. Stop the Python server in its terminal with **Ctrl+C**.

Back up through **Settings & Data → Download Complete Backup** or `python.exe manage.py backup`. Keep the complete `data/` folder when updating the application. Restart the server and press **Ctrl+F5** after installing source changes.

## Guides

| File | Purpose |
| --- | --- |
| [user_manual.md](user_manual.md) | Short user guide in English and Japanese |
| [setup_instruction.md](setup_instruction.md) | VS Code setup, login, stopping, and maintenance |
| [technical_architecture.md](technical_architecture.md) | Detailed file map, database, APIs, rules, and workflows |
| [docs/TEST_REPORT.md](docs/TEST_REPORT.md) | Recorded verification results |

Python serves both the API and interface; no Node.js build, database server, or cloud account is required. Data stays in the installation's `data` folder. The application binds to `127.0.0.1` and displays workflow dates in **Japan Standard Time**.

**Prototype scope:** use synthetic or appropriately de-identified data. Photo measurements are approximate, and a green site means only that software checks passed. This application is not clinically validated. Data and backups are not encrypted by the application.
