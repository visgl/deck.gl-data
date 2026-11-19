# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Check the WOA23 converter on small synthetic files with the WOA23 layout.

No NCEI data is needed: the inputs copy the WOA23 dimension, variable and
attribute names on a 6 x 12 grid with all 102 standard depths.
"""
import gzip
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import netCDF4
import numpy as np
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('converter', HERE / 'create-woa23-parquet.py')
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)

DEPTHS = np.array([*range(0, 100, 5), *range(100, 500, 25), *range(500, 2000, 50),
                   *range(2000, 5600, 100)], np.float32)
FILL = np.float32(9.96921e36)


def make_source(path, prefix, identifier, rng):
    lat = np.linspace(-75, 75, 6, dtype=np.float32)
    lon = np.linspace(-165, 165, 12, dtype=np.float32)
    with netCDF4.Dataset(path, 'w') as ds:
        ds.id = identifier
        ds.license = 'These data are openly available to the public.'
        for name, size in [('time', 1), ('depth', len(DEPTHS)), ('lat', len(lat)), ('lon', len(lon)), ('nbounds', 2)]:
            ds.createDimension(name, size)
        for name, values in [('depth', DEPTHS), ('lat', lat), ('lon', lon)]:
            ds.createVariable(name, 'f4', (name,))[:] = values
        ds.createVariable('depth_bnds', 'f4', ('depth', 'nbounds'))[:] = np.stack([DEPTHS, DEPTHS + 1], 1)
        ds.createVariable('climatology_bounds', 'f4', ('time', 'nbounds'))[:] = [[0, 24837]]
        ds.createVariable('time', 'f4', ('time',))[:] = [386.0]
        seafloor = rng.integers(0, len(DEPTHS) + 1, (len(lat), len(lon)))
        land = seafloor == 0
        below = np.arange(len(DEPTHS))[:, None, None] >= seafloor[None]
        base = 2 + 26 * np.exp(-DEPTHS / 800)[:, None, None] if prefix == 't' else 34 + 0.5 * np.cos(DEPTHS / 900)[:, None, None]
        for statistic in ['an', 'mn', 'sd', 'se', 'oa', 'sdo', 'sea']:
            variable = ds.createVariable(f'{prefix}_{statistic}', 'f4', ('time', 'depth', 'lat', 'lon'), fill_value=FILL)
            values = (base + rng.normal(0, 0.3, (len(DEPTHS), len(lat), len(lon)))).astype(np.float32)
            variable[0] = np.ma.masked_array(values, below | land[None])
            variable.units = 'degrees_celsius' if prefix == 't' else '1'
        for statistic in ['dd', 'gp']:
            variable = ds.createVariable(f'{prefix}_{statistic}', 'i4', ('time', 'depth', 'lat', 'lon'), fill_value=-32767)
            variable[0] = np.ma.masked_array(rng.integers(0, 500, (len(DEPTHS), len(lat), len(lon))), below | land[None])
    return seafloor


def main():
    rng = np.random.default_rng(613)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        t_path, s_path, out = root / 't.nc', root / 's.nc', root / 'out'
        make_source(t_path, 't', 'woa23_decav_t00_01.nc', np.random.default_rng(1))
        make_source(s_path, 's', 'woa23_decav_s00_01.nc', np.random.default_rng(1))
        for prefix, path in [('t', t_path), ('s', s_path)]:
            converter.SOURCES[prefix]['bytes'] = path.stat().st_size
            converter.SOURCES[prefix]['sha256'] = converter.digest(path)
        converter.convert(t_path, s_path, out)

        manifest = json.loads((out / 'manifest.json').read_text())
        assert manifest['rows'] == 102 * 6 * 12
        assert [entry['path'] for entry in manifest['files']] == ['grids.parquet', 'preview.bin.gz', 'preview-manifest.json']
        parquet = pq.ParquetFile(out / 'grids.parquet')
        assert parquet.num_row_groups == 102
        assert 't_dd' in parquet.schema_arrow.names and 's_sea' in parquet.schema_arrow.names
        assert parquet.schema_arrow.field('t_dd').type == 'int32'

        # Decode the preview as the example does and compare with the source.
        preview = json.loads((out / 'preview-manifest.json').read_text())
        raw = gzip.decompress((out / 'preview.bin.gz').read_bytes())
        cells = len(preview['latitudes']) * len(preview['longitudes'])
        levels = len(preview['depths'])
        assert len(raw) == cells * levels * 4 == preview['uncompressedBytes']
        temperature = np.frombuffer(raw, '<i2', cells * levels).reshape(3, 6, levels)
        salinity = np.frombuffer(raw, '<u2', cells * levels, cells * levels * 2).reshape(3, 6, levels)
        with netCDF4.Dataset(t_path) as t_ds, netCDF4.Dataset(s_path) as s_ds:
            for row in range(3):
                for col in range(6):
                    for level, depth in enumerate(preview['depths']):
                        index = int(np.flatnonzero(DEPTHS == depth)[0])
                        for packed, ds, name, fill in [(temperature, t_ds, 't_an', -32768), (salinity, s_ds, 's_an', 65535)]:
                            source = ds[name][0, index, 2 * row, 2 * col]
                            if np.ma.is_masked(source):
                                assert packed[row, col, level] == fill
                            else:
                                assert abs(packed[row, col, level] / converter.PREVIEW_SCALE - float(source)) <= 0.5 / converter.PREVIEW_SCALE + 1e-6
    print('WOA23 converter: lossless Parquet, nulls and preview decoding verified on synthetic inputs.')


if __name__ == '__main__':
    sys.exit(main())
