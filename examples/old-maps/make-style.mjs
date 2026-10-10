// Builds an "old map" MapLibre style by recolouring OpenFreeMap's Positron style.
// Usage: node make-style.mjs > style.json

const BASE_STYLE = 'https://tiles.openfreemap.org/styles/positron';

// Positron is almost greyscale, so each colour is mapped by its lightness onto a ramp
// from ink to paper
const SEPIA_RAMP = [
  [0, [46, 33, 22]],
  [0.45, [102, 80, 56]],
  [0.7, [168, 145, 112]],
  [0.86, [218, 201, 167]],
  [0.95, [240, 229, 203]],
  [1, [250, 244, 228]]
];

// Colours that should keep a hue of their own, by layer id and paint property
const OVERRIDES = {
  water: {'fill-color': '#b8c3b4'},
  waterway: {'line-color': '#a7b5a6'},
  waterway_line_label: {'text-color': '#56685f'},
  water_name_point_label: {'text-color': '#4c5f57'},
  water_name_line_label: {'text-color': '#4c5f57'},
  park: {'fill-color': '#e2dbb6'},
  landcover_wood: {'fill-color': '#dbd5ae'}
};

// Modern map furniture that looks out of place next to an old map
const REMOVED_LAYERS = [
  'highway-shield-non-us',
  'highway-shield-us-interstate',
  'road_shield_us',
  'airport'
];

// Engraved maps letter their places in spaced capitals
const SPACED_CAPITALS = ['label_city', 'label_city_capital', 'label_town'];

function parseColor(value) {
  let m = value.match(/^#([0-9a-f]{3,8})$/i);
  if (m) {
    let hex = m[1];
    if (hex.length <= 4) {
      hex = [...hex].map(c => c + c).join('');
    }
    const n = hex.match(/../g).map(h => parseInt(h, 16));
    return [n[0], n[1], n[2], n.length > 3 ? n[3] / 255 : 1];
  }
  m = value.match(/^(rgba?|hsla?)\(([^)]*)\)$/i);
  if (!m) {
    return null;
  }
  const parts = m[2].split(',').map(s => parseFloat(s));
  const alpha = parts.length > 3 ? parts[3] : 1;
  if (m[1].startsWith('rgb')) {
    return [parts[0], parts[1], parts[2], alpha];
  }
  const [h, s, l] = [parts[0] / 360, parts[1] / 100, parts[2] / 100];
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const hue = t => {
    t = (t + 1) % 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  return [hue(h + 1 / 3) * 255, hue(h) * 255, hue(h - 1 / 3) * 255, alpha];
}

function toSepia([r, g, b, a]) {
  const lightness = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  let i = 1;
  while (i < SEPIA_RAMP.length - 1 && SEPIA_RAMP[i][0] < lightness) {
    i++;
  }
  const [l0, c0] = SEPIA_RAMP[i - 1];
  const [l1, c1] = SEPIA_RAMP[i];
  const t = Math.min(Math.max((lightness - l0) / (l1 - l0), 0), 1);
  const [sr, sg, sb] = c0.map((c, k) => Math.round(c + (c1[k] - c) * t));
  return a < 1 ? `rgba(${sr},${sg},${sb},${a})` : `rgb(${sr},${sg},${sb})`;
}

// Recolours every colour string in a paint value, including the stops of expressions
function recolor(value) {
  if (Array.isArray(value)) {
    return value.map(recolor);
  }
  if (typeof value === 'string') {
    const color = parseColor(value);
    return color ? toSepia(color) : value;
  }
  return value;
}

const style = await (await fetch(BASE_STYLE)).json();

style.name = 'Old maps (sepia Positron)';
delete style.sources.ne2_shaded;
style.layers = style.layers.filter(layer => !REMOVED_LAYERS.includes(layer.id));

for (const layer of style.layers) {
  for (const [key, value] of Object.entries(layer.paint || {})) {
    if (key.endsWith('color')) {
      layer.paint[key] = OVERRIDES[layer.id]?.[key] ?? recolor(value);
    }
  }
  if (SPACED_CAPITALS.includes(layer.id)) {
    layer.layout = {...layer.layout, 'text-transform': 'uppercase', 'text-letter-spacing': 0.12};
  }
}

process.stdout.write(`${JSON.stringify(style, null, 2)}\n`);
