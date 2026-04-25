/* ============================================================
   app.js  –  North End Gentrification Heatmap
   Leaflet + vanilla JS, no framework dependencies
   ============================================================ */

'use strict';

// ── Constants ────────────────────────────────────────────────────────────────

const YEARS = [1950, 1960, 1970, 1980, 1990, 2000];

const _v = Date.now();   // cache-busting timestamp
const GEOJSON_PATHS = {
  '1950_1960': `./final_datasets/north_end_census_1950_1960_geo.geojson?v=${_v}`,
  '1970_2000': `./final_datasets/north_end_census_1970_2000_geo.geojson?v=${_v}`,
};

const MAP_CENTER = [42.3659, -71.0543];
const MAP_ZOOM   = 15;

// Gentrification color ramp: very light → dark red
const GENT_COLOR_STOPS = [
  [255, 245, 240],   // very light blush
  [252, 187, 161],   // light salmon
  [251, 106,  74],   // orange-red
  [203,  24,  29],   // red
  [103,   0,  13],   // dark crimson
];

// ── State ────────────────────────────────────────────────────────────────────

let map;
let geoData      = {};
let currentYearIdx = 0;
let activeLayer  = null;
let tooltip;
let lastHoverFeature = null;

let weights = { occupation: 5, income: 5, rent: 5 };

// ── Color helpers ─────────────────────────────────────────────────────────────

function lerpColor(a, b, t) {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

function sampleRamp(stops, t) {
  t = Math.max(0, Math.min(1, t));
  const n   = stops.length - 1;
  const raw = t * n;
  const lo  = Math.floor(raw);
  const hi  = Math.min(lo + 1, n);
  return lerpColor(stops[lo], stops[hi], raw - lo);
}

function rgbStr([r, g, b]) { return `rgb(${r},${g},${b})`; }

// ── Format helpers ────────────────────────────────────────────────────────────

function fmt(n, decimals = 0) {
  if (n == null) return '—';
  return Number(n).toLocaleString('en-US', { maximumFractionDigits: decimals });
}
function fmtCurrency(n) {
  if (n == null) return '—';
  return '$' + Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 });
}
function fmtPct(n) {
  if (n == null) return '—';
  return (Number(n) * 100).toFixed(1) + '%';
}
function fmtNorm(n) {
  if (n == null) return '—';
  return Number(n).toFixed(3);
}

// ── Data helpers ──────────────────────────────────────────────────────────────

function getCensus(feature, year) {
  return feature.properties[`census_${year}`] || null;
}

function datasetKey(year) {
  return year <= 1960 ? '1950_1960' : '1970_2000';
}

function tractLabel(feature, year) {
  const p = feature.properties;
  if (p.TRACTA) {
    const n = typeof p.TRACTA === 'number' ? p.TRACTA : parseInt(p.TRACTA);
    return `Tract ${n}`;
  }
  const c  = getCensus(feature, year);
  if (c && c.TRACTA) return `Tract F-${c.TRACTA}`;
  const gj = p.GISJOIN || '';
  const m  = gj.match(/F000(\d)$/);
  return m ? `Tract F-${m[1]}` : gj;
}

// ── Gentrification index ──────────────────────────────────────────────────────

function computeIndex(census) {
  if (!census) return null;
  const { occupation, income, rent } = weights;
  let sum = 0, used = 0;

  const wc  = census.Norm_Pct_White_Collar;
  const inc = census.Norm_Median_Family_Income;  // matches Python output field name
  const rnt = census.Norm_Median_Rent;

  if (wc  != null && occupation > 0) { sum += occupation * wc;  used += occupation; }
  if (inc != null && income     > 0) { sum += income     * inc; used += income; }
  if (rnt != null && rent       > 0) { sum += rent       * rnt; used += rent; }

  return used > 0 ? sum / used : null;
}

function getIndexRange(data, year) {
  const vals = data.features
    .map(f => computeIndex(getCensus(f, year)))
    .filter(v => v != null);
  if (!vals.length) return { min: 0, max: 1 };
  return { min: Math.min(...vals), max: Math.max(...vals) };
}

