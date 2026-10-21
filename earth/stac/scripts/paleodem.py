# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Register the immutable, licensed PALEOMAP PaleoDEM node-table snapshot."""
import json
from generate import ROOT, WORLD, GEOMETRY, FILE_EXTENSION, link, write, url

COMMIT = 'eaa2649826c795492ee89a2632d863788545f2a2'
DATE = '2026-10-21T03:17:32Z'


def generate_paleodem():
    directory = ROOT.parent / 'paleogeography/v1/paleodem'
    manifest = json.loads((directory / 'manifest.json').read_text())
    source = {'commit': COMMIT, 'path': 'earth/paleogeography/v1/paleodem'}
    identifier = 'visgl-paleodem'
    title = 'Scotese and Wright (2018) PALEOMAP PaleoDEMs v2'
    description = ('109 reconstructed elevation/bathymetry grids at 5 Ma intervals, '
                   '0–540 Ma before present, converted losslessly from the licensed CSV v2 archive. '
                   'Numeric Parquet nodes, not vector geometries; one age grid per row group. '
                   'Source-specific grid dimensions and coordinates are preserved. '
                   'Geologic ages are separate from repository snapshot datetime.')
    collection = {
        'type': 'Collection', 'stac_version': '1.1.0', 'id': identifier,
        'title': title, 'description': description, 'license': manifest['license'],
        'providers': [
            {'name': 'Christopher R. Scotese and Nicky M. Wright',
             'roles': ['producer', 'licensor'], 'url': manifest['dataset']},
            {'name': 'vis.gl', 'roles': ['processor', 'host'],
             'url': 'https://github.com/visgl/deck.gl-data'}],
        'extent': {'spatial': {'bbox': [WORLD]},
                   'temporal': {'interval': [[DATE, DATE]]}},
        'summaries': {'paleo:age_min_ma': [0], 'paleo:age_max_ma': [540],
                      'paleo:age_step_ma': [5], 'paleo:age_unit': ['Ma before present']},
        'links': [link('root', '../catalog.json'), link('parent', '../catalog.json'),
                  link('self', 'collection.json'),
                  link('license', manifest['licenseUrl'], 'text/html'),
                  link('derived_from', manifest['dataset'], 'text/html'),
                  link('item', 'snapshot.json', 'application/geo+json')]}
    info = manifest['files'][0]
    assets = {
        'elevation': {'href': url(source, info['path'], media=True),
                      'type': 'application/vnd.apache.parquet', 'roles': ['data'],
                      'title': 'All 109 PaleoDEM age grids (ZSTD Parquet)',
                      'file:size': info['bytes'], 'file:checksum': '1220' + info['sha256']},
        'manifest': {'href': url(source, 'manifest.json'),
                     'type': 'application/json', 'roles': ['metadata']},
        'attribution': {'href': url(source, 'ATTRIBUTION.md'),
                        'type': 'text/markdown', 'roles': ['metadata']},
        'source-license': {'href': url(source, 'LICENSE.source.txt'),
                           'type': 'text/plain', 'roles': ['metadata']}}
    item = {
        'type': 'Feature', 'stac_version': '1.1.0', 'stac_extensions': [FILE_EXTENSION],
        'id': identifier + '-snapshot', 'collection': identifier,
        'geometry': GEOMETRY, 'bbox': WORLD,
        'properties': {'datetime': DATE, 'title': title, 'description': description,
                       'visgl:source_commit': COMMIT,
                       'visgl:datetime_semantics': 'Repository dataset snapshot commit time; not observation time or geologic age',
                       'paleo:age_min_ma': 0, 'paleo:age_max_ma': 540,
                       'paleo:age_step_ma': 5, 'paleo:age_count': 109,
                       'paleo:age_unit': 'Ma before present',
                       'paleo:coordinate_frame': manifest['coordinateFrame'],
                       'paleo:row_groups': info['rowGroups'], 'paleo:node_count': info['rows']},
        'links': [link('root', '../catalog.json'), link('parent', 'collection.json'),
                  link('collection', 'collection.json'),
                  link('self', 'snapshot.json', 'application/geo+json')], 'assets': assets}
    write('paleodem/collection.json', collection)
    write('paleodem/snapshot.json', item)
    catalog = json.loads((ROOT / 'catalog.json').read_text())
    catalog['links'] = [entry for entry in catalog['links']
                        if entry['href'] != 'paleodem/collection.json']
    catalog['links'].append(link('child', 'paleodem/collection.json', title=title))
    write('catalog.json', catalog)


if __name__ == '__main__':
    generate_paleodem()
