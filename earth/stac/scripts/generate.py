# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Generate static STAC 1.1.0 from immutable dataset manifests (stdlib only)."""
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REPO = 'visgl/deck.gl-data'
FILE_EXTENSION = 'https://stac-extensions.github.io/file/v2.1.0/schema.json'
WORLD = [-180, -90, 180, 90]
GEOMETRY = {'type': 'Polygon', 'coordinates': [[
    [-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]]]}
SOURCES = [
    {'id': 'visgl-egm96', 'path': 'earth/geoid/v1',
     'commit': '676fb53ffef120e7ca4d1acdc91e94b4cc37ef69',
     'datetime': '2026-10-07T12:55:48Z', 'title': 'NGA EGM96 geoid grids'},
    {'id': 'visgl-cao2024', 'path': 'earth/tectonic-movements/v1/cao2024',
     'commit': '6b82e2df927725dc54ba729267204498d4ac6c74',
     'datetime': '2026-10-06T23:01:40Z', 'title': 'Cao et al. (2024) tectonic snapshot'},
    {'id': 'visgl-muller2022', 'path': 'earth/tectonic-movements/v1/muller2022',
     'commit': '6b82e2df927725dc54ba729267204498d4ac6c74',
     'datetime': '2026-10-06T23:01:40Z', 'title': 'Müller et al. (2022) tectonic snapshot'},
]


def url(source, name, media=False):
    prefix = f'https://media.githubusercontent.com/media/{REPO}' if media else f'https://raw.githubusercontent.com/{REPO}'
    return f"{prefix}/{source['commit']}/{source['path']}/{name}"


def link(rel, href, media_type='application/json', **extra):
    return dict(rel=rel, href=href, type=media_type, **extra)


def write(path, document):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, indent=2, ensure_ascii=False) + '\n')


def data_asset(source, name, info):
    return {'href': url(source, name, media=True), 'title': name,
            'type': 'application/vnd.apache.parquet' if name.endswith('.parquet') else 'image/x-portable-graymap',
            'roles': ['data'], 'file:size': info['bytes'],
            'file:checksum': '1220' + info['sha256']}


def item(source, suffix, description, assets, properties):
    identifier = f"{source['id']}-{suffix}"
    return {'type': 'Feature', 'stac_version': '1.1.0',
            'stac_extensions': [FILE_EXTENSION], 'id': identifier,
            'collection': source['id'], 'geometry': GEOMETRY, 'bbox': WORLD,
            'properties': {'datetime': source['datetime'], 'title': identifier,
                           'description': description,
                           'visgl:datetime_semantics': 'Repository dataset snapshot commit time; not observation time or geologic age',
                           'visgl:source_commit': source['commit'], **properties},
            'links': [link('root', '../catalog.json'), link('parent', 'collection.json'),
                      link('collection', 'collection.json'),
                      link('self', f'{suffix}.json', 'application/geo+json')],
            'assets': {**assets,
                       'manifest': {'href': url(source, 'manifest.json'), 'type': 'application/json', 'roles': ['metadata']},
                       'attribution': {'href': url(source, 'ATTRIBUTION.md'), 'type': 'text/markdown', 'roles': ['metadata']}}}