// ── GeoJSON loading ───────────────────────────────────────────────────────────

async function loadGeoJSON(key, path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  geoData[key] = await res.json();
}

// ── Map init ──────────────────────────────────────────────────────────────────

function initMap() {
  map = L.map('map', { center: MAP_CENTER, zoom: MAP_ZOOM });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);
}

// ── Rendering ─────────────────────────────────────────────────────────────────

function renderYear(yearIdx) {
  const year = YEARS[yearIdx];
  const key  = datasetKey(year);
  const data = geoData[key];
  if (!data) { console.warn('Data not loaded:', key); return; }

  if (activeLayer) { map.removeLayer(activeLayer); activeLayer = null; }

  const { min, max } = getIndexRange(data, year);
  const range = max - min || 1;

  activeLayer = L.geoJSON(data, {
    style: feature => {
      const idx = computeIndex(getCensus(feature, year));
      const t   = idx != null ? (idx - min) / range : 0;
      const rgb = sampleRamp(GENT_COLOR_STOPS, t);
      return {
        fillColor:   rgbStr(rgb),
        fillOpacity: 0.80,
        color:       'rgba(80,80,80,0.3)',
        weight:      1.5,
      };
    },
    onEachFeature: (feature, layer) => {
      layer.on({
        mouseover: e => onHover(e, feature, year),
        mousemove: e => onHover(e, feature, year),
        mouseout:  ()  => onOut(),
      });
    },
  }).addTo(map);

  if (yearIdx === 0 || !lastHoverFeature) {
    try { map.fitBounds(activeLayer.getBounds(), { padding: [20, 20] }); } catch (_) {}
  }

  updateLegend(min, max);
  updateStats(data, year);
}

// ── Tooltip ───────────────────────────────────────────────────────────────────

function onHover(e, feature, year) {
  lastHoverFeature = feature;
  e.target.setStyle({ fillOpacity: 0.97, weight: 2.5, color: 'rgba(40,40,40,0.7)' });

  const rect = document.getElementById('map').getBoundingClientRect();
  showTooltip(
    e.originalEvent.clientX - rect.left,
    e.originalEvent.clientY - rect.top,
    feature, year
  );
}

function onOut() {
  lastHoverFeature = null;
  hideTooltip();
  if (activeLayer) activeLayer.resetStyle();
}

function showTooltip(x, y, feature, year) {
  const census = getCensus(feature, year);
  const label  = tractLabel(feature, year);

  tooltip.classList.remove('hidden');
  document.getElementById('tt-tract-id').textContent = label;
  document.getElementById('tt-year').textContent     = year;

  const grid = document.getElementById('tt-grid');
  grid.innerHTML = '';

  if (!census) {
    grid.innerHTML = '<span class="tt-label" style="grid-column:1/-1;color:var(--text-3)">No data</span>';
  } else {
    buildTooltipRows(census, year).forEach(row => {
      if (row === 'sep') {
        const d = document.createElement('div');
        d.className = 'tt-separator';
        grid.appendChild(d);
        return;
      }
      const lbl = document.createElement('span');
      lbl.className = 'tt-label';
      lbl.textContent = row.label;
      const val = document.createElement('span');
      val.className = `tt-value${row.highlight ? ' highlight' : ''}`;
      val.textContent = row.value;
      grid.appendChild(lbl);
      grid.appendChild(val);
    });
  }

  // Position
  const mapEl   = document.getElementById('map');
  const mapRect = mapEl.getBoundingClientRect();
  const ttW = 265, ttH = 360;
  let tx = x + 16, ty = y - 20;
  if (tx + ttW > mapRect.width)  tx = x - ttW - 16;
  if (ty + ttH > mapRect.height) ty = mapRect.height - ttH - 10;
  if (ty < 0) ty = 10;
  tooltip.style.left = tx + 'px';
  tooltip.style.top  = ty + 'px';
}

function hideTooltip() {
  tooltip.classList.add('hidden');
}

