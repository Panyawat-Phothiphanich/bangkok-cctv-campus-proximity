import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from campus_pipeline import distance, near, valid_coords, normal_name, candidate, deduplicate, calculate, polygon_rings, within_campus, boundary_distance, apply_reference_review
import tempfile
import json


class ProximityTests(unittest.TestCase):
    def test_distance(self):
        self.assertEqual(distance(13.7,100.5,13.7,100.5),0)
        self.assertAlmostEqual(distance(0,0,0,1),111195.0802,places=3)
        self.assertAlmostEqual(distance(13.7,100.5,13.8,100.6),distance(13.8,100.6,13.7,100.5))

    def test_cutoff_unrounded(self):
        self.assertTrue(near(1500,1500))
        self.assertFalse(near(1500.0001,1500))

    def test_coordinates(self):
        for lat,lon in [('nan',100),('',100),(91,100),(10,181),(10,'inf')]:
            self.assertFalse(valid_coords(lat,lon))
        self.assertTrue(valid_coords('13.7','100.5'))

    def test_dedup_and_separate_campuses(self):
        rows=[candidate('BMA','1','โรงเรียน Test',13.7,100.5,'school'),candidate('OSM','2','Test',13.70001,100.5,'school'),
              candidate('OSM','3','Test',13.8,100.5,'school')]
        kept,audit,rejected=deduplicate(rows,250)
        self.assertEqual((len(kept),len(audit),len(rejected)),(2,1,0))
        self.assertEqual(len(kept[0]['source_records']),2)

    def test_multiple_matches_preserve_camera_grain(self):
        rows=[candidate('BMA','1','A',13.7,100.5,'school'),candidate('OSM','2','B',13.7,100.501,'university')]
        institutions,_,_=deduplicate(rows,250)
        cams=[dict(camera_id='1',latitude='13.7',longitude='100.5'),dict(camera_id='2',latitude='',longitude='100.5')]
        summary,matches,issues=calculate(cams,institutions,1500,100,True)
        self.assertEqual(len(summary),2)
        self.assertEqual(len(matches),2)
        self.assertTrue(summary[0]['near_school'])
        self.assertTrue(summary[0]['near_university_college'])
        self.assertEqual(summary[1]['near_any_education'],'')

    def test_missing_supplement_not_false_higher_ed(self):
        institutions,_,_=deduplicate([candidate('BMA','1','A',13.7,100.5,'school')],250)
        summary,_,_=calculate([dict(camera_id='1',latitude=13.7,longitude=100.5)],institutions,1500,100,False)
        self.assertEqual(summary[0]['near_university_college'],'')

    def test_duplicate_camera_ids_fail(self):
        with self.assertRaises(ValueError):
            calculate([dict(camera_id='1'),dict(camera_id='1')],[],1500,100,True)

    def test_relation_segments_and_hole(self):
        geometry=lambda ps:[dict(lon=x,lat=y) for x,y in ps]
        element=dict(type='relation',members=[
            dict(role='outer',geometry=geometry([(0,0),(2,0),(2,2)])),
            dict(role='outer',geometry=geometry([(0,0),(0,2),(2,2)])),
            dict(role='inner',geometry=geometry([(.5,.5),(1.5,.5),(1.5,1.5),(.5,1.5),(.5,.5)]))])
        rings=polygon_rings(element)
        self.assertTrue(within_campus(.25,.25,rings))
        self.assertFalse(within_campus(1,1,rings))
        self.assertFalse(within_campus(3,3,rings))

    def test_boundary_sensitivity_does_not_change_point_rule(self):
        rings={'outer':[[(100.5,13.7),(100.51,13.7),(100.51,13.71),(100.5,13.71),(100.5,13.7)]],'inner':[]}
        self.assertEqual(boundary_distance(13.705,100.505,rings),0)
        self.assertAlmostEqual(boundary_distance(13.69,100.505,rings),1111.950802,places=3)
        self.assertFalse(near(distance(13.69,100.505,13.71,100.505),1500))
        self.assertTrue(near(boundary_distance(13.69,100.505,rings),1500))

    def test_reference_review_is_evidence_backed_and_exact(self):
        rows=[candidate('OSM','way/1','College',13.7,100.5,'school')]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'review.json'
            p.write_text(json.dumps({'corrections':[{'source':'OSM','source_id':'way/1','fields':{'institution_type':'college'},'evidence_url':'https://example.edu/','reason':'college identity verified'}]}))
            result,log=apply_reference_review(rows,p)
            self.assertEqual(result[0]['institution_type'],'college')
            self.assertEqual(log[0]['old_value'],'school')
            with self.assertRaises(ValueError):apply_reference_review([],p)


if __name__=='__main__':
    unittest.main()
