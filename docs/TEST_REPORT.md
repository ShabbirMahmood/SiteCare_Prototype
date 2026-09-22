# Packaging verification report

## Patient Options And Longitudinal Records — 2026-09-23

The complete synthetic Windows suite passed **136 tests**, with one existing Starlette/AnyIO deprecation warning. All six JavaScript modules passed syntax checks. Coverage now includes full ellipse containment and validation; separate Pain/Tenderness types; patient-isolated dosage presets, reason requirements and completion defaults; out-of-order history; day-count/weekday appointment rules and one-next-visit calendars; JST monthly/yearly aggregation; unknown legacy rates; recovery and deletion counts; dated photo overlays; correction snapshots; expanded CSV; nurse permissions and deletion/session revocation; unused-photo protection; and schema-1 migration preserving old geometry, unknown dosage and later calibration choices.

A separate temporary installation on port 8001 was checked with synthetic records in English and Japanese. Browser checks exercised linked X/Y dimensions, independent ellipse height, mouse-drawn width/height with retained observations, dosage step buttons and change colors, preset completion and next-dose defaults, the single identity checkbox, exclusive appointment methods, monthly/yearly/site reports, alert histograms, historical photo overlays, record correction history, and patient-code links with readable audit summaries. No JavaScript console errors were reported. The user’s data folder was not used by these tests.

The earlier dated sections below describe earlier releases; default calibration and scheduling behavior changed in this update.

## Photo History and Keep Calibration Verification — 2026-09-20

The full Windows suite completed with **112 passed**, with one existing Starlette/AnyIO deprecation warning. JavaScript syntax checks passed for all four modules. Nine new synthetic test cases cover:

- Separate #1/#2/#3 photo numbering across interleaved patients and application restart.
- Editing/resetting a new photo after a prior puncture or skin record, while preserving older layouts, alignment and records.
- Historical assignment using the source photo's layout and selection of the appropriate layout when moving the demonstration date.
- Enabling reuse of a verified photo beyond 24 hours, including another procedure, and immediate restoration of the age limit when disabled.
- Continued rest/skin restrictions, required calibration of new uploads, and rejection of future current photos.
- Administrator/CSRF checks, strict boolean validation, stale revisions and patient versions, audit entries, restart persistence and isolation between installations.
- Additive upgrade of an earlier schema, preserved history and non-overwriting layout backfill on repeated initialization.

A separate temporary installation on port 8001 was checked in the browser with synthetic images. Patient A displayed #1 and #2 despite an intervening upload for patient B, which displayed #1. The new photo had Edit 14 Sites and all four bottom controls enabled. Default Layout saved successfully; the earlier recorded photo kept read-only geometry and visible disabled edit controls. Computed control colors remained green, yellow, red and blue.

Keep Calibration appeared to the right of Change Date, unchecked by default. Checking it immediately restored candidate eligibility for a three-day-old verified photo; unchecking immediately restored the stale-photo message and removed those candidates. Japanese labels and the same behavior were checked, and no browser console warnings/errors were reported. The temporary preview was closed afterward. These checks did not use or change the user's patient records.

## Layout controls and interface verification — 2026-09-20

The full Windows test suite completed with **103 passed**, with the existing Starlette/AnyIO deprecation warning. JavaScript syntax checks passed. Added API coverage verifies restoration of every default coordinate, unchanged photos/alignment and candidate results, before/after audit details, stale-version rejection, both puncture and skin-record locks, and ambiguous reset payload rejection.

A disposable local installation was checked in the browser. Dragging and saving a site worked; Default Layout immediately restored and saved the default coordinates. Unsaved photo rotation survived the reset and Discard Changes restored the saved alignment. Computed button backgrounds were red, blue and yellow, and desktop overlay labels were 12px. English navigation, headings, buttons, options and statuses use title capitalization; patient-entered text retains its original case.

## Administrator deletion verification — 2026-09-18