function buildTooltipRows(census, year) {
  const rows = [];
  const idx  = computeIndex(census);

  // Gentrification index (top, highlighted)
  rows.push({ label: 'Gentrification Index', value: idx != null ? idx.toFixed(3) : '—', highlight: true });
  rows.push('sep');

  // Population
  rows.push({ label: 'Total Population', value: fmt(census.Total_Population) });

  // Italian groups with pct
  const italianKey = 'Total_Italian_Foreign_Stock' in census
    ? 'Total_Italian_Foreign_Stock' : 'Total_Italian_Demographic';
  if (census[italianKey]             != null) rows.push({ label: 'Italian Demographic', value: `${fmt(census[italianKey])} (${fmtPct(census.Pct_Italian_Demographic)})` });
  if (census.Italian_1st_Generation != null) rows.push({ label: '1st Gen Italian',      value: `${fmt(census.Italian_1st_Generation)} (${fmtPct(census.Pct_Italian_1st_Gen)})` });
  if (census.Italian_Americans       != null) rows.push({ label: 'Italian Americans',    value: `${fmt(census.Italian_Americans)} (${fmtPct(census.Pct_Italian_Americans)})` });
  if (census.Non_Italian_Population  != null) rows.push({ label: 'Non-Italian',          value: `${fmt(census.Non_Italian_Population)} (${fmtPct(census.Pct_Non_Italian)})` });
  rows.push('sep');

  // Economic (raw + normalized)
  if (census.Median_Rent         != null) rows.push({ label: 'Median Rent',    value: `${fmtCurrency(census.Median_Rent)} [${fmtNorm(census.Norm_Median_Rent)}]` });
  if (census.Median_Family_Income!= null) rows.push({ label: 'Median Income',  value: `${fmtCurrency(census.Median_Family_Income)} [${fmtNorm(census.Norm_Median_Family_Income)}]` });
  if (census.Median_Age          != null) rows.push({ label: 'Median Age',     value: `${fmt(census.Median_Age, 1)} [${fmtNorm(census.Norm_Median_Age)}]` });
  rows.push('sep');

  // Occupation (raw + normalized)
  if (census.Pct_White_Collar != null) rows.push({ label: '% White Collar', value: `${fmtPct(census.Pct_White_Collar)} [${fmtNorm(census.Norm_Pct_White_Collar)}]` });
  if (census.Pct_Blue_Collar  != null) rows.push({ label: '% Blue Collar',  value: `${fmtPct(census.Pct_Blue_Collar)} [${fmtNorm(census.Norm_Pct_Blue_Collar)}]` });

  return rows;
}

// ── Legend & Stats ────────────────────────────────────────────────────────────

function updateLegend(min, max) {
  document.getElementById('legend-min').textContent = min.toFixed(3);
  document.getElementById('legend-max').textContent = max.toFixed(3);
}

function updateStats(data, year) {
  const censuses = data.features.map(f => getCensus(f, year)).filter(Boolean);

  const sumKey = key => censuses.reduce((s, c) => s + (c[key] != null ? Number(c[key]) : 0), 0);
  const avgKey = key => {
    const vals = censuses.map(c => c[key]).filter(v => v != null);
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  };
  const hasKey = key => censuses.some(c => c[key] != null);

  const italianKey = hasKey('Total_Italian_Foreign_Stock')
    ? 'Total_Italian_Foreign_Stock' : 'Total_Italian_Demographic';

  // Avg gentrification index
  const idxVals = censuses.map(c => computeIndex(c)).filter(v => v != null);
  const avgIdx  = idxVals.length ? idxVals.reduce((a, b) => a + b, 0) / idxVals.length : null;

  const rows = [];
  rows.push({ label: 'Avg. Gent. Index',  value: avgIdx != null ? avgIdx.toFixed(3) : '—' });
  rows.push({ sep: true });
  rows.push({ label: 'Total Population',  value: fmt(sumKey('Total_Population')) });
  if (hasKey(italianKey))              rows.push({ label: 'Italian Demographic', value: fmt(sumKey(italianKey)) });
  if (hasKey('Italian_1st_Generation')) rows.push({ label: '1st Gen. Italian',  value: fmt(sumKey('Italian_1st_Generation')) });
  if (hasKey('Italian_Americans'))      rows.push({ label: 'Italian Americans', value: fmt(sumKey('Italian_Americans')) });
  if (hasKey('Non_Italian_Population')) rows.push({ label: 'Non-Italian',       value: fmt(sumKey('Non_Italian_Population')) });
  rows.push({ sep: true });
  rows.push({ label: 'Avg. Median Rent',   value: fmtCurrency(avgKey('Median_Rent')) });
  rows.push({ label: 'Avg. Median Income', value: fmtCurrency(avgKey('Median_Family_Income')) });
  rows.push({ label: 'Avg. % White Collar',value: fmtPct(avgKey('Pct_White_Collar')) });

  document.getElementById('stats-rows').innerHTML = rows.map(r => {
    if (r.sep) return '<div class="stat-sep"></div>';
    return `<div class="stat-row"><span class="stat-label">${r.label}</span><span class="stat-value">${r.value}</span></div>`;
  }).join('');
}

