// deck.gl
// SPDX-License-Identifier: MIT
// Copyright (c) vis.gl contributors

const SERVICE_URL =
  'https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/SDOT_Channelization_view/FeatureServer';
const CANDIDATES = [
  {
    name: 'Dexter Avenue N and Thomas Street',
    bounds: [-122.3431, 47.62025, -122.3415, 47.6215]
  },
  {
    name: '2nd Avenue and Pike Street',
    bounds: [-122.341, 47.6087, -122.3385, 47.6103]
  }
];

async function queryLayer(bounds, layerId) {
  const url = new URL(`${SERVICE_URL}/${layerId}/query`);
  const parameters = {
    f: 'geojson',
    where: '1=1',
    geometry: bounds.join(','),
    geometryType: 'esriGeometryEnvelope',
    inSR: 4326,
    outSR: 4326,
    spatialRel: 'esriSpatialRelIntersects',
    outFields: '*',
    returnGeometry: true
  };
  for (const [key, value] of Object.entries(parameters)) {
    url.searchParams.set(key, String(value));
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: ${url}`);
  }
  const data = await response.json();
  if (data.error) {
    throw new Error(data.error.message);
  }
  return data.features;
}

for (const candidate of CANDIDATES) {
  const layers = await Promise.all(Array.from({length: 7}, (_, layerId) => queryLayer(candidate.bounds, layerId)));
  const longitudinal = layers[4];
  const dashTypes = [
    ...new Set(
      longitudinal
        .map(feature => feature.properties.Type)
        .filter(value => value && value !== 'Solid')
    )
  ];
  const nonNullWidths = longitudinal.filter(feature => feature.properties.Width != null).length;
  const score = [
    dashTypes.length >= 2,
    dashTypes.some(type => /dash.+skip/i.test(type)),
    layers[3].length > 0,
    layers[5].length > 0,
    layers[0].length > 0,
    layers[1].length > 0,
    layers[2].length > 0,
    nonNullWidths > 0
  ].filter(Boolean).length;
  console.log(
    JSON.stringify({
      candidate: candidate.name,
      score,
      maximumScore: 8,
      featureCounts: layers.map(features => features.length),
      dashTypes,
      longitudinalFeaturesWithWidth: nonNullWidths
    })
  );
}