The full Windows test suite now completes with **98 passed**, with the same dependency deprecation warning. JavaScript syntax checking passed. New synthetic tests verify deletion of empty/populated profiles, dependent records and photos, preservation of other patients and audit history, permission/CSRF checks, typed confirmation, stale versions, transaction rollback, locked-file cleanup retry, permanent record IDs, demo reload, and backup/deletion coordination.

A separate temporary demo installation was used to inspect the Profile deletion option and confirmation dialog in the browser. The final button was disabled until the exact patient ID was entered. Actual deletion was exercised by the automated API tests. No existing patient in the user's installation was deleted.

## Local update verification — 2026-09-18

The numbered candidate-order fix and demonstration clock were verified on the current Windows workspace using Python 3.12. The full suite completed with **86 passed**, with one existing Starlette/AnyIO deprecation warning. JavaScript syntax checks passed for the modified modules.

New coverage includes the exact candidate transition from 3, 4, 6 to 3, 4, 5 after recovery; rotation wraparound; forward/backward application dates; rest expiry and stale photographs; appointment calculations; unchanged saved timestamps; clock persistence and isolation between installations; invalid dates; stale edits; administrator permissions; and real-time session expiry.

A browser check used a temporary database with synthetic demo records on a separate local port. It verified the date dialog, running demo-date indicator, dashboard overdue counts, calendar month, reset to system time, and patient workspace rendering. The actual installation remains in system-date mode. The original packaging report below describes its earlier environment and checks.

## Environment

Operating system: Linux. Python: 3.13.5.

The already-installed package versions used for the checks were:

- fastapi: 0.128.2
- uvicorn: 0.48.0
- python-multipart: 0.0.29
- Pillow: 12.3.0
- pytest: 9.0.2
- httpx: 0.28.1

These match the direct runtime and test requirements distributed with the project.

## Automated suite

Command: `python -m pytest -q`, run from the project directory.

Result: **71 passed**. The suite also passed again after extracting the distribution ZIP to a separate temporary folder. The tests cover the backend/API and deterministic rule engine with synthetic fixtures. Test databases are temporary; no actual patient images are used.

## Local server checks

The Linux start helper was run from outside the project directory with an isolated temporary data folder and the environment's preinstalled packages. The following real-loopback-HTTP checks passed:

- Linux start helper with --no-browser, custom port, and separate data directory.
- Main HTML served over real loopback HTTP.
- All distributed static assets served.
- First-run account setup through real HTTP.
- Synthetic demo creation, patient workspace with 14 sites, and photo retrieval.
- Database-and-photo backup download is a valid ZIP.

Both macOS/Linux shell helpers passed `bash -n` syntax checking. The Windows batch helpers were provided and reviewed, but were not executed on Windows. No macOS runtime test was available. Browser auto-opening and every interactive control were not retested during this packaging step.

## Fresh-install limitation

A fresh virtual environment was successfully created by the Linux setup helper. However, package installation could not finish because this execution environment could not resolve/reach the package index. The installer reported DNS/connection errors followed by no available package versions. That output does not establish whether a version is available from the index; the network lookup failed.

Accordingly, this package has NOT had a successful clean dependency-download installation in this environment. Tests and startup checks used the already-installed versions listed above, not a newly downloaded environment. Windows/macOS installation remains unverified. Installation on the user's computer requires internet access to download Python packages.

## Distribution checks

The release ZIP is checked for readable contents, expected project files, checksums, and exclusion of runtime databases, uploaded patient images, environments, and caches. The archive contains a single `SiteCare_Prototype/` root folder. The bundled practice image and interface screenshot are synthetic demonstration assets.

The application sources are unchanged from the prior project; this handoff adds documentation, setup/start helpers, and demonstration assets. The screenshot is an earlier demonstration-workspace capture, not proof of a new browser regression test.

## Scope

These are software packaging and functionality checks. They do not establish clinical accuracy, patient safety, security certification, regulatory compliance, or production readiness. All distance estimates and candidate suggestions require independent clinical review.
