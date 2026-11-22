# Working on this project

The current project is the CCTV-failure analysis at the repository root. Start with README.md.

```sh
python -m pip install -r requirements.txt
python -m unittest -v test_analysis
python run.py
```

- Keep the working code in run.py (loading/calculations) and report.py (charts/PDF). Avoid adding a framework or another pipeline.
- Use the supplied inputs. Recreating this report does not require raw images, YOLO inference, an API key or a GPU.
- Preserve failure labels, image paths, quality eligibility, source hashes and missing counts. An unavailable picture is not zero traffic.
- Whole-image vehicle counts are sightings, not unique trips, speed or network bitrate. The report describes associations and possible causes, not confirmed hardware failures.
- Timing and camera/district rankings use the whole week. The matched pre-freeze traffic comparison has its own documented eligibility rules; do not silently change them.
- The seed, camera-level weighting, observation intervals and small sample limits matter. Keep numbers calculated from the inputs rather than hardcoded into the report.
- Run the tests and a full report rebuild for calculation changes. Inspect the PDF for report/layout changes. Preserve existing reviewed results unless updating them intentionally.
- If publishing a new submission, regenerate submission_manifest.json after reviewing outputs. Exclude the manifest itself, caches, environments and temporary rebuilds. Do not update hashes merely to hide changed results.
- The previous school-traffic submission is preserved in archive/traffic-study-20261122. It is not part of the active workflow; preserve it unless the user asks for changes there.
- Use a separate branch. Target Panyawat-Phothiphanich/bangkok-cctv-campus-proximity explicitly in GitHub CLI commands. Publish/merge only within the user's request; do not message teammates automatically.
