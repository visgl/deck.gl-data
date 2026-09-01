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
const CROSSWALK_WIDTH_PIXELS = 18;
const APPROACH_LANE_WIDTH_FEET = 12;
const APPROACH_LANE_WIDTH_METERS = APPROACH_LANE_WIDTH_FEET * FEET_TO_METERS;
export const SYMBOL_JOIN_TOLERANCE_METERS = 0.002;
const CROSSWALK_WIDTH_METERS = 3;
const CROSSWALK_MATCH_PADDING_METERS = 0.25;
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

function isPointWithinCrosswalk(point, path, widthMeters) {
  const origin = path[0];
  const [endX, endY] = toLocalMeters(path.at(-1), origin);
  const [pointX, pointY] = toLocalMeters(point, origin);
  const pathLengthSquared = endX ** 2 + endY ** 2;
  const pathLength = Math.sqrt(pathLengthSquared);
  const ratio = (pointX * endX + pointY * endY) / pathLengthSquared;
  const perpendicularDistanceMeters = Math.abs(pointX * endY - pointY * endX) / pathLength;
  return (
    ratio >= 0 &&
    ratio <= 1 &&
    perpendicularDistanceMeters <= widthMeters / 2 + CROSSWALK_MATCH_PADDING_METERS
  );
}

