# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Convert all CSV snapshots in the licensed PaleoDEMs v2 archive, or validate them."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

SOURCE = 'https://zenodo.org/records/5460860/files/PaleoDEMS_long_lat_elev_csv_v2.zip'
SOURCE_SHA256 = 'db43e6261411ff468c9030ca240778a73f224bf34bf8186c735477e41454c873'
CREDIT = 'Scotese, Christopher R. and Wright, Nicky M. (2018). PALEOMAP Paleodigital Elevation Models (PaleoDEMs) for the Phanerozoic, v2. https://doi.org/10.5281/zenodo.5460860'
SCHEMA = pa.schema([('age_ma', pa.uint16()), ('longitude', pa.float64()),
                    ('latitude', pa.float64()), ('elevation_m', pa.float64())])
NAME = 'paleodem.parquet'
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / 'paleodem'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(archive):
    entries = []
    for name in archive.namelist():
        match = re.search(r'/Map[\d.]+_(\d+)Ma\.csv$', name)
        if match:
            entries.append((int(match[1]), name))
    entries.sort()
    if [age for age, _ in entries] != list(range(0, 541, 5)):
        raise ValueError('Expected exactly 109 distinct CSV ages, 0–540 Ma at 5 Ma intervals')
    return entries


def read_source(archive, name):
    content = archive.read(name)
    if content.splitlines()[0] not in (b'# lon,lat,elev', b'longitude,latitude,elevation'):
        raise ValueError(f'Unexpected CSV header: {name}')
    data = np.loadtxt(io.StringIO(content.decode('utf-8'), newline=None), delimiter=',', skiprows=1)
    if data.ndim != 2 or data.shape[1] != 3 or not np.isfinite(data).all():
        raise ValueError(f'Invalid numeric source grid: {name}')
    grid_info(data)
    return data


def grid_info(data):
    longitude = np.unique(data[:, 0])
    latitude = np.unique(data[:, 1])[::-1]
    if (not np.allclose(np.diff(longitude), 1, atol=1e-10, rtol=0) or
            not np.allclose(np.diff(latitude), -1, atol=1e-10, rtol=0) or
            not np.array_equal(data[:, 0], np.tile(longitude, len(latitude))) or
            not np.array_equal(data[:, 1], np.repeat(latitude, len(longitude))) or
            longitude[0] < -180 or longitude[-1] > 180 or
            latitude[-1] < -90 or latitude[0] > 90):
        raise ValueError('Unexpected source grid layout')
    return {'width': len(longitude), 'height': len(latitude),
            'bbox': [float(longitude[0]), float(latitude[-1]),
                     float(longitude[-1]), float(latitude[0])]}


def source_table(age, data, schema):
    return pa.Table.from_arrays([pa.array(np.full(len(data), age, dtype=np.uint16)),
                                 *[pa.array(data[:, i]) for i in range(3)]], schema=schema)


