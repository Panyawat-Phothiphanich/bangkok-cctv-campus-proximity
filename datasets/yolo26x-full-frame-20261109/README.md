# Bangkok CCTV — completed YOLO26x full-image dataset

**61,319 images · 100 cameras · 67 columns · 25–31 August 2026 · Asia/Bangkok**

All images were processed successfully. This release counts the entire image with no road boundaries. Classes: car, motorcycle, bus, truck and bicycle.

## Download

- [Full CSV, original export](https://github.com/Panyawat-Phothiphanich/bangkok-cctv-campus-proximity/releases/download/yolo26x-full-frame-20261109/traffic_full_frame.csv)
- [Full CSV, gzip-compressed](https://github.com/Panyawat-Phothiphanich/bangkok-cctv-campus-proximity/releases/download/yolo26x-full-frame-20261109/traffic_full_frame.csv.gz)
- [Parquet, recommended for Python](https://github.com/Panyawat-Phothiphanich/bangkok-cctv-campus-proximity/releases/download/yolo26x-full-frame-20261109/traffic_full_frame.parquet)
- [Complete teammate bundle: CSV, Parquet, guide, dictionary, summaries and plots](https://github.com/Panyawat-Phothiphanich/bangkok-cctv-campus-proximity/releases/download/yolo26x-full-frame-20261109/Bangkok_CCTV_YOLO26x_Full_Image_20261109.zip)
- [Release page and all files](https://github.com/Panyawat-Phothiphanich/bangkok-cctv-campus-proximity/releases/tag/yolo26x-full-frame-20261109)

The CSV is about 77 MB. The repository's `preview_200_images.csv` is a **200-row preview**, not the full dataset. The full files are Release downloads.

## Start analysing

```python
import pandas as pd

# Run after downloading the CSV or use the gzip download URL directly.
df = pd.read_csv("traffic_full_frame.csv", dtype={"camera_id": "string"})
df["observed_at_local"] = pd.to_datetime(df["observed_at_utc"], utc=True).dt.tz_convert("Asia/Bangkok")
analysis = df.loc[df["eligible_temporal"]].copy()
print(len(df), len(analysis))  # 61319, 59834
```

Parquet preserves nullable integers, timestamps and list fields:

```python
df = pd.read_parquet("traffic_full_frame.parquet")
analysis = df.loc[df["eligible_temporal"]].copy()
```

For a direct compressed CSV download in pandas:

```python
df = pd.read_csv("https://github.com/Panyawat-Phothiphanich/bangkok-cctv-campus-proximity/releases/download/yolo26x-full-frame-20261109/traffic_full_frame.csv.gz", dtype={"camera_id": "string"})
```

## Which counts should I use?

| Fields | Meaning |
|---|---|
| `raw_car_count`, `raw_motorcycle_count`, `raw_bus_count`, `raw_truck_count`, `raw_bicycle_count`, `raw_vehicle_count` | Predictions for every successfully inferred image, including flagged imagery. |
| `car_count`, `motorcycle_count`, `bus_count`, `truck_count`, `bicycle_count`, `vehicle_count` | Same counts, set to null when quality/acquisition/inference rules exclude the row. |
| `eligible_temporal` | Recommended filter for preliminary time-pattern analysis. |
| `quality_status`, `quality_flags`, `exclusion_reasons` | Reasons an image needs review; automatic quality decisions remain provisional. |

A count of zero means the model counted zero vehicles. A null analysis count means the row is excluded. **Do not fill excluded counts with zero.** List fields such as `quality_flags` are JSON arrays in the CSV.

The complete [67-column dictionary](data_dictionary.csv) describes every field and its null count.

## Completed totals

| Class | Raw sightings across all snapshots |
|---|---:|
| Car | 435,552 |
| Motorcycle | 67,412 |
| Bus | 15,434 |
| Truck | 48,958 |
| Bicycle | 797 |
| **Total** | **568,153** |

59,834 rows are usable for preliminary temporal analysis. 1,485 rows are quality-flagged and retain their raw predictions. All 61,319 have successful inference.

## Interpretation and limits

- These are visible vehicle sightings per snapshot. Repeated images can show the same vehicle. Counts are not unique journeys, traffic flow, speed, passenger demand or congestion delay.
- Whole-image counting includes parked vehicles, every visible road direction/level and distant vehicles. Camera viewpoint and visibility affect the counts. Do not sum cameras as unique city traffic.
- The model is YOLO26x at input size 960, with class-agnostic suppression, retention floor 0.10 and counting threshold 0.25. Thresholds are not accuracy percentages. Full-image precision/recall have not been measured against independent human labels.
- The week is 25–31 August 2026, approximately 06:00–21:00 Bangkok time. Coverage varies. Check hourly source/usable coverage; 27 August has a substantial early-morning acquisition gap. Most 21:00 hours contain only an endpoint snapshot.
- Timestamps use source collection time from filenames; they are not exact camera exposure timestamps.
- Supplied place labels and coordinates are retained. English names have known errors: cameras 1188 and 529 are examples where Thai metadata/filenames indicate Phutthamonthon Sai 2 but the English label names a central-Bangkok location. Verify sites before spatial claims. `eligible_temporal` does not mean the location has been verified.
- Raw source images, model weights, inference caches and the per-box detection table are not part of this teammate package. `source_path` is an archive-relative reference, not a bundled image or a path on your computer.
- This is the **completed full-image run**. Earlier road-boundary results and any batch-processing handoff in the repository are separate products.

## Included companion files

The ZIP includes `summary.json`, `completion_verification.json`, `comparison_summary.csv`, `camera_summary.csv`, `coverage_by_camera_hour.csv`, `camera_day_hour.csv`, `hourly_profiles.csv`, and `plots/`. The comparison uses 6,694 matching images from the previous boundary-count dataset; it measures count differences, not accuracy. Bicycles are excluded from that four-class comparison; fresh five-class suppression can also affect differences.

## Provenance and verification

Derived academic-project outputs from the supplied Bangkok CCTV archive. The run identifier is `yolo26x_all_20261109`. `manifest.json` contains file sizes and SHA256 checksums; `SHA256SUMS.txt` can verify the downloads. The published CSV and Parquet are byte-identical to the completed local exports. Source image archive SHA256: `2a088ff18129120d2b2b81b270b3cb879328ba9ad9ccb69c8fb2b1febf88ce87`.

The files are frozen to this release tag. You can share this URL with teammates: **https://github.com/Panyawat-Phothiphanich/bangkok-cctv-campus-proximity/releases/tag/yolo26x-full-frame-20261109**.
