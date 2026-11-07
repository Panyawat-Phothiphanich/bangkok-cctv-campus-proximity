#!/usr/bin/env python3
"""Explicit source refresh; never invoked automatically by the offline pipeline."""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENDPOINT='https://maps.mail.ru/osm/tools/overpass/api/interpreter'


def main():
    for query_file,output in [('overpass_query.txt','osm_education.json'),('overpass_campus_geometry_query.txt','osm_campus_geometry.json')]:
        query=(ROOT/'data/reference'/query_file).read_text()
        url=ENDPOINT+'?'+urllib.parse.urlencode({'data':query})
        request=urllib.request.Request(url,headers={'User-Agent':'BangkokCCTVCampusResearch/1.0 (local course project)'})
        with urllib.request.urlopen(request,timeout=60) as response:
            content=response.read()
        parsed=json.loads(content)
        if 'elements' not in parsed or parsed.get('remark'):
            raise RuntimeError('Incomplete response; existing snapshot not overwritten')
        destination=ROOT/'data/reference'/output
        temp=destination.with_suffix('.pending')
        temp.write_bytes(content);temp.replace(destination)
        print(output,len(parsed['elements']),'objects')
    (ROOT/'data/reference/source_collection.json').write_text(json.dumps({'endpoint':ENDPOINT,'retrieved_unix':time.time(),'queries':['overpass_query.txt','overpass_campus_geometry_query.txt']},indent=2)+'\n')


if __name__=='__main__':main()
