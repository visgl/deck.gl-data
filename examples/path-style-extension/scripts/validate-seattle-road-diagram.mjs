// deck.gl
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const SCRIPT_DIRECTORY = dirname(fileURLToPath(import.meta.url));
const REPOSITORY_ROOT = resolve(SCRIPT_DIRECTORY, '../../..');
const DATA_DIRECTORY = process.argv[2]
  ? resolve(REPOSITORY_ROOT, process.argv[2])
  : resolve(SCRIPT_DIRECTORY, '../data');

export function parseLengthFeet(value) {
  const match = String(value).trim().match(/^(\d+(?:\.\d+)?)\s*(?:'|ft)$/i);
  if (!match) {
    throw new Error(`Unsupported feet value: ${value}`);
  }
  return Number(match[1]) * 0.3048;
}

export function parseDashPattern(value) {
  if (/^solid$/i.test(String(value).trim())) {
    return [0, 0];
  }
  const match = String(value)
    .trim()
    .match(/^(\d+(?:\.\d+)?)'\s*(?:dash)?\s*[,/]?\s*(\d+(?:\.\d+)?)'\s*(?:skip|pattern)$/i);
  if (!match) {
    throw new Error(`Unsupported dash pattern: ${value}`);
  }
  return [Number(match[1]) * 0.3048, Number(match[2]) * 0.3048];
}

function visitCoordinates(geometry, visitor) {
  const visit = coordinates => {
    if (typeof coordinates[0] === 'number') {
      visitor(coordinates);
    } else {
      coordinates.forEach(visit);
    }
  };
  visit(geometry.coordinates);
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

const snapshot = JSON.parse(
  await readFile(resolve(DATA_DIRECTORY, 'seattle-road-diagram.json'), 'utf8')
);
const manifest = await readOptionalJson(
  resolve(DATA_DIRECTORY, 'seattle-road-diagram.manifest.json')
);

if (manifest) {
  assert.equal(snapshot.dataset, manifest.dataset);
  assert.deepEqual(snapshot.displayBounds, manifest.displayBounds);
  assert.equal(
    manifest.validation.extractionGate.passed,
    true,
    'candidate must pass extraction gate'
  );
  assert.deepEqual(
    Object.keys(snapshot.layers).sort(),
    manifest.sources.map(source => source.key).sort(),
    'manifest source keys'
  );
}

for (const [sourceKey, layer] of Object.entries(snapshot.layers)) {
  const features = layer.features;
  const source = manifest?.sources.find(candidate => candidate.key === sourceKey);
  if (source) {
    assert.equal(features.length, source.outputFeatureCount, `${sourceKey} output count`);
    assert.equal(source.rawFeatureCount, source.objectIds.length, `${sourceKey} object ID count`);
    assert.match(source.rawSha256, /^[a-f0-9]{64}$/);
    assert.ok(source.queryUrls.length > 0 || source.rawFeatureCount === 0);
  }
  for (const feature of features) {
    assert.ok(feature.geometry, `${sourceKey} feature has geometry`);
    assert.ok(feature.properties.OBJECTID != null, `${sourceKey} feature has an object ID`);
    visitCoordinates(feature.geometry, ([longitude, latitude]) => {
      assert.ok(longitude >= -180 && longitude <= 180);
      assert.ok(latitude >= -90 && latitude <= 90);
    });
  }
}

assert.deepEqual(parseDashPattern("2' dash, 4' skip"), [0.6096, 1.2192]);
assert.deepEqual(parseDashPattern("3' dash, 6' skip"), [0.9144000000000001, 1.8288000000000002]);
assert.deepEqual(parseDashPattern("3' dash, 9' skip"), [0.9144000000000001, 2.7432000000000003]);
assert.deepEqual(parseDashPattern("10'/20' pattern"), [3.048, 6.096]);
assert.deepEqual(parseDashPattern('Solid'), [0, 0]);
assert.throws(() => parseDashPattern('unknown'), /Unsupported dash pattern/);
assert.equal(parseLengthFeet("12'"), 3.6576000000000004);

assert.ok(snapshot.derived.laneBands.length >= 8);
assert.ok(snapshot.derived.crosswalkGuides.length >= 1);
for (const feature of [...snapshot.derived.laneBands, ...snapshot.derived.crosswalkGuides]) {
  assert.equal(feature.derived, true);
  assert.ok(feature.source.length >= 2);
  assert.ok(feature.derivation.operation);
}

const transverseMarkingObjectIds = new Set(
  snapshot.layers.transverseMarkings.features.map(feature => feature.properties.OBJECTID)
);
const matchedTransverseMarkingObjectIds = snapshot.derived.crosswalkGuides.flatMap(
  guide => guide.transverseMarkingObjectIds
);
assert.ok(matchedTransverseMarkingObjectIds.length > 0);
assert.equal(
  new Set(matchedTransverseMarkingObjectIds).size,
  matchedTransverseMarkingObjectIds.length,
  'a source transverse marking must not be matched to multiple crosswalks'
);
for (const objectId of matchedTransverseMarkingObjectIds) {
  assert.ok(transverseMarkingObjectIds.has(objectId), `matched transverse marking ${objectId} exists`);
}

const sourceSymbolPaths = snapshot.layers.symbols.features.flatMap(feature =>
  feature.geometry.type === 'LineString' ? [feature.geometry.coordinates] : feature.geometry.coordinates
);
assert.ok(snapshot.derived.symbolPaths.length < sourceSymbolPaths.length);
if (manifest) {
  const symbolStitching = manifest.validation.symbolStitching;
  assert.equal(symbolStitching.sourceFeatureCount, snapshot.layers.symbols.features.length);
  assert.equal(symbolStitching.sourcePathCount, sourceSymbolPaths.length);
  assert.equal(symbolStitching.outputPathCount, snapshot.derived.symbolPaths.length);
  assert.ok(symbolStitching.maximumJoinDistanceMeters <= 0.002);
  assert.ok(
    symbolStitching.maximumBridgeDistanceMeters <= symbolStitching.maximumJoinDistanceMeters
  );
}

const symbolPathsByObjectId = Map.groupBy(
  snapshot.derived.symbolPaths,
  symbolPath => symbolPath.source[0].objectId
);
for (const feature of snapshot.layers.symbols.features) {
  const stitchedPaths = symbolPathsByObjectId.get(feature.properties.OBJECTID);
  assert.ok(stitchedPaths?.length > 0, `symbol ${feature.properties.OBJECTID} has display paths`);
  const stitchedCoordinates = new Set(
    stitchedPaths.flatMap(symbolPath => symbolPath.path.map(coordinate => JSON.stringify(coordinate)))
  );
  visitCoordinates(feature.geometry, coordinate => {
    assert.ok(
      stitchedCoordinates.has(JSON.stringify(coordinate)),
      `symbol ${feature.properties.OBJECTID} source coordinate was retained`
    );
  });
  for (const symbolPath of stitchedPaths) {
    assert.equal(symbolPath.derived, true);
    assert.equal(symbolPath.source.length, 1);
    assert.equal(symbolPath.derivation.operation, 'endpoint-connected CAD fragment stitching');
    assert.ok(symbolPath.path.length >= 2);
  }
}

const groupedLaneBands = Map.groupBy(snapshot.derived.laneBands, lane => lane.source[0].objectId);
for (const lanes of groupedLaneBands.values()) {
  const offsets = lanes.map(lane => lane.offsetWidths).sort((valueA, valueB) => valueA - valueB);
  assert.equal(offsets[0], -offsets.at(-1));
  assert.ok(lanes.every(lane => lane.widthMeters > 0));
}

const sourceFeatureCount = Object.values(snapshot.layers).reduce(
  (total, layer) => total + layer.features.length,
  0
);
const validationScope = manifest ? ' with provenance checks' : '';
console.log(
  `Validated ${sourceFeatureCount} source features, ${snapshot.derived.laneBands.length} lane bands, ${snapshot.derived.crosswalkGuides.length} crosswalk guides, and ${snapshot.derived.symbolPaths.length} stitched symbol paths${validationScope}.`
);
