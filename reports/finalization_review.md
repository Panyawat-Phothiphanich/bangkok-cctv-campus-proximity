# Targeted finalization review

## Outcome

- School identity/address review completed for cameras 224 and 225. The official school contact address matches the mapped school address, and the official news feed has 2026 school activity. Canonical Thai spelling was corrected. Original point distances are retained: approximately 1,261 m and 1,245 m. This supports the recorded school match without claiming a surveyed entrance coordinate.
- Reviewed all 13 original university/college no-match cameras. 7 became positive after reference corrections: 1103, 26, 158, 1195, 251, 1076, 36.
- 6 retain no university/college point match: 124, 125, 529, 1804, 123, 938.
- 4 of those are within 1.5 km of a mapped university/college outline: 124, 125, 123, 938. They must not be treated as unexposed solely because a campus centre is farther away.
- Camera 529 remains just outside the closest mapped college outline (approximately 1,572 m), so it remains sensitive to location accuracy. Camera 1804 has no qualifying college found in the reviewed reference; nearest point is approximately 2,522 m and nearest mapped outline approximately 2,472 m. This is not certified absence of all institutions.

## Changes and evidence

The previously omitted Royal Thai Navy College of Nursing was added from its official contact address and map reference. Its coordinate role is an embedded-map viewport centre, explicitly approximate. Six Thonburi cameras gain a point match. Don Bosco and three other explicitly verified technological-college records were reclassified from school to college; no coordinate was moved for these type corrections. Official sources and the full correction history are in reference_review.json, verification_notes.json and reference_corrections.csv.

The expanded named-feature search retrieved 249 map objects for coverage review. Bus stops, shops, sports grounds and buildings containing university names were not automatically promoted to institutions. Source completeness remains unverified, so no camera is certified as a causal control.

## Detailed review

See camera_review.csv for one row per targeted camera, before/after flags, nearest points, nearest mapped outlines and comparison warnings. The main camera CSV includes the same review status fields. The primary inclusive 1,500 m point rule is unchanged; boundary distance is a separate sensitivity check.

## Visual map check

Not completed: the browser tool reports a saved permission or managed policy denying access to http://127.0.0.1:8765 even after the user requested a preview. No alternate browser route or security-policy workaround was attempted. The map JavaScript is syntax-checked, but this does not verify rendering. Open campus_proximity_map.html directly to inspect the 15-camera review filter, the remaining university/college no-match filter, and camera details.
