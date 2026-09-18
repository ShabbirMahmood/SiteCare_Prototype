# SiteCare Prototype

**A local Python web application for demonstrating abdominal puncture-site documentation and appointment planning.**

Version: 1.0.0-prototype  
Interface: Japanese and English  
Storage: SQLite database plus local image files

> Demonstration only. This is not a clinically validated medical device or an approved clinical record system. Use fictional or institution-approved de-identified data. The application does not diagnose skin complications, prescribe a medicine, or authorize a puncture. Green means only that the configured software checks passed.

## 1. What is included

The ZIP contains the complete application source, pinned package requirements, setup/start helpers, tests, a workflow guide, a synthetic practice image, and a screenshot of the demonstration workspace. You do not need to download the source files separately.

The program supports patient profiles, photo upload and manual alignment, a 14-position transparent overlay, exact puncture coordinates, 12-day rest countdowns, manually drawn skin-alert areas, complication types, up to three rule-screened candidate sites, history tables, and three-day appointment suggestions.

Python must be installed separately. Internet access is needed to install Python and download packages. The project does not require Node.js, Docker, a separate database server, or a cloud account. After installation, the application serves its interface locally without using an external service.

## 2. Before you start

Use Python **3.13** to match the tested Python minor version. The launcher accepts Python 3.11 or newer, but other Python versions have not been verified for this package. The packaging checks used Python 3.13.5 on Linux.

Use a desktop browser such as Chrome or Edge. The app uses the computer clock by default. Administrators can use the top date bar's Change date control to set a shared demonstration date/time, or choose Use system date to reset it. Countdown and appointment calculations follow the selected clock; saved record timestamps are preserved. The interface displays and accepts clinical date/time values in **Japan Standard Time (UTC+09:00)**, even on a computer outside Japan.

Extract the entire ZIP before running anything. Keep all the extracted files and folders together. Choose an ordinary writable local folder, for example `C:\SiteCare_Prototype`, or a folder inside your user directory. Avoid `Program Files`, network shares, and cloud-synchronized folders for the live database. You do not need to run the application as an administrator.

**Windows and macOS installers/launchers have not been executed on those operating systems.** The included Windows helpers are convenience scripts; the explicit manual commands below are also provided. A fresh package-download installation could not be completed in the packaging environment because the package index was unreachable. Runtime checks used the already-installed pinned packages. See `docs/TEST_REPORT.md` for the checks actually performed.

## 3. Windows: first-time installation

### Step 1 - Install Python

Open https://www.python.org/downloads/ and install Python 3.13 for your computer. Follow the official installer instructions. When offered, enable **Add Python to PATH** and the Python launcher (`py`).

After installation, close and reopen any Command Prompt windows.

### Step 2 - Extract the ZIP

Right-click `SiteCare_Prototype.zip`, choose **Extract All**, and choose a writable local location. Open the extracted folder that contains `run.py` and `README.md`. Depending on the extraction destination, there may be two nested folders with the same name; the correct one is the folder containing `run.py`.

Do not run files while viewing the compressed ZIP.

### Step 3 - Install the application's packages

Double-click **`setup_windows.bat`**.

This script looks for a suitable Python interpreter, creates a private `.venv` folder, and installs the packages in `requirements.txt`. It does not install packages into your system Python. An internet connection is needed for package downloads.

Wait until it displays **Setup complete**. Read any error instead of closing the window immediately.

### Step 4 - Start the application

Double-click **`start_windows.bat`**.

A command window starts the local server. A browser window should open automatically. Otherwise, type this address into the browser's address bar:

```text
http://127.0.0.1:8000
```

Keep the command window open while using SiteCare. Closing it stops the server.

### Step 5 - Create your account

On first launch, create an administrator account with a username, display name, and password of **12 to 128 characters**. There is no preset administrator password. Use the **日本語 / EN** language control to switch the interface to English.

Choose **Load demo** on the empty overview to create fictional patients. See Section 6 for a first practice session.

### Windows manual alternative

Use these commands if you prefer not to run a `.bat` file. Open the project folder in File Explorer, click the address bar, type `cmd`, and press Enter. Copy one line at a time:

```bat
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

If `py` is unavailable but `python --version` reports your installed Python 3.13, use `python -m venv .venv` for the first line. Do not continue if `python` opens the Microsoft Store instead of running Python; complete the Python installation first.

No virtual-environment activation or PowerShell execution-policy changes are needed.

## 4. macOS / Linux: first-time installation

Install Python 3.13 using the official Python installer on macOS, or your Linux distribution's supported package-installation process. On Linux, the separate `venv` package matching your Python interpreter may also be needed.

Extract the ZIP. Open Terminal, type `cd ` (including the space), drag the extracted folder containing `run.py` into Terminal, and press Enter. Alternatively, type the folder path in quotes.

Run:

```bash
bash setup_macos_linux.sh
bash start_macos_linux.sh
```

The setup script searches for `python3.13`, then other available Python 3.11-or-newer interpreters. It creates a local `.venv` and installs the pinned runtime requirements. Use Python 3.13 for the closest match to the tested environment.

Manual alternative, when `python3` is your installed Python 3.13:

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

Open `http://127.0.0.1:8000` in a browser if it does not open automatically. Complete account creation as described in the Windows instructions. Do not use `sudo` for the setup or start scripts.

