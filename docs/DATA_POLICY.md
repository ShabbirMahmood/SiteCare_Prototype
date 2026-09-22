# Data Storage, Access And Record Management

Implementation policy for this local prototype, updated 23 September 2026. An organisation must set its own retention period and operational access policy; the application does not impose an automatic expiry schedule.

## Stored Data

| Location | Contents |
| --- | --- |
| `data/sitecare.sqlite3` | Profiles, patient dosage/appointment preferences, punctures, skin observations, per-photo geometry, appointments, users, hashed credentials, sessions, corrections, audit entries, demonstration clock and calibration setting |
| `data/photos/` | Sanitized JPEG photos addressed through authenticated application routes |
| Exported backup ZIP | Consistent SQLite snapshot and every photo referenced by that snapshot; sessions are removed from the backup copy |
| Patient CSV | Puncture and skin-observation rows, including dosage, dimensions, source IDs and deletion fields; no image bytes or complete revision history |

The server listens on localhost. The app does not send patient records to a cloud service or encrypt database/photo/backup files. Anyone with sufficient operating-system access to those files can read them. Login permissions protect the application interface; they are not disk encryption. Restrict local device access and use an appropriate encrypted backup destination.

## Who Can Do What

| Operation | Nurse | Administrator |
| --- | --- | --- |
| Read patient records, reports, retained photos and correction history | Yes | Yes |
| Create/update profiles; record punctures, skin alerts and recovery | Yes | Yes |
| Set patient dosage and next-appointment preferences | Yes | Yes |
| Change shared Keep Calibration setting | Yes | Yes |
| Change the demonstration clock | No | Yes |
| Correct an individual puncture or skin record with a reason | No | Yes |
| Delete an individual puncture/skin record from active use with a reason | No | Yes |
| Permanently delete unused photos or a complete patient | No | Yes |
| Create accounts, delete nurse accounts, view installation audit, export complete backup | No | Yes |

There is no per-patient assignment boundary: signed-in accounts in an installation share its patients. Every mutation still needs CSRF validation and, for patient records, the current patient version. A stale window must refresh before saving.

## Historical Access

- **Patient Record** lists active and inactive patients. Search by the user-facing patient ID or name.
- Month/Year/Total views and site filters provide longitudinal dosage and skin-episode summaries. Dates follow JST and the application clock; future clinical records are excluded from current graphs.
- **Photo History** retains source photographs. A selected historical date shows the alerts active at that time, projected on that photo’s saved alignment and site layout.
- Historical views use the latest corrected facts plus observation, recovery and deletion timestamps. They are not a forensic reconstruction of every screen or draft as it appeared in the past. Correction history separately exposes original and revised values.
- **Manage Records → Include Deleted Entries** retains access to individually deleted observations. **Correction History → View Changes** shows changed values, reason, actor and time.
- **Audit Trail** shows the latest 200 entries in the interface. Older audit entries remain in SQLite and complete backups; the limit is a display limit, not deletion.

## Creation And Correction

Completed punctures are created in the patient workspace. Historical entry requires an explanation and keeps screening conflicts as warnings. A saved dosage preset does not create a puncture or graph point until the puncture is saved.

Administrator corrections update the current record and store the complete before/after record in `record_revisions` in the same transaction. Corrections also update the patient version and audit trail. Puncture changes refresh the next appointment and current dosage default when applicable. Geometry edits use the original source photo’s saved layout, and affected rule warnings are recalculated. Original recorder and recorded time remain separate from the correcting administrator.

Changing an earlier dosage does not silently rewrite comparison statements already saved on later punctures. Each later record retains its original comparison rate; its table shows that comparison explicitly. Reports use the current corrected numerical rates.

## Deletion And Retention

- **Individual puncture/skin record:** logical deletion stores actor, time and reason. Current screening and graphs exclude it; the original row and revisions remain. This is not permanent erasure. There is no restore button; an administrator can add a corrected historical entry when needed.
- **Referenced photo:** retained even if its linked records were logically deleted, so their source remains available. Saved alignment and layout stay locked.
- **Unused photo:** an administrator can permanently delete it with a reason. Database removal is committed before physical cleanup; failed file removals are queued for retry.
- **Complete patient:** administrator-only permanent deletion requires the exact patient code. It removes the profile, preferences, sites, photos, punctures, skin observations, reviews, appointment and record revisions. Audit records retain the patient code and deletion summary. An old audit link shows “Deleted Patient” instead of linking to a different patient.
- **Nurse account:** administrator-only deletion requires its username. All that nurse’s sessions and login account are removed. Existing records retain their recorded display name. Administrator accounts cannot be deleted through this action.
- **Previous exports/backups:** never silently removed by any application deletion. A restored backup can reintroduce data that was later deleted. Manage exported copies and retention separately.

The local audit is not tamper-proof against someone who can modify SQLite files. User display names are retained strings; deleting or recreating an account does not establish cryptographically signed identity.

## Backup And Restore

1. Download **Settings & Data → Download Complete Backup**, or run `python manage.py backup`.
2. Keep the database and its corresponding photo set together. CSV alone cannot restore the installation.
3. To restore, stop the server, preserve the current `data` folder, then replace it with the complete `data` folder from one backup. Do not merge unrelated database and photo sets.
4. Start the server and sign in again. Restored sessions are deliberately invalidated.
5. Run `python manage.py check` to verify database integrity and photo presence.

## Upgrade To Schema Version 2

Startup adds patient preference fields, nullable dosage columns, ellipse dimensions, deletion fields, the patient code on audit entries and `record_revisions`. Older punctures keep **unknown dosage** rather than receiving invented values. Existing circles become equal width/height (`2 × radius`), preserving their geometry. Earlier combined pain/tenderness observations retain a legacy combined label.

This upgrade enables Keep Calibration once, as requested. Subsequent user changes persist across restarts and backups. Existing photo layouts and clinical timestamps remain. Keep a complete backup before replacing application files; older application versions do not support the upgraded schema.
