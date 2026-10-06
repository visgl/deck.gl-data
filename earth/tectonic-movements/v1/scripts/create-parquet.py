# math.gl
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
# Original offline conversion. Source data retains CC-BY-4.0; pyGPlates is an external tool.
"""Create streamable geometry and finite-rotation Parquet snapshots from pinned model archives.

Run in a separate environment: pip install pygplates==1.0.0 pyarrow==23.0.1
No GPlates implementation is copied into, or shipped with, math.gl.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import pyarrow as pa
import pyarrow.parquet as pq
import pygplates

MODELS = {
    'CAO2024': {
        'version': '2.4', 'maxAge': 1800, 'frame': 'Paleomagnetic',
        'record': 'https://zenodo.org/records/13628813',
        'archiveMD5': '4a032d3ab46e6023d14add8a54b6a541',
        'geometry': '1.8Ga_model_GSF/shapes_continents.gpmlz',
        'rotations': ['1.8Ga_model_GSF/1000_0_rotfile.rot', '1.8Ga_model_GSF/1800_1000_rotfile.rot'],
        'credit': 'Xianzhi Cao, Alan Collins, Sergei Pisarevsky, Nicolas Flament, Sanzhong Li, Derrick Hasterok and Dietmar Müller (2024)',
    },
    'MULLER2022': {
        'version': '1.2.4', 'maxAge': 1000, 'frame': 'Optimised mantle',
        'record': 'https://zenodo.org/records/13636799',
        'archiveMD5': '1f409e19e42128a8cf245ce54b75f1ae',
        'geometry': 'Coastlines/shapes_coastlines_Merdith_etal.gpmlz',
        # This complete model uses the optimised mantle frame. The paleomagnetic
        # Rotations/1000_0_rotfile.rot is an alternative, never an extra time slice.
        'rotations': ['optimisation/1000_0_rotfile_MantleOpt.rot'],
        'credit': 'R. Dietmar Müller, Nicolas Flament, John Cannon, Michael G. Tetley, Simon E. Williams, Xianzhi Cao, Ömer F. Bodur, Sabin Zahirovic and Andrew Merdith (2022); coastline templates after Merdith et al. (2021)',
    },
}
NS = {'gml': 'http://www.opengis.net/gml', 'gpml': 'http://www.gplates.org/gplates'}
LICENSE = 'https://creativecommons.org/licenses/by/4.0/'


def digest(path, name='sha256'):
    return hashlib.new(name, path.read_bytes()).hexdigest()


def time_value(value, fallback):
    if value is None:
        return fallback
    if value.endswith('distantPast'):
        return math.inf
    if value.endswith('distantFuture'):
        return -math.inf
    return float(value)


def geometry_rows(data):
    doc = ET.fromstring(gzip.decompress(data))
    rows, skipped = [], 0
    for member in doc.findall('gml:featureMember', NS):
        pid = member.findtext('.//gpml:reconstructionPlateId/gpml:ConstantValue/gpml:value', namespaces=NS)
        # gpml:value can be wrapped differently between model versions.
        if pid is None:
            pid = member.findtext('.//gpml:reconstructionPlateId//gpml:value', namespaces=NS)
        if pid is None:
            skipped += 1
            continue
        pid = int(pid)
        feature_id = member.findtext('.//gpml:identity', namespaces=NS)
        name = member.findtext('.//gml:name', default=f'Plate {pid}', namespaces=NS)
        begin = time_value(member.findtext('.//gml:TimePeriod/gml:begin/gml:TimeInstant/gml:timePosition', namespaces=NS), math.inf)
        end = time_value(member.findtext('.//gml:TimePeriod/gml:end/gml:TimeInstant/gml:timePosition', namespaces=NS), 0)
        import_time = member.findtext('.//gpml:geometryImportTime//gml:timePosition', namespaces=NS)
        if import_time is not None and float(import_time) != 0:
            raise ValueError('Only present-day geometry templates are supported')
        for polygon_index, polygon in enumerate(member.findall('.//gml:Polygon', NS)):
            rings = []
            for positions in polygon.findall('.//gml:posList', NS):
                numbers = list(map(float, positions.text.split()))
                if len(numbers) % 2 or not all(math.isfinite(x) for x in numbers):
                    raise ValueError('Invalid GPML coordinates')
                ring = [(numbers[i+1], numbers[i]) for i in range(0, len(numbers), 2)]
                if any(abs(lon) > 180 or abs(lat) > 90 for lon, lat in ring):
                    raise ValueError('Coordinates outside geographic domain')
                if ring and ring[0] != ring[-1]:
                    ring.append(ring[0])
                if len(ring) < 4:
                    raise ValueError('Degenerate polygon ring')
                rings.append(ring)
            if not rings:
                skipped += 1
                continue
            # Standard little-endian WKB Polygon, retaining holes and every source vertex.
            wkb = bytearray(struct.pack('<BII', 1, 3, len(rings)))
            for ring in rings:
                wkb.extend(struct.pack('<I', len(ring)))
                for lon, lat in ring:
                    wkb.extend(struct.pack('<dd', lon, lat))
            rows.append({'featureId': feature_id, 'polygonIndex': polygon_index, 'plateId': pid,
                         'name': name, 'beginAge': begin, 'endAge': end, 'geometry': bytes(wkb)})
    if not rows:
        raise ValueError('No usable polygons')
    return rows, skipped


def metadata(model_id, model):
    return {b'math.gl.tectonic': json.dumps({
        'model': model_id, 'version': model['version'], 'referenceFrame': model['frame'],
        'source': model['record'], 'license': 'CC-BY-4.0', 'licenseUrl': LICENSE,
        'credit': model['credit'], 'anchorPlateId': 0, 'ageUnit': 'Ma before present',
    }, sort_keys=True).encode()}


def split_groups(table, count, unit=1):
    """Split complete units (one age's plates for rotations) across exactly count groups."""
    units = table.num_rows // unit
    if table.num_rows % unit or units < count:
        raise ValueError('Cannot split complete units into requested row groups')
    return [table.slice((i * units // count) * unit,
                        ((i + 1) * units // count - i * units // count) * unit)
            for i in range(count)]


def age_groups(table, plate_count, max_age):
    # Half-open 100 Ma windows, with the model's final endpoint in the last group.
    return [table.slice((start // 10) * plate_count,
                        ((min(start + 100, max_age) - start) // 10 +
                         (1 if start + 100 >= max_age else 0)) * plate_count)
            for start in range(0, max_age, 100)]


def write_table(path, table, groups):
    index = []
    for number, group in enumerate(groups):
        ages = group.column('age').drop_null().to_pylist() if 'age' in group.column_names else []
        record_type = (group.column('recordType')[0].as_py() if 'recordType' in group.column_names
                       else ('rotation' if ages else 'geometry'))
        index.append({'rowGroup': number, 'recordType': record_type, 'rows': group.num_rows,
                      'minAge': min(ages) if ages else None, 'maxAge': max(ages) if ages else None})
    table = table.replace_schema_metadata({**table.schema.metadata,
        b'math.gl.tectonic.rowGroups': json.dumps(index, sort_keys=True).encode()})
    # Writing one supplied chunk at a time preserves geometry/age boundaries.
    with pq.ParquetWriter(path, table.schema, compression='zstd', compression_level=6,
                          write_statistics=True) as writer:
        for group in groups:
            writer.write_table(group, row_group_size=group.num_rows)
    restored = pq.read_table(path)
    if not restored.equals(table):
        raise ValueError(f'Parquet round-trip mismatch: {path}')
    return {'path': path.name, 'bytes': path.stat().st_size, 'sha256': digest(path),
            'rows': table.num_rows, 'rowGroups': pq.ParquetFile(path).metadata.num_row_groups,
            'schema': str(table.schema), 'compression': 'ZSTD', 'compressionLevel': 6,
            'rowGroupIndex': index}


def convert(model_id, archive_path, output):
    model = MODELS[model_id]
    if digest(archive_path, 'md5') != model['archiveMD5']:
        raise ValueError(f'Archive does not match pinned Zenodo revision: {model_id}')
    dest = output / model_id.lower()
    dest.mkdir(parents=True, exist_ok=True)
    geometry_schema = pa.schema([
        ('featureId', pa.string()), ('polygonIndex', pa.int32()), ('plateId', pa.int32()),
        ('name', pa.string()), ('beginAge', pa.float64()), ('endAge', pa.float64()),
        ('geometry', pa.binary()),
    ], metadata=metadata(model_id, model))
    # GeoParquet uses implicit OGC:CRS84 longitude/latitude when crs is omitted.
    geo = {'version': '1.1.0', 'primary_column': 'geometry', 'columns': {'geometry': {
        'encoding': 'WKB', 'geometry_types': ['Polygon'], 'edges': 'spherical',
    }}}
    geometry_schema = geometry_schema.with_metadata({**geometry_schema.metadata, b'geo': json.dumps(geo).encode()})
    rotation_schema = pa.schema([
        ('age', pa.int16()), ('plateId', pa.int32()), ('available', pa.bool_()),
        ('w', pa.float64()), ('x', pa.float64()), ('y', pa.float64()), ('z', pa.float64()),
    ], metadata=metadata(model_id, model))
    with zipfile.ZipFile(archive_path) as archive, tempfile.TemporaryDirectory() as temp:
        source_hashes = {}
        for name in [model['geometry'], *model['rotations']]:
            source_hashes[name] = hashlib.sha256(archive.read(name)).hexdigest()
        geometry, skipped = geometry_rows(archive.read(model['geometry']))
        geometry_table = pa.Table.from_pylist(geometry, schema=geometry_schema)
        ids = sorted({row['plateId'] for row in geometry})
        rotation_paths = []
        for i, name in enumerate(model['rotations']):
            path = Path(temp) / f'{i}.rot'
            path.write_bytes(archive.read(name))
            rotation_paths.append(str(path))
        rotation_model = pygplates.RotationModel(rotation_paths, default_anchor_plate_id=0)
        all_rows = []
        for age in range(0, model['maxAge'] + 1, 10):
            for pid in ids:
                rotation = rotation_model.get_rotation(age, pid, use_identity_for_missing_plate_ids=False)
                if rotation is None:
                    q = [None] * 4
                else:
                    pole, angle = rotation.get_euler_pole_and_angle()
                    axis = pole.to_xyz()
                    sine = math.sin(angle / 2)
                    q = [math.cos(angle / 2), *(component * sine for component in axis)]
                    norm = math.sqrt(sum(value * value for value in q))
                    if not math.isfinite(norm) or abs(norm-1) > 1e-12:
                        raise ValueError('Non-unit quaternion')
                    q = [value / norm for value in q]
                all_rows.append(dict(zip(rotation_schema.names, [age, pid, rotation is not None, *q])))
        rotation_table = pa.Table.from_pylist(all_rows, schema=rotation_schema)
        if model_id == 'CAO2024':
            # A tagged union stores each template once, followed by rotation samples.
            # Geometry first makes the templates usable before the full timeline loads.
            combined_schema = pa.schema([
                ('recordType', pa.string()), *geometry_schema,
                *[field for field in rotation_schema if field.name != 'plateId'],
            ], metadata=geometry_schema.metadata)
            geometry_records = pa.Table.from_pylist(
                [dict(recordType='geometry', **row) for row in geometry], schema=combined_schema)
            rotation_records = pa.Table.from_pylist(
                [dict(recordType='rotation', **row) for row in all_rows], schema=combined_schema)
            table = pa.concat_tables([geometry_records, rotation_records])
            groups = [geometry_records, *age_groups(rotation_records, len(ids), model['maxAge'])]
            files = [write_table(dest / 'tectonic.parquet', table, groups)]
        else:
            files = [write_table(dest / 'geometry.parquet', geometry_table,
                                 split_groups(geometry_table, 10)),
                     write_table(dest / 'rotations.parquet', rotation_table,
                                 age_groups(rotation_table, len(ids), model['maxAge']))]
        # Check nontrivial quaternion orientation against pyGPlates' independent point rotation.
        reference_checks = 0
        point = pygplates.PointOnSphere(10, 20)
        px, py, pz = point.to_xyz()
        for row in all_rows:
            if not row['available'] or row['age'] not in (0, 100, 500, model['maxAge']):
                continue
            w, x, y, z = [row[name] for name in ['w', 'x', 'y', 'z']]
            tx, ty, tz = 2*(y*pz-z*py), 2*(z*px-x*pz), 2*(x*py-y*px)
            actual = (px+w*tx+y*tz-z*ty, py+w*ty+z*tx-x*tz, pz+w*tz+x*ty-y*tx)
            expected = (rotation_model.get_rotation(row['age'], row['plateId']) * point).to_xyz()
            if max(abs(a-b) for a,b in zip(actual,expected)) > 1e-12:
                raise ValueError('Quaternion coordinate convention mismatch')
            reference_checks += 1
    manifest = {
        'model': model_id, 'version': model['version'], 'dataset': model['record'],
        'license': 'CC-BY-4.0', 'licenseUrl': LICENSE, 'credit': model['credit'],
        'archiveMD5': digest(archive_path, 'md5'), 'archiveSHA256': digest(archive_path),
        'sourceFilesSHA256': source_hashes, 'referenceFrame': model['frame'],
        'anchorPlateId': 0, 'quaternionOrder': ['w','x','y','z'],
        'cartesianAxes': 'X at lon=0 lat=0, Y at lon=90 lat=0, Z at North Pole',
        'ages': {'unit': 'Ma before present', 'min': 0, 'max': model['maxAge'], 'step': 10},
        'geometry': 'Unreconstructed present-day source templates; WKB Polygon lon/lat degrees; spherical edges; holes retained; no simplification',
        'missingRotations': 'available=false and null quaternion; no fabricated identity rotation',
        'rowGroupLayout': '100 Ma rotation windows, final endpoint included in last group; Cao geometry first; Muller geometry in 10 groups',
        'changes': ['GPML templates converted to GeoParquet', 'Equivalent total rotations computed relative to anchor plate 0 at 10 Ma intervals', 'Raw source vertices retained; explicit ring closure added when absent', 'No plate topology, paleogeographic shoreline or future reconstruction exported'],
        'tools': {'pygplates': pygplates.__version__, 'pyarrow': pa.__version__},
        'verification': {'roundTrip': 'Every Parquet table equals its pre-write Arrow table',
                         'pointRotationChecks': reference_checks, 'unitQuaternionTolerance': 1e-12},
        'polygonRows': len(geometry), 'plateCount': len(ids), 'skippedSourceMembers': skipped,
        'files': files,
    }
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+'\n')
    pairing = ('Geometry and rotations share one tagged Parquet file.' if model_id == 'CAO2024'
               else 'Geometry and rotations must stay paired. Only the complete optimised mantle rotation model is used; the alternative paleomagnetic model is excluded.')
    (dest / 'ATTRIBUTION.md').write_text(f"# {model_id} Parquet snapshot\n\n{model['credit']}.\n\nSource: {model['record']} (version {model['version']}).\n\nLicense: [CC-BY-4.0]({LICENSE}). These data files are not relicensed as MIT.\n\nConverted by math.gl: present-day GPML polygons to GeoParquet, and finite rotations to 10 Ma quaternion samples. No source geometry simplification. See manifest.json for input/output checksums, exact frame, schemas, missing-data policy and conversion tools.\n\nThis snapshot represents this pinned model revision, not the mutable live GPlates service. {pairing}\n")
    print(model_id, json.dumps({'plates':len(ids), 'polygons':len(geometry), 'rotationRows':len(all_rows), 'files':[(f['path'],f['bytes']) for f in files]}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cao', type=Path, required=True)
    parser.add_argument('--muller', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    convert('CAO2024', args.cao, args.out)
    convert('MULLER2022', args.muller, args.out)
