# Campus proximity quality report

## Results

- Cameras: 100; near an educational institution: 100.
- Near a school: 100; near a university/college: 94.
- No match in catalog: 0; invalid camera coordinates: 0.
- Camera–institution pairs within 1500 m: 2306.
- Input institution records: 1285; retained after merging: 1154; merged: 96; internal campus components collapsed: 35; invalid coordinates rejected: 0.
- Candidate sources: {"OBEC": 159, "BMA": 437, "OSM": 688, "OFFICIAL": 1}.
- Institution types after merging: {"school": 1055, "university": 48, "college": 51}.
- Camera–institution pairs within 100 m either side of cutoff: 554. See borderline_matches.csv, including outside-radius cases.

## Method

Inclusive 1500 m straight-line cutoff on unrounded Haversine distances. Supplied school points retain source coordinates; OSM ways/relations use bounding-box centres and nodes use their mapped point. Points are not verified campus gates or boundaries. Nearest means nearest within the cached catalog, which is spatially bounded for OSM. Round distances only for display.

Reviewed corrections and an official-site college addition are applied from reference_review.json. The Royal Thai Navy College of Nursing reference is the viewport centre of the official contact-page embedded map, explicitly labelled approximate rather than a verified pin or entrance. Primary near flags still use the agreed point-distance rule. Mapped campus-boundary distances in the 15-row targeted review are an auxiliary sensitivity check, calculated in a local tangent plane; they never silently replace the primary point rule.

The 437 BMA records omitted by the team's name-column mapping were recovered using explicit workbook fields. Existing 159 OBEC records were reused. Exact normalized names or mapped aliases within 250 m and compatible education types are merged conservatively, preserving source evidence. Same-name campuses farther apart remain separate. Faculty/building records inside a mapped university campus are collapsed into the campus, with evidence in campus_components.csv. Standalone faculties outside a mapped parent boundary remain location records and require review. Alternative-name or unnamed map objects may remain duplicates; this can inflate institution counts. No match means no catalog match, not geographic absence.

## Coverage and review

OSM supplementary data available: True. Open-map results cover schools/universities/colleges inside the padded camera bounding box; every camera's 1.5 km circle is inside that query envelope. The public catalog is not certified complete. School source coordinate-role accuracy and current operation are unverified. BMA records carry academic-year 2568. The raw OPEC file has no coordinates and remains unresolved rather than being assigned invented positions.

All camera flags are computed provisional proximity classifications. All rows retain review_required=True because reference points are not verified entrances. No claim of exhaustive manual verification is made. Inspect the map, borderline pairs, nearby alternative names and source links before interpreting exposure or institution counts. Positive evidence can be used as proximity to a recorded institution; false values only describe the cached reference. Offline map has a coordinate grid; optional online street tiles and external source links require internet.

The generated map's JavaScript syntax was checked. A saved browser permission or managed policy blocked local-origin access even after the user requested the preview, so visual browser verification remains unperformed. Primary-site identity/address checks and unresolved cases are recorded in data/reference/verification_notes.json; they do not certify the exact mapped coordinates. Targeted reviews of the original 13 university/college no-match cameras plus school matches 224 and 225 are in reports/camera_review.csv.

The supplied 19 calendar events are Chula BBA International only and have not been attached to schools. Image timestamps, term status, actual commuting paths and traffic outcomes are outside this camera-level task. No image ZIP was downloaded.

## Analysis implication

Every camera is near at least one recorded educational institution, so the 1.5 km binary flag provides no unexposed comparison group in this sample. Use institution type, continuous distance or a separately justified design downstream.

## Sources

- Camera metadata: supplied Google Drive cctv_info.csv; see run_manifest.json.
- OBEC and BMA school locations: team handoff, source paths and source years preserved in institution_provenance.csv. A specific original BMA download URL was not supplied and is not invented.
- OpenStreetMap contributors: https://www.openstreetmap.org/copyright ; ODbL https://opendatacommons.org/licenses/odbl/1-0/ . Supplementary snapshot and exact query are cached. Review licenses before redistributing the combined reference.
