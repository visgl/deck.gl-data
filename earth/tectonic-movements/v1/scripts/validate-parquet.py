# deck.gl-data
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Validate the streamable Parquet snapshots and their provenance manifests."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import pyarrow as pa
import pyarrow.parquet as pq

GEOMETRY = pa.schema([
    ('featureId', pa.string()), ('polygonIndex', pa.int32()), ('plateId', pa.int32()),
    ('name', pa.string()), ('beginAge', pa.float64()), ('endAge', pa.float64()),
    ('geometry', pa.binary()),
])
ROTATIONS = pa.schema([
    ('age', pa.int16()), ('plateId', pa.int32()), ('available', pa.bool_()),
    ('w', pa.float64()), ('x', pa.float64()), ('y', pa.float64()), ('z', pa.float64()),
])

COMBINED = pa.schema([('recordType', pa.string()), *GEOMETRY,
                      *[field for field in ROTATIONS if field.name != 'plateId']])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(root):
    total = file_count = 0
    for name in ('cao2024', 'muller2022'):
        model = root / name
        manifest = json.loads((model / 'manifest.json').read_text())
        require(manifest['license'] == 'CC-BY-4.0', 'Dataset license mismatch')
        require(manifest['anchorPlateId'] == 0, 'Unexpected reference anchor')
        require(manifest['quaternionOrder'] == ['w', 'x', 'y', 'z'], 'Quaternion order mismatch')
        require((model / 'ATTRIBUTION.md').is_file(), 'Missing attribution')
        tables = {}
        for record in manifest['files']:
            path = model / record['path']
            require(path.name in ('geometry.parquet', 'rotations.parquet', 'tectonic.parquet'), 'Unexpected snapshot file')
            data = path.read_bytes()
            require(data[:4] == b'PAR1' and data[-4:] == b'PAR1', 'Not binary Parquet')
            require(len(data) == record['bytes'], 'File size mismatch')
            require(hashlib.sha256(data).hexdigest() == record['sha256'], 'SHA-256 mismatch')
            require(record['compression'] == 'ZSTD' and record['compressionLevel'] == 6,
                    'Unexpected declared compression')
            parquet = pq.ParquetFile(path)
            require(parquet.metadata.num_rows == record['rows'], 'Row count mismatch')
            require(parquet.metadata.num_row_groups == record['rowGroups'], 'Row group count mismatch')
            for group in range(parquet.metadata.num_row_groups):
                row_group = parquet.metadata.row_group(group)
                for column in range(row_group.num_columns):
                    require(row_group.column(column).compression == 'ZSTD', 'Uncompressed column')
            table = parquet.read()
            expected = {'geometry.parquet': GEOMETRY, 'rotations.parquet': ROTATIONS,
                        'tectonic.parquet': COMBINED}[path.name]
            require(table.schema.remove_metadata().equals(expected), 'Column schema mismatch')
            metadata = json.loads(table.schema.metadata[b'math.gl.tectonic'])
            require(metadata['model'] == manifest['model'] and metadata['version'] == manifest['version'],
                    'Model revision mismatch')
            require(metadata['referenceFrame'] == manifest['referenceFrame'], 'Frame mismatch')
            index = json.loads(table.schema.metadata[b'math.gl.tectonic.rowGroups'])
            require(index == record['rowGroupIndex'], 'Footer/manifest row group index mismatch')
            require(len(index) == parquet.num_row_groups, 'Incomplete row group index')
            for number, entry in enumerate(index):
                group = parquet.read_row_group(number)
                require(entry['rowGroup'] == number and entry['rows'] == group.num_rows,
                        'Incorrect indexed row group')
                if 'recordType' in group.column_names:
                    require(set(group.column('recordType').to_pylist()) == {entry['recordType']},
                            'Mixed record types in row group')
                ages_in_group = group.column('age').drop_null().to_pylist() if 'age' in group.column_names else []
                require(entry['minAge'] == (min(ages_in_group) if ages_in_group else None) and
                        entry['maxAge'] == (max(ages_in_group) if ages_in_group else None),
                        'Indexed age range mismatch')
                if entry['recordType'] == 'rotation':
                    stats = parquet.metadata.row_group(number).column(group.schema.get_field_index('age')).statistics
                    require(stats is not None and stats.min == entry['minAge'] and stats.max == entry['maxAge'],
                            'Missing age range statistics')
                elif 'age' in group.column_names:
                    require(group.column('age').null_count == group.num_rows, 'Geometry age must be null')
            # Exercise incremental decoding with column pruning, including boundaries within row groups.
            streamed = pa.Table.from_batches(parquet.iter_batches(batch_size=1024, columns=['plateId']))
            require(streamed.column('plateId').equals(table.column('plateId')), 'Streamed column mismatch')
            tables[path.name] = table
            total += len(data)
            file_count += 1

        expected_files = {'tectonic.parquet'} if name == 'cao2024' else {'geometry.parquet', 'rotations.parquet'}
        require(set(tables) == expected_files, 'Snapshot layout mismatch')
        if 'tectonic.parquet' in tables:
            combined = tables['tectonic.parquet']
            rows = combined.to_pylist()
            require(all(row['recordType'] in ('geometry', 'rotation') for row in rows), 'Unknown record type')
            polygons = [row for row in rows if row['recordType'] == 'geometry']
            rotation_rows = [row for row in rows if row['recordType'] == 'rotation']
            require(all(all(row[field] is None for field in ROTATIONS.names if field != 'plateId')
                        for row in polygons), 'Geometry record has rotation fields')
            require(all(all(row[field] is None for field in GEOMETRY.names if field != 'plateId')
                        for row in rotation_rows), 'Rotation record has geometry fields')
            geometry = pa.Table.from_pylist(polygons, schema=GEOMETRY.with_metadata(combined.schema.metadata))
            rotation_file = 'tectonic.parquet'
        else:
            geometry = tables['geometry.parquet']
            rotation_rows = tables['rotations.parquet'].to_pylist()
            rotation_file = 'rotations.parquet'
            require(pq.ParquetFile(model / 'geometry.parquet').num_row_groups == 10, 'Expected 10 geometry groups')
        geo = json.loads(geometry.schema.metadata[b'geo'])
        require(geo['version'] == '1.1.0' and geo['primary_column'] == 'geometry', 'GeoParquet metadata mismatch')
        require(geo['columns']['geometry'] == {
            'encoding': 'WKB', 'geometry_types': ['Polygon'], 'edges': 'spherical'
        }, 'Geometry encoding or CRS convention mismatch')
        polygons = geometry.to_pylist()
        ids = {row['plateId'] for row in polygons}
        require(len(ids) == manifest['plateCount'], 'Plate count mismatch')
        require(len(polygons) == manifest['polygonRows'], 'Polygon count mismatch')
        vertices = holes = 0
        for row in polygons:
            require(row['beginAge'] >= row['endAge'], 'Invalid feature age range')
            data = row['geometry']
            byte_order, kind, rings = struct.unpack_from('<BII', data)
            require(byte_order == 1 and kind == 3 and rings > 0, 'Invalid WKB polygon')
            holes += rings - 1
            offset = 9
            for _ in range(rings):
                count, = struct.unpack_from('<I', data, offset)
                offset += 4
                require(count >= 4, 'Degenerate polygon ring')
                first = struct.unpack_from('<dd', data, offset)
                last = struct.unpack_from('<dd', data, offset + 16 * (count - 1))
                require(first == last, 'Unclosed polygon ring')
                for index in range(count):
                    lon, lat = struct.unpack_from('<dd', data, offset + 16 * index)
                    require(math.isfinite(lon) and math.isfinite(lat) and abs(lon) <= 180 and abs(lat) <= 90,
                            'Invalid geographic coordinate')
                vertices += count
                offset += 16 * count
            require(offset == len(data), 'Trailing WKB bytes')

        ages = manifest['ages']
        expected_ages = list(range(ages['min'], ages['max'] + 1, ages['step']))
        rows_by_age = {}
        missing = 0
        for row in rotation_rows:
            rows_by_age.setdefault(row['age'], []).append(row)
            q = [row[component] for component in 'wxyz']
            if row['available']:
                require(all(value is not None and math.isfinite(value) for value in q), 'Invalid quaternion')
                require(abs(sum(value * value for value in q) - 1) <= 1e-12, 'Non-unit quaternion')
            else:
                require(row['available'] is False and q == [None] * 4, 'Missing rotation must not be fabricated')
                missing += 1
        require(sorted(rows_by_age) == expected_ages, 'Missing or unexpected sample ages')
        for rows in rows_by_age.values():
            require(len(rows) == len(ids) and {row['plateId'] for row in rows} == ids, 'Incomplete age sample')
        rotation_record = next(record for record in manifest['files'] if record['path'] == rotation_file)
        groups = [entry for entry in rotation_record['rowGroupIndex'] if entry['recordType'] == 'rotation']
        require(len(groups) == math.ceil(ages['max'] / 100), 'Unexpected number of rotation windows')
        for index, group in enumerate(groups):
            start = index * 100
            final = start + 100 >= ages['max']
            last = ages['max'] if final else start + 90
            require(group['minAge'] == start and group['maxAge'] == last, 'Unexpected 100 Ma window')
            require(group['rows'] == len(range(start, last + 1, 10)) * len(ids), 'Incomplete window')
        print(f'{name}: {len(polygons)} polygons, {vertices} vertices, {holes} holes, '
              f'{len(expected_ages)} complete age groups, {missing} unavailable rotations')
    print(f'Validated all {file_count} Parquet files: {total:,} bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    validate(parser.parse_args().root)
