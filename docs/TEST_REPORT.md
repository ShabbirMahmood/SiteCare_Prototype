# Packaging verification report

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
