# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Convert pinned glaciation sources without quantization or spatial decimation."""
import argparse, hashlib, json, shutil, zipfile
from pathlib import Path
import netCDF4
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def convert(source, target, identifier, credit, dataset, license, fields, age_name, scale):
    target.mkdir(parents=True, exist_ok=True)
    original = target / 'source.nc'
    shutil.copyfile(source, original)
    with netCDF4.Dataset(source) as n:
        ages = np.asarray(n[age_name][:]) * scale
        manifest = dict(id=identifier, credit=credit, dataset=dataset, license=license,
            licenseUrl=f'https://creativecommons.org/licenses/by/{"4.0" if license.endswith("4.0") else "3.0"}/',
            ageUnit='ka before present', ages=ages.tolist(),
            sourceSha256=digest(source), columns=fields,
            sourceAttributes={k: str(n.getncattr(k)) for k in n.ncattrs()},
            variableAttributes={k:{a:str(n[k].getncattr(a)) for a in n[k].ncattrs()} for k in fields},
            coordinateSystem='EPSG:32632' if 'mapping' in n.variables else 'OGC:CRS84',
            mapping=str(n['mapping'].proj4) if 'mapping' in n.variables else None,
            conversion='Full native grid, all source ages and selected scientific variables; no interpolation, rounding or decimation. Masked values are null.', files=[])
        output = target / 'grids.parquet'
        writer = None
        groups = []
        for i, age in enumerate(ages):
            shape = n[fields[0]][i].shape
            yy, xx = np.indices(shape)
            columns = {'ageKa':pa.array(np.full(xx.size, age)), 'gridX':pa.array(xx.ravel().astype('int32')), 'gridY':pa.array(yy.ravel().astype('int32'))}
            for key in ['x','y','lon','lat']:
                if key not in n.variables: continue
                v = np.asarray(n[key][:])
                values = v.ravel() if v.ndim == 2 else (v[xx.ravel()] if key in ['x','lon'] else v[yy.ravel()])
                columns[key] = pa.array(values)
            for key in fields:
                values = np.ma.asarray(n[key][i]).ravel()
                columns[key] = pa.array(values.data, mask=np.ma.getmaskarray(values))
            table = pa.table(columns)
            if writer is None:
                schema=table.schema.with_metadata({b'visgl.glaciation':json.dumps(manifest).encode()})
                writer=pq.ParquetWriter(output, schema, compression='zstd', compression_level=6)
            writer.write_table(table, row_group_size=table.num_rows)
            groups.append(dict(rowGroup=i,ageKa=float(age),rows=table.num_rows))
        writer.close()
        parquet=pq.ParquetFile(output)
        assert parquet.num_row_groups==len(ages)
        for i, age in enumerate(ages):
            table=parquet.read_row_group(i)
            assert table['ageKa'][0].as_py()==age
            for key in fields:
                expected=np.ma.asarray(n[key][i]).ravel()
                actual=table[key].to_numpy()
                np.testing.assert_array_equal(actual[~np.ma.getmaskarray(expected)],expected.data[~np.ma.getmaskarray(expected)])
        manifest['rowGroupIndex']=groups
        manifest['files']=[dict(path=p.name,bytes=p.stat().st_size,sha256=digest(p)) for p in [original,output]]
        (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(identifier, output.stat().st_size, 'bytes; all scientific values verified')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--alpine',type=Path,required=True);p.add_argument('--global-ice',type=Path,required=True);p.add_argument('--climate',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    assert digest(a.global_ice)=='ab6f74541339f5be44dd630dfb9c41189a6c1dfaf58fce6fc3c356430b539037'
    assert hashlib.md5(a.alpine.read_bytes()).hexdigest()=='0b59b7c26bb8d1b1797c9414638a2f32'
    assert digest(a.climate)=='0f256898ea93d07dac22f1eeea9cf1bf4c2a77d525058cacde3900b3f837d050'
    convert(a.global_ice,a.out/'paleomist', 'paleomist','Gowan et al. (2021)','https://doi.pangaea.de/10.1594/PANGAEA.905800','CC-BY-4.0',['ice_thickness','base_topography','paleo_topography','sea_level'],'time',-.001)
    convert(a.alpine,a.out/'alpine','alpine','Julien Seguinot and colleagues (2018)','https://doi.org/10.5281/zenodo.7802275','CC-BY-4.0',['thk','topg','tempicethk_basal','temppabase','uvelbase','uvelsurf','vvelbase','vvelsurf'],'age',-1)
    target=a.out/'koehler2015';target.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(a.climate,target/'source.zip')
    z=zipfile.ZipFile(a.climate)
    files=[]
    for key,pattern,names in [('temperature','fig2c',['ageKa','temperature1K','sigma1K','temperature2K','sigma2K','temperature3K','sigma3K']),('albedo','fig4c',['ageKa','forcingWm2','sigmaWm2'])]:
        member=next(n for n in z.namelist() if pattern in n)
        raw=z.read(member);(target/(key+'.dat')).write_bytes(raw)
        rows=np.array([[float(x) for x in line.split()] for line in raw.decode().splitlines() if line.strip() and not line.startswith('#')]);rows[:,0]*=-1
        table=pa.table({name:pa.array(rows[:,i]) for i,name in enumerate(names)})
        table=table.replace_schema_metadata({b'visgl.climate':json.dumps(dict(credit='Köhler et al. (2015)',dataset='https://doi.pangaea.de/10.1594/PANGAEA.855449',license='CC-BY-3.0',sourceHeader=raw.decode().split('\n-')[0],ageUnit='ka before present')).encode()})
        path=target/(key+'.parquet');pq.write_table(table,path,compression='zstd',compression_level=6,row_group_size=250)
        assert pq.read_table(path).equals(table)
    manifest=dict(id='koehler2015',credit='Köhler, de Boer, von der Heydt, Stap and van de Wal (2015)',dataset='https://doi.pangaea.de/10.1594/PANGAEA.855449',license='CC-BY-3.0',licenseUrl='https://creativecommons.org/licenses/by/3.0/',ageUnit='ka before present',ages=[0,5000],sourceSha256=digest(a.climate),conversion='Original source values and all three temperature variants retained. Negative source time converted to positive ka BP. No rebasing or extrapolation.',files=[dict(path=f.name,bytes=f.stat().st_size,sha256=digest(f)) for f in sorted(target.iterdir())])
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
