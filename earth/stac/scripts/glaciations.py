# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Add immutable glaciation dataset collections to the Earth catalog."""
import json
from pathlib import Path
from generate import ROOT, WORLD, GEOMETRY, FILE_EXTENSION, link, write, url
COMMIT='a5c369be5e8029cd741be65c0cef91b7e287556d'
DATE='2026-10-07T13:46:54Z'
TYPES={'.parquet':'application/vnd.apache.parquet','.nc':'application/x-netcdf','.zip':'application/zip','.gz':'application/gzip','.json':'application/json','.dat':'text/plain'}


def generate_glaciations():
    catalog=json.loads((ROOT/'catalog.json').read_text())
    for name,bounds in [('paleomist',WORLD),('alpine',[4.229902267456055,43.33127975463867,16.476024627685547,48.93292999267578]),('koehler2015',WORLD)]:
        directory=ROOT.parent/'glaciations/v1'/name
        manifest=json.loads((directory/'manifest.json').read_text())
        identifier='visgl-'+name
        source={'commit':COMMIT,'path':'earth/glaciations/v1/'+name}
        collection={'type':'Collection','stac_version':'1.1.0','id':identifier,'title':manifest['credit']+' — '+name,
            'description':manifest['conversion']+' Ages in ka before present are separate from the repository snapshot datetime.',
            'license':manifest['license'],
            'providers':[{'name':manifest['credit'],'roles':['producer','licensor'],'url':manifest['dataset']},{'name':'vis.gl','roles':['processor','host'],'url':'https://github.com/visgl/deck.gl-data'}],
            'extent':{'spatial':{'bbox':[bounds]},'temporal':{'interval':[[DATE,DATE]]}},
            'summaries':{'paleo:age_min_ka':[min(manifest['ages'])],'paleo:age_max_ka':[max(manifest['ages'])]},
            'links':[link('root','../catalog.json'),link('parent','../catalog.json'),link('self','collection.json'),link('license',manifest['licenseUrl'],'text/html'),link('derived_from',manifest['dataset'],'text/html'),link('item','snapshot.json','application/geo+json')]}
        a,b,c,d=bounds
        geometry={'type':'Polygon','coordinates':[[[a,b],[c,b],[c,d],[a,d],[a,b]]]}
        assets={}
        for record in manifest['files']:
            filename=record['path']
            assets[filename]={'href':url(source,filename,media=Path(filename).suffix in ['.parquet','.nc','.zip','.gz']),'type':TYPES[Path(filename).suffix],
                'roles':['metadata'] if filename=='preview-manifest.json' else ['data'],
                'file:size':record['bytes'],'file:checksum':'1220'+record['sha256']}
        assets.update(manifest={'href':url(source,'manifest.json'),'type':'application/json','roles':['metadata']},attribution={'href':url(source,'ATTRIBUTION.md'),'type':'text/markdown','roles':['metadata']})
        item={'type':'Feature','stac_version':'1.1.0','stac_extensions':[FILE_EXTENSION],'id':identifier+'-snapshot','collection':identifier,'bbox':bounds,'geometry':geometry,
            'properties':{'datetime':DATE,'visgl:source_commit':COMMIT,'visgl:datetime_semantics':'Repository dataset snapshot commit time; not observation time or geologic age','paleo:age_min_ka':min(manifest['ages']),'paleo:age_max_ka':max(manifest['ages']),'paleo:age_unit':'ka before present'},
            'links':[link('root','../catalog.json'),link('parent','collection.json'),link('collection','collection.json'),link('self','snapshot.json','application/geo+json')],'assets':assets}
        write(name+'/collection.json',collection);write(name+'/snapshot.json',item)
        catalog['links']=[entry for entry in catalog['links'] if entry['href']!=name+'/collection.json']
        catalog['links'].append(link('child',name+'/collection.json',title=collection['title']))
    write('catalog.json',catalog)

if __name__=='__main__':generate_glaciations()