def generate():
    catalog = {'type': 'Catalog', 'stac_version': '1.1.0', 'id': 'visgl-earth',
               'title': 'vis.gl Earth datasets',
               'description': 'Static discovery catalog for version-pinned Earth datasets. Assets retain their own licenses; dates identify repository snapshots.',
               'links': [link('self', 'catalog.json'), link('root', 'catalog.json')]}
    for source in SOURCES:
        with urlopen(url(source, 'manifest.json')) as response:
            manifest = json.load(response)
        geoid = source['id'] == 'visgl-egm96'
        directory = source['id'].removeprefix('visgl-')
        description = ('Public-domain NGA EGM96 geoid undulation grids, distributed through GeographicLib. Heights N are meters above WGS84; h = H + N. Low resolution is a decimated preview, not terrain elevation.' if geoid else
                       'CC-BY-4.0 present-day geometry templates and finite rotations. Geometry is unreconstructed; geologic ages in Ma before present are separate from the STAC snapshot datetime. ' + manifest['credit'])
        license_url = ('https://raw.githubusercontent.com/OSGeo/PROJ-data/master/us_nga/us_nga_README.txt' if geoid else manifest['licenseUrl'])
        providers = ([{'name': 'US National Geospatial-Intelligence Agency', 'roles': ['producer']},
                      {'name': 'GeographicLib', 'roles': ['processor'], 'url': 'https://geographiclib.sourceforge.io/'}] if geoid else
                     [{'name': manifest['credit'], 'roles': ['producer', 'licensor'], 'url': manifest['dataset']}])
        providers.append({'name': 'vis.gl', 'roles': ['processor', 'host'], 'url': 'https://github.com/visgl/deck.gl-data'})
        collection = {'type': 'Collection', 'stac_version': '1.1.0', 'id': source['id'],
                      'title': source['title'], 'description': description,
                      'license': 'other' if geoid else manifest['license'], 'providers': providers,
                      'extent': {'spatial': {'bbox': [WORLD]},
                                 'temporal': {'interval': [[source['datetime'], source['datetime']]]}},
                      'links': [link('root', '../catalog.json'), link('parent', '../catalog.json'),
                                link('self', 'collection.json'), link('license', license_url, 'text/plain' if geoid else 'text/html'),
                                link('derived_from', manifest['source'] if geoid else manifest['dataset'], 'application/x-bzip2' if geoid else 'text/html')]}
        catalog['links'].append(link('child', f'{directory}/collection.json', title=source['title']))
        items = []
        if geoid:
            collection['summaries'] = {'geoid:spacing_arc_minutes': [15, 60], 'geoid:model': ['EGM96']}
            for resolution in ['low', 'hi']:
                stem = f'geoid-egm96-{resolution}'
                info = manifest['files'][stem + '.parquet']
                assets = {format_name: data_asset(source, stem + '.' + format_name, manifest['files'][stem + '.' + format_name]) for format_name in ['pgm', 'parquet']}
                items.append((resolution, item(source, resolution, description, assets,
                    {'geoid:model': 'EGM96', 'geoid:width': info['width'], 'geoid:height': info['height'],
                     'geoid:spacing_arc_minutes': info['spacingArcMinutes'], 'geoid:preview': info['preview'],
                     'geoid:height_units': 'meters', 'geoid:height_reference': 'WGS84 ellipsoid'})))
        else:
            collection['summaries'] = {'tectonic:model': [manifest['model']],
                                      'tectonic:age_min_ma': [manifest['ages']['min']],
                                      'tectonic:age_max_ma': [manifest['ages']['max']]}
            assets = {entry['path'].removesuffix('.parquet'): data_asset(source, entry['path'], entry) for entry in manifest['files']}
            items.append(('snapshot', item(source, 'snapshot', description, assets,
                {'tectonic:model': manifest['model'], 'tectonic:source_version': manifest['version'],
                 'tectonic:age_min_ma': manifest['ages']['min'], 'tectonic:age_max_ma': manifest['ages']['max'],
                 'tectonic:age_step_ma': manifest['ages']['step'], 'tectonic:reference_frame': manifest['referenceFrame'],
                 'tectonic:anchor_plate_id': manifest['anchorPlateId']})))
        for suffix, document in items:
            collection['links'].append(link('item', suffix + '.json', 'application/geo+json'))
            write(f'{directory}/{suffix}.json', document)
        write(f'{directory}/collection.json', collection)
    write('catalog.json', catalog)
    print('Generated 1 Catalog, 3 Collections, and 4 Items.')


if __name__ == '__main__':
    generate()
    from glaciations import generate_glaciations
    generate_glaciations()
    from reference import generate_reference
    generate_reference()

    from krapp2021 import generate_krapp
    generate_krapp()
