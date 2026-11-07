#!/usr/bin/env python3
"""Independent output checks, including distance and targeted-review reconciliation."""
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def main():
    cams=read(ROOT/'data/raw/cctv_info.csv')
    flags=read(ROOT/'data/processed/cctv_campus_flags.csv')
    matches=read(ROOT/'data/processed/camera_institution_matches.csv')
    institutions=read(ROOT/'data/processed/institutions_clean.csv')
    reviews=read(ROOT/'reports/camera_review.csv')
    baseline=read(ROOT/'data/reference/pre_review_camera_flags.csv')
    counts=json.loads((ROOT/'reports/summary.json').read_text())
    manifest=json.loads((ROOT/'reports/run_manifest.json').read_text())
    for p,h in manifest['input_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,('Source changed after run',p)
    assert len(flags)==len(cams)==len({r['camera_id'] for r in flags})==100
    assert {r['camera_id'] for r in flags}=={r['camera_id'] for r in cams}
    assert len(institutions)==len({r['institution_id'] for r in institutions})
    assert len(matches)==len({(r['camera_id'],r['institution_id']) for r in matches})
    assert counts['candidate_records']==counts['institutions']+counts['merged_records']+counts['rejected_records']+counts['campus_components_collapsed']
    lookup={r['institution_id']:r for r in institutions};camera_lookup={r['camera_id']:r for r in cams}
    max_delta=0
    for m in matches:
        c=camera_lookup[m['camera_id']];i=lookup[m['institution_id']]
        a,b=math.radians(float(c['latitude'])),math.radians(float(i['latitude']))
        dlon=math.radians(float(c['longitude'])-float(i['longitude']))
        d=6371008.8*math.acos(max(-1,min(1,math.sin(a)*math.sin(b)+math.cos(a)*math.cos(b)*math.cos(dlon))))
        assert d<=1500.001
        delta=abs(d-float(m['distance_m']));assert delta<.01
        max_delta=max(max_delta,delta)
    for f in flags:
        ms=[m for m in matches if m['camera_id']==f['camera_id']]
        assert len(ms)==int(f['institutions_within_radius'])
        assert bool(ms)==(f['near_any_education']=='True')
        for field,kinds in [('near_school',('school',)),('near_university_college',('university','college'))]:
            assert any(m['institution_type'] in kinds for m in ms)==(f[field]=='True')
    original_no_match={r['camera_id'] for r in baseline if r['near_university_college']=='False'}
    assert len(original_no_match)==13
    assert {r['camera_id'] for r in reviews}==original_no_match|{'224','225'}
    assert len(reviews)==15
    by_id={r['camera_id']:r for r in flags}
    for r in reviews:
        assert r['after_near_university_college']==by_id[r['camera_id']]['near_university_college']
        assert r['review_status']!='not_targeted'
        if r['after_near_university_college']=='False' and r['within_radius_of_mapped_boundary']=='True':
            assert r['university_comparison_status']=='boundary_sensitive_do_not_use_as_unexposed'
    # A second run must preserve all substantive generated outputs.
    paths=list((ROOT/'data/processed').glob('*.csv'))+[ROOT/'reports/camera_review.csv',ROOT/'reports/campus_proximity_map.html',ROOT/'reports/quality_report.md',ROOT/'reports/finalization_review.md']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    subprocess.run(['python3',str(ROOT/'scripts/campus_pipeline.py')],check=True,capture_output=True)
    assert hashes=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    tests=subprocess.run(['python3','-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],check=True,capture_output=True,text=True)
    report=dict(camera_rows=100,source_hashes_match_manifest=True,unique_camera_ids=True,unique_match_pairs=True,
                source_camera_ids_preserved=True,candidate_record_reconciliation=True,all_flags_reconcile_to_match_table=True,
                all_matched_distances_independently_checked=True,max_distance_difference_m=max_delta,
                targeted_camera_reviews=15,original_no_match_reviews=13,review_flags_reconcile=True,
                repeat_run_same_csv_map_report_hashes=True,unit_tests_passed=10,
                browser_visual_preview='blocked_by_saved_permission_or_managed_policy',output_sha256=hashes)
    (ROOT/'reports/validation_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='output_sha256'},indent=2))


if __name__=='__main__':main()
