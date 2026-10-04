// deck.gl
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {mkdir, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const SCRIPT_DIRECTORY = dirname(fileURLToPath(import.meta.url));
const REPOSITORY_ROOT = resolve(SCRIPT_DIRECTORY, '../../..');
const DEFAULT_DATA_DIRECTORY = resolve(SCRIPT_DIRECTORY, '../data');

export const DISPLAY_BOUNDS = [-122.3431, 47.62025, -122.3415, 47.6215];
export const CANDIDATE_NAME = 'Dexter Avenue N and Thomas Street, Seattle, Washington';

const CHANNELIZATION_URL =
  'https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/SDOT_Channelization_view/FeatureServer';
const SEATTLE_SERVICE_ROOT =
  'https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services';

export const SOURCES = [
  ...[
    ['verticalElements', 0, 'VerticalElements'],
    ['laneWidths', 1, 'LaneWidth'],
    ['background', 2, 'GENBKGRND'],
    ['panelMarkings', 3, 'PanelMarkings'],
    ['longitudinalMarkings', 4, 'Longitudinal_Markings'],
    ['transverseMarkings', 5, 'TransverseMarkings'],
    ['symbols', 6, 'Legend_and_Symbols']
  ].map(([key, layerId, layerName]) => ({
    key,
    provider: 'City of Seattle Department of Transportation',
    itemId: 'e7c54ba0f1b24128a9cb2a95912a5194',
    serviceUrl: CHANNELIZATION_URL,
    layerId,
    layerName,
    where: '1=1',
    catalogUrl:
      'https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/SDOT_Channelization_view/FeatureServer'
  })),
  {
    key: 'streets',
    provider: 'City of Seattle Department of Transportation',
    itemId: 'f91318f1cc43489fb0e7aca2fde22899',
    serviceUrl: `${SEATTLE_SERVICE_ROOT}/Seattle_Streets_1/FeatureServer`,
    layerId: 0,
    layerName: 'Seattle Streets',
    where: "STATUS = 'INSVC'",
    catalogUrl: 'https://catalog.data.gov/dataset/seattle-streets'
  },
  {
    key: 'sidewalks',
    provider: 'City of Seattle Department of Transportation',
    itemId: '20abc2269f6f4283a53cf31b93de718f',
    serviceUrl: `${SEATTLE_SERVICE_ROOT}/Sidewalks_CDL/FeatureServer`,
    layerId: 0,
    layerName: 'Sidewalks',
    where: "CURRENT_STATUS IN ('INSVC', 'PLNRECON') OR CURRENT_STATUS = ''",
    catalogUrl: 'https://catalog.data.gov/dataset/sidewalks-32d94'
  },
  {
    key: 'crosswalks',
    provider: 'City of Seattle Department of Transportation',
    itemId: '53635945962e42b9a1f4473557176861',
    serviceUrl: `${SEATTLE_SERVICE_ROOT}/Marked_Crosswalks_CDL/FeatureServer`,
    layerId: 0,
    layerName: 'Marked Crosswalks',
    where: "CURRENT_STATUS IN ('INSVC', 'PLNRECON') OR CURRENT_STATUS = ''",
    catalogUrl: 'https://catalog.data.gov/dataset/marked-crosswalks'
  },
  {
    key: 'bikeFacilities',
    provider: 'City of Seattle Department of Transportation',
    itemId: 'bf36bd11b499489d8cc1d491b72eb712',
    serviceUrl: `${SEATTLE_SERVICE_ROOT}/SDOT_Bike_Facilities/FeatureServer`,
    layerId: 2,
    layerName: 'Existing Bike Facilities',
    where: "CURRENT_STATUS = 'INSVC'",
    catalogUrl: 'https://catalog.data.gov/dataset/existing-bike-facilities'
  }
];

const IMPORTANT_FIELDS = [
  'Type',
  'UseDesignation',
  'Width',
  'Color',
  'Material',
  'DataConfidence'
];
const FEET_TO_METERS = 0.3048;
const INCHES_TO_METERS = 0.0254;
const DEFAULT_MARKING_WIDTH_METERS = 0.15;
const DEFAULT_MARKING_WIDTH_PIXELS = 2;
// Screen-space scale of crossing rows, close to their physical size at the example's initial zoom
const CROSSING_PIXELS_PER_METER = 8;
const APPROACH_LANE_WIDTH_FEET = 12;
const APPROACH_LANE_WIDTH_METERS = APPROACH_LANE_WIDTH_FEET * FEET_TO_METERS;
export const SYMBOL_JOIN_TOLERANCE_METERS = 0.002;
// Repeated rectangles of equal size, at most this far apart, are redrawn as one dashed row.
export const ROW_TOLERANCE_METERS = 0.03;
const MAXIMUM_ROW_PITCH_METERS = 2.5;
const MINIMUM_ROW_DASH_COUNT = 4;
const CROSSWALK_MATCH_DISTANCE_METERS = 5;
// Parallel lines this far apart are redrawn as one shared path with two offsets, if both copies
// stay within the tolerance of their source line. Shorter pairs would cut lines into small pieces.
const DOUBLE_LINE_SEPARATION_METERS = [0.1, 0.5];
export const DOUBLE_LINE_TOLERANCE_METERS = 0.04;
const MINIMUM_DOUBLE_LINE_LENGTH_METERS = 10;
const LOCAL_ORIGIN = [
  (DISPLAY_BOUNDS[0] + DISPLAY_BOUNDS[2]) / 2,
  (DISPLAY_BOUNDS[1] + DISPLAY_BOUNDS[3]) / 2
];
// Only Dexter has nearby 12-foot annotations aligned with its centerline. Thomas Street remains
// visible as an official surface but is not split into inferred lanes.
const APPROACH_ROAD_KEYS = new Set([10072, 10073]);

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function formatDate(timestamp) {
  return timestamp ? new Date(timestamp).toISOString() : null;
}

function getGeneratorCommit() {
  if (process.env.GITHUB_SHA) {
    return process.env.GITHUB_SHA;
  }
  return execFileSync('git', ['rev-parse', 'HEAD'], {
    cwd: REPOSITORY_ROOT,
    encoding: 'utf8'
  }).trim();
}

function createQueryUrl(source, extraParameters = {}) {
  const url = new URL(`${source.serviceUrl}/${source.layerId}/query`);
  const parameters = {
    f: 'json',
    where: source.where,
    geometry: DISPLAY_BOUNDS.join(','),
    geometryType: 'esriGeometryEnvelope',
    inSR: '4326',
    spatialRel: 'esriSpatialRelIntersects',
    ...extraParameters
  };
  for (const [key, value] of Object.entries(parameters)) {
    url.searchParams.set(key, String(value));
  }
  return url;
}

async function fetchText(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${url}`);
  }
  return response.text();
}

async function fetchJson(url) {
  const text = await fetchText(url);
  const data = JSON.parse(text);
  if (data.error) {
    throw new Error(`${data.error.message}: ${url}`);
  }
  return {data, text};
}

async function querySource(source) {
  const metadataUrl = `${source.serviceUrl}/${source.layerId}?f=json`;
  const [{data: metadata}, {data: idResponse}] = await Promise.all([
    fetchJson(metadataUrl),
    fetchJson(createQueryUrl(source, {returnIdsOnly: true, returnGeometry: false}))
  ]);
  const objectIds = [...(idResponse.objectIds || [])].sort((a, b) => a - b);
  const objectIdField = metadata.objectIdField || metadata.objectIdFieldName || 'OBJECTID';
  // Keep object-ID query strings below conservative proxy and CDN URL-length limits.
  const pageSize = Math.min(metadata.maxRecordCount || 1000, 100);
  const responses = [];
  const features = [];
  const queryUrls = [];

  for (let index = 0; index < objectIds.length; index += pageSize) {
    const page = objectIds.slice(index, index + pageSize);
    const url = createQueryUrl(source, {
      f: 'geojson',
      objectIds: page.join(','),
      outFields: '*',
      outSR: 4326,
      returnGeometry: true
    });
    // Object IDs already encode the bounded query; omitting the envelope from page requests
    // makes the downloaded query URL easier to reproduce independently.
    url.searchParams.delete('geometry');
    url.searchParams.delete('geometryType');
    url.searchParams.delete('inSR');
    url.searchParams.delete('spatialRel');
    const {data, text} = await fetchJson(url);
    responses.push(text);
    queryUrls.push(url.toString());
    features.push(...(data.features || []));
  }

  features.sort(
    (featureA, featureB) =>
      Number(featureA.properties[objectIdField]) - Number(featureB.properties[objectIdField])
  );

  return {
    metadata,
    objectIdField,
    objectIds,
    queryUrls,
    rawText: responses.join('\n'),
    featureCollection: {type: 'FeatureCollection', features}
  };
}

function visitCoordinates(geometry, visitor) {
  if (!geometry) {
    return;
  }
  const visit = coordinates => {
    if (typeof coordinates[0] === 'number') {
      visitor(coordinates);
    } else {
      for (const child of coordinates) {
        visit(child);
      }
    }
  };
  visit(geometry.coordinates);
}

function getCoordinateCount(geometry) {
  let count = 0;
  visitCoordinates(geometry, () => count++);
  return count;
}

function getBounds(features) {
  const bounds = [Infinity, Infinity, -Infinity, -Infinity];
  for (const feature of features) {
    visitCoordinates(feature.geometry, ([longitude, latitude]) => {
      bounds[0] = Math.min(bounds[0], longitude);
      bounds[1] = Math.min(bounds[1], latitude);
      bounds[2] = Math.max(bounds[2], longitude);
      bounds[3] = Math.max(bounds[3], latitude);
    });
  }
  return Number.isFinite(bounds[0]) ? bounds : null;
}

function validateQueriedSources(resultsByKey) {
  for (const [sourceKey, result] of Object.entries(resultsByKey)) {
    for (const feature of result.featureCollection.features) {
      if (!feature.geometry) {
        throw new Error(`${sourceKey} feature is missing geometry`);
      }
      if (feature.properties.OBJECTID == null) {
        throw new Error(`${sourceKey} feature is missing an object ID`);
      }
      visitCoordinates(feature.geometry, ([longitude, latitude]) => {
        if (longitude < -180 || longitude > 180 || latitude < -90 || latitude > 90) {
          throw new Error(`${sourceKey} feature has an invalid coordinate`);
        }
      });
    }
  }
}

function getDistinctValues(features, field) {
  return [
    ...new Set(
      features
        .map(feature => feature.properties[field])
        .filter(value => value !== null && value !== undefined && value !== '')
    )
  ].sort((valueA, valueB) => String(valueA).localeCompare(String(valueB)));
}

function getDuplicateCounts(features, objectIdField) {
  const exact = new Map();
  const near = new Map();
  for (const feature of features) {
    const properties = {...feature.properties};
    delete properties[objectIdField];
    const exactKey = JSON.stringify([feature.geometry, properties]);
    exact.set(exactKey, (exact.get(exactKey) || 0) + 1);

    const roundedCoordinates = JSON.stringify(feature.geometry, (key, value) =>
      typeof value === 'number' ? Number(value.toFixed(6)) : value
    );
    const nearKey = `${roundedCoordinates}:${properties.Type}:${properties.Color}`;
    near.set(nearKey, (near.get(nearKey) || 0) + 1);
  }
  const countExtras = values =>
    [...values.values()].reduce((total, count) => total + Math.max(0, count - 1), 0);
  return {exact: countExtras(exact), near: countExtras(near)};
}

function summarizeSource(result) {
  const features = result.featureCollection.features;
  const coordinateCounts = features.map(feature => getCoordinateCount(feature.geometry)).sort((a, b) => a - b);
  const percentile = ratio =>
    coordinateCounts.length
      ? coordinateCounts[Math.min(coordinateCounts.length - 1, Math.floor(coordinateCounts.length * ratio))]
      : 0;
  const nullRates = Object.fromEntries(
    IMPORTANT_FIELDS.map(field => [
      field,
      features.length
        ? features.filter(feature => feature.properties[field] == null || feature.properties[field] === '')
            .length / features.length
        : 1
    ])
  );

  return {
    featureCount: features.length,
    objectIds: result.objectIds,
    geometryTypes: [...new Set(features.map(feature => feature.geometry?.type || 'null'))].sort(),
    multipartCount: features.filter(feature => feature.geometry?.type.startsWith('Multi')).length,
    coordinateCount: {
      minimum: coordinateCounts[0] || 0,
      median: percentile(0.5),
      p95: percentile(0.95),
      maximum: coordinateCounts.at(-1) || 0
    },
    bounds: getBounds(features),
    nullRates,
    distinctValues: Object.fromEntries(
      IMPORTANT_FIELDS.map(field => [field, getDistinctValues(features, field)])
    ),
    duplicates: getDuplicateCounts(features, result.objectIdField)
  };
}

function getLinePaths(geometry) {
  if (geometry?.type === 'LineString') {
    return [geometry.coordinates];
  }
  if (geometry?.type === 'MultiLineString') {
    return geometry.coordinates;
  }
  return [];
}

function getDistanceMeters(pointA, pointB) {
  const [x, y] = toLocalMeters(pointB, pointA);
  return Math.hypot(x, y);
}

function appendPath(path, addition, maximumDistanceMeters) {
  const distanceMeters = getDistanceMeters(path.at(-1), addition[0]);
  if (distanceMeters > maximumDistanceMeters) {
    return null;
  }
  return {
    path: distanceMeters === 0 ? [...path, ...addition.slice(1)] : [...path, ...addition],
    bridgeDistanceMeters: distanceMeters
  };
}

/**
 * Joins CAD fragments whose endpoints are coincident or separated by a sub-survey-scale gap.
 * Every source coordinate is retained; a nonzero gap is represented by an explicit bridge segment.
 */
export function stitchLinePaths(paths, maximumDistanceMeters = SYMBOL_JOIN_TOLERANCE_METERS) {
  const remaining = paths
    .map((path, sourcePathIndex) => ({path, sourcePathIndex}))
    .filter(({path}) => path.length >= 2);
  const stitchedPaths = [];

  const findNearestMatch = (endpoint, matchAtEnd) => {
    let nearest = null;
    for (let remainingIndex = 0; remainingIndex < remaining.length; remainingIndex++) {
      const candidate = remaining[remainingIndex];
      for (const reverse of [false, true]) {
        const coordinate = matchAtEnd
          ? reverse
            ? candidate.path[0]
            : candidate.path.at(-1)
          : reverse
            ? candidate.path.at(-1)
            : candidate.path[0];
        const distanceMeters = getDistanceMeters(endpoint, coordinate);
        if (
          distanceMeters <= maximumDistanceMeters &&
          (!nearest ||
            distanceMeters < nearest.distanceMeters ||
            (distanceMeters === nearest.distanceMeters &&
              candidate.sourcePathIndex < nearest.candidate.sourcePathIndex))
        ) {
          nearest = {candidate, distanceMeters, remainingIndex, reverse};
        }
      }
    }
    return nearest;
  };

  while (remaining.length) {
    const first = remaining.shift();
    let path = [...first.path];
    const sourcePathIndexes = [first.sourcePathIndex];
    const bridgeDistancesMeters = [];

    for (const extendAtStart of [false, true]) {
      let match = findNearestMatch(extendAtStart ? path[0] : path.at(-1), extendAtStart);
      while (match) {
        const {candidate, remainingIndex, reverse} = match;
        remaining.splice(remainingIndex, 1);
        const orientedPath = reverse ? candidate.path.toReversed() : candidate.path;
        const joined = extendAtStart
          ? appendPath(orientedPath, path, maximumDistanceMeters)
          : appendPath(path, orientedPath, maximumDistanceMeters);
        path = joined.path;
        sourcePathIndexes.push(candidate.sourcePathIndex);
        if (joined.bridgeDistanceMeters > 0) {
          bridgeDistancesMeters.push(joined.bridgeDistanceMeters);
        }
        match = findNearestMatch(extendAtStart ? path[0] : path.at(-1), extendAtStart);
      }
    }

    const closingDistanceMeters = getDistanceMeters(path[0], path.at(-1));
    if (closingDistanceMeters > 0 && closingDistanceMeters <= maximumDistanceMeters) {
      path.push(path[0]);
      bridgeDistancesMeters.push(closingDistanceMeters);
    }

    stitchedPaths.push({
      path,
      sourcePathIndexes: sourcePathIndexes.toSorted((indexA, indexB) => indexA - indexB),
      bridgeDistancesMeters
    });
  }

  return stitchedPaths;
}

function toLocalMeters([longitude, latitude], origin) {
  const latitudeRadians = (origin[1] * Math.PI) / 180;
  return [
    (longitude - origin[0]) * 111320 * Math.cos(latitudeRadians),
    (latitude - origin[1]) * 110540
  ];
}

function fromLocalMeters([x, y], origin) {
  const latitudeRadians = (origin[1] * Math.PI) / 180;
  return [origin[0] + x / (111320 * Math.cos(latitudeRadians)), origin[1] + y / 110540];
}

function getPointToSegmentDistance(point, start, end) {
  const origin = point;
  const [startX, startY] = toLocalMeters(start, origin);
  const [endX, endY] = toLocalMeters(end, origin);
  const segmentLengthSquared = (endX - startX) ** 2 + (endY - startY) ** 2;
  const ratio = segmentLengthSquared
    ? Math.max(
        0,
        Math.min(1, (-(startX) * (endX - startX) + -(startY) * (endY - startY)) / segmentLengthSquared)
      )
    : 0;
  return Math.hypot(startX + ratio * (endX - startX), startY + ratio * (endY - startY));
}

function getPointToPathDistance(point, path) {
  let distance = Infinity;
  for (let index = 1; index < path.length; index++) {
    distance = Math.min(distance, getPointToSegmentDistance(point, path[index - 1], path[index]));
  }
  return distance;
}

function isClosedPath(path) {
  const first = path[0];
  const last = path.at(-1);
  return path.length >= 4 && first[0] === last[0] && first[1] === last[1];
}

function getPathCentroid(path) {
  const coordinates = isClosedPath(path) ? path.slice(0, -1) : path;
  return coordinates
    .reduce(
      ([longitude, latitude], coordinate) => [
        longitude + coordinate[0] / coordinates.length,
        latitude + coordinate[1] / coordinates.length
      ],
      [0, 0]
    );
}

function getSourceRef(source, feature) {
  return {
    provider: source.provider,
    itemId: source.itemId,
    layerId: source.layerId,
    layerName: source.layerName,
    objectId: feature.properties.OBJECTID,
    url: `${source.serviceUrl}/${source.layerId}/${encodeURIComponent(feature.properties.OBJECTID)}`
  };
}

export function parseDashPattern(value) {
  if (!value || /^solid$/i.test(String(value).trim())) {
    return [0, 0];
  }
  const match = String(value)
    .trim()
    .match(/^(\d+(?:\.\d+)?)'\s*(?:dash)?\s*[,\/]?\s*(\d+(?:\.\d+)?)'\s*(?:skip|pattern)$/i);
  if (!match) {
    throw new Error(`Unsupported dash pattern: ${value}`);
  }
  return [Number(match[1]) * FEET_TO_METERS, Number(match[2]) * FEET_TO_METERS];
}

export function getScreenDashPattern(pattern) {
  if (!pattern[0] || !pattern[1]) {
    return [0, 0];
  }
  const dashPixels = pattern[0] <= 0.7 ? 4 : 6;
  return [dashPixels, dashPixels * (pattern[1] / pattern[0])];
}

export function parseMarkingWidth(value) {
  if (typeof value === 'number' && value > 0) {
    return value * INCHES_TO_METERS;
  }
  const match = String(value || '').match(/^(\d+(?:\.\d+)?)\s*(?:"|in)$/i);
  return match ? Number(match[1]) * INCHES_TO_METERS : null;
}

function getPathLengthMeters(path) {
  let lengthMeters = 0;
  for (let index = 1; index < path.length; index++) {
    lengthMeters += getDistanceMeters(path[index - 1], path[index]);
  }
  return lengthMeters;
}

function getSidewalkWidthMeters(asset) {
  return Math.max(1.5, Number(asset.sourceProperties.SW_WIDTH || 72) * INCHES_TO_METERS);
}

function createDetails(properties) {
  return [
    ['Type', properties.Type || properties.MARKING_TYPE],
    ['Color', properties.Color],
    ['Width', properties.Width],
    ['Material', properties.Material]
  ]
    .filter(([, value]) => value !== null && value !== undefined && value !== '')
    .map(([label, value]) => ({label, value}));
}

function createSourcePaths(resultsByKey, sourceKey, label) {
  const source = SOURCES.find(candidate => candidate.key === sourceKey);
  return resultsByKey[sourceKey].featureCollection.features.flatMap(feature =>
    getLinePaths(feature.geometry).map((path, pathIndex) => ({
      id: `${sourceKey}-${feature.properties.OBJECTID}-${pathIndex}`,
      label,
      path,
      source: [getSourceRef(source, feature)],
      details: createDetails(feature.properties),
      sourceProperties: feature.properties
    }))
  );
}

function createSourcePolygons(resultsByKey, sourceKey, label) {
  return createSourcePaths(resultsByKey, sourceKey, label)
    .filter(asset => isClosedPath(asset.path))
    .map(({path, ...asset}) => ({...asset, polygon: path}));
}

function omitSourceProperties(asset) {
  const {sourceProperties, ...renderAsset} = asset;
  return renderAsset;
}

function createRenderAssets(
  resultsByKey,
  {laneBands, crossings, longitudinalMarkings, symbolPaths}
) {
  const roadSurfaces = createSourcePaths(resultsByKey, 'streets', 'Street surface').map(asset =>
    omitSourceProperties({
      ...asset,
      style: {
        widthMeters: Number(asset.sourceProperties.SURFACEWIDTH || 0) * FEET_TO_METERS,
        colorRole: 'asphalt'
      }
    })
  );
  const sidewalks = createSourcePaths(resultsByKey, 'sidewalks', 'Sidewalk')
    .map(asset => ({
      ...asset,
      style: {widthMeters: getSidewalkWidthMeters(asset), colorRole: 'sidewalk'}
    }))
    .filter(asset => getPathLengthMeters(asset.path) >= asset.style.widthMeters * 2)
    .map(omitSourceProperties);
  const backgroundPaths = createSourcePaths(
    resultsByKey,
    'background',
    'Source drafting line'
  ).map(omitSourceProperties);
  const bikePanels = createSourcePolygons(resultsByKey, 'panelMarkings', 'Bicycle panel')
    .filter(asset => !crossings.replacedAssetIds.has(asset.id))
    .map(omitSourceProperties);
  const transversePolygons = createSourcePolygons(
    resultsByKey,
    'transverseMarkings',
    'Transverse marking'
  )
    .filter(asset => !crossings.replacedAssetIds.has(asset.id))
    .map(omitSourceProperties);
  const transversePaths = createSourcePaths(
    resultsByKey,
    'transverseMarkings',
    'Transverse marking'
  )
    .filter(asset => !isClosedPath(asset.path))
    .map(asset =>
      omitSourceProperties({...asset, style: {widthMeters: DEFAULT_MARKING_WIDTH_METERS}})
    );
  const curbs = createSourcePaths(
    resultsByKey,
    'verticalElements',
    'Curb or separator'
  ).map(asset =>
    omitSourceProperties({...asset, style: {widthMeters: 0.12, colorRole: 'curb'}})
  );
  const symbols = symbolPaths.map(symbol => ({
    id: symbol.id,
    label: symbol.label,
    path: symbol.path,
    source: symbol.source,
    details: createDetails(symbol.properties),
    style: {widthMeters: 0.1, colorRole: 'pavementSymbol'}
  }));

  return {
    surfacePaths: [...roadSurfaces, ...sidewalks],
    backgroundPaths,
    laneBands: laneBands.map(lane => ({
      id: lane.id,
      label: 'Vehicle lane',
      path: lane.path,
      source: lane.source,
      details: [],
      style: {widthMeters: lane.widthMeters, offset: lane.offsetWidths}
    })),
    bikePanels,
    crossings: crossings.crossings,
    transversePolygons,
    transversePaths,
    longitudinalMarkings: longitudinalMarkings.map(omitSourceProperties),
    detailPaths: [...curbs, ...symbols]
  };
}

function createLongitudinalMarkings(resultsByKey) {
  const markings = createSourcePaths(
    resultsByKey,
    'longitudinalMarkings',
    'Longitudinal marking'
  ).map(asset => {
    const dashMeters = parseDashPattern(asset.sourceProperties.Type);
    return {
      ...asset,
      style: {
        widthMeters:
          parseMarkingWidth(asset.sourceProperties.Width) || DEFAULT_MARKING_WIDTH_METERS,
        widthPixels: DEFAULT_MARKING_WIDTH_PIXELS,
        colorRole:
          asset.sourceProperties.Color === 'Yellow' ? 'yellowMarking' : 'whiteMarking',
        dashMeters,
        dashPixels: getScreenDashPattern(dashMeters),
        offset: 0,
        dashMode: 'path',
        dashJustified: false,
        dashGapPickable: true
      }
    };
  });
  return createDoubleLines(markings);
}

function createStitchedSymbolPaths(resultsByKey) {
  const symbolSource = SOURCES.find(source => source.key === 'symbols');
  const symbolPaths = [];
  let sourcePathCount = 0;
  let bridgeCount = 0;
  let maximumBridgeDistanceMeters = 0;

  for (const feature of resultsByKey.symbols.featureCollection.features) {
    const sourcePaths = getLinePaths(feature.geometry);
    sourcePathCount += sourcePaths.length;
    const stitchedPaths = stitchLinePaths(sourcePaths);
    for (let index = 0; index < stitchedPaths.length; index++) {
      const stitched = stitchedPaths[index];
      bridgeCount += stitched.bridgeDistancesMeters.length;
      maximumBridgeDistanceMeters = Math.max(
        maximumBridgeDistanceMeters,
        ...stitched.bridgeDistancesMeters
      );
      symbolPaths.push({
        id: `symbol-${feature.properties.OBJECTID}-${index}`,
        label: 'Pavement symbol',
        path: stitched.path,
        source: [getSourceRef(symbolSource, feature)],
        properties: feature.properties,
        derived: true,
        derivation: {
          operation: 'endpoint-connected CAD fragment stitching',
          parameters: {
            maximumJoinDistanceMeters: SYMBOL_JOIN_TOLERANCE_METERS,
            sourcePathIndexes: stitched.sourcePathIndexes.join(','),
            sourcePathCount: stitched.sourcePathIndexes.length,
            bridgeCount: stitched.bridgeDistancesMeters.length,
            maximumBridgeDistanceMeters: Math.max(0, ...stitched.bridgeDistancesMeters)
          },
          representation:
            'topology-repaired display path; every source coordinate is retained'
        }
      });
    }
  }

  return {
    symbolPaths,
    summary: {
      sourceFeatureCount: resultsByKey.symbols.featureCollection.features.length,
      sourcePathCount,
      outputPathCount: symbolPaths.length,
      maximumJoinDistanceMeters: SYMBOL_JOIN_TOLERANCE_METERS,
      bridgeCount,
      maximumBridgeDistanceMeters
    }
  };
}

function validateSymbolCoordinates(resultsByKey, symbolPaths) {
  const pathsByObjectId = Map.groupBy(symbolPaths, path => path.source[0].objectId);
  for (const feature of resultsByKey.symbols.featureCollection.features) {
    const stitchedPaths = pathsByObjectId.get(feature.properties.OBJECTID);
    if (!stitchedPaths?.length) {
      throw new Error(`Symbol ${feature.properties.OBJECTID} has no render path`);
    }
    const stitchedCoordinates = new Set(
      stitchedPaths.flatMap(path => path.path.map(coordinate => JSON.stringify(coordinate)))
    );
    visitCoordinates(feature.geometry, coordinate => {
      if (!stitchedCoordinates.has(JSON.stringify(coordinate))) {
        throw new Error(`Symbol ${feature.properties.OBJECTID} lost a source coordinate`);
      }
    });
  }
}

function createLaneBands(resultsByKey) {
  const streetsSource = SOURCES.find(source => source.key === 'streets');
  const laneWidthSource = SOURCES.find(source => source.key === 'laneWidths');
  const streetFeatures = resultsByKey.streets.featureCollection.features.filter(feature =>
    APPROACH_ROAD_KEYS.has(Number(feature.properties.COMPKEY))
  );
  const widthFeatures = resultsByKey.laneWidths.featureCollection.features.filter(
    feature => Number(feature.properties.LaneWidth) === APPROACH_LANE_WIDTH_FEET
  );
  const laneBands = [];
  const spatialJoins = [];

  for (const street of streetFeatures) {
    const path = getLinePaths(street.geometry)[0];
    const nearestWidthFeature = widthFeatures
      .map(feature => ({
        feature,
        distanceMeters: getPointToPathDistance(feature.geometry.coordinates, path)
      }))
      .sort((resultA, resultB) => resultA.distanceMeters - resultB.distanceMeters)[0];
    const laneCount = 4;
    const parentSources = [getSourceRef(streetsSource, street)];
    if (nearestWidthFeature) {
      parentSources.push(getSourceRef(laneWidthSource, nearestWidthFeature.feature));
      spatialJoins.push({
        streetObjectId: street.properties.OBJECTID,
        laneWidthObjectId: nearestWidthFeature.feature.properties.OBJECTID,
        residualMeters: nearestWidthFeature.distanceMeters
      });
    }

    for (let index = 0; index < laneCount; index++) {
      laneBands.push({
        id: `lane-${street.properties.COMPKEY}-${index + 1}`,
        path,
        widthMeters: APPROACH_LANE_WIDTH_METERS,
        offsetWidths: index - (laneCount - 1) / 2,
        kind: 'vehicle',
        source: parentSources,
        derived: true,
        derivation: {
          operation: 'centered equal-width lane band from official street centerline',
          parameters: {
            laneWidthFeet: APPROACH_LANE_WIDTH_FEET,
            laneCount,
            offsetUnits: 'rendered path widths',
            spatialJoinResidualMeters: nearestWidthFeature?.distanceMeters ?? null
          },
          representation: 'cartographic depiction; not surveyed lane geometry'
        }
      });
    }
  }
  return {laneBands, spatialJoins};
}

function subtract(pointA, pointB) {
  return [pointA[0] - pointB[0], pointA[1] - pointB[1]];
}

function add(pointA, pointB, scale = 1) {
  return [pointA[0] + pointB[0] * scale, pointA[1] + pointB[1] * scale];
}

function dot(vectorA, vectorB) {
  return vectorA[0] * vectorB[0] + vectorA[1] * vectorB[1];
}

function cross(vectorA, vectorB) {
  return vectorA[0] * vectorB[1] - vectorA[1] * vectorB[0];
}

function normalize(vector) {
  const length = Math.hypot(vector[0], vector[1]);
  return [vector[0] / length, vector[1] / length];
}

// PathStyleExtension offsets are positive to the right of the path direction
function getRightNormal([x, y]) {
  return [y, -x];
}

function roundNumber(value, digits) {
  return Number(value.toFixed(digits));
}

function toLngLat(point) {
  return fromLocalMeters(point, LOCAL_ORIGIN).map(value => roundNumber(value, 9));
}

function getLocalSegmentDistance(point, start, end) {
  const segment = subtract(end, start);
  const lengthSquared = dot(segment, segment);
  const ratio = lengthSquared
    ? Math.max(0, Math.min(1, dot(subtract(point, start), segment) / lengthSquared))
    : 0;
  return Math.hypot(...subtract(point, add(start, segment, ratio)));
}

function getLocalPathDistance(point, points) {
  let distance = Infinity;
  for (let index = 1; index < points.length; index++) {
    distance = Math.min(distance, getLocalSegmentDistance(point, points[index - 1], points[index]));
  }
  return distance;
}

function getLocalPathLength(points) {
  let length = 0;
  for (let index = 1; index < points.length; index++) {
    length += Math.hypot(...subtract(points[index], points[index - 1]));
  }
  return length;
}

// Distance along a polyline to the point on it nearest to `point`
function getArcPosition(point, points) {
  let nearest = {distance: Infinity, position: 0};
  let traveled = 0;
  for (let index = 1; index < points.length; index++) {
    const start = points[index - 1];
    const segment = subtract(points[index], start);
    const length = Math.hypot(...segment);
    const ratio = Math.max(0, Math.min(1, dot(subtract(point, start), segment) / length ** 2));
    const distance = Math.hypot(...subtract(point, add(start, segment, ratio)));
    if (distance < nearest.distance) {
      nearest = {distance, position: traveled + ratio * length};
    }
    traveled += length;
  }
  return nearest.position;
}

// Cuts the part of a source path between two arc positions, keeping its own vertices
function slicePath(path, points, from, to) {
  const sliced = [];
  let traveled = 0;
  for (let index = 1; index < points.length; index++) {
    const length = Math.hypot(...subtract(points[index], points[index - 1]));
    const interpolate = position => {
      const ratio = (position - traveled) / length;
      return path[index - 1].map((value, axis) => value + (path[index][axis] - value) * ratio);
    };
    if (!sliced.length && traveled + length > from) {
      sliced.push(interpolate(from));
    }
    if (sliced.length) {
      if (traveled + length >= to) {
        sliced.push(interpolate(to));
        break;
      }
      sliced.push(path[index]);
    }
    traveled += length;
  }
  return sliced;
}

// Returns the polyline shifted to the right by `distance` meters (left if negative), with mitered corners
function offsetPolyline(points, distance, closed) {
  const vertices = closed ? points.slice(0, -1) : points;
  const normals = vertices
    .slice(0, closed ? vertices.length : -1)
    .map((vertex, index) =>
      getRightNormal(normalize(subtract(vertices[(index + 1) % vertices.length], vertex)))
    );
  const shifted = vertices.map((vertex, index) => {
    const previous = closed
      ? normals.at(index - 1)
      : normals[index - 1] || normals[index];
    const next = normals[index] || normals[index - 1];
    const miter = add(previous, next);
    return add(vertex, miter, distance / (1 + dot(previous, next)));
  });
  return closed ? [...shifted, shifted[0]] : shifted;
}

// Returns the center, side directions and side lengths of a rectangular polygon in local meters
function getRectangle(polygon) {
  const corners = polygon.slice(0, -1).map(coordinate => toLocalMeters(coordinate, LOCAL_ORIGIN));
  if (corners.length !== 4) {
    return null;
  }
  const edges = corners.map((corner, index) => subtract(corners[(index + 1) % 4], corner));
  const lengths = edges.map(edge => Math.hypot(...edge));
  const isRectangle =
    Math.abs(lengths[0] - lengths[2]) <= ROW_TOLERANCE_METERS &&
    Math.abs(lengths[1] - lengths[3]) <= ROW_TOLERANCE_METERS &&
    edges.every(
      (edge, index) =>
        Math.abs(dot(edge, edges[(index + 1) % 4])) <= ROW_TOLERANCE_METERS * lengths[index]
    );
  if (!isRectangle) {
    return null;
  }
  return {
    center: [
      corners.reduce((sum, corner) => sum + corner[0], 0) / 4,
      corners.reduce((sum, corner) => sum + corner[1], 0) / 4
    ],
    sides: [0, 1].map(index => ({direction: normalize(edges[index]), length: lengths[index]}))
  };
}

function hasRectangleSize(rectangle, direction, dashLength, width) {
  const along = rectangle.sides.find(side => Math.abs(cross(side.direction, direction)) < 0.02);
  const across = rectangle.sides.find(side => side !== along);
  return (
    along &&
    Math.abs(along.length - dashLength) <= ROW_TOLERANCE_METERS &&
    Math.abs(across.length - width) <= ROW_TOLERANCE_METERS
  );
}

// Splits positions along a row into evenly spaced series. Crosswalk bars that come in pairs
// alternate between two spacings and form two interleaved series.
function getDashSeries(positions, dashLength) {
  const spacings = positions.slice(1).map((position, index) => position - positions[index]);
  const isUniform = values =>
    values.every(value => Math.abs(value - values[0]) <= ROW_TOLERANCE_METERS);
  const indexes = positions.map((position, index) => index);
  if (spacings.length && isUniform(spacings) && spacings[0] > dashLength + ROW_TOLERANCE_METERS) {
    return positions.length >= MINIMUM_ROW_DASH_COUNT ? [indexes] : null;
  }
  const evenSpacings = spacings.filter((spacing, index) => index % 2 === 0);
  const oddSpacings = spacings.filter((spacing, index) => index % 2 === 1);
  if (spacings.length >= 3 && isUniform(evenSpacings) && isUniform(oddSpacings)) {
    const series = [0, 1].map(parity => indexes.filter(index => index % 2 === parity));
    return series.every(members => members.length >= MINIMUM_ROW_DASH_COUNT) ? series : null;
  }
  return null;
}

// Finds equal rectangles repeated at a constant spacing along a line, and describes each such
// row as a path with a dash pattern
function findDashRows(polygons) {
  const unused = new Set(
    polygons
      .map(asset => ({asset, rectangle: getRectangle(asset.polygon)}))
      .filter(item => item.rectangle)
  );
  const rows = [];
  for (const seed of [...unused]) {
    if (!unused.has(seed)) {
      continue;
    }
    for (const sideIndex of [0, 1]) {
      const {direction, length: dashLength} = seed.rectangle.sides[sideIndex];
      const width = seed.rectangle.sides[1 - sideIndex].length;
      const normal = getRightNormal(direction);
      const getAlong = item => dot(subtract(item.rectangle.center, seed.rectangle.center), direction);
      const line = [...unused]
        .filter(
          item =>
            hasRectangleSize(item.rectangle, direction, dashLength, width) &&
            Math.abs(dot(subtract(item.rectangle.center, seed.rectangle.center), normal)) <=
              ROW_TOLERANCE_METERS
        )
        .sort((itemA, itemB) => getAlong(itemA) - getAlong(itemB));
      // Keep the stretch around the seed without a gap longer than one row pitch
      let first = line.indexOf(seed);
      let last = first;
      while (first > 0 && getAlong(line[first]) - getAlong(line[first - 1]) <= MAXIMUM_ROW_PITCH_METERS) {
        first--;
      }
      while (
        last < line.length - 1 &&
        getAlong(line[last + 1]) - getAlong(line[last]) <= MAXIMUM_ROW_PITCH_METERS
      ) {
        last++;
      }
      const run = line.slice(first, last + 1);
      const series = getDashSeries(run.map(getAlong), dashLength);
      if (!series) {
        continue;
      }
      for (const indexes of series) {
        const members = indexes.map(index => run[index]);
        const start = members[0].rectangle.center;
        const end = members.at(-1).rectangle.center;
        const pitch = dot(subtract(end, start), direction) / (members.length - 1);
        members.forEach(member => unused.delete(member));
        rows.push({
          members,
          direction,
          widthMeters: width,
          pitch,
          dashMeters: [dashLength, pitch - dashLength],
          start: add(start, direction, -dashLength / 2),
          end: add(end, direction, dashLength / 2)
        });
      }
      break;
    }
  }
  return rows;
}

// Rows that start and end together side by side, such as the blocks and edge lines of a bicycle
// crossing, share one center path and are drawn at different offsets from it
function groupDashRows(rows) {
  const groups = [];
  for (const row of rows) {
    const group = groups.find(([reference, ...others]) => {
      if (Math.abs(cross(reference.direction, row.direction)) > 0.02) {
        return false;
      }
      const isReversed = dot(reference.direction, row.direction) < 0;
      const [start, end] = isReversed ? [row.end, row.start] : [row.start, row.end];
      const normal = getRightNormal(reference.direction);
      return (
        Math.abs(dot(subtract(start, reference.start), reference.direction)) <= ROW_TOLERANCE_METERS &&
        Math.abs(dot(subtract(end, reference.end), reference.direction)) <= ROW_TOLERANCE_METERS &&
        Math.abs(Math.abs(row.pitch) - Math.abs(reference.pitch)) <= ROW_TOLERANCE_METERS &&
        [reference, ...others].some(
          member =>
            Math.abs(dot(subtract(start, member.start), normal)) <= MAXIMUM_ROW_PITCH_METERS
        )
      );
    });
    if (group) {
      if (dot(group[0].direction, row.direction) < 0) {
        [row.start, row.end] = [row.end, row.start];
        row.direction = [-row.direction[0], -row.direction[1]];
      }
      group.push(row);
    } else {
      groups.push([row]);
    }
  }

  return groups.map(group => {
    const [reference] = group;
    const normal = getRightNormal(reference.direction);
    const positions = group.map(row => dot(subtract(row.start, reference.start), normal));
    const left = Math.min(...group.map((row, index) => positions[index] - row.widthMeters / 2));
    const right = Math.max(...group.map((row, index) => positions[index] + row.widthMeters / 2));
    const center = (left + right) / 2;
    return {
      path: [add(reference.start, normal, center), add(reference.end, normal, center)],
      rows: group.map((row, index) => ({
        ...row,
        offset: roundNumber((positions[index] - center) / row.widthMeters, 4)
      }))
    };
  });
}

function createCrossings(resultsByKey) {
  const crosswalkSource = SOURCES.find(source => source.key === 'crosswalks');
  const crosswalkPoints = resultsByKey.crosswalks.featureCollection.features.map(feature => ({
    feature,
    point: toLocalMeters(feature.geometry.coordinates, LOCAL_ORIGIN)
  }));
  const crossings = [];
  const replacedAssetIds = new Set();
  const groupSummaries = [];

  for (const [sourceKey, colorRole] of [
    ['panelMarkings', 'bikePanel'],
    ['transverseMarkings', 'whiteMarking']
  ]) {
    const polygons = createSourcePolygons(resultsByKey, sourceKey, '');
    for (const group of groupDashRows(findDashRows(polygons))) {
      const crosswalk =
        sourceKey === 'transverseMarkings' &&
        crosswalkPoints.find(
          ({point}) => getLocalPathDistance(point, group.path) <= CROSSWALK_MATCH_DISTANCE_METERS
        );
      groupSummaries.push({
        sourceKey,
        crosswalkObjectId: crosswalk ? crosswalk.feature.properties.OBJECTID : null,
        rowCount: group.rows.length,
        dashCounts: group.rows.map(row => row.members.length).join(','),
        offsets: group.rows.map(row => row.offset).join(',')
      });
      for (const row of group.rows) {
        const members = row.members.map(member => member.asset);
        members.forEach(member => replacedAssetIds.add(member.id));
        const dashMeters = row.dashMeters.map(value => roundNumber(value, 3));
        crossings.push({
          id: `crossing-${members[0].id}`,
          label: crosswalk
            ? 'Crosswalk'
            : sourceKey === 'panelMarkings'
              ? 'Bicycle crossing'
              : 'Transverse marking',
          path: group.path.map(toLngLat),
          source: [
            ...(crosswalk ? [getSourceRef(crosswalkSource, crosswalk.feature)] : []),
            ...members.flatMap(member => member.source)
          ],
          details: crosswalk
            ? createDetails(crosswalk.feature.properties)
            : members[0].details,
          style: {
            widthMeters: roundNumber(row.widthMeters, 3),
            widthPixels: roundNumber(row.widthMeters * CROSSING_PIXELS_PER_METER, 1),
            colorRole,
            dashMeters,
            dashPixels: dashMeters.map(value => roundNumber(value * CROSSING_PIXELS_PER_METER, 1)),
            offset: row.offset,
            dashMode: 'path',
            // Each row spans a whole number of dashes, so the pattern needs no stretching
            dashJustified: false,
            dashGapPickable: true
          }
        });
      }
    }
  }
  return {crossings, replacedAssetIds, groups: groupSummaries};
}

// Finds the stretches of `points` that run parallel to `otherPoints` at a constant distance.
// Returns the distance to the right of `points`, positive or negative.
function findParallelRuns(points, otherPoints, closed) {
  const segmentDistances = points.slice(1).map((end, index) => {
    const start = points[index];
    const direction = normalize(subtract(end, start));
    const normal = getRightNormal(direction);
    const segmentLength = Math.hypot(...subtract(end, start));
    for (let otherIndex = 1; otherIndex < otherPoints.length; otherIndex++) {
      const otherStart = otherPoints[otherIndex - 1];
      const otherEnd = otherPoints[otherIndex];
      if (Math.abs(cross(direction, normalize(subtract(otherEnd, otherStart)))) > 0.01) {
        continue;
      }
      const startDistance = dot(subtract(otherStart, start), normal);
      const endDistance = dot(subtract(otherEnd, start), normal);
      const distance = (startDistance + endDistance) / 2;
      const along = [dot(subtract(otherStart, start), direction), dot(subtract(otherEnd, start), direction)];
      if (
        Math.abs(startDistance - endDistance) / 2 <= DOUBLE_LINE_TOLERANCE_METERS &&
        Math.abs(distance) >= DOUBLE_LINE_SEPARATION_METERS[0] &&
        Math.abs(distance) <= DOUBLE_LINE_SEPARATION_METERS[1] &&
        Math.min(Math.max(...along), segmentLength) > Math.max(Math.min(...along), 0)
      ) {
        return distance;
      }
    }
    return null;
  });

  if (closed && segmentDistances.every(distance => distance !== null)) {
    const distance = segmentDistances[0];
    if (segmentDistances.every(value => Math.abs(value - distance) <= DOUBLE_LINE_TOLERANCE_METERS)) {
      return [{startIndex: 0, endIndex: points.length - 1, distance, closed: true}];
    }
  }
  const runs = [];
  segmentDistances.forEach((distance, index) => {
    const run = runs.at(-1);
    if (distance === null) {
      return;
    }
    if (run && run.endIndex === index && Math.abs(run.distance - distance) <= DOUBLE_LINE_TOLERANCE_METERS) {
      run.endIndex = index + 1;
    } else {
      runs.push({startIndex: index, endIndex: index + 1, distance, closed: false});
    }
  });
  return runs;
}

function overlapsInterval(intervals, [from, to]) {
  return intervals.some(
    interval =>
      Math.min(interval[1], to) - Math.max(interval[0], from) > DOUBLE_LINE_TOLERANCE_METERS
  );
}

// Redraws pairs of parallel yellow lines, such as a solid line beside a dashed one, as one shared
// center path drawn twice with opposite offsets. The parts of each line outside the pair are kept.
function createDoubleLines(markings) {
  const lines = markings.map(asset => {
    const points = asset.path.map(coordinate => toLocalMeters(coordinate, LOCAL_ORIGIN));
    return {asset, points, length: getLocalPathLength(points), consumed: [], copies: []};
  });
  const candidates = lines
    .filter(line => line.asset.style.colorRole === 'yellowMarking')
    .sort((lineA, lineB) => lineA.length - lineB.length);
  const runs = [];
  candidates.forEach((shorter, index) => {
    const shorterClosed = isClosedPath(shorter.asset.path);
    for (const longer of candidates.slice(index + 1)) {
      const longerClosed = isClosedPath(longer.asset.path);
      for (const run of findParallelRuns(shorter.points, longer.points, shorterClosed)) {
        const points = shorter.points.slice(run.startIndex, run.endIndex + 1);
        const lengthMeters = getLocalPathLength(points);
        if (lengthMeters < MINIMUM_DOUBLE_LINE_LENGTH_METERS) {
          continue;
        }
        const longerCopy = offsetPolyline(points, run.distance, run.closed);
        const shorterInterval = run.closed
          ? [0, shorter.length]
          : [run.startIndex, run.endIndex].map(vertex =>
              getLocalPathLength(shorter.points.slice(0, vertex + 1))
            );
        const longerInterval =
          run.closed && longerClosed
            ? [0, longer.length]
            : [longerCopy[0], longerCopy.at(-1)]
                .map(point => getArcPosition(point, longer.points))
                .sort((positionA, positionB) => positionA - positionB);
        const longerVertices = longer.points.filter(point => {
          const position = getArcPosition(point, longer.points);
          return (
            (run.closed && longerClosed) ||
            (position > longerInterval[0] + DOUBLE_LINE_TOLERANCE_METERS &&
              position < longerInterval[1] - DOUBLE_LINE_TOLERANCE_METERS)
          );
        });
        const isFaithful =
          longerCopy.every(
            point => getLocalPathDistance(point, longer.points) <= DOUBLE_LINE_TOLERANCE_METERS
          ) &&
          longerVertices.every(
            point => getLocalPathDistance(point, longerCopy) <= DOUBLE_LINE_TOLERANCE_METERS
          );
        if (isFaithful) {
          runs.push({...run, shorter, longer, points, lengthMeters, shorterInterval, longerInterval});
        }
      }
    }
  });

  // Keep the longest pairs when the same stretch of line pairs with more than one other line
  const pairs = [];
  runs.sort((runA, runB) => runB.lengthMeters - runA.lengthMeters);
  for (const run of runs) {
    const {shorter, longer} = run;
    if (
      overlapsInterval(shorter.consumed, run.shorterInterval) ||
      overlapsInterval(longer.consumed, run.longerInterval)
    ) {
      continue;
    }
    shorter.consumed.push(run.shorterInterval);
    longer.consumed.push(run.longerInterval);
    const path = offsetPolyline(run.points, run.distance / 2, run.closed).map(toLngLat);
    for (const [line, sign] of [
      [shorter, -1],
      [longer, 1]
    ]) {
      line.copies.push({
        ...line.asset,
        id: `${line.asset.id}-double-${line.copies.length + 1}`,
        path,
        style: {
          ...line.asset.style,
          offset: roundNumber((sign * run.distance) / 2 / line.asset.style.widthMeters, 4)
        }
      });
    }
    pairs.push({
      shorterId: shorter.asset.id,
      longerId: longer.asset.id,
      separationMeters: roundNumber(Math.abs(run.distance), 3),
      lengthMeters: roundNumber(run.lengthMeters, 1),
      closed: run.closed
    });
  }

  const longitudinalMarkings = lines.flatMap(line => {
    if (!line.consumed.length) {
      return [line.asset];
    }
    const cuts = [...line.consumed].sort((intervalA, intervalB) => intervalA[0] - intervalB[0]);
    const remaining = [];
    let position = 0;
    for (const [from, to] of [...cuts, [line.length, line.length]]) {
      if (from - position >= 0.05) {
        remaining.push([position, from]);
      }
      position = Math.max(position, to);
    }
    return [
      ...line.copies,
      ...remaining.map(([from, to], index) => ({
        ...line.asset,
        id: `${line.asset.id}-part-${index + 1}`,
        path: slicePath(line.asset.path, line.points, from, to)
      }))
    ];
  });
  return {longitudinalMarkings, pairs};
}

function createGateValidation(resultsByKey) {
  const longitudinal = resultsByKey.longitudinalMarkings.featureCollection.features;
  const dashTypes = getDistinctValues(longitudinal, 'Type').filter(value => value !== 'Solid');
  const laneWidths = getDistinctValues(resultsByKey.laneWidths.featureCollection.features, 'LaneWidth');
  const gate = {
    twoLongitudinalPatterns: dashTypes.length >= 2,
    trueDashSkipPattern: dashTypes.some(value => /dash.+skip/i.test(String(value))),
    denseDashedPath: longitudinal.some(
      feature =>
        feature.properties.Type !== 'Solid' && getCoordinateCount(feature.geometry) >= 5
    ),
    bicyclePanel: resultsByKey.panelMarkings.featureCollection.features.length > 0,
    markedCrosswalk: resultsByKey.crosswalks.featureCollection.features.length > 0,
    curbOrSeparator: resultsByKey.verticalElements.featureCollection.features.length > 0,
    streetSurfaceWidth: resultsByKey.streets.featureCollection.features.some(
      feature => Number(feature.properties.SURFACEWIDTH) > 0
    ),
    laneWidths: laneWidths.filter(value => Number(value) > 0).length >= 2,
    sourceContext:
      resultsByKey.sidewalks.featureCollection.features.length > 0 ||
      resultsByKey.background.featureCollection.features.length > 0
  };
  return {passed: Object.values(gate).every(Boolean), criteria: gate};
}

function renderReport(manifest) {
  const sourceRows = manifest.sources
    .map(
      source =>
        `| ${source.layerName} | ${source.rawFeatureCount} | ${source.geometryTypes.join(', ')} | ${
          source.multipartCount
        } | ${source.duplicates.exact} | ${source.duplicates.near} |`
    )
    .join('\n');
  const gateRows = Object.entries(manifest.validation.extractionGate.criteria)
    .map(([criterion, passed]) => `| ${criterion} | ${passed ? 'pass' : 'fail'} |`)
    .join('\n');
  const longitudinal = manifest.sources.find(source => source.key === 'longitudinalMarkings');
  const widths = manifest.sources.find(source => source.key === 'laneWidths');

  return `# Seattle road-diagram extraction report

Generated: ${manifest.generatedAt}

Candidate: ${CANDIDATE_NAME}

Display bounds: \`${DISPLAY_BOUNDS.join(', ')}\`

Extraction gate: **${manifest.validation.extractionGate.passed ? 'PASS' : 'FAIL'}**

## Source summary

| Layer | Features | Geometry | Multipart | Exact duplicates | Near duplicates |
| --- | ---: | --- | ---: | ---: | ---: |
${sourceRows}

## Gate criteria

| Criterion | Result |
| --- | --- |
${gateRows}

## Key source values

- Longitudinal marking types: ${longitudinal.distinctValues.Type.join(', ')}
- Longitudinal colors: ${longitudinal.distinctValues.Color.join(', ')}
- Longitudinal source widths: ${longitudinal.distinctValues.Width.join(', ') || 'none in this CAD crop'}
- Lane-width annotations: ${widths.distinctValues.Width.join(', ') || widths.distinctLaneWidths.join(', ')}
- Lane-band spatial-join residuals: ${manifest.validation.spatialAlignment.laneWidthToStreetResidualMeters
    .map(value => value.toFixed(2))
    .join(', ')} meters

The channelization records around Dexter and Thomas preserve authoritative geometry and dash class,
but most descriptive asset fields are null in this CAD-derived crop. Longitudinal stroke widths use
a cartographic fallback while dash/skip lengths come directly from the source \`Type\` values.

## Transformations

- Requested a bounded EPSG:4326 snapshot and paged by sorted object ID.
- Preserved returned source data while producing the render-ready asset snapshot.
- Derived continuous pavement-symbol paths by joining source fragment endpoints within ${manifest.validation.symbolStitching.maximumJoinDistanceMeters} meters; no source vertex was moved.
- Derived equal-width lane bands from official street centerlines plus the nearest 12-foot lane-width annotations.
- Redrew ${manifest.derivations.find(derivation => derivation.output === 'assets.crossings').replacedPolygonCount} bicycle-crossing and crosswalk rectangles as ${manifest.derivations.find(derivation => derivation.output === 'assets.crossings').outputFeatureCount} dashed rows, each spanning its first to last rectangle. Rows side by side share a center path and are offset from it.
- Redrew ${manifest.derivations.find(derivation => derivation.output === 'assets.longitudinalMarkings').pairs.length} pairs of parallel yellow lines as one center path drawn twice at opposite offsets, after checking both copies stay within ${DOUBLE_LINE_TOLERANCE_METERS} meters of the source lines.
- Did not simplify, manually redraw, or snap any other official channelization geometry.

## License and limitations

City of Seattle Department of Transportation data is used under PDDL 1.0. This visualization and
its derived cartographic constructions are for demonstrating deck.gl rendering. They are not for
engineering, construction, legal interpretation, or navigation.
`;
}

export async function extractRoadDiagram(outputDirectory) {
  const generatedAt = new Date().toISOString();
  const queriedSources = await Promise.all(SOURCES.map(querySource));
  const resultsByKey = Object.fromEntries(
    SOURCES.map((source, index) => [source.key, queriedSources[index]])
  );
  validateQueriedSources(resultsByKey);
  const {laneBands, spatialJoins} = createLaneBands(resultsByKey);
  const crossings = createCrossings(resultsByKey);
  const {longitudinalMarkings, pairs: doubleLines} = createLongitudinalMarkings(resultsByKey);
  const {symbolPaths, summary: symbolStitching} = createStitchedSymbolPaths(resultsByKey);
  validateSymbolCoordinates(resultsByKey, symbolPaths);
  const assets = createRenderAssets(resultsByKey, {
    laneBands,
    crossings,
    longitudinalMarkings,
    symbolPaths
  });
  const extractionGate = createGateValidation(resultsByKey);
  const generatorCommit = getGeneratorCommit();

  const snapshot = {
    dataset: 'deck.gl PathStyleExtension Seattle road diagram',
    generatedAt,
    candidate: CANDIDATE_NAME,
    displayBounds: DISPLAY_BOUNDS,
    assets
  };

  const manifestSources = SOURCES.map(source => {
    const result = resultsByKey[source.key];
    const summary = summarizeSource(result);
    return {
      key: source.key,
      provider: source.provider,
      itemId: source.itemId,
      serviceUrl: source.serviceUrl,
      layerId: source.layerId,
      layerName: source.layerName,
      catalogUrl: source.catalogUrl,
      retrievedAt: generatedAt,
      sourceLastEdit: formatDate(
        result.metadata.editingInfo?.dataLastEditDate || result.metadata.editingInfo?.lastEditDate
      ),
      query: {
        geometry: DISPLAY_BOUNDS,
        geometryType: 'esriGeometryEnvelope',
        where: source.where,
        outFields: '*',
        outSR: 4326,
        paging: 'sorted object IDs in pages of at most 100'
      },
      queryUrls: result.queryUrls,
      rawSha256: sha256(result.rawText),
      rawByteCount: Buffer.byteLength(result.rawText),
      rawFeatureCount: result.objectIds.length,
      outputFeatureCount: result.featureCollection.features.length,
      license: 'PDDL 1.0',
      transformations: ['requested EPSG:4326 output', 'sorted by source object ID'],
      ...summary,
      distinctLaneWidths: getDistinctValues(result.featureCollection.features, 'LaneWidth')
    };
  });

  const warnings = [];
  const longitudinalSummary = manifestSources.find(source => source.key === 'longitudinalMarkings');
  if (!longitudinalSummary.distinctValues.Width.length) {
    warnings.push(
      'Longitudinal Width is null throughout this crop; the example uses a disclosed cartographic fallback stroke width.'
    );
  }
  if (!extractionGate.passed) {
    warnings.push('The selected site did not pass every extraction-gate criterion.');
  }
  const manifest = {
    dataset: snapshot.dataset,
    generatedAt,
    generatorCommit,
    candidate: CANDIDATE_NAME,
    displayBounds: DISPLAY_BOUNDS,
    sources: manifestSources,
    derivations: [
      {
        output: 'assets.laneBands',
        operation: 'centered equal-width offsets',
        sourceKeys: ['streets', 'laneWidths'],
        outputFeatureCount: laneBands.length
      },
      {
        output: 'assets.crossings',
        operation:
          'rows of equal, evenly spaced rectangles redrawn as dashed paths; side-by-side rows share a center path and are offset from it',
        sourceKeys: ['panelMarkings', 'transverseMarkings', 'crosswalks'],
        parameters: {
          toleranceMeters: ROW_TOLERANCE_METERS,
          maximumPitchMeters: MAXIMUM_ROW_PITCH_METERS,
          minimumDashCount: MINIMUM_ROW_DASH_COUNT,
          crosswalkMatchDistanceMeters: CROSSWALK_MATCH_DISTANCE_METERS
        },
        replacedPolygonCount: crossings.replacedAssetIds.size,
        groups: crossings.groups,
        outputFeatureCount: crossings.crossings.length
      },
      {
        output: 'assets.longitudinalMarkings',
        outputFilter: {colorRole: 'yellowMarking'},
        operation:
          'parallel yellow line pairs redrawn as one shared center path with two offsets; the rest of each line is kept',
        sourceKeys: ['longitudinalMarkings'],
        parameters: {
          separationMeters: DOUBLE_LINE_SEPARATION_METERS,
          toleranceMeters: DOUBLE_LINE_TOLERANCE_METERS,
          minimumLengthMeters: MINIMUM_DOUBLE_LINE_LENGTH_METERS
        },
        pairs: doubleLines,
        outputFeatureCount: doubleLines.length * 2
      },
      {
        output: 'assets.detailPaths',
        outputFilter: {colorRole: 'pavementSymbol'},
        operation: 'endpoint-connected CAD fragment stitching',
        sourceKeys: ['symbols'],
        parameters: {maximumJoinDistanceMeters: SYMBOL_JOIN_TOLERANCE_METERS},
        outputFeatureCount: symbolPaths.length
      }
    ],
    validation: {
      extractionGate,
      symbolStitching,
      renderAssetCounts: Object.fromEntries(
        Object.entries(assets).map(([key, value]) => [key, value.length])
      ),
      spatialAlignment: {
        laneWidthToStreetResidualMeters: spatialJoins.map(join => join.residualMeters),
        spatialJoins
      },
      warnings,
      errors: extractionGate.passed ? [] : ['Extraction gate failed']
    },
    license: {
      name: 'Public Domain Dedication and License 1.0',
      shortName: 'PDDL 1.0',
      url: 'https://opendatacommons.org/licenses/pddl/1-0/',
      attribution:
        'Road, sidewalk, bicycle-facility, crosswalk, and channelization data: City of Seattle Department of Transportation.'
    }
  };
  const report = renderReport(manifest);

  await mkdir(outputDirectory, {recursive: true});
  await Promise.all([
    writeFile(resolve(outputDirectory, 'seattle-road-diagram.json'), `${JSON.stringify(snapshot)}\n`),
    writeFile(
      resolve(outputDirectory, 'seattle-road-diagram.manifest.json'),
      `${JSON.stringify(manifest, null, 2)}\n`
    ),
    writeFile(resolve(outputDirectory, 'seattle-road-diagram-report.md'), report)
  ]);
  return {snapshot, manifest, report};
}

const isMainModule = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMainModule) {
  const outputDirectory = process.argv[2]
    ? resolve(REPOSITORY_ROOT, process.argv[2])
    : DEFAULT_DATA_DIRECTORY;
  const {manifest} = await extractRoadDiagram(outputDirectory);
  console.log(
    `Wrote ${manifest.sources.reduce((total, source) => total + source.outputFeatureCount, 0)} source features to ${outputDirectory}`
  );
  console.log(`Extraction gate: ${manifest.validation.extractionGate.passed ? 'PASS' : 'FAIL'}`);
}