// ── Sliders ───────────────────────────────────────────────────────────────────

function updateWeightFormula() {
  const { occupation: o, income: i, rent: r } = weights;
  const total = o + i + r;
  let txt;
  if (total === 0) {
    txt = '(all weights are 0)';
  } else {
    const parts = [];
    if (o > 0) parts.push(`${(o/total*100).toFixed(0)}% occupation`);
    if (i > 0) parts.push(`${(i/total*100).toFixed(0)}% income`);
    if (r > 0) parts.push(`${(r/total*100).toFixed(0)}% rent`);
    txt = parts.join(' + ');
  }
  document.getElementById('formula-txt').textContent = txt;
}

function initWeightSliders() {
  const configs = [
    { id: 'w-occ',  valId: 'w-occ-val',  key: 'occupation' },
    { id: 'w-inc',  valId: 'w-inc-val',  key: 'income' },
    { id: 'w-rent', valId: 'w-rent-val', key: 'rent' },
  ];

  configs.forEach(({ id, valId, key }) => {
    const slider = document.getElementById(id);
    const label  = document.getElementById(valId);

    function update() {
      const v = parseInt(slider.value);
      weights[key] = v;
      label.textContent = v;
      // Update fill
      const pct = (v / 10) * 100;
      slider.style.setProperty('--pct', pct + '%');
      updateWeightFormula();
      renderYear(currentYearIdx);
    }

    slider.addEventListener('input', update);
    // Init fill
    slider.style.setProperty('--pct', '50%');
  });

  updateWeightFormula();
}

function initYearSlider() {
  const slider = document.getElementById('year-slider');

  function updateFill() {
    const pct = (parseInt(slider.value) / (YEARS.length - 1)) * 100;
    slider.style.setProperty('--pct', pct + '%');
  }

  slider.addEventListener('input', () => {
    const idx  = parseInt(slider.value);
    const year = YEARS[idx];
    currentYearIdx = idx;
    document.getElementById('year-display').textContent      = year;
    document.getElementById('header-year-label').textContent = year;
    updateFill();
    renderYear(idx);
  });

  updateFill();
}

// ── Boot ──────────────────────────────────────────────────────────────────────

async function boot() {
  tooltip = document.getElementById('tooltip');
  initMap();
  initYearSlider();
  initWeightSliders();

  document.getElementById('stats-rows').innerHTML =
    '<div class="stat-row"><span class="stat-label">Loading data…</span></div>';

  try {
    await Promise.all([
      loadGeoJSON('1950_1960', GEOJSON_PATHS['1950_1960']),
      loadGeoJSON('1970_2000', GEOJSON_PATHS['1970_2000']),
    ]);
    renderYear(0);
  } catch (err) {
    console.error('Failed to load GeoJSON:', err);
    document.getElementById('stats-rows').innerHTML =
      '<div class="stat-row"><span class="stat-label" style="color:red">Error loading data</span></div>';
  }
}

document.addEventListener('DOMContentLoaded', boot);