def convert(source, output):
    if digest(source) != SOURCE_SHA256:
        raise ValueError('Source archive SHA-256 does not match the audited release')
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        entries = inventory(archive)
        groups = []
        for i, (age, name) in enumerate(entries):
            data = read_source(archive, name)
            groups.append({'index': i, 'ageMa': age, 'sourceFile': name,
                           'rows': len(data), **grid_info(data)})
        provenance = {
            'title': 'PALEOMAP PaleoDEMs for the Phanerozoic', 'version': 'v2',
            'dataset': 'https://doi.org/10.5281/zenodo.5460860', 'source': SOURCE,
            'sourceSha256': SOURCE_SHA256, 'credit': CREDIT, 'license': 'CC-BY-4.0',
            'licenseUrl': 'https://creativecommons.org/licenses/by/4.0/',
            'sourceLicenseFile': 'License.txt',
            'model': 'PALEOMAP Scotese and Wright (2018)',
            'coordinateFrame': 'Source reconstructed paleogeographic longitude/latitude; no datum or plate-model transformation applied',
            'columns': {'age_ma': 'Million years before present (positive into the past)',
                        'longitude': 'Degrees east', 'latitude': 'Degrees north',
                        'elevation_m': 'Source paleotopography/bathymetry in meters; positive land, negative ocean depth; not a modern geodetic vertical datum'},
            'grid': {'spacingDegrees': 1,
                     'order': 'Latitude descending, longitude ascending (longitude varies fastest)',
                     'endpoints': 'Source-specific dimensions and bounds retained per row group; no edge or pole nodes added or removed',
                     'precision': 'All float64 values preserved, including near-zero source latitude at 145 Ma'},
            'compression': {'codec': 'ZSTD', 'level': 6},
            'ages': {'min': 0, 'max': 540, 'step': 5, 'count': len(entries)},
            'rowGroups': groups,
            'conversion': 'Lossless numeric CSV-to-Parquet conversion; all 109 CSV grids included, original node order and float64 values retained. No resampling, deduplication, contouring, reconstruction or inferred missing values. ZSTD level 6; one complete age grid per row group; column statistics enable age filtering.',
            'software': {'pyarrow': pa.__version__, 'numpy': np.__version__}}
        schema = SCHEMA.with_metadata({b'paleodem': json.dumps(provenance, sort_keys=True).encode()})
        with pq.ParquetWriter(output / NAME, schema, compression='zstd', compression_level=6,
                              write_statistics=True, use_dictionary=True, version='2.6') as writer:
            for age, name in entries:
                data = read_source(archive, name)
                writer.write_table(source_table(age, data, schema), row_group_size=len(data))
        (output / 'LICENSE.source.txt').write_bytes(archive.read('License.txt'))
    file = output / NAME
    manifest = {**provenance, 'files': [{'path': NAME, 'bytes': file.stat().st_size,
                'sha256': digest(file), 'rows': sum(group['rows'] for group in groups), 'rowGroups': len(entries)}]}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def validate(source, output):
    if digest(source) != SOURCE_SHA256:
        raise ValueError('Incorrect source archive')
    manifest = json.loads((output / 'manifest.json').read_text())
    path = output / NAME
    info = manifest['files'][0]
    assert path.read_bytes()[:4] == b'PAR1' and path.read_bytes()[-4:] == b'PAR1'
    assert info['sha256'] == digest(path) and info['bytes'] == path.stat().st_size
    parquet = pq.ParquetFile(path)
    assert parquet.schema_arrow.remove_metadata() == SCHEMA
    embedded = json.loads(parquet.schema_arrow.metadata[b'paleodem'])
    assert {k: v for k, v in manifest.items() if k != 'files'} == embedded
    with zipfile.ZipFile(source) as archive:
        entries = inventory(archive)
        assert (output / 'LICENSE.source.txt').read_bytes() == archive.read('License.txt')
        assert parquet.num_row_groups == len(entries) == info['rowGroups'] == 109
        assert parquet.metadata.num_rows == info['rows'] == 7095119
        for i, (age, name) in enumerate(entries):
            group = parquet.metadata.row_group(i)
            data = read_source(archive, name)
            assert group.num_rows == len(data)
            for column in range(4):
                assert group.column(column).compression == 'ZSTD'
                assert group.column(column).statistics.null_count == 0
            stats = group.column(0).statistics
            assert stats.min == stats.max == age
            actual = parquet.read_row_group(i)
            expected = source_table(age, data, SCHEMA)
            assert actual.equals(expected, check_metadata=False), name
            assert embedded['rowGroups'][i] == {'index': i, 'ageMa': age, 'sourceFile': name, 'rows': group.num_rows, **grid_info(data)}
    # Exercise predicate pushdown: one selected age, all other age groups excluded.
    import pyarrow.dataset as ds
    dataset = ds.dataset(path, format='parquet')
    predicate = ds.field('age_ma') == 300
    fragments = list(next(dataset.get_fragments()).split_by_row_group(filter=predicate))
    assert len(fragments) == 1 and fragments[0].row_groups[0].id == 60
    selected = dataset.to_table(columns=['age_ma', 'elevation_m'], filter=predicate)
    assert selected.num_rows == embedded['rowGroups'][60]['rows'] and selected.column_names == ['age_ma', 'elevation_m']
    # Batch iteration can start before decoding the entire file.
    assert sum(batch.num_rows for batch in parquet.iter_batches(batch_size=16384)) == info['rows']
    print(f"Validated all {len(entries)} source grids / {info['rows']:,} nodes, exact values, ZSTD, row-group filtering and batch streaming; {info['bytes']:,} bytes")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    if not args.validate_only:
        convert(args.archive, args.output)
    validate(args.archive, args.output)
