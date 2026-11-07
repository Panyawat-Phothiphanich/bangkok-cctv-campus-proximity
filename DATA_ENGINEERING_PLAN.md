# Local CCTV campus-proximity implementation plan

Status: implemented and executed locally. The final run has 100 camera rows, 100 near a recorded school, and 94 near a university/college at the inclusive 1.5 km cutoff. CSVs, map, source evidence and validation checks are delivered. Flags remain provisional source-point classifications; see reports/quality_report.md.

## Confirmed objective

Deliver one row for each of the 100 supplied CCTV cameras indicating proximity to universities, colleges and schools within an inclusive 1,500 m straight-line radius. Execute locally and reuse the supplied material first. Complete missing location coverage independently rather than waiting for the web scraping team.

The output supports downstream campus-commute traffic analysis. Proximity alone does not establish a commuting effect or make unmatched cameras valid controls.

## What the handoff actually contains

Input package: /Users/ayeeaindraykyawkhaung/Downloads/Project-Webscraping/

| Input | Inspection result | Decision |
|---|---|---|
| data/school_coordinates.csv | 159 OBEC school rows, 159 unique IDs/names, numeric latitude/longitude in valid global ranges; no repeated coordinate pairs. | Reuse as the existing school reference after spatial review. Numeric validity does not prove exact location accuracy. |
| raw_data/bma_schools.xlsx | 437 school records after two header rows, 437 unique IDs, all 437 with numeric coordinates in valid ranges. Academic-year field is 2568. | Recover these records from the workbook. Preserve source year and investigate current operation where relevant. |
| data/school_directory.csv and data/school_names.csv | The same 159 OBEC schools, represented differently. | Treat as supporting views, not additional institutions. |
| data/schools_needing_coordinates.csv | Header only, zero records. | This means the 159 exported schools have coordinates, not that the full education catalog is complete. |
| raw_data/opec_school.csv | 159 records of names, IDs and historical enrolment fields; no coordinate columns. | Retain as supplementary input. Verify provenance and institution type before enrichment; do not fabricate locations or use enrolment as current commuting demand. |
| data/academic_calendar.csv | 19 events, all for Chulalongkorn University BBA International, with date text in 2026–2027. | Preserve as a programme-specific optional source. It is not a school-wide calendar or required for proximity flags. |
| scripts/03_academic_calendar.py | Expects raw_data/calendar_sources/*.csv, a directory absent from this package, and a schema different from data/academic_calendar.csv. | Do not run as if it completes the provided calendar. No calendar repair is required for the current task. |

The OBEC and BMA inputs provide 596 candidate school records before cross-source deduplication. This is not yet a count of distinct verified institutions or a complete campus catalog. No university/college location table is supplied.

## Why usable school data was missed

Inspection of scripts/01_school_names.py found that its name aliases omit the workbook header ชื่อสถานศึกษา, and its other aliases also miss fields such as รหัสสถานศึกษา and ลองจิจูด. Consequently the BMA workbook is not successfully represented in the supplied 159-row output. The script also expects opec_schools.csv, whereas the supplied file is opec_school.csv, and lacks the idschool alias.

Implement source-specific import adapters in our workspace. Preserve the downloaded team package unchanged. Do not blindly rerun scripts with top-level execution or outputs pointing into the source package.

## Implementation sequence

### 1. Preserve and validate inputs

- Copy required source files into a local raw-input area and record original paths, hashes, source IDs/URLs when available and retrieval dates.
- Retrieve the existing CCTV metadata CSV from Drive; validate expected camera count, unique IDs, coordinates and label inconsistencies.
- Import 159 OBEC records and recover 437 BMA records with explicit field mappings and correct handling of the two header rows.
- Standardize names/whitespace and missing values, retain Thai labels and source-qualified IDs, and assign stable internal institution IDs.
- Deduplicate using source ID evidence, normalized names, address and spatial agreement. Do not merge separate campuses just because names match.

### 2. Complete location coverage

- Start with the recovered supplied coordinates; do not recollect them wholesale.
- Supplement missing universities/colleges and school coverage using a targeted open-map lookup within 1.5 km of the camera locations. Include institutions across administrative boundaries.
- Verify ambiguous matches, campus identity, duplicated map representations and threshold-sensitive locations against official institution information where available.
- Treat unlocated supplementary records explicitly as unresolved. Coordinate-free enrolment rows must not silently count as spatial matches.
- Save the supplement, source evidence and collection date so calculation reruns can work from cached references.

### 3. Define and calculate proximity

Use the supplied institution location points for the initial calculation. Their role is not established as a gate or campus centre, so set point_role=source_point_unverified unless evidence establishes otherwise. For supplemented points, record the actual role. This replaces the earlier proposed entrance-only rule so existing usable data can be retained honestly.

- Record coordinate method/role on every match. Approximate source-point proximity is not road distance or distance to a verified campus boundary.
- Calculate distances in metres using a documented geodesic method or Haversine approximation, with finite-value and coordinate-range guards.
- Apply the inclusive 1,500 m cutoff to unrounded distances.
- Produce all qualifying camera–institution pairs. Keep the nearest institution and distinct-institution count in the camera summary.
- Separate near_school, near_university_college and near_any_education flags so downstream analysis can distinguish institution types. Use null for an unresolved type-specific result when coverage is inadequate.
- Preserve every camera. Invalid camera coordinates produce unknown status. Positive matches remain evidence of proximity even if broader reference coverage is incomplete. A no-match value means no match in the documented catalog, not proof of absence.
- Store reference_coverage_status and match_review_status alongside the flags. A documented borderline review band (initially 100 m either side of the cutoff) triggers review rather than changing the 1,500 m rule.

### 4. Review and validate

- Generate an HTML map showing cameras, institution points, source/type labels and proximity circles.
- Review close-to-cutoff matches, suspicious coordinates, duplicates and a sample of no-match cameras for missing institutions.
- Reconcile the 596 pre-dedup school input rows with imported, merged, unresolved and retained records; report supplemental sources separately.
- Check that the final camera summary contains one row per source camera and that all positive matches have distances and source evidence.
- Test same-location distance, a known coordinate pair, inclusive cutoff logic, invalid coordinates, multiple institutions and cross-source duplicates.
- Confirm a left join on camera_id does not multiply downstream traffic observations, and a repeat run with unchanged inputs/configuration gives stable substantive results.

### 5. Publish the local handoff

| Deliverable | Format and purpose |
|---|---|
| cctv_campus_flags.csv | Main table: camera ID/location/coordinates, near_any_education, near_school, near_university_college, nearest institution/name/type/distance, count within 1.5 km, radius, reference coverage and review status. |
| camera_institution_matches.csv | Every distinct camera–institution pair within 1.5 km, with distance, coordinate role and provenance. |
| institutions_clean.csv | Deduplicated reference with original IDs, normalized fields, source year, source paths/URLs, location role and unresolved issues. |
| campus_proximity_map.html | Browser-readable map for reviewing cameras, institutions and matches. |
| quality_report.md | Input reconciliation, near/no-match/unknown counts, excluded or unresolved records, map review decisions and coverage limitations. |
| run_manifest.json | Source hashes, reference/config versions, source refresh dates and run metadata. |
| Python script, config.json and README.md | One-command calculation, configurable local paths, data dictionary and separate explicit reference-refresh instructions. |

Use UTF-8 CSVs compatible with Thai text and common spreadsheet tools. Keep counts/flags and null conventions documented. No database, GPU or raw-image processing is needed for this scope.

## Calendar decision

Do not delay spatial flagging to finish script 3. Preserve the 19 supplied events as raw programme-specific evidence. If temporal calendar analysis is later requested, normalize dates, verify programme/campus applicability and overlap with actual CCTV capture dates, and retain unknown status for other institutions. Never apply Chula BBA term dates to schools or other university programmes. Generic morning/afternoon periods may be labelled analysis windows, but cannot be presented as verified class schedules.

## Execution order and dependency

1. Recover and clean the supplied school data; validate CCTV metadata.
2. Supplement the missing university/college and school locations in the camera study area.
3. Calculate the 1.5 km flags and all matches.
4. Review the map and unresolved/borderline cases.
5. Deliver the CSVs, map, report and reproducible local pipeline.

No further handoff from the web scraping team is required to start or complete this proximity task. Remaining work is local import repair, targeted location enrichment, distance calculation and quality review. Executed result: 1,285 candidate records became 1,154 retained reference entities after 96 duplicate merges and collapsing 35 internal campus components; 2,306 within-radius camera–institution pairs were exported. Ten unit tests and output/repeat-run consistency checks passed. The image ZIP is unnecessary for this task.


## Targeted finalization review

Reviewed the original 13 university/college no-match cameras and school matches 224/225. Seven no-matches became positive after correcting college types and adding the Royal Thai Navy College of Nursing from its official contact-page map reference. Four remaining point no-matches have mapped campus edges within 1.5 km, one is near the cutoff, and one has no qualifying institution found in the reviewed catalog. See reports/finalization_review.md and reports/camera_review.csv. Visual map review remains blocked by a saved browser permission or managed policy.
