# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Prepare attributed Earth reference assets from existing repository files."""
import argparse,hashlib,json,shutil,zipfile
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

SOURCE_COMMIT='c120179186c1e0cacb536c04cf667348e6dde937'
SPECS=[('countries','boundaries/v1/countries','formats/geoparquet/countries/countries_zstd.parquet','Natural Earth / DataHub','https://datahub.io/core/geo-countries','ODC-PDDL-1.0','https://opendatacommons.org/licenses/pddl/1-0/'),('major-rivers','hydrography/v1/major-rivers','formats/geoparquet/major-rivers/major-rivers_0.4.0_gzip.parquet','World Bank: Major Rivers of the World','https://datacatalog.worldbank.org/infrastructure-data/search/dataset/0042032/major-rivers-of-the-world','CC-BY-4.0','https://creativecommons.org/licenses/by/4.0/')]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(target, data):
    data['files']=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(target.iterdir()) if p.name not in ['manifest.json','ATTRIBUTION.md','README.md']]
    (target/'manifest.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    (target/'ATTRIBUTION.md').write_text(f"# {data['title']}\n\nProducer: {data['credit']}.\nSource: {data['dataset']}.\nLicense: [{data['license']}]({data['licenseUrl']}).\n\nData retains this license separately from MIT conversion code.\nChanges: {data['conversion']}\nLegacy input paths and source checksums are recorded in manifest.json.\n")


def prepare(root,out):
    pinned=json.loads(Path(__file__).with_name("source-reference.json").read_text())
    for name,digest in pinned.items():
        if sha(root/name)!=digest:raise ValueError(f"Source checksum mismatch: {name}")
    for name,folder,source,credit,url,license,license_url in SPECS:
        target=out/folder;target.mkdir(parents=True,exist_ok=True)
        original=root/source
        if original.read_bytes()[:4]!=b'PAR1':raise ValueError('Download original LFS data before converting')
        table=pq.read_table(original)
        geo=json.loads(table.schema.metadata[b'geo'])
        geo['version']='1.1.0';geo.pop('creator',None)
        for column in geo['columns'].values():
            if 'geometry_type' in column:column['geometry_types']=column.pop('geometry_type')
        metadata={**table.schema.metadata,b'geo':json.dumps(geo).encode()}
        table=table.replace_schema_metadata(metadata)
        parquet=target/(name+'.parquet');pq.write_table(table,parquet,compression='zstd',compression_level=6)
        assert pq.read_table(parquet).equals(table)
        original_copy=target/'source.parquet';shutil.copyfile(original,original_copy)
        if name=='countries':shutil.copyfile(root/'formats/geojson/countries.geojson',target/'countries.geojson')
        manifest(target,dict(id=name,title=credit,credit=credit,dataset=url,license=license,licenseUrl=license_url,
            sourceRepositoryCommit=SOURCE_COMMIT,sourcePath=source,sourceSha256=sha(original),rows=table.num_rows,
            columns=table.column_names,geometry=geo,bbox=[max(-180,geo['columns']['geometry']['bbox'][0]),geo['columns']['geometry']['bbox'][1],min(180,geo['columns']['geometry']['bbox'][2]),geo['columns']['geometry']['bbox'][3]],
            conversion='Source rows, WKB geometry and attributes retained exactly. GeoParquet metadata upgraded to 1.1.0; ZSTD level 6. Country GeoJSON is retained separately from the legacy repository and is not claimed to be byte-equivalent to its Parquet geometry.'))
        print(name,table.num_rows,'rows, lossless round trip')
    target=out/'geoid/egm2008/v1';target.mkdir(parents=True,exist_ok=True)
    source=root/'egm/egm2008-5.zip';shutil.copyfile(source,target/'source.zip')
    archive=zipfile.ZipFile(source);raw=archive.read('geoids/egm2008-5.pgm');pgm=target/'egm2008-5.pgm';pgm.write_bytes(raw)
    header,pixels=raw.split(b'65535\n',1);lines=header.decode().splitlines();width,height=map(int,lines[-1].split());fields=dict(line[2:].split(' ',1) for line in lines if line.startswith('# '));offset=float(fields['Offset']);scale=float(fields['Scale']);grid=np.frombuffer(pixels,dtype='>u2').reshape(height,width)
    path=target/'egm2008-5.parquet';writer=None;index=[]
    meta=dict(model='EGM2008',units='meters',heightReference='WGS84 ellipsoid',heightDefinition='Geoid undulation N; h = H + N, not terrain elevation',width=width,height=height,spacingArcMinutes=5,offset=offset,scale=scale,sourcePgmSha256=sha(pgm),license='Public Domain',rowOrder='north to south; columns east from 0 degrees')
    for start in range(0,height,120):
        stop=min(height,start+120);row=np.repeat(np.arange(start,stop,dtype='int32'),width);col=np.tile(np.arange(width,dtype='int32'),stop-start);lon=col.astype(float)*360/width;lon=np.where(lon>=180,lon-360,lon);lat=90-row.astype(float)*180/(height-1);values=grid[start:stop].ravel().astype('uint16');table=pa.table(dict(row=row,column=col,longitude=lon,latitude=lat,geoid_height=offset+scale*values,raw_value=values)).replace_schema_metadata({b'geoid':json.dumps(meta).encode()})
        if writer is None:writer=pq.ParquetWriter(path,table.schema,compression='zstd',compression_level=6)
        writer.write_table(table,row_group_size=table.num_rows);index.append(dict(rowGroup=len(index),rowStart=start,rowStop=stop,rows=table.num_rows))
    writer.close();parquet=pq.ParquetFile(path)
    for group in index:
        table=parquet.read_row_group(group['rowGroup']);expected=grid[group['rowStart']:group['rowStop']].ravel().astype('uint16');np.testing.assert_array_equal(table['raw_value'].to_numpy(),expected);np.testing.assert_array_equal(table['geoid_height'].to_numpy(),offset+scale*expected)
    manifest(target,dict(id='egm2008',title='NGA EGM2008 5-minute geoid grid',credit='NGA; GeographicLib PGM distribution',dataset='https://geographiclib.sourceforge.io/C++/doc/geoid.html',license='other',licenseUrl='https://raw.githubusercontent.com/OSGeo/PROJ-data/master/us_nga/us_nga_README.txt',licenseDescription='Public-domain NGA EGM2008 model data; not a CC0 assertion',sourceRepositoryCommit=SOURCE_COMMIT,sourcePath='egm/egm2008-5.zip',sourceSha256=sha(source),bbox=[-180,-90,180,90],rows=width*height,rowGroupIndex=index,grid=meta,conversion='Original ZIP retained and PGM extracted unchanged. Full native grid converted without decimation; raw uint16 values and scaled float64 meter heights both retained. ZSTD level 6.'))
    print('egm2008',width*height,'nodes, all source pixels and heights verified')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();prepare(a.source_root,a.out)
