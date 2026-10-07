# SPDX-License-Identifier: MIT
"""Losslessly convert the pinned Krapp et al. ice masks; one age per row group."""
import argparse
import hashlib
import json
from pathlib import Path
import netCDF4
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

SHA = '722f7d964fb1b947563a0974026b7f8a289875393f5e52f9af6b46972f50d8d3'

def convert(source, out):
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SHA, 'Unexpected source version'
    out.mkdir(parents=True, exist_ok=True)
    with netCDF4.Dataset(source) as ds:
        ds.set_auto_mask(False)
        lon, lat = ds['lon'][:], ds['lat'][:]
        x, y = np.meshgrid(np.arange(len(lon), dtype=np.uint16), np.arange(len(lat), dtype=np.uint16))
        coords = [x.ravel(), y.ravel(), np.tile(lon, len(lat)), np.repeat(lat, len(lon))]
        attrs = {name: {key: ds[name].getncattr(key) for key in ds[name].ncattrs()} for name in ds.variables}
        metadata = {'sourceSha256': SHA, 'variables': attrs,
                    'globalAttributes': {key: ds.getncattr(key) for key in ds.ncattrs()},
                    'maskClasses': {'0': 'ocean', '1': 'land', '2': 'ice'},
                    'ordering': 'source time order; latitude-major, longitude-minor'}
        schema = pa.schema([('gridX', pa.uint16()), ('gridY', pa.uint16()),
                            ('longitude', pa.float32()), ('latitude', pa.float32()),
                            ('ageKa', pa.float64()), ('sourceTimeYears', pa.float64()),
                            ('land_max', pa.int16()), ('mask', pa.int16())],
                           metadata={b'krapp2021': json.dumps(metadata).encode()})
        with pq.ParquetWriter(out / 'grids.parquet', schema, compression='zstd', compression_level=6) as writer:
            for index, time in enumerate(ds['time'][:]):
                arrays = coords + [np.full(x.size, -float(time) / 1000), np.full(x.size, float(time)),
                                   ds['land_max'][index].ravel(), ds['mask'][index].ravel()]
                writer.write_table(pa.Table.from_arrays(arrays, schema=schema), row_group_size=x.size)
                if index % 100 == 0:
                    print(f'Converted {index + 1}/800 snapshots', flush=True)
    files = [{'path': name, 'bytes': (out / name).stat().st_size,
              'sha256': hashlib.sha256((out / name).read_bytes()).hexdigest()} for name in ['source.nc', 'grids.parquet']]
    manifest = dict(dataset='https://osf.io/8n43x/', paper='https://doi.org/10.1038/s41597-021-01009-3',
                    credit='Krapp et al. (2021), Terrestrial climate of the last 800,000 years',
                    license='CC-BY-4.0', licenseUrl='https://creativecommons.org/licenses/by/4.0/',
                    ages=list(range(799, -1, -1)), ageUnit='ka before present',
                    dimensions={'time': 800, 'lat': 360, 'lon': 720}, rows=207360000,
                    source={'filename': 'icesheets_000-800_cru.nc', 'osfFileId': '5fd87e75149e750381029864',
                            'version': 1, 'sha256': SHA,
                            'download': 'https://files.osf.io/v1/resources/8n43x/providers/osfstorage/5fd87e75149e750381029864'},
                    conversion='All native cells and values; no interpolation, decimation or quantization. One snapshot per Parquet row group.',
                    metadata=metadata, files=files)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    convert(args.source, args.out)