function getCrosswalkTransverseMarkingObjectIds(resultsByKey, path, widthMeters) {
  return resultsByKey.transverseMarkings.featureCollection.features
    .filter(feature => {
      const sourcePaths = getLinePaths(feature.geometry);
      return (
        sourcePaths.length === 1 &&
        isClosedPath(sourcePaths[0]) &&
        isPointWithinCrosswalk(getPathCentroid(sourcePaths[0]), path, widthMeters)
      );
    })
    .map(feature => feature.properties.OBJECTID)
    .sort((objectIdA, objectIdB) => Number(objectIdA) - Number(objectIdB));
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

function createRenderAssets(resultsByKey, {laneBands, crosswalkGuides, symbolPaths}) {
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
  const bikePanels = createSourcePolygons(
    resultsByKey,
    'panelMarkings',
    'Bicycle panel'
  ).map(omitSourceProperties);
  const longitudinalMarkings = createSourcePaths(
    resultsByKey,
    'longitudinalMarkings',
    'Longitudinal marking'
  ).map(asset => {
    const dashMeters = parseDashPattern(asset.sourceProperties.Type);
    return omitSourceProperties({
      ...asset,
      style: {
        widthMeters:
          parseMarkingWidth(asset.sourceProperties.Width) || DEFAULT_MARKING_WIDTH_METERS,
        widthPixels: DEFAULT_MARKING_WIDTH_PIXELS,
        colorRole:
          asset.sourceProperties.Color === 'Yellow' ? 'yellowMarking' : 'whiteMarking',
        dashMeters,
        dashPixels: getScreenDashPattern(dashMeters),
        dashMode: 'path',
        dashJustified: false,
        dashGapPickable: true
      }
    });
  });
  const replacedTransverseMarkingObjectIdList = crosswalkGuides.flatMap(
    crosswalk => crosswalk.transverseMarkingObjectIds
  );
  const replacedTransverseMarkingObjectIds = new Set(replacedTransverseMarkingObjectIdList);
  if (replacedTransverseMarkingObjectIds.size !== replacedTransverseMarkingObjectIdList.length) {
    throw new Error('A transverse marking was matched to more than one crosswalk');
  }
  const transversePolygons = createSourcePolygons(
    resultsByKey,
    'transverseMarkings',
    'Transverse marking'
  )
    .filter(asset => !replacedTransverseMarkingObjectIds.has(asset.source[0].objectId))
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
    crosswalks: crosswalkGuides.map(crosswalk => ({
      id: crosswalk.id,
      label: 'Crosswalk',
      path: crosswalk.path,
      source: crosswalk.source,
      details: createDetails(crosswalk.properties),
      style: {
        widthMeters: crosswalk.widthMeters,
        widthPixels: CROSSWALK_WIDTH_PIXELS,
        dashMeters: crosswalk.dashMeters,
        dashPixels: crosswalk.dashPixels,
        dashMode: 'path',
        dashJustified: true,
        dashGapPickable: true
      }
    })),
    transversePolygons,
    transversePaths,
    longitudinalMarkings,
    detailPaths: [...curbs, ...symbols]
  };
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

function getNearestStreetSegment(point, streetFeatures) {
  let nearest = null;
  for (const street of streetFeatures) {
    const path = getLinePaths(street.geometry)[0];
    for (let index = 1; index < path.length; index++) {
      const distanceMeters = getPointToSegmentDistance(point, path[index - 1], path[index]);
      if (!nearest || distanceMeters < nearest.distanceMeters) {
        nearest = {street, start: path[index - 1], end: path[index], distanceMeters};
      }
    }
  }
  return nearest;
}

function createCrosswalkGuides(resultsByKey) {
  const streetSource = SOURCES.find(source => source.key === 'streets');
  const crosswalkSource = SOURCES.find(source => source.key === 'crosswalks');
  const streetFeatures = resultsByKey.streets.featureCollection.features;
  return resultsByKey.crosswalks.featureCollection.features.map(crosswalk => {
    const point = crosswalk.geometry.coordinates;
    const preferredStreet = streetFeatures.filter(
      street => Number(street.properties.COMPKEY) === Number(crosswalk.properties.SEGKEY)
    );
    const nearest = getNearestStreetSegment(point, preferredStreet.length ? preferredStreet : streetFeatures);
    const surfaceWidthMeters = Number(nearest.street.properties.SURFACEWIDTH) * FEET_TO_METERS;
    const localStart = toLocalMeters(nearest.start, point);
    const localEnd = toLocalMeters(nearest.end, point);
    const directionLength = Math.hypot(localEnd[0] - localStart[0], localEnd[1] - localStart[1]);
    const normal = [
      -(localEnd[1] - localStart[1]) / directionLength,
      (localEnd[0] - localStart[0]) / directionLength
    ];
    const halfWidth = surfaceWidthMeters / 2;
    const path = [
      fromLocalMeters([-normal[0] * halfWidth, -normal[1] * halfWidth], point),
      fromLocalMeters([normal[0] * halfWidth, normal[1] * halfWidth], point)
    ];
    const transverseMarkingObjectIds = getCrosswalkTransverseMarkingObjectIds(
      resultsByKey,
      path,
      CROSSWALK_WIDTH_METERS
    );
    return {
      id: `crosswalk-guide-${crosswalk.properties.OBJECTID}`,
      path,
      widthMeters: CROSSWALK_WIDTH_METERS,
      dashMeters: [0.6, 0.6],
      dashPixels: [7, 7],
      justified: true,
      transverseMarkingObjectIds,
      source: [
        getSourceRef(crosswalkSource, crosswalk),
        getSourceRef(streetSource, nearest.street)
      ],
      properties: crosswalk.properties,
      derived: true,
      derivation: {
        operation: 'perpendicular crosswalk guide centered on inventory point',
        parameters: {
          streetSurfaceWidthFeet: nearest.street.properties.SURFACEWIDTH,
          sourceToCenterlineResidualMeters: nearest.distanceMeters,
          barWidthMeters: 0.6,
          gapWidthMeters: 0.6
        },
        representation:
          'cartographic crosswalk extent replacing matched SDOT stripe polygons in the runtime assets'
      }
    };
  });
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
- Derived two crosswalk guides from official in-service inventory points and official street surface widths; matched source stripe polygons are omitted from the runtime assets.
- Did not simplify, manually redraw, or snap official channelization geometry.

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
  const crosswalkGuides = createCrosswalkGuides(resultsByKey);
  const {symbolPaths, summary: symbolStitching} = createStitchedSymbolPaths(resultsByKey);
  validateSymbolCoordinates(resultsByKey, symbolPaths);
  const assets = createRenderAssets(resultsByKey, {laneBands, crosswalkGuides, symbolPaths});
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
        output: 'assets.crosswalks',
        operation: 'perpendicular baseline across official surface width',
        sourceKeys: ['crosswalks', 'streets'],
        matchedTransverseMarkingCount: crosswalkGuides.reduce(
          (count, guide) => count + guide.transverseMarkingObjectIds.length,
          0
        ),
        outputFeatureCount: crosswalkGuides.length
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
