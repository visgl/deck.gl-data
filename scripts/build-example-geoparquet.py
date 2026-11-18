"""Build full GeoParquet example datasets from the original website sources.

Requires pyarrow==21.0.0, shapely==2.0.7, Node.js and a deck.gl checkout.
Run: python scripts/build-example-geoparquet.py /path/to/deck.gl
"""
import csv
import subprocess
import sys
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import shape
from shapely import to_wkb
root=Path(__file__).resolve().parents[1]
deck=Path(sys.argv[1]).resolve()
# Execute the original MIT-licensed decoders rather than maintain a second copy.
decoder = r"""
const fs=require('fs'),vm=require('vm');
const [deck,root,name,source]=process.argv.slice(1);
const rows=[];
const context=vm.createContext({importScripts(){},postMessage(message){if(message.data) rows.push(...message.data);}});
for(const file of ['util.js',`${name}-decoder.js`]) {
 vm.runInContext(fs.readFileSync(`${deck}/website/static/workers/${file}`,'utf8'),context);
}
context.onmessage({data:{text:fs.readFileSync(`${root}/website/${source}.txt`,'utf8'),event:'load'}});
process.stdout.write(JSON.stringify(rows));
"""
def decode(name, source):
    """Decode every record in source order, including reverse county flows."""
    return json.loads(subprocess.check_output(['node', '-e', decoder, str(deck), str(root), name, source]))

for source,target in [('vancouver-blocks','geojson/vancouver-blocks'),('highway-roads','highway/roads'),('arc-data','arc/counties')]:
 rows=decode('geojson-data' if source=='vancouver-blocks' else source,source)
 assert len(rows)=={'vancouver-blocks':4627,'highway-roads':20592,'arc-data':3220}[source]
 columns={}
 for key in rows[0]['properties']:
  values=[r['properties'][key] for r in rows]
  if key=='flows':
   columns[key]=pa.array([list(v.items()) for v in values],type=pa.map_(pa.string(),pa.float64()))
  elif isinstance(values[0],(int,float)):
   columns[key]=pa.array(values,type=pa.float64())
  else: columns[key]=pa.array(values)
 geometries=[shape(r['geometry']) for r in rows]
 columns['geometry']=pa.array([to_wkb(g,byte_order=1) for g in geometries],type=pa.binary())
 table=pa.table(columns)
 bbox=[min(g.bounds[0] for g in geometries),min(g.bounds[1] for g in geometries),max(g.bounds[2] for g in geometries),max(g.bounds[3] for g in geometries)]
 geo={'version':'1.0.0','primary_column':'geometry','columns':{'geometry':{'encoding':'WKB','geometry_types':sorted(set(g.geom_type for g in geometries)),'bbox':bbox}}}
 table=table.replace_schema_metadata({'geo':json.dumps(geo)})
 path=root/'examples'/f'{target}.parquet';pq.write_table(table,path,compression='zstd',compression_level=19,use_dictionary=source=='arc-data')
 assert pq.read_table(path).equals(table)
 print(target,len(rows),path.stat().st_size)

# Accident records have no geometry; keep the complete small table human-readable.
rows=decode('highway-accidents','highway-accidents')
assert len(rows)==29342
with (root/'examples/highway/accidents-full.csv').open('w', encoding='utf-8', newline='') as output:
 writer=csv.DictWriter(output,fieldnames=['state','type','id','year','incidents','fatalities'])
 writer.writeheader()
 writer.writerows(rows)
