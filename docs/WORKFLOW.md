# SiteCare demonstration workflow

This guide describes the prototype interface, not a clinical procedure. Use fictional data to evaluate it. Confirm any proposed clinical workflow with the responsible team.

## Patient identification and first visit

Create a patient with a unique ID, minimal display label, therapy/protocol label, initial due date/time, and any appropriate notes. The initial due date anchors appointment suggestions until an actual puncture is recorded. Dates in the interface use Japan Standard Time.

Open the patient and upload a JPEG/PNG abdominal photograph. The uploader requires a capture date/time and confirmation of authorized image use. Actual patient photographs are not included in the distribution.

The initial 14 positions reproduce the numbering arrangement of the supplied rotation diagram, not physical dimensions taken from the printed page. The patient's site layout can be adjusted before historical records are attached. Once records exist, the layout is locked to avoid changing the meaning of historical site numbers.

### Editing or restoring the 14-site layout

With an editable photo open, choose **Edit 14 Sites** and drag the numbered circles. The controls below the map are:

- **Save 14-Site Layout** (red): save the dragged positions. The server checks numbering, the 5 cm navel distance, and 2.5 cm spacing between sites.
- **Default Layout** (blue): immediately restore and save all 14 original positions. No additional Save click is needed. Photo alignment and its unsaved adjustments are kept.
- **Discard Changes** (yellow): restore the last saved layout and photo alignment, discarding unsaved edits. This does not undo a layout already saved by either of the other buttons.

Default Layout uses the same original coordinates as a newly created patient, records the change in the audit trail, and refreshes the map. These actions remain available only before a puncture or skin observation locks the layout. **Verify & Save Alignment** continues to save photo alignment separately.

## Photo alignment and calibration

Use Navel to locate the navel. Move the photograph beneath the layer and adjust its scale and rotation. Use a visible known-length ruler segment for calibration; in the included synthetic image, the 0-to-10 segment is 10 cm. Review all alignment confirmations and save. Unsaved or unverified alignment is not sufficient for procedure recording.

Viewing zoom is separate from mapping scale. Increasing screen zoom should not change stored centimetre coordinates. Every new photograph starts unverified, while historical patient-relative points and their restrictions are retained.

Manual alignment does not correct skin deformation, perspective, abdominal curvature, or posture changes. It is an approximate two-dimensional coordinate system. Confirm actual distances and suitability independently at the bedside. Do not interpret a successful software calibration as a verified physical measurement.

## Review sites and mark a point

Tap any numbered position to see details. Green means the configured rule checks passed; blue means resting; red means a blocking issue; gray means further photo verification is required. More than one restriction may apply, and a blocking issue can take precedence over the rest color. Review the listed reasons rather than relying only on color.

The prototype proposes up to three numbered candidates in rotation order after the latest applicable puncture, skipping ineligible sites and wrapping after site 14. It does not promise that there will always be three. Resolved skin observations do not lower a site's priority. It does not diagnose or examine skin.

Use Exact point to select the actual location. The program retains its coordinates and assigns the nearest numbered site. Exact points and numbered centers are therefore distinct records.

## Document a completed puncture

After the actual procedure has been completed under the appropriate clinical workflow, record its actual date/time and point, confirm identity and documentation checks, and save. For demonstration, use only a fictional event.

A saved event restricts its assigned numbered site for 12 days from the recorded time. It also restricts any candidate less than 2.5 cm from a puncture recorded within the preceding 12 days, even if the candidate has a different number. The navel-exclusion check requires at least 5 cm from the mapped navel. These values implement the supplied project brief and need protocol confirmation before a clinical pilot.

The next due date/time becomes the latest actual puncture timestamp plus 72 hours. An alignment referenced by saved records is locked. New photographs can still be uploaded and aligned at subsequent visits.

Historical documentation is a separate action. It exists to preserve factual records of previous events, not to override restrictions prospectively. Incorrect puncture entries can be voided by an administrator with a reason; the original entry remains in history. Never void a genuine event to make a resting site appear available.

## Record skin concerns

Choose Draw alert and drag from an area's center toward its edge. Select observation type(s), severity as observed by the nurse, date/time, and notes. The program does not automatically assess severity or diagnose a complication.

Available observation types include redness, hardening, pain/tenderness, swelling, bruising, leakage, and other/avoid area. Alerts are circular; overlapping circles can cover a more irregular region. This version does not provide polygon/freehand contours.

An unresolved alert remains blocking without an automatic time expiry. Record recovery only after the required bedside assessment confirms full recovery. Independent rest and other restrictions still apply afterward.

Resolving skin alerts clears their restrictions immediately. Repeated observations do not impose an additional recurrence-review hold. Separate rest, active-alert, photo, and geometry checks still apply.

## History and appointments

The workspace's right-side information includes site status, selected-point details, history, skin observations, and a calendar. The separate Appointments page shows near-term visits and future three-day projections.

A suggested appointment is not a confirmed booking. Rescheduling does not change the original due date or erase an overdue warning. Projection entries are estimates, not evidence that a procedure occurred. Confirmed dates are still local application records; there is no external calendar integration or automatic message delivery.

## End of session

Finish saving, check the patient's history, sign out, and stop the local server when finished. Keep regular database-and-photo backups. Do not share a populated database or patient photographs when asking for technical support.

## Demonstration date and candidate order

The date bar at the top of every signed-in page shows the current application time in JST. Administrators can select **Change date**, choose **Choose demonstration date**, enter a date and time, then **Apply date**. Time continues advancing from that point. Select **Use system date** in the same dialog to return to real time. The choice applies to all patients/windows and persists after restart.

Countdowns, candidates, photo freshness, appointment due/overdue calculations, calendars, and new-entry defaults all follow this clock. Existing saved timestamps are retained. A photo older than 24 hours at the selected time requires a new calibrated visit photo.

Candidates follow numbered rotation after the most recent applicable puncture, skipping currently unavailable sites. A recovered site returns to its numbered position immediately: 3, 4, 6 becomes 3, 4, 5 when site 5 becomes eligible. Past resolved alerts do not reduce its priority.

## Delete a patient (administrator only)

1. Open the patient workspace and select **Profile**.
2. Select **Delete patient…** at the bottom of the dialog.
3. Check the patient name/ID and record counts, then type the exact patient ID.
4. Optionally enter a reason and select **Delete permanently**.

This removes the profile, photos, puncture history, skin observations, reviews, layout, and appointment, then returns to the patient list. Audit records and existing backup archives remain. Deletion cannot be undone in the app. If a photo file is locked, the app reports that cleanup is pending and retries it when SiteCare restarts.
