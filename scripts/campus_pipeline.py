#!/usr/bin/env python3
"""Reproducible local camera proximity pipeline; standard library only."""
import argparse
import csv
import hashlib
import html
import json
import math
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def valid_coords(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
        return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180
    except (TypeError, ValueError):
        return False


def distance(lat1, lon1, lat2, lon2):
    """Spherical Haversine distance in metres, using mean Earth radius."""
    a, b, c, d = map(math.radians, map(float, (lat1, lon1, lat2, lon2)))
    h = math.sin((c-a)/2)**2 + math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 6371008.8 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def near(distance_m, radius_m):
    return distance_m <= radius_m


def normal_name(name):
    name = unicodedata.normalize('NFKC', name).casefold()
    name = re.sub(r'^โรงเรียน\s*', '', name)
    return re.sub(r'[\s\-()（）.,]', '', name)


def read_bma(path):
    """Explicitly map the supplied two-header BMA workbook without Excel deps."""
    with zipfile.ZipFile(path) as z:
        strings = [''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        result = []
        for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('s:sheetData/s:row', NS)[2:]:
            values = {}
            for cell in row:
                value = cell.find('s:v', NS)
                value = value.text if value is not None else ''.join(cell.itertext())
                values[re.sub(r'\d', '', cell.get('r'))] = strings[int(value)] if cell.get('t') == 's' else value
            if values.get('A') and values.get('C'):
                result.append(values)
        return result


def candidate(source, source_id, name, lat, lon, kind, **extra):
    return dict(source=source, source_id=source_id, institution_name=name.strip(), latitude=lat,
                longitude=lon, institution_type=kind, point_role='source_point_unverified', **extra)


def polygon_rings(element):
    """Assemble closed OSM way segments; preserve inner rings separately."""
    members = ([dict(role='outer', geometry=element.get('geometry', []))] if element['type']=='way'
               else element.get('members', []))
    result = {'outer': [], 'inner': []}
    for role in result:
        segments = [[(p['lon'],p['lat']) for p in m.get('geometry', []) if p and 'lon' in p]
                    for m in members if m.get('role', '') in (('', 'outer') if role=='outer' else ('inner',))]
        segments = [s for s in segments if len(s)>1]
        while segments:
            chain=segments.pop(0)
            changed=True
            while chain[0]!=chain[-1] and changed:
                changed=False
                for j,s in enumerate(segments):
                    if chain[-1]==s[0]: chain+=s[1:]
                    elif chain[-1]==s[-1]: chain+=list(reversed(s))[1:]
                    elif chain[0]==s[-1]: chain=s[:-1]+chain
                    elif chain[0]==s[0]: chain=list(reversed(s))[:-1]+chain
                    else: continue
                    segments.pop(j);changed=True;break
            if len(chain)>=4 and chain[0]==chain[-1]: result[role].append(chain)
    return result


def in_ring(lat, lon, ring):
    inside=False
    for (x1,y1),(x2,y2) in zip(ring,ring[1:]):
        if (y1>lat)!=(y2>lat) and lon<(x2-x1)*(lat-y1)/(y2-y1)+x1:
            inside=not inside
    return inside


def within_campus(lat, lon, rings):
    return any(in_ring(lat,lon,r) for r in rings['outer']) and not any(in_ring(lat,lon,r) for r in rings['inner'])


def collapse_campus_components(rows, geometry_path):
    """Attach internal faculty/building points to enclosing mapped campuses."""
    if not geometry_path.exists(): return rows, []
    data=json.loads(geometry_path.read_text())
    if data.get('remark'): raise ValueError('Incomplete campus geometry response')
    geometries={f"{e['type']}/{e['id']}":e for e in data['elements']}
    parents=[]
    for r in rows:
        name=r['institution_name']
        is_root = ('มหาวิทยาลัย' in name or 'university' in name.lower()) and not name.startswith(('คณะ','สมาคม'))
        if r['source']=='OSM' and r['institution_type'] in ('university','college') and is_root:
            e=geometries.get(r['source_id'])
            if e and e['type']!='node':
                rings=polygon_rings(e)
                if rings['outer']:parents.append((r,rings))
    suppressed=[]; retained=[]
    for r in rows:
        name=r['institution_name']; en=r.get('name_en','')
        component=(name.startswith(('คณะ','อาคาร','สำนักวิทยาศาสตร์','ศูนย์เรียน','สมาคมนิสิตเก่า')) or
                   any(s in (name+' '+en).lower() for s in ('faculty of',' hall','building','central library',"salle d' expo")))
        matches=[p for p,g in parents if p['source_id']!=r['source_id'] and valid_coords(r['latitude'],r['longitude']) and
                 within_campus(float(r['latitude']),float(r['longitude']),g)] if component and r['source']=='OSM' else []
        if matches:
            parent=min(matches,key=lambda p:distance(p['latitude'],p['longitude'],r['latitude'],r['longitude']))
            suppressed.append(dict(source_id=r['source_id'],component_name=name,parent_source_id=parent['source_id'],
                                   parent_name=parent['institution_name'],rule='component_inside_mapped_campus'))
        else: retained.append(r)
    return retained,suppressed


def load_candidates(team, osm_path):
    rows = []
    for r in read_csv(team/'data/school_coordinates.csv'):
        rows.append(candidate('OBEC', r['school_id'], r['school_name'], r['latitude'], r['longitude'], 'school',
                              source_file='data/raw/webscraping/data/school_coordinates.csv', source_url='https://data.go.th/en/dataset/schooladdress',
                              source_year='', address=r['address'], official_url=''))
    for r in read_bma(team/'raw_data/bma_schools.xlsx'):
        rows.append(candidate('BMA', r['A'], r['C'], r.get('O'), r.get('P'), 'school',
                              source_file='data/raw/webscraping/raw_data/bma_schools.xlsx', source_url='', source_year=r.get('B',''),
                              address=' '.join(r.get(k,'') for k in ['E','F','G']), official_url=r.get('M','')))
    osm_loaded = False
    if osm_path.exists():
        d = json.loads(osm_path.read_text())
        if 'elements' not in d or d.get('remark'):
            raise ValueError('Incomplete OSM response: '+str(d.get('remark')))
        osm_loaded = True
        for r in d['elements']:
            t = r.get('tags', {})
            kind = t.get('amenity')
            if kind not in ('school', 'university', 'college'):
                continue
            # Former facilities should not become current proximity evidence.
            if any(t.get(k) in ('yes', 'true', '1') for k in ('disused','abandoned','demolished')):
                continue
            pos = r if r['type'] == 'node' else r.get('center', {})
            name = t.get('name:th') or t.get('name') or t.get('name:en') or ''
            ident = f"{r['type']}/{r['id']}"
            rows.append(candidate('OSM', ident, name or f'Unnamed {kind} ({ident})', pos.get('lat'), pos.get('lon'), kind,
                                  source_file='data/reference/osm_education.json', source_url='https://www.openstreetmap.org/'+ident,
                                  source_year='', address=t.get('addr:full',''), official_url=t.get('website', t.get('contact:website','')),
                                  point_role_osm='mapped_node' if r['type']=='node' else 'bounding_box_center',
                                  name_en=t.get('name:en',''), wikidata=t.get('wikidata',''), unnamed=not bool(name),
                                  alt_names=[t.get(k,'') for k in ('name','name:th','name:en','alt_name')]))
    return rows, osm_loaded


def apply_reference_review(rows, path):
    if not path.exists(): return rows, []
    data=json.loads(path.read_text())
    changes=[]
    for edit in data['corrections']:
        found=[r for r in rows if r['source']==edit['source'] and r['source_id']==edit['source_id']]
        if len(found)!=1: raise ValueError('Reference correction must match exactly one record: '+edit['source_id'])
        r=found[0]
        for field,value in edit['fields'].items():
            changes.append(dict(source=r['source'],source_id=r['source_id'],field=field,old_value=r.get(field,''),new_value=value,
                                evidence_url=edit['evidence_url'],reason=edit['reason']))
            r[field]=value
        r['review_evidence_url']=edit['evidence_url']
    rows.extend(data.get('additions',[]))
    return rows,changes


def boundary_distance(lat,lon,rings):
    """Local tangent-plane approximation for auxiliary footprint sensitivity only."""
    if within_campus(float(lat),float(lon),rings): return 0.0
    lat=float(lat);lon=float(lon)
    scale=6371008.8*math.pi/180
    result=math.inf
    for ring in rings['outer']+rings['inner']:
        for (x1,y1),(x2,y2) in zip(ring,ring[1:]):
            ax=(x1-lon)*scale*math.cos(math.radians(lat));ay=(y1-lat)*scale
            bx=(x2-lon)*scale*math.cos(math.radians(lat));by=(y2-lat)*scale
            dx=bx-ax;dy=by-ay
            t=max(0,min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy else 0
            result=min(result,math.hypot(ax+t*dx,ay+t*dy))
    return result


def review_camera_results(summary,institutions,root,radius):
    baseline_path=root/'data/reference/pre_review_camera_flags.csv'
    if not baseline_path.exists(): return []
    baseline={r['camera_id']:r for r in read_csv(baseline_path)}
    target_ids={r['camera_id'] for r in baseline.values() if r['near_university_college']=='False'}|{'224','225'}
    geometry_path=root/'data/reference/osm_campus_geometry.json'
    geometries={f"{e['type']}/{e['id']}":polygon_rings(e) for e in json.loads(geometry_path.read_text())['elements'] if e['type']!='node'} if geometry_path.exists() else {}
    higher=[]
    for institution in institutions:
        if institution['institution_type'] not in ('university','college'): continue
        for r in institution['source_records']:
            rings=geometries.get(r['source_id']) if r['source']=='OSM' else None
            if rings and rings['outer']:higher.append((institution,rings))
    review=[]
    for r in summary:
        r.update(targeted_review_status='not_targeted',school_identity_review_status='not_targeted',
                 nearest_mapped_university_boundary_name='',nearest_mapped_university_boundary_distance_m='',
                 within_radius_of_mapped_university_boundary='',university_comparison_status='exposed_by_reference_point' if r['near_university_college'] is True else 'no_point_match_catalog_incomplete')
        if r['camera_id'] not in target_ids:continue
        ds=sorted([(boundary_distance(r['latitude'],r['longitude'],rings),i) for i,rings in higher],key=lambda x:(x[0],x[1]['institution_id']))
        if ds:
            d,i=ds[0]
            r.update(nearest_mapped_university_boundary_name=i['institution_name'],nearest_mapped_university_boundary_distance_m=round(d,3),
                     within_radius_of_mapped_university_boundary=d<=radius)
        old=baseline[r['camera_id']]
        if r['camera_id'] in ('224','225'):
            r['school_identity_review_status']='official_site_and_contact_map_support_identity;exact_coordinate_not_independently_surveyed'
        if old['near_university_college']=='False' and r['near_university_college'] is True:
            status='corrected_positive_after_reference_review'
        elif r['near_university_college'] is False and r['within_radius_of_mapped_university_boundary'] is True:
            status='no_point_match_but_mapped_boundary_within_radius'
            r['university_comparison_status']='boundary_sensitive_do_not_use_as_unexposed'
        elif r['near_university_college'] is False:
            status='no_new_point_match_found;absence_not_certified'
            if ds and ds[0][0] <= radius+100:
                r['university_comparison_status']='near_cutoff_requires_location_review'
        else:status='school_identity_review_completed;point_distance_remains_approximate'
        r['targeted_review_status']=status
        review.append(dict(camera_id=r['camera_id'],before_near_university_college=old['near_university_college'],after_near_university_college=r['near_university_college'],
                           near_school=r['near_school'],nearest_school_name=r['nearest_school_name'],nearest_school_distance_m=r['nearest_school_distance_m'],
                           nearest_university_college_name=r['nearest_university_college_name'],nearest_university_college_distance_m=r['nearest_university_college_distance_m'],
                           nearest_mapped_boundary_name=r['nearest_mapped_university_boundary_name'],nearest_mapped_boundary_distance_m=r['nearest_mapped_university_boundary_distance_m'],
                           within_radius_of_mapped_boundary=r['within_radius_of_mapped_university_boundary'],review_status=status,
                           university_comparison_status=r['university_comparison_status'],school_identity_review_status=r['school_identity_review_status']))
    return review


def deduplicate(rows, threshold):
    """Conservative exact normalized-name + compatible type + proximity merge."""
    kept, audit, rejected = [], [], []
    for r in rows:
        if not valid_coords(r['latitude'], r['longitude']):
            rejected.append(dict(source=r['source'],source_id=r['source_id'],issue='invalid_coordinates'))
            continue
        r['latitude'], r['longitude'] = float(r['latitude']), float(r['longitude'])
        keys = {normal_name(x) for x in [r['institution_name']]+r.get('alt_names',[]) if x}
        matches = [k for k in kept if keys.intersection({normal_name(x) for x in [k['institution_name']]+k.get('alt_names',[]) if x}) and
                   (k['institution_type']=='school') == (r['institution_type']=='school') and
                   distance(k['latitude'],k['longitude'],r['latitude'],r['longitude']) <= threshold]
        if matches:
            target = min(matches, key=lambda k: distance(k['latitude'],k['longitude'],r['latitude'],r['longitude']))
            target['source_records'].append(r)
            audit.append(dict(kept_id=target['institution_id'], merged_source=r['source'], merged_source_id=r['source_id'],
                              rule='exact_normalized_name_or_alias_within_250m', distance_m=round(distance(target['latitude'],target['longitude'],r['latitude'],r['longitude']),2)))
        else:
            ident = hashlib.sha256((r['source']+':'+r['source_id']).encode()).hexdigest()[:12]
            kept.append(dict(r, institution_id='edu_'+ident, source_records=[r]))
    for r in kept:
        r['point_role'] = r.get('point_role_osm', r['point_role'])
        r['sources'] = ';'.join(sorted({x['source'] for x in r['source_records']}))
        r['source_record_ids'] = ';'.join(x['source']+':'+x['source_id'] for x in r['source_records'])
        r['source_urls'] = ';'.join(sorted({u for x in r['source_records'] for u in [x.get('source_url',''),x.get('review_evidence_url','')] if u}))
    return kept, audit, rejected


def calculate(cameras, institutions, radius, band, osm_loaded):
    summaries, matches, issues = [], [], []
    if len({r['camera_id'] for r in cameras}) != len(cameras):
        raise ValueError('Duplicate camera IDs')
    for camera in cameras:
        row = dict(camera, radius_m=radius, reference_coverage_status='incomplete_public_catalog',
                   coordinate_status='valid', near_any_education='',near_school='',near_university_college='',
                   match_status='unknown', institutions_within_radius=0, schools_within_radius=0, universities_colleges_within_radius=0,
                   nearest_institution_id='', nearest_institution_name='', nearest_institution_type='', nearest_distance_m='',
                   nearest_point_role='', review_required=True, review_reason='')
        for category in ('school','university_college'):
            for field in ('id','name','distance_m'):
                row[f'nearest_{category}_{field}']=''
        if not valid_coords(camera['latitude'], camera['longitude']):
            row.update(coordinate_status='invalid', review_reason='invalid_camera_coordinates')
            summaries.append(row)
            continue
        distances = sorted([(distance(camera['latitude'],camera['longitude'],i['latitude'],i['longitude']),i) for i in institutions],
                           key=lambda x:(x[0],x[1]['institution_id']))
        within = [(d,i) for d,i in distances if near(d,radius)]
        schools = [(d,i) for d,i in within if i['institution_type']=='school']
        higher = [(d,i) for d,i in within if i['institution_type'] in ('university','college')]
        # False means no match in the cached catalog, never certified geographic absence.
        row.update(near_any_education=bool(within), near_school=bool(schools),
                   near_university_college=bool(higher) if osm_loaded else '',
                   match_status='matched' if within else 'no_match_in_catalog',
                   institutions_within_radius=len(within), schools_within_radius=len(schools), universities_colleges_within_radius=len(higher))
        if distances:
            d,i = distances[0]
            row.update(nearest_institution_id=i['institution_id'], nearest_institution_name=i['institution_name'],
                       nearest_institution_type=i['institution_type'],nearest_distance_m=round(d,3),nearest_point_role=i['point_role'])
        for category,kinds in [('school',('school',)),('university_college',('university','college'))]:
            closest=next(((d,i) for d,i in distances if i['institution_type'] in kinds),None)
            if closest:
                d,i=closest
                row.update({f'nearest_{category}_id':i['institution_id'],f'nearest_{category}_name':i['institution_name'],f'nearest_{category}_distance_m':round(d,3)})
        reasons = ['point_locations_not_verified_entrances']
        if any(abs(d-radius)<=band for d,i in distances):
            reasons.append('institution_within_100m_of_cutoff')
        if not within:
            reasons.append('no_match_requires_catalog_coverage_review')
        row['review_reason']=';'.join(reasons)
        for d,i in within:
            matches.append(dict(camera_id=camera['camera_id'], institution_id=i['institution_id'],institution_name=i['institution_name'],
                                institution_type=i['institution_type'],distance_m=round(d,3),latitude=i['latitude'],longitude=i['longitude'],
                                point_role=i['point_role'],sources=i['sources'],source_urls=i['source_urls'],
                                borderline=abs(d-radius)<=band,unnamed=i.get('unnamed',False)))
        for d,i in distances:
            if abs(d-radius)<=band:
                issues.append(dict(camera_id=camera['camera_id'],institution_id=i['institution_id'],institution_name=i['institution_name'],
                                   distance_m=round(d,3),inside_radius=near(d,radius),issue='within_100m_of_cutoff'))
        summaries.append(row)
    return summaries,matches,issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=str(ROOT/'config.json'))
    args = parser.parse_args()
    cfg=json.loads(Path(args.config).read_text())
    radius=float(cfg['radius_m'])
    if radius<=0 or cfg['dedup_distance_m']!=250 or cfg['borderline_band_m']!=100:
        raise ValueError('This version requires a positive radius, dedup_distance_m=250, borderline_band_m=100')
    cameras=read_csv(ROOT/cfg['camera_file'])
    if len(cameras)!=cfg['expected_camera_count']:
        raise ValueError('Unexpected camera count: '+str(len(cameras)))
    candidates,osm_loaded=load_candidates(ROOT/cfg['team_folder'],ROOT/cfg['osm_file'])
    candidates,corrections=apply_reference_review(candidates,ROOT/'data/reference/reference_review.json')
    retained,components=collapse_campus_components(candidates,ROOT/'data/reference/osm_campus_geometry.json')
    institutions,audit,rejected=deduplicate(retained,cfg['dedup_distance_m'])
    summary,matches,issues=calculate(cameras,institutions,radius,cfg['borderline_band_m'],osm_loaded)
    camera_reviews=review_camera_results(summary,institutions,ROOT,radius)
    out=ROOT/'data/processed'; out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'cctv_campus_flags.csv',summary,list(summary[0]))
    write_csv(out/'camera_institution_matches.csv',matches,['camera_id','institution_id','institution_name','institution_type','distance_m','latitude','longitude','point_role','sources','source_urls','borderline','unnamed'])
    institution_fields=['institution_id','institution_name','institution_type','latitude','longitude','point_role','sources','source_record_ids','source_urls','source_file','source_year','address','official_url']
    write_csv(out/'institutions_clean.csv',institutions,institution_fields)
    write_csv(out/'deduplication_log.csv',audit,['kept_id','merged_source','merged_source_id','rule','distance_m'])
    write_csv(out/'borderline_matches.csv',issues,['camera_id','institution_id','institution_name','distance_m','inside_radius','issue'])
    write_csv(out/'rejected_records.csv',rejected,['source','source_id','issue'])
    write_csv(out/'campus_components.csv',components,['source_id','component_name','parent_source_id','parent_name','rule'])
    write_csv(out/'reference_corrections.csv',corrections,['source','source_id','field','old_value','new_value','evidence_url','reason'])
    write_csv(ROOT/'reports/camera_review.csv',camera_reviews,list(camera_reviews[0]) if camera_reviews else ['camera_id','review_status'])
    provenance=[dict(institution_id=i['institution_id'], **{k:r.get(k,'') for k in ['source','source_id','source_file','source_url','source_year','latitude','longitude','institution_name']}) for i in institutions for r in i['source_records']]
    write_csv(out/'institution_provenance.csv',provenance,list(provenance[0]))
    counts=dict(cameras=len(cameras),near_any=sum(r['near_any_education'] is True for r in summary),near_school=sum(r['near_school'] is True for r in summary),
                near_university_college=sum(r['near_university_college'] is True for r in summary),no_match=sum(r['match_status']=='no_match_in_catalog' for r in summary),
                unknown=sum(r['match_status']=='unknown' for r in summary),candidate_records=len(candidates),institutions=len(institutions),merged_records=len(audit),
                rejected_records=len(rejected),campus_components_collapsed=len(components),camera_institution_pairs=len(matches),borderline_pairs=len(issues),osm_loaded=osm_loaded,
                candidate_sources=dict(Counter(r['source'] for r in candidates)),institution_types=dict(Counter(r['institution_type'] for r in institutions)))
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    (reports/'summary.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2)+'\n')
    source_files=[ROOT/cfg['camera_file'],ROOT/'config.json',Path(__file__),ROOT/'scripts/map_template.html',ROOT/cfg['team_folder']/'data/school_coordinates.csv',ROOT/cfg['team_folder']/'raw_data/bma_schools.xlsx']
    if osm_loaded: source_files += [ROOT/cfg['osm_file'],ROOT/'data/reference/overpass_query.txt']
    if (ROOT/'data/reference/osm_campus_geometry.json').exists(): source_files += [ROOT/'data/reference/osm_campus_geometry.json',ROOT/'data/reference/overpass_campus_geometry_query.txt']
    if (ROOT/'data/reference/verification_notes.json').exists(): source_files += [ROOT/'data/reference/verification_notes.json']
    for f in ['reference_review.json','pre_review_camera_flags.csv','osm_review_candidates.json','overpass_review_query.txt']:
        if (ROOT/'data/reference'/f).exists():source_files.append(ROOT/'data/reference'/f)
    source_files.extend(sorted((ROOT/'data/reference/review_sources').glob('*.html')))
    file_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    manifest=dict(run_utc=datetime.now(timezone.utc).isoformat(),pipeline_version='1.1',configuration=cfg,counts=counts,input_sha256=file_hashes,
                  camera_origin='https://drive.google.com/file/d/1VSCzWeNOV7ds_d9BNJ9i20_9JzyncL2F/view',
                  camera_copy_method='Drive connector readable CSV response; content preserved, CRLF normalized to LF',
                  distance_method='Haversine, mean Earth radius 6371008.8 m',osm_snapshot=json.loads((ROOT/cfg['osm_file']).read_text()).get('osm3s',{}) if osm_loaded else None)
    (reports/'run_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    report=f'''# Campus proximity quality report

## Results

- Cameras: {counts['cameras']}; near an educational institution: {counts['near_any']}.
- Near a school: {counts['near_school']}; near a university/college: {counts['near_university_college']}.
- No match in catalog: {counts['no_match']}; invalid camera coordinates: {counts['unknown']}.
- Camera–institution pairs within {radius:g} m: {len(matches)}.
- Input institution records: {len(candidates)}; retained after merging: {len(institutions)}; merged: {len(audit)}; internal campus components collapsed: {len(components)}; invalid coordinates rejected: {len(rejected)}.
- Candidate sources: {json.dumps(counts['candidate_sources'])}.
- Institution types after merging: {json.dumps(counts['institution_types'])}.
- Camera–institution pairs within 100 m either side of cutoff: {len(issues)}. See borderline_matches.csv, including outside-radius cases.

## Method

Inclusive {radius:g} m straight-line cutoff on unrounded Haversine distances. Supplied school points retain source coordinates; OSM ways/relations use bounding-box centres and nodes use their mapped point. Points are not verified campus gates or boundaries. Nearest means nearest within the cached catalog, which is spatially bounded for OSM. Round distances only for display.

Reviewed corrections and an official-site college addition are applied from reference_review.json. The Royal Thai Navy College of Nursing reference is the viewport centre of the official contact-page embedded map, explicitly labelled approximate rather than a verified pin or entrance. Primary near flags still use the agreed point-distance rule. Mapped campus-boundary distances in the 15-row targeted review are an auxiliary sensitivity check, calculated in a local tangent plane; they never silently replace the primary point rule.

The 437 BMA records omitted by the team's name-column mapping were recovered using explicit workbook fields. Existing 159 OBEC records were reused. Exact normalized names or mapped aliases within 250 m and compatible education types are merged conservatively, preserving source evidence. Same-name campuses farther apart remain separate. Faculty/building records inside a mapped university campus are collapsed into the campus, with evidence in campus_components.csv. Standalone faculties outside a mapped parent boundary remain location records and require review. Alternative-name or unnamed map objects may remain duplicates; this can inflate institution counts. No match means no catalog match, not geographic absence.

## Coverage and review

OSM supplementary data available: {osm_loaded}. Open-map results cover schools/universities/colleges inside the padded camera bounding box; every camera's 1.5 km circle is inside that query envelope. The public catalog is not certified complete. School source coordinate-role accuracy and current operation are unverified. BMA records carry academic-year 2568. The raw OPEC file has no coordinates and remains unresolved rather than being assigned invented positions.

All camera flags are computed provisional proximity classifications. All rows retain review_required=True because reference points are not verified entrances. No claim of exhaustive manual verification is made. Inspect the map, borderline pairs, nearby alternative names and source links before interpreting exposure or institution counts. Positive evidence can be used as proximity to a recorded institution; false values only describe the cached reference. Offline map has a coordinate grid; optional online street tiles and external source links require internet.

The generated map's JavaScript syntax was checked. A saved browser permission or managed policy blocked local-origin access even after the user requested the preview, so visual browser verification remains unperformed. Primary-site identity/address checks and unresolved cases are recorded in data/reference/verification_notes.json; they do not certify the exact mapped coordinates. Targeted reviews of the original 13 university/college no-match cameras plus school matches 224 and 225 are in reports/camera_review.csv.

The supplied 19 calendar events are Chula BBA International only and have not been attached to schools. Image timestamps, term status, actual commuting paths and traffic outcomes are outside this camera-level task. No image ZIP was downloaded.

## Analysis implication

{'Every camera is near at least one recorded educational institution, so the 1.5 km binary flag provides no unexposed comparison group in this sample. Use institution type, continuous distance or a separately justified design downstream.' if counts['near_any']==len(cameras) else 'No-match cameras need catalog-coverage checks before being considered controls.'}

## Sources

- Camera metadata: supplied Google Drive cctv_info.csv; see run_manifest.json.
- OBEC and BMA school locations: team handoff, source paths and source years preserved in institution_provenance.csv. A specific original BMA download URL was not supplied and is not invented.
- OpenStreetMap contributors: https://www.openstreetmap.org/copyright ; ODbL https://opendatacommons.org/licenses/odbl/1-0/ . Supplementary snapshot and exact query are cached. Review licenses before redistributing the combined reference.
'''
    (reports/'quality_report.md').write_text(report)
    if camera_reviews:
        higher_review=[r for r in camera_reviews if r['before_near_university_college']=='False']
        changed=[r['camera_id'] for r in higher_review if r['after_near_university_college'] is True]
        boundary_sensitive=[r['camera_id'] for r in higher_review if r['university_comparison_status']=='boundary_sensitive_do_not_use_as_unexposed']
        remaining=[r['camera_id'] for r in higher_review if r['after_near_university_college'] is False]
        review_report=f'''# Targeted finalization review

## Outcome

- School identity/address review completed for cameras 224 and 225. The official school contact address matches the mapped school address, and the official news feed has 2026 school activity. Canonical Thai spelling was corrected. Original point distances are retained: approximately 1,261 m and 1,245 m. This supports the recorded school match without claiming a surveyed entrance coordinate.
- Reviewed all {len(higher_review)} original university/college no-match cameras. {len(changed)} became positive after reference corrections: {', '.join(changed)}.
- {len(remaining)} retain no university/college point match: {', '.join(remaining)}.
- {len(boundary_sensitive)} of those are within 1.5 km of a mapped university/college outline: {', '.join(boundary_sensitive)}. They must not be treated as unexposed solely because a campus centre is farther away.
- Camera 529 remains just outside the closest mapped college outline (approximately 1,572 m), so it remains sensitive to location accuracy. Camera 1804 has no qualifying college found in the reviewed reference; nearest point is approximately 2,522 m and nearest mapped outline approximately 2,472 m. This is not certified absence of all institutions.

## Changes and evidence

The previously omitted Royal Thai Navy College of Nursing was added from its official contact address and map reference. Its coordinate role is an embedded-map viewport centre, explicitly approximate. Six Thonburi cameras gain a point match. Don Bosco and three other explicitly verified technological-college records were reclassified from school to college; no coordinate was moved for these type corrections. Official sources and the full correction history are in reference_review.json, verification_notes.json and reference_corrections.csv.

The expanded named-feature search retrieved 249 map objects for coverage review. Bus stops, shops, sports grounds and buildings containing university names were not automatically promoted to institutions. Source completeness remains unverified, so no camera is certified as a causal control.

## Detailed review

See camera_review.csv for one row per targeted camera, before/after flags, nearest points, nearest mapped outlines and comparison warnings. The main camera CSV includes the same review status fields. The primary inclusive 1,500 m point rule is unchanged; boundary distance is a separate sensitivity check.

## Visual map check

Not completed: the browser tool reports a saved permission or managed policy denying access to http://127.0.0.1:8765 even after the user requested a preview. No alternate browser route or security-policy workaround was attempted. The map JavaScript is syntax-checked, but this does not verify rendering. Open campus_proximity_map.html directly to inspect the 15-camera review filter, the remaining university/college no-match filter, and camera details.
'''
        (reports/'finalization_review.md').write_text(review_report)
    payload=dict(cameras=summary,institutions=[{k:i.get(k,'') for k in institution_fields} for i in institutions],matches=matches,counts=counts,radius=radius)
    template=(ROOT/'scripts/map_template.html').read_text()
    encoded=json.dumps(payload,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    (reports/'campus_proximity_map.html').write_text(template.replace('__PAYLOAD__',encoded))
    print(json.dumps(counts,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
