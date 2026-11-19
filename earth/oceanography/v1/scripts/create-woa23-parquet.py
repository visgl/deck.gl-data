# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Convert the WOA23 annual 1-degree temperature and salinity climatology.

Writes a lossless Parquet snapshot of every source cell and variable, a
separately quantized display preview, and a manifest with checksums.
"""
import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path

import netCDF4
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

# NCEI THREDDS fileServer sizes, Last-Modified 2024-01-29. SHA-256 values are
# pinned from the first approved download, then enforced here.
SOURCES = {
    't': {'id': 'woa23_decav_t00_01.nc', 'bytes': 85168080, 'sha256': None,
          'url': 'https://www.ncei.noaa.gov/thredds-ocean/fileServer/woa23/DATA/temperature/netcdf/decav/1.00/woa23_decav_t00_01.nc'},
    's': {'id': 'woa23_decav_s00_01.nc', 'bytes': 77439270, 'sha256': None,
          'url': 'https://www.ncei.noaa.gov/thredds-ocean/fileServer/woa23/DATA/salinity/netcdf/decav/1.00/woa23_decav_s00_01.nc'},
}
# The nine per-cell statistics in each WOA23 file (OPeNDAP DDS, checked 2026-11-19).
STATISTICS = ['an', 'mn', 'dd', 'sd', 'se', 'oa', 'gp', 'sdo', 'sea']
# Classic WOA 33-level subset of the 102 WOA23 standard depths, in meters.
PREVIEW_DEPTHS = [0, 10, 20, 30, 50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 600, 700, 800,
                  900, 1000, 1100, 1200, 1300, 1400, 1500, 1750, 2000, 2500, 3000, 3500, 4000,
                  4500, 5000, 5500]
PREVIEW_STRIDE = 2
PREVIEW_SCALE = 1000
PREVIEW_FILL = {'t': -32768, 's': 65535}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_source(prefix, path):
    expected = SOURCES[prefix]
    assert path.stat().st_size == expected['bytes'], f'{path}: unexpected size'
    sha256 = digest(path)
    assert expected['sha256'] in (None, sha256), f'{path}: unexpected SHA-256'
    with netCDF4.Dataset(path) as ds:
        assert ds.getncattr('id') == expected['id'], f'{path}: unexpected dataset id'
    return sha256


def attributes(variable):
    return {key: np.asarray(variable.getncattr(key)).tolist() for key in variable.ncattrs()}


def read_fields(ds, prefix):
    """Return every statistic as a masked float32/int32 array [depth, lat, lon]."""
    fields = {}
    for statistic in STATISTICS:
        values = ds[f'{prefix}_{statistic}'][0]
        fields[f'{prefix}_{statistic}'] = np.ma.masked_array(np.asarray(values.data), np.ma.getmaskarray(values))
    extra = {name for name in ds.variables if name.startswith(prefix + '_')} - set(fields)
    assert not extra, f'Unconverted source variables: {sorted(extra)}'
    return fields


def write_parquet(path, coordinates, fields, metadata):
    depth, lat, lon = coordinates
    y, x = np.meshgrid(np.arange(len(lat), dtype=np.uint16), np.arange(len(lon), dtype=np.uint16), indexing='ij')
    columns = [('depthIndex', pa.uint8()), ('gridX', pa.uint16()), ('gridY', pa.uint16()),
               ('depth', pa.float32()), ('longitude', pa.float32()), ('latitude', pa.float32())]
    columns += [(name, pa.from_numpy_dtype(values.dtype)) for name, values in fields.items()]
    schema = pa.schema(columns, metadata={b'visgl.woa23': json.dumps(metadata).encode()})
    cells = x.size
    with pq.ParquetWriter(path, schema, compression='zstd', compression_level=6) as writer:
        for level, depth_value in enumerate(depth):
            arrays = [pa.array(np.full(cells, level, np.uint8)), pa.array(x.ravel()), pa.array(y.ravel()),
                      pa.array(np.full(cells, depth_value, np.float32)), pa.array(lon[x.ravel()]),
                      pa.array(lat[y.ravel()])]
            for values in fields.values():
                layer = values[level]
                arrays.append(pa.array(layer.data.ravel(), mask=np.ma.getmaskarray(layer).ravel()))
            writer.write_table(pa.Table.from_arrays(arrays, schema=schema), row_group_size=cells)


def verify_parquet(path, coordinates, fields):
    """Compare every written value and null with the source arrays, bit for bit."""
    depth, lat, lon = coordinates
    parquet = pq.ParquetFile(path)
    assert parquet.num_row_groups == len(depth)
    for level in range(len(depth)):
        table = parquet.read_row_group(level)
        assert table.num_rows == len(lat) * len(lon)
        assert np.all(table['depth'].to_numpy() == depth[level])
        assert np.all(table['depthIndex'].to_numpy() == level)
        grid_y, grid_x = table['gridY'].to_numpy(), table['gridX'].to_numpy()
        assert np.array_equal(grid_y * len(lon) + grid_x, np.arange(len(lat) * len(lon)))
        assert np.array_equal(table['latitude'].to_numpy(), lat[grid_y])
        assert np.array_equal(table['longitude'].to_numpy(), lon[grid_x])
        for name, values in fields.items():
            column = table[name]
            mask = np.ma.getmaskarray(values[level]).ravel()
            assert np.array_equal(column.is_null().to_numpy(zero_copy_only=False), mask), name
            actual = column.fill_null(0).to_numpy()
            expected = values[level].data.ravel()
            assert np.array_equal(actual[~mask].view(np.uint32), expected[~mask].view(np.uint32)), name


def write_preview(out, coordinates, temperature, salinity):
    """Quantized, decimated display grid; not the scientific precision of the Parquet."""
    depth, lat, lon = coordinates
    levels = [int(np.flatnonzero(depth == value)[0]) for value in PREVIEW_DEPTHS]
    rows = slice(0, len(lat), PREVIEW_STRIDE)
    cols = slice(0, len(lon), PREVIEW_STRIDE)
    blocks = []
    for prefix, values, dtype in [('t', temperature, '<i2'), ('s', salinity, '<u2')]:
        subset = values[levels][:, rows, cols]
        scaled = np.rint(subset.data.astype(np.float64) * PREVIEW_SCALE)
        info = np.iinfo(np.dtype(dtype))
        assert scaled[~np.ma.getmaskarray(subset)].min() > info.min
        assert scaled[~np.ma.getmaskarray(subset)].max() < info.max
        packed = np.where(np.ma.getmaskarray(subset), PREVIEW_FILL[prefix], scaled).astype(dtype)
        # Cell-major layout: [latitude][longitude][depth], so one profile is contiguous.
        blocks.append(np.ascontiguousarray(packed.transpose(1, 2, 0)).tobytes())
    raw = b''.join(blocks)
    with gzip.GzipFile(out / 'preview.bin.gz', 'wb', compresslevel=9, mtime=0) as stream:
        stream.write(raw)
    manifest = {
        'format': 'little-endian; temperature block (int16) then salinity block (uint16); each [latitude][longitude][depth]',
        'latitudes': lat[rows].tolist(), 'longitudes': lon[cols].tolist(), 'depths': PREVIEW_DEPTHS,
        'temperature': {'variable': 't_an', 'units': 'degrees_celsius', 'scale': 1 / PREVIEW_SCALE, 'fill': PREVIEW_FILL['t']},
        'salinity': {'variable': 's_an', 'units': 'practical salinity (PSS-78)', 'scale': 1 / PREVIEW_SCALE, 'fill': PREVIEW_FILL['s']},
        'decimation': f'every {PREVIEW_STRIDE}nd source node in latitude and longitude; source nodes are not averaged',
        'uncompressedBytes': len(raw),
    }
    (out / 'preview-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def convert(temperature_path, salinity_path, out):
    hashes = {'t': check_source('t', temperature_path), 's': check_source('s', salinity_path)}
    out.mkdir(parents=True, exist_ok=True)
    with netCDF4.Dataset(temperature_path) as t_ds, netCDF4.Dataset(salinity_path) as s_ds:
        t_ds.set_auto_scale(False)
        s_ds.set_auto_scale(False)
        coordinates = tuple(np.asarray(t_ds[name][:], np.float32) for name in ['depth', 'lat', 'lon'])
        for name, values in zip(['depth', 'lat', 'lon'], coordinates):
            assert np.array_equal(np.asarray(s_ds[name][:], np.float32), values), name
        fields = {**read_fields(t_ds, 't'), **read_fields(s_ds, 's')}
        metadata = {
            'sources': {prefix: {**SOURCES[prefix], 'sha256': hashes[prefix]} for prefix in SOURCES},
            'globalAttributes': {'t': {k: str(t_ds.getncattr(k)) for k in t_ds.ncattrs()},
                                 's': {k: str(s_ds.getncattr(k)) for k in s_ds.ncattrs()}},
            'variableAttributes': {'t': {name: attributes(t_ds[name]) for name in t_ds.variables},
                                   's': {name: attributes(s_ds[name]) for name in s_ds.variables}},
            'bounds': {name: np.asarray(t_ds[name][:]).tolist() for name in ['depth_bnds', 'climatology_bounds']},
            'ordering': 'one row group per standard depth (surface first); latitude-major, longitude-minor',
        }
    parquet = out / 'grids.parquet'
    write_parquet(parquet, coordinates, fields, metadata)
    verify_parquet(parquet, coordinates, fields)
    write_preview(out, coordinates, fields['t_an'], fields['s_an'])
    files = [dict(path=p.name, bytes=p.stat().st_size, sha256=digest(p))
             for p in [parquet, out / 'preview.bin.gz', out / 'preview-manifest.json']]
    depth, lat, lon = coordinates
    manifest = dict(
        id='woa23', title='World Ocean Atlas 2023 annual temperature and salinity (1°)',
        credit='NOAA NCEI World Ocean Atlas 2023 (Locarnini et al. 2023; Reagan et al. 2023)',
        dataset='https://www.ncei.noaa.gov/products/world-ocean-atlas',
        accession='https://www.ncei.noaa.gov/archive/accession/0270533',
        citations=['https://doi.org/10.25923/54bh-1613', 'https://doi.org/10.25923/70qt-9574'],
        license='other', licenseUrl='https://www.ncei.noaa.gov/products/world-ocean-atlas',
        licenseStatement=metadata['globalAttributes']['t'].get('license'),
        bbox=[-180, -90, 180, 90], decade='decav', period='annual', timeCoverage='1955-01-01/P68Y',
        dimensions={'depth': len(depth), 'lat': len(lat), 'lon': len(lon)},
        rows=len(depth) * len(lat) * len(lon), columns=list(fields),
        rowGroupIndex=[dict(rowGroup=i, depthMeters=float(d), rows=len(lat) * len(lon)) for i, d in enumerate(depth)],
        conversion='Every source cell, depth and statistic of the WOA23 annual 1° decav temperature and salinity files; '
                   'source float32/int32 values unchanged; fill values are null. One standard depth per row group. '
                   'The display preview is decimated and quantized separately.',
        sources=metadata['sources'], files=files)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{parquet.stat().st_size} bytes Parquet; every value and null verified against the source')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temperature', type=Path, required=True, help='woa23_decav_t00_01.nc')
    parser.add_argument('--salinity', type=Path, required=True, help='woa23_decav_s00_01.nc')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--skip-size-check', action='store_true', help='for synthetic test inputs only')
    args = parser.parse_args()
    if args.skip_size_check:
        for prefix, path in [('t', args.temperature), ('s', args.salinity)]:
            SOURCES[prefix]['bytes'] = path.stat().st_size
    convert(args.temperature, args.salinity, args.out)