## 5. Everyday starting and stopping

**Windows:** double-click `start_windows.bat`.

**macOS/Linux:** open Terminal in the project folder and run `bash start_macos_linux.sh`.

You only need to install the packages once per environment. Your records remain in the `data` folder between sessions. If you move the project to a different computer or operating system, transfer the project and an appropriate backup, then recreate the `.venv` there; do not copy a virtual environment between computers.

To stop, finish saving your work and press **Ctrl+C** in the server's command window. Closing only the browser does not stop the server. On restart, use the same project folder to open the same database.

The launcher listens only on `127.0.0.1`. This prototype is intentionally for the same computer; it does not provide access from a phone, another PC, the hospital network, or the internet.

## 6. First practice session

1. Sign in and select **Load demo**. Open **DEMO-001**. Its initial image and records are fictional; they demonstrate resting sites, skin alerts, candidates, history, and appointments.
2. Select **New visit photo** and upload `samples/synthetic_abdomen.jpg`. Use the current capture time for this simulated new visit. Do not change an actual photograph's time to bypass a freshness check.
3. Use **Navel** to identify the navel, and **Move photo**, photo-size, and rotation controls to align the image beneath the chart. The photograph moves relative to the overlay; separate viewing zoom does not change the saved coordinates.
4. Use **Ruler** to select the 0 and 10 marks on the synthetic image's ruler, enter **10 cm**, then complete **Verify & save alignment**. Review the confirmations before saving. Every new photo requires new calibration and verification.
5. Tap a numbered circle or a candidate to review its status. Use **Exact point** to mark a simulated actual location. Record a fictional completed puncture and observe the blue countdown, history entry, and next appointment. This button documents a completed procedure; it is not an instruction to perform one.
6. Use **Draw alert**, drag a circular area, choose complication types, and save an observation. View appointments on the separate **Appointments** page. Open `docs/WORKFLOW.md` for more detail.

The demo's original photograph is deliberately alignment-locked because saved records refer to it. Upload a new photo to practice alignment. Its status also becomes unverified for new-procedure screening when the photograph is older than 24 hours.

A practice image and demonstration screenshot are included, but **no real patient photographs, patient database, or preconfigured account are included in this ZIP**.

## 7. Local data and backup

The application automatically creates:

```text
data/
  sitecare.sqlite3
  photos/
```

SQLite may also create `sitecare.sqlite3-wal` and `sitecare.sqlite3-shm` while the application is running. These are working database files. Do not delete them or copy only the database while the application is open.

**Create a backup:** sign in as an administrator and use **Settings & data** to download a database-and-photos backup. A CSV export is not a complete backup.

You can also run the maintenance command from the project folder:

Windows:

```bat
.venv\Scripts\python.exe manage.py backup
```

macOS/Linux:

```bash
.venv/bin/python manage.py backup
```

Command-line backups are saved in `backups/`. Both backup methods use a SQLite snapshot and include the image files referenced by that snapshot. Existing login sessions are omitted from the backup.

**Restore a backup:** stop SiteCare, preserve the current `data` folder in a separate safe location, extract the backup, and replace the entire project `data` folder with the backup's `data` folder. Do not merge it with unrelated photos or keep old database sidecar files. Restart, sign in, and verify the restored patient records. A backup includes accounts and password hashes, so use credentials from that backup.

**Storage is not encrypted by this application.** This applies to the database, uploaded photographs, and backups. Use appropriate institution-approved encrypted storage, access controls, and handling procedures before considering identifiable information. Do not send a populated `data` folder or backup as part of a support request.

## 8. Troubleshooting

