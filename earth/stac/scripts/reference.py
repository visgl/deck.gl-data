# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Catalog attributed vector and geoid reference datasets."""
import json
from pathlib import Path
from generate import ROOT,FILE_EXTENSION,link,write,url
COMMIT='eecfffd67766d44de1a240ef548b6c053dcbd62f'
DATE='2026-10-07T16:31:40Z'
SOURCES={'countries':'earth/boundaries/v1/countries','major-rivers':'earth/hydrography/v1/major-rivers','egm2008':'earth/geoid/egm2008/v1'}
TYPES={'.parquet':'application/vnd.apache.parquet','.pgm':'image/x-portable-graymap','.zip':'application/zip','.geojson':'application/geo+json'}


def generate_reference():
    catalog=json.loads((ROOT/'catalog.json').read_text())
    for name,folder in SOURCES.items():
        manifest=json.loads((ROOT.parents[1]/folder/'manifest.json').read_text())
        source={'commit':COMMIT,'path':folder};identifier='visgl-'+name;bounds=manifest['bbox'];west,south,east,north=bounds
        description=manifest['conversion']+' '+('Geoid undulation N in meters above WGS84; h = H + N. Not terrain elevation.' if name=='egm2008' else 'Pinned legacy vector snapshot; geometry conventions follow the source.')
        collection={'type':'Collection','stac_version':'1.1.0','id':identifier,'title':manifest['title'],'description':description,'license':manifest['license'],'providers':[{'name':manifest['credit'],'roles':['producer','licensor'],'url':manifest['dataset']},{'name':'vis.gl','roles':['processor','host'],'url':'https://github.com/visgl/deck.gl-data'}],'extent':{'spatial':{'bbox':[bounds]},'temporal':{'interval':[[DATE,DATE]]}},'links':[link('root','../catalog.json'),link('parent','../catalog.json'),link('self','collection.json'),link('license',manifest['licenseUrl'],'text/plain' if name=='egm2008' else 'text/html'),link('derived_from',manifest['dataset'],'text/html'),link('item','snapshot.json','application/geo+json')]}
        assets={}
        for record in manifest['files']:
            filename=record['path'];suffix=Path(filename).suffix
            assets[filename]={'href':url(source,filename,media=suffix!='.geojson'),'type':TYPES[suffix],'roles':['data'],'file:size':record['bytes'],'file:checksum':'1220'+record['sha256']}
        assets.update(manifest={'href':url(source,'manifest.json'),'type':'application/json','roles':['metadata']},attribution={'href':url(source,'ATTRIBUTION.md'),'type':'text/markdown','roles':['metadata']})
        item={'type':'Feature','stac_version':'1.1.0','stac_extensions':[FILE_EXTENSION],'id':identifier+'-snapshot','collection':identifier,'bbox':bounds,'geometry':{'type':'Polygon','coordinates':[[[west,south],[east,south],[east,north],[west,north],[west,south]]]},'properties':{'datetime':DATE,'visgl:source_commit':COMMIT,'visgl:datetime_semantics':'Repository dataset snapshot commit time; not observation or measurement time','visgl:rows':manifest['rows']},'links':[link('root','../catalog.json'),link('parent','collection.json'),link('collection','collection.json'),link('self','snapshot.json','application/geo+json')],'assets':assets}
        write(name+'/collection.json',collection);write(name+'/snapshot.json',item)
        catalog['links']=[entry for entry in catalog['links'] if entry['href']!=name+'/collection.json']
        catalog['links'].append(link('child',name+'/collection.json',title=manifest['title']))
    write('catalog.json',catalog)

if __name__=='__main__':generate_reference()
