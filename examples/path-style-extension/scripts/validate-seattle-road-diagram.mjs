// deck.gl
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

import {
  getScreenDashPattern,
  parseDashPattern,
  parseMarkingWidth
} from './extract-seattle-road-diagram.mjs';

const SCRIPT_DIRECTORY = dirname(fileURLToPath(import.meta.url));
const REPOSITORY_ROOT = resolve(SCRIPT_DIRECTORY, '../../..');
const DATA_DIRECTORY = process.argv[2]
  ? resolve(REPOSITORY_ROOT, process.argv[2])
  : resolve(SCRIPT_DIRECTORY, '../data');

const ASSET_GEOMETRY = {
  roadSurfaces: 'path',
  sidewalks: 'path',
  backgroundPaths: 'path',
  laneBands: 'path',
  bikePanels: 'polygon',
  crosswalks: 'path',
  transversePolygons: 'polygon',
  transversePaths: 'path',
  longitudinalMarkings: 'path',
  curbs: 'path',
  symbols: 'path'
};

function visitCoordinates(coordinates, visitor) {
  if (typeof coordinates[0] === 'number') {
    visitor(coordinates);
  } else {
    coordinates.forEach(coordinate => visitCoordinates(coordinate, visitor));
  }
}

async function readOptionalJson(path) {
  try {
    return JSON.parse(await readFile(path, 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') {
      return null;
    }
    throw error;
  }
}

function validateStyle(asset, assetKey) {
  if (!asset.style) {
    return;
  }
  for (const widthKey of ['widthMeters', 'widthPixels']) {
    if (asset.style[widthKey] !== undefined) {
      assert.ok(asset.style[widthKey] > 0, `${asset.id} ${widthKey}`);
    }
  }
  if (asset.style.offset !== undefined) {
    assert.equal(typeof asset.style.offset, 'number', `${asset.id} offset`);
  }
  if (asset.style.colorRole !== undefined) {
    assert.ok(
      ['whiteMarking', 'yellowMarking'].includes(asset.style.colorRole),
      `${asset.id} color role`
    );
  }
  for (const dashKey of ['dashMeters', 'dashPixels']) {
    if (asset.style[dashKey] !== undefined) {
      assert.equal(asset.style[dashKey].length, 2, `${asset.id} ${dashKey}`);
      assert.ok(asset.style[dashKey].every(value => value >= 0), `${asset.id} ${dashKey}`);
    }
  }
  if (asset.style.dashMode !== undefined) {
    assert.equal(asset.style.dashMode, 'path', `${asset.id} dash mode`);
    assert.equal(typeof asset.style.dashJustified, 'boolean', `${asset.id} justified`);
    assert.equal(typeof asset.style.dashGapPickable, 'boolean', `${asset.id} gap picking`);
    assert.ok(asset.style.dashMeters, `${asset.id} meter dash pattern`);
    assert.ok(asset.style.dashPixels, `${asset.id} pixel dash pattern`);
  }
  if (assetKey === 'longitudinalMarkings') {
    assert.ok(asset.style.widthMeters && asset.style.widthPixels, `${asset.id} marking widths`);
    assert.ok(asset.style.colorRole, `${asset.id} marking color`);
  }
}

const snapshot = JSON.parse(
  await readFile(resolve(DATA_DIRECTORY, 'seattle-road-diagram.json'), 'utf8')
);
const manifest = await readOptionalJson(
  resolve(DATA_DIRECTORY, 'seattle-road-diagram.manifest.json')
);

assert.equal(snapshot.layers, undefined, 'runtime snapshot must not include raw layers');
assert.equal(snapshot.derived, undefined, 'runtime snapshot must not include extraction intermediates');
assert.deepEqual(Object.keys(snapshot.assets).sort(), Object.keys(ASSET_GEOMETRY).sort());
assert.equal(snapshot.displayBounds.length, 4);

const assetIds = new Set();
for (const [assetKey, geometryKey] of Object.entries(ASSET_GEOMETRY)) {
  const assets = snapshot.assets[assetKey];
  assert.ok(Array.isArray(assets), `${assetKey} collection`);
  assert.ok(assets.length > 0, `${assetKey} is not empty`);
  for (const asset of assets) {
    assert.ok(asset.id, `${assetKey} asset ID`);
    assert.ok(!assetIds.has(asset.id), `duplicate asset ID ${asset.id}`);
    assetIds.add(asset.id);
    assert.ok(asset.label, `${asset.id} label`);
    assert.ok(Array.isArray(asset.details), `${asset.id} details`);
    assert.ok(Array.isArray(asset.source) && asset.source.length > 0, `${asset.id} source`);
    for (const detail of asset.details) {
      assert.ok(detail.label && detail.value !== undefined, `${asset.id} detail`);
    }
    for (const source of asset.source) {
      assert.ok(source.provider && source.layerName, `${asset.id} source description`);
      assert.ok(source.itemId && source.objectId != null, `${asset.id} source identity`);
      assert.doesNotThrow(() => new URL(source.url), `${asset.id} source URL`);
    }
    const coordinates = asset[geometryKey];
    assert.ok(Array.isArray(coordinates) && coordinates.length >= 2, `${asset.id} geometry`);
    visitCoordinates(coordinates, ([longitude, latitude]) => {
      assert.ok(longitude >= -180 && longitude <= 180, `${asset.id} longitude`);
      assert.ok(latitude >= -90 && latitude <= 90, `${asset.id} latitude`);
    });
    if (geometryKey === 'polygon') {
      assert.deepEqual(coordinates[0], coordinates.at(-1), `${asset.id} closed polygon`);
    }
    validateStyle(asset, assetKey);
  }
}

assert.ok(snapshot.assets.laneBands.length >= 8);
assert.ok(snapshot.assets.crosswalks.length >= 1);
assert.ok(snapshot.assets.symbols.length > 0);
assert.ok(
  snapshot.assets.crosswalks.every(
    asset => asset.style.dashJustified && asset.style.dashGapPickable
  )
);
assert.ok(
  snapshot.assets.longitudinalMarkings.every(
    asset => !asset.style.dashJustified && asset.style.dashGapPickable
  )
);

const groupedLaneBands = Map.groupBy(
  snapshot.assets.laneBands,
  lane => lane.source[0].objectId
);
for (const lanes of groupedLaneBands.values()) {
  const offsets = lanes.map(lane => lane.style.offset).sort((valueA, valueB) => valueA - valueB);
  assert.equal(offsets[0], -offsets.at(-1));
}

assert.deepEqual(parseDashPattern("2' dash, 4' skip"), [0.6096, 1.2192]);
assert.deepEqual(parseDashPattern("3' dash, 6' skip"), [0.9144000000000001, 1.8288000000000002]);
assert.deepEqual(parseDashPattern("3' dash, 9' skip"), [0.9144000000000001, 2.7432000000000003]);
assert.deepEqual(parseDashPattern("10'/20' pattern"), [3.048, 6.096]);
assert.deepEqual(parseDashPattern('Solid'), [0, 0]);
assert.deepEqual(getScreenDashPattern([0.6096, 1.2192]), [4, 8]);
assert.equal(parseMarkingWidth('6"'), 0.15239999999999998);
assert.throws(() => parseDashPattern('unknown'), /Unsupported dash pattern/);

if (manifest) {
  assert.equal(snapshot.dataset, manifest.dataset);
  assert.deepEqual(snapshot.displayBounds, manifest.displayBounds);
  assert.equal(
    manifest.validation.extractionGate.passed,
    true,
    'candidate must pass extraction gate'
  );
  assert.deepEqual(
    Object.fromEntries(
      Object.entries(snapshot.assets).map(([key, assets]) => [key, assets.length])
    ),
    manifest.validation.renderAssetCounts
  );

  const manifestSources = new Map(
    manifest.sources.map(source => [`${source.itemId}/${source.layerId}`, source])
  );
  for (const source of manifest.sources) {
    assert.equal(source.rawFeatureCount, source.objectIds.length, `${source.key} object ID count`);
    assert.match(source.rawSha256, /^[a-f0-9]{64}$/);
    assert.ok(source.queryUrls.length > 0 || source.rawFeatureCount === 0);
  }
  for (const assets of Object.values(snapshot.assets)) {
    for (const asset of assets) {
      for (const source of asset.source) {
        const manifestSource = manifestSources.get(`${source.itemId}/${source.layerId}`);
        assert.ok(manifestSource, `${asset.id} manifest source`);
        assert.ok(
          manifestSource.objectIds.some(objectId => String(objectId) === String(source.objectId)),
          `${asset.id} manifest object ID`
        );
      }
    }
  }

  assert.equal(
    manifest.validation.symbolStitching.outputPathCount,
    snapshot.assets.symbols.length
  );
  assert.ok(
    manifest.validation.symbolStitching.outputPathCount <
      manifest.validation.symbolStitching.sourcePathCount
  );
  assert.ok(manifest.validation.symbolStitching.maximumJoinDistanceMeters <= 0.002);
  assert.ok(
    manifest.validation.symbolStitching.maximumBridgeDistanceMeters <=
      manifest.validation.symbolStitching.maximumJoinDistanceMeters
  );
}

const assetCount = Object.values(snapshot.assets).reduce(
  (total, assets) => total + assets.length,
  0
);
const validationScope = manifest ? ' with provenance checks' : '';
console.log(
  `Validated ${assetCount} render assets across ${Object.keys(snapshot.assets).length} collections${validationScope}.`
);