| Symptom | Action |
| --- | --- |
| Python is not found | Complete the Python installation, then reopen the terminal. Check `py -3.13 --version` on Windows or `python3 --version` elsewhere. |
| Windows hides filename extensions | The setup/start files may appear without `.bat`. Look for `setup_windows` and `start_windows`; ensure you extracted the ZIP. |
| A school/hospital policy blocks a script | Do not disable security protections. Ask your administrator, or use the approved manual setup process. |
| Packages will not install | Read the error. Check internet access, proxy restrictions, available disk space, and that Python 3.13 is in use. Do not remove version pins at random. |
| Linux says `ensurepip` or `venv` is unavailable | Install the matching Python virtual-environment support through your distribution's supported package process, then retry. |
| A moved or damaged `.venv` no longer starts | Stop the application, rename only `.venv` to `.venv_old`, and rerun setup. Do not remove `data`. |
| `No module named fastapi` | Run the setup script, or install `requirements.txt` using the `.venv` Python shown above. |
| Browser cannot connect | Keep the server terminal open; inspect it for startup errors. Use `http://127.0.0.1:8000`, not a `file://` HTML page. |
| Port 8000 is already in use | Stop the other copy, or run the start script with `--port 8001` and open `http://127.0.0.1:8001`. |
| Browser did not open automatically | Copy the printed local address into the browser. |
| Upload is rejected | Use JPEG/PNG under 16 MB, at least 200 pixels on each side and no more than 32 megapixels. Convert HEIC first. |
| All positions are gray | Calibrate and verify the latest photograph; new-procedure screening requires a photograph captured within the preceding 24 hours. |
| Alignment cannot be changed | A saved record references that photograph. Upload a new visit photograph. |
| A site remains red after 12 days | Active skin alerts do not expire with the rest countdown. Recovery and, when applicable, recurrence review must be recorded explicitly. |
| Session expired | Sign in again. Idle sessions expire after 30 minutes; sessions have an 8-hour maximum lifetime. |
| Another window changed the patient | Refresh before editing again. The application rejects conflicting saves rather than silently overwriting them. |
| Times appear different from your computer's local time | Clinical date/time controls use Japan Standard Time. This is intentional. |

To change the port on Windows, open Command Prompt in the project folder and run:

```bat
start_windows.bat --port 8001
```

On macOS/Linux:

```bash
bash start_macos_linux.sh --port 8001
```

To reset a forgotten local account password, stop the server and use the maintenance command, replacing `YOUR_USERNAME` with your actual username:

```bat
.venv\Scripts\python.exe manage.py reset-password YOUR_USERNAME
```

On macOS/Linux, substitute `.venv/bin/python` for `.venv\Scripts\python.exe`. The new password is entered privately in the terminal. Existing sessions for that user are revoked. Anyone with access to these local files can perform local maintenance; the application's login does not replace operating-system access controls.

## 9. Optional automated tests

Testing packages are separate from runtime packages. From the project folder:

Windows:

```bat
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

macOS/Linux:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

The included automated tests use synthetic fixtures and temporary databases. See `docs/TEST_REPORT.md` for packaging-time results and limits. Passing software tests is not clinical validation.

## 10. Project map

```text
SiteCare_Prototype/
  README.md                    Full setup and operating instructions
  README.txt                   Same instructions, easy to open in a text editor
  START_HERE.txt               Very short starting instructions
  setup_windows.bat            Windows first-time setup helper
  start_windows.bat            Windows daily start helper
  setup_macos_linux.sh          macOS/Linux setup helper
  start_macos_linux.sh          macOS/Linux daily start helper
  run.py                       Local server launcher
  manage.py                    Backup, integrity check, password reset
  requirements.txt             Pinned runtime packages
  requirements-dev.txt         Optional testing packages
  pytest.ini                   Test configuration
  sitecare/                    Python backend, database, screening, security, demo
  static/                      Browser JavaScript, CSS, favicon
  templates/                   Main application HTML
  tests/                       Automated tests
  docs/WORKFLOW.md              Nursing-workflow demonstration guide
  docs/TECHNICAL_NOTES.md       Architecture, assumptions, limitations
  docs/TEST_REPORT.md           Actual packaging checks
  docs/workspace_preview.png    Synthetic demonstration screenshot
  samples/synthetic_abdomen.jpg Synthetic practice image with a 10 cm ruler
  FILES_SHA256.txt              Checksums of distributed files
```

Folders such as `.venv`, `data`, `backups`, and test caches are created locally as needed; they are not distributed in the ZIP.

## 11. Prototype boundaries

The configured 12-day rest, three-day appointment interval, 2.5 cm spacing, and 5 cm navel exclusion implement the supplied project brief; they are not an independently verified treatment protocol. The medication/device protocol and the correct starting point of any restriction require confirmation by the responsible clinical team.

Photo coordinates are approximate two-dimensional measurements. A ruler and manual alignment do not correct abdominal curvature, skin folds, changes of posture, or perspective. A green point is not a safety guarantee. The numbered layer is a customizable starting template, not proof that every patient has 14 suitable sites.

The 24-hour photograph limit and recurrence alert threshold (two related observations in 90 days) are prototype engineering settings, not validated clinical thresholds. Skin observation and recovery are manual. Appointment suggestions are not confirmed bookings and do not send email, SMS, or background notifications. There is no diagnosis AI, automated anatomical registration, hospital-record integration, or production security/compliance certification.

Review `docs/TECHNICAL_NOTES.md` before modifying the application or planning a clinical pilot.
