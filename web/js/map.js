import { DATA, MAP_INIT, NORREBRO_BOUNDS, SCORE_RAMP, GROUP_RAMPS, TABS } from "./config.js";
import { disableScrollLock } from "./state.js";

let map;
let _stepOverlay  = null;
let _imagePanel   = null;
let _segmentFeatures = null;
let _stopFeatures = null;
let _dynamicRampApplied = false;
let _activeDemoFields = null;
let _rampLo = null;
let _rampHi = null;
let _stopSelectCallback = null;
let _activeGroup = "aggregate";
let _activeMode  = "contextual";

const STOP_SCORE_FIELD = {
  baseline:    "score_catchment",
  aggregate:   "score_health_combined",
  working_age: "score_health_working_age",
  elderly:     "score_health_elderly",
  children:    "score_health_children",
};

const DEMO_GROUP_FIELD = {
  aggregate:   { mid: "pop_total_mid",              lo: "pop_total_low",              hi: "pop_total_high",              unc: "unc_pct_total"      },
  working_age: { mid: "pop_working_age_30_64_mid",  lo: "pop_working_age_30_64_low",  hi: "pop_working_age_30_64_high",  unc: "unc_pct_working_age" },
  elderly:     { mid: "pop_older_adults_65_79_mid", lo: "pop_older_adults_65_79_low", hi: "pop_older_adults_65_79_high", unc: "unc_pct_elderly"     },
  children:    { mid: "pop_children_0_14_mid",      lo: "pop_children_0_14_low",      hi: "pop_children_0_14_high",      unc: "unc_pct_children"    },
};

// ── Initialise MapLibre map ──────────────────────────────────────────────────

export function initMap() {
  map = new maplibregl.Map({
    container: "map",
    style: {
      version: 8,
      glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
      sources: {},
      layers: [
        {
          id: "background",
          type: "background",
          paint: { "background-color": "#e8edf2" },
        },
      ],
    },
    center: MAP_INIT.center,
    zoom: MAP_INIT.zoom,
    minZoom: 11,
    maxZoom: 18,
    maxBounds: [[12.46, 55.64], [12.64, 55.74]],
    attributionControl: false,
  });

  map.on("load", () => {
    _addSources();
    _addLayers();
    _addAttribution();
    _addPopups();
    // Narrative mode: map is a locked viewport, not an interactive tool
    _lockMap();
    showOverview();
  });

  return map;
}

// ── Source registration ──────────────────────────────────────────────────────

function _addSources() {
  map.addSource("boundary-src",     { type: "geojson", data: DATA.boundary });
  map.addSource("bus-context-src",  { type: "geojson", data: DATA.busContext });
  map.addSource("segments-src",     { type: "geojson", data: DATA.segments });
  map.addSource("stops-src",        { type: "geojson", data: DATA.stops });
  map.addSource("demographics-src", { type: "geojson", data: DATA.demographics });
  map.addSource("footprints-src",   { type: "geojson", data: DATA.footprints });
  map.addSource("parks-src",        { type: "geojson", data: DATA.parks });

  // Pre-fetch segment features; apply dynamic ramp once loaded
  fetch(DATA.segments).then(r => r.json()).then(d => {
    _segmentFeatures = d.features;
    _applyDynamicRamp(_segmentFeatures);
  });

  // Pre-fetch stop features for scatter plot
  fetch(DATA.stops).then(r => r.json()).then(d => { _stopFeatures = d.features; });
}

export function getSegmentFeatures() { return _segmentFeatures; }
export function getStopFeatures()    { return _stopFeatures;    }

// ── Layer registration ───────────────────────────────────────────────────────

function _addLayers() {
  // Base street tile layer (OSM Bright via CARTO CDN)
  map.addSource("osm", {
    type: "raster",
    tiles: ["https://a.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png"],
    tileSize: 256,
    attribution: "© OpenStreetMap contributors © CARTO",
  });
  map.addLayer({ id: "basemap", type: "raster", source: "osm", paint: { "raster-opacity": 0.55 } });

  // District boundary
  map.addLayer({
    id: "boundary-fill",
    type: "fill",
    source: "boundary-src",
    paint: { "fill-color": "#2171b5", "fill-opacity": 0.04 },
  });
  map.addLayer({
    id: "boundary-line",
    type: "line",
    source: "boundary-src",
    paint: { "line-color": "#2171b5", "line-width": 1.5, "line-dasharray": [4, 3] },
  });

  // Park polygons — hidden initially (toggled by overlay checkbox).
  map.addLayer({
    id: "parks-fill",
    type: "fill",
    source: "parks-src",
    layout: { visibility: "none" },
    paint: { "fill-color": "#4caf50", "fill-opacity": 0.25 },
  });
  map.addLayer({
    id: "parks-line",
    type: "line",
    source: "parks-src",
    layout: { visibility: "none" },
    paint: { "line-color": "#2e7d32", "line-width": 1, "line-opacity": 0.6 },
  });

  // Demographics heatmap — hidden initially (toggled by overlay checkbox).
  // Radius scales exponentially with zoom (base 2) so the heatmap covers the
  // same geographic footprint regardless of zoom level (~150m radius at all zooms).
  map.addLayer({
    id: "demographics-heatmap",
    type: "heatmap",
    source: "demographics-src",
    layout: { visibility: "none" },
    paint: {
      "heatmap-weight": ["interpolate", ["linear"], ["get", "pop_total_mid"], 0, 0, 50, 1],
      "heatmap-intensity": 0.8,
      // Radius = 5px at zoom 12, exponential base-2 → geographically stable
      "heatmap-radius": ["interpolate", ["exponential", 2], ["zoom"], 10, 1.25, 16, 80],
      "heatmap-opacity": 0.60,
      "heatmap-color": [
        "interpolate", ["linear"], ["heatmap-density"],
        0,    "rgba(255,255,255,0)",
        0.25, "rgba(160,160,160,0.5)",
        0.7,  "rgba(40,40,40,0.85)",
        1.0,  "rgba(10,10,10,0.97)",
      ],
    },
  });

  // Building footprints — greyscale, height-tinted, subtle. Hidden until step 4.
  map.addLayer({
    id: "footprints-layer",
    type: "fill",
    source: "footprints-src",
    layout: { visibility: "none" },
    paint: {
      // Taller buildings → slightly darker grey
      "fill-color": [
        "interpolate", ["linear"], ["get", "floors"],
        1, "#d8d8d8",
        4, "#b0b0b0",
        8, "#888888",
       12, "#606060",
      ],
      "fill-opacity": 0.35,
      "fill-outline-color": "rgba(80,80,80,0.15)",
    },
  });

  // Grey context bus routes (outside scoring zone) — hidden until scored segments shown
  map.addLayer({
    id: "bus-routes-context",
    type: "line",
    source: "bus-context-src",
    layout: { visibility: "none" },
    paint: {
      "line-color": "#aaa",
      "line-width": ["interpolate", ["linear"], ["zoom"], 12, 1.0, 16, 2.5],
      "line-opacity": 0.5,
    },
  });

  // Scored segments (aggregate) — hidden initially
  map.addLayer({
    id: "segments-aggregate",
    type: "line",
    source: "segments-src",
    layout: { visibility: "none" },
    paint: {
      "line-color": SCORE_RAMP,
      "line-width": ["interpolate", ["linear"], ["zoom"], 12, 2.0, 16, 5],
      "line-opacity": 1.0,
    },
  });

  // Per-group segment layers (share from same source, different paint)
  for (const [group, ramp] of Object.entries(GROUP_RAMPS)) {
    if (group === "aggregate") continue;
    map.addLayer({
      id: `segments-${group}`,
      type: "line",
      source: "segments-src",
      layout: { visibility: "none" },
      paint: {
        "line-color": ramp,
        "line-width": ["interpolate", ["linear"], ["zoom"], 12, 2.0, 16, 5],
        "line-opacity": 1.0,
      },
    });
  }

  // Existing bus stops — two-tone using palette:
  //   internal (context=false): steel-azure #004e98
  //   context  (context=true):  silver      #c0c0c0
  map.addLayer({
    id: "stops-layer",
    type: "circle",
    source: "stops-src",
    layout: { visibility: "none" },
    paint: {
      "circle-radius":       ["case", ["get", "context"], 3.5, 5],
      "circle-color":        ["case", ["get", "context"], "#c0c0c0", "#004e98"],
      "circle-stroke-width": ["case", ["get", "context"], 0.8, 1.5],
      "circle-stroke-color": "#ffffff",
      "circle-opacity":      ["case", ["get", "context"], 0.5, 0.9],
    },
  });

  // Selection ring — always rendered, controlled by filter (empty → nothing shown)
  map.addLayer({
    id: "stops-highlight",
    type: "circle",
    source: "stops-src",
    filter: ["==", ["get", "stop_id"], ""],
    paint: {
      "circle-radius": 10,
      "circle-color": "rgba(0,0,0,0)",
      "circle-stroke-width": 2.5,
      "circle-stroke-color": "#ffffff",
    },
  });
}

// Band definitions for stop popups (mirrors scatter.js BANDS — keep in sync)
const _POPUP_BANDS = [
  { lo: 0,    hi: 0.20,     label: "Low benefit", color: "#c94e00" },
  { lo: 0.20, hi: 0.40,     label: "Moderate",    color: "#7a7a7a" },
  { lo: 0.40, hi: 0.60,     label: "Good",        color: "#3a6ea5" },
  { lo: 0.60, hi: 0.80,     label: "High",        color: "#1d5490" },
  { lo: 0.80, hi: Infinity, label: "Optimal",     color: "#004e98" },
];

function _getBand(normScore) {
  return _POPUP_BANDS.find(b => normScore >= b.lo && normScore < b.hi) || _POPUP_BANDS[_POPUP_BANDS.length - 1];
}

const _GROUP_LABEL = {
  aggregate: "Aggregate", working_age: "Working-age",
  elderly: "Elderly",     children: "Children",
};

const SEG_LAYERS = ["segments-aggregate", "segments-working_age", "segments-elderly", "segments-children"];

function _addPopups() {
  // ── Segment hover/click popup ──────────────────────────────────────────────
  const _segPopup = new maplibregl.Popup({ maxWidth: "220px", closeButton: false, closeOnClick: false });

  SEG_LAYERS.forEach(layerId => {
    map.on("mouseenter", layerId, (e) => {
      map.getCanvas().style.cursor = "pointer";
      const p = e.features[0].properties;
      const dec = (v) => (v != null && !isNaN(+v) ? (+v).toFixed(3) : "—");

      const isBaseline = _activeMode === "baseline";
      const activeField = isBaseline
        ? "score_catchment"
        : (STOP_SCORE_FIELD[_activeGroup] || STOP_SCORE_FIELD.aggregate);
      const rawScore = +(p[activeField]) || 0;
      const normScore = (_rampLo !== null && _rampHi !== _rampLo)
        ? Math.max(0, Math.min(1, (rawScore - _rampLo) / (_rampHi - _rampLo)))
        : rawScore;
      const band = _getBand(normScore);
      const modeName = isBaseline ? "Catchment Score" : "Health Score";

      const groupRows = isBaseline ? "" : `
        <hr class="popup-hr">
        <div class="popup-score-row popup-score-sub"><span>Working-age</span><span>${dec(p.score_health_working_age)}</span></div>
        <div class="popup-score-row popup-score-sub"><span>Elderly</span><span>${dec(p.score_health_elderly)}</span></div>
        <div class="popup-score-row popup-score-sub"><span>Children</span><span>${dec(p.score_health_children)}</span></div>`;

      const greenRow = isBaseline
        ? (p.green_pct_catchment != null
            ? `<div class="popup-score-row popup-score-sub" style="color:#2e7d32"><span>Green paths</span><span>${(+p.green_pct_catchment * 100).toFixed(1)}%</span></div>`
            : "")
        : (p.green_time_working_age != null
            ? `<div class="popup-score-row popup-score-sub" style="color:#2e7d32"><span>In green (WA / El / Ch)</span><span>${(+p.green_time_working_age).toFixed(1)} / ${(+p.green_time_elderly).toFixed(1)} / ${(+p.green_time_children).toFixed(1)} min</span></div>`
            : "");

      _segPopup
        .setLngLat(e.lngLat)
        .setHTML(`
          <div style="font-size:0.78em;color:#666;margin-bottom:4px">Bus-route segment</div>
          <div class="popup-score-row"><span>${modeName}</span><span>${dec(rawScore)}</span></div>
          <div class="popup-category" style="color:${band.color}">${band.label}</div>
          ${groupRows}
          ${greenRow}
        `)
        .addTo(map);
    });

    map.on("mousemove", layerId, (e) => {
      _segPopup.setLngLat(e.lngLat);
    });

    map.on("mouseleave", layerId, () => {
      map.getCanvas().style.cursor = "";
      _segPopup.remove();
    });
  });

  // Tooltips only on bus stops — not on segment/route layers
  map.on("click", "stops-layer", (e) => {
    const p = e.features[0].properties;
    if (p.context) return;
    highlightMapStop(p.stop_id);
    if (_stopSelectCallback) _stopSelectCallback(p.stop_id);

    const dec = (v) => (v != null && !isNaN(+v) ? (+v).toFixed(2) : "—");

    // Use active group + mode to determine the category label
    const scoreField = _activeMode === "baseline"
      ? "score_catchment"
      : (STOP_SCORE_FIELD[_activeGroup] || STOP_SCORE_FIELD.aggregate);
    const rawScore = +(p[scoreField]) || 0;
    const normScore = (_rampLo !== null && _rampHi !== _rampLo)
      ? Math.max(0, Math.min(1, (rawScore - _rampLo) / (_rampHi - _rampLo)))
      : rawScore;
    const band = _getBand(normScore);
    const modeName = _activeMode === "baseline" ? "Catchment Score" : "Health Score";

    new maplibregl.Popup({ maxWidth: "250px" })
      .setLngLat(e.lngLat)
      .setHTML(`
        <strong>${p.stop_name || "Bus stop"}</strong>
        ${p.route_names ? `<div style="font-size:0.78em;color:#666;margin:2px 0">Routes: ${p.route_names}</div>` : ""}
        <div class="popup-category" style="color:${band.color}">${band.label}</div>
        <div class="popup-mode">(${modeName} mode)</div>
        ${p.score_health_combined != null ? `
        <hr class="popup-hr">
        <div class="popup-score-row"><span>Combined</span><span>${dec(p.score_health_combined)}</span></div>
        <hr class="popup-hr">
        <div class="popup-score-row popup-score-sub"><span>Working-age</span><span>${dec(p.score_health_working_age)}</span></div>
        <div class="popup-score-row popup-score-sub"><span>Elderly</span><span>${dec(p.score_health_elderly)}</span></div>
        <div class="popup-score-row popup-score-sub"><span>Children</span><span>${dec(p.score_health_children)}</span></div>
        ` : ""}
      `)
      .addTo(map);
  });
  map.on("mouseenter", "stops-layer", () => { map.getCanvas().style.cursor = "pointer"; });
  map.on("mouseleave", "stops-layer", () => { map.getCanvas().style.cursor = ""; });
}

function _addAttribution() {
  map.addControl(
    new maplibregl.AttributionControl({ compact: true }),
    "bottom-right"
  );
}

// ── Scroll-step transition functions ────────────────────────────────────────

// Steps 1–3 are covered by image/SVG overlays.
// The map functions still prep the correct layer state so step 4 (showScoredNetwork)
// can reveal the scored network without a visible jump.
export function showOverview() { /* map hidden behind image panel — no action needed */ }

export function showCatchmentRing() {
  // Step 2: image overlay is shown; set district view + footprints as background.
  _setVisibility("footprints-layer", "visible");
  _setVisibility("segments-aggregate", "none");
  _setVisibility("bus-routes-context", "none");
  _setVisibility("stops-layer", "none");
  map.fitBounds(NORREBRO_BOUNDS, { padding: 50, duration: 0 });
}

export function showBenefitCurves() {
  // Step 3: fullscreen SVG overlay is shown; keep district view so the transition
  // into showScoredNetwork (step 4) is seamless when the overlay clears.
  _setVisibility("footprints-layer", "visible");
  _setVisibility("segments-aggregate", "none");
  _setVisibility("bus-routes-context", "none");
  _setVisibility("stops-layer", "none");
  map.fitBounds(NORREBRO_BOUNDS, { padding: 50, duration: 0 });
}

// Steps 4–5 share one locked view: district bounding box with buffer, instant (duration 0).
export function showScoredNetwork() {
  _setVisibility("segments-aggregate", "visible");
  _setVisibility("bus-routes-context", "visible");
  _setVisibility("footprints-layer", "visible");
  _setVisibility("stops-layer", "none");
  map.fitBounds(NORREBRO_BOUNDS, { padding: 50, duration: 0 });
}

export function showGapAnalysis() {
  _setVisibility("segments-aggregate", "visible");
  _setVisibility("bus-routes-context", "visible");
  _setVisibility("stops-layer", "visible");
  _setVisibility("footprints-layer", "none");
  // Same view as step 4 — no camera change
}

export function enterInteractiveTool() {
  _setVisibility("segments-aggregate", "visible");
  _setVisibility("bus-routes-context", "visible");
  _setVisibility("stops-layer", "visible");
  _removePlaceholderOverlay();
  removeStepOverlay();
  removeImagePanel();
  document.getElementById("tool-panel").classList.remove("hidden");
  document.getElementById("chart-panel").classList.remove("hidden");
  document.body.classList.add("is-interactive");
  _unlockMap();
  requestAnimationFrame(() => map.resize());
  setScoreMode("contextual");
}

// Non-bus tabs: open the panel but show only the basemap (no data layers)
export function enterInteractiveToolBasemap() {
  _hideAllScoreLayers();
  _setVisibility("stops-layer", "none");
  _removePlaceholderOverlay();
  document.getElementById("tool-panel").classList.remove("hidden");
  document.getElementById("chart-panel").classList.remove("hidden");
  document.body.classList.add("is-interactive");
  _unlockMap();
  requestAnimationFrame(() => map.resize());
}

// ── Score mode toggle ────────────────────────────────────────────────────────

export function setScoreMode(mode) {
  _activeMode = mode;
  const groupSection = document.getElementById("group-selector-section");
  if (groupSection) groupSection.classList.toggle("hidden", mode === "baseline");

  const titleEl = document.getElementById("legend-title");

  if (mode === "baseline") {
    if (titleEl) titleEl.textContent = "Network coverage";
    setActiveGroup("aggregate");
    if (_rampLo !== null) {
      if (map.getLayer("segments-aggregate"))
        map.setPaintProperty("segments-aggregate", "line-color", _buildRamp("score_catchment"));
      _applyStopRamp("baseline");
    }
  } else {
    if (titleEl) titleEl.textContent = "Health benefit score";
    if (_rampLo !== null) {
      if (map.getLayer("segments-aggregate"))
        map.setPaintProperty("segments-aggregate", "line-color", _buildRamp("score_health_combined"));
      _applyStopRamp("aggregate");
    }
  }
}

// ── Placeholder transitions for Rail / Cycling / Green tabs ──────────────────

let _placeholderOverlay = null;

function _showPlaceholderOverlay(message) {
  _removePlaceholderOverlay();
  _placeholderOverlay = document.createElement("div");
  _placeholderOverlay.id = "placeholder-overlay";
  _placeholderOverlay.innerHTML = `<p>${message}</p>`;
  document.getElementById("map").appendChild(_placeholderOverlay);
}

function _removePlaceholderOverlay() {
  if (_placeholderOverlay) {
    _placeholderOverlay.remove();
    _placeholderOverlay = null;
  }
}

export function showRailPlaceholder() {
  _hideAllScoreLayers();
  _setVisibility("stops-layer", "none");
  _removeCatchmentRing();
  _showPlaceholderOverlay("Rail scoring — data pipeline in progress");
  map.fitBounds(NORREBRO_BOUNDS, { padding: 40, duration: 1200 });
}

export function showCyclingPlaceholder() {
  _hideAllScoreLayers();
  _setVisibility("stops-layer", "none");
  _removeCatchmentRing();
  _showPlaceholderOverlay("Cycling analysis — methodology in development");
  map.fitBounds(NORREBRO_BOUNDS, { padding: 40, duration: 1200 });
}

export function showGreenPlaceholder() {
  _hideAllScoreLayers();
  _setVisibility("stops-layer", "none");
  _removeCatchmentRing();
  _showPlaceholderOverlay("Green space scoring — data pipeline in progress");
  map.fitBounds(NORREBRO_BOUNDS, { padding: 40, duration: 1200 });
}

export function backToNarrative() {
  disableScrollLock();
  document.getElementById("tool-panel").classList.add("hidden");
  document.getElementById("chart-panel").classList.add("hidden");
  document.body.classList.remove("is-interactive");
  _lockMap();
  requestAnimationFrame(() => {
    map.resize();
    window.scrollTo({ top: 0, behavior: "smooth" });
    showOverview();
  });
}

// ── Interactive tool: group toggle ──────────────────────────────────────────

export function setActiveGroup(group) {
  _activeGroup = group;
  const allLayers = [
    "segments-aggregate",
    "segments-working_age",
    "segments-elderly",
    "segments-children",
  ];
  for (const layer of allLayers) {
    _setVisibility(layer, "none");
  }
  const target = group === "aggregate" ? "segments-aggregate" : `segments-${group}`;
  _setVisibility(target, "visible");
  _applyStopRamp(group);
  _updateDemographicsGroup(group);
}

function _updateDemographicsGroup(group) {
  const f = DEMO_GROUP_FIELD[group] || DEMO_GROUP_FIELD.aggregate;
  _activeDemoFields = f;
  if (!map.getLayer("demographics-heatmap")) return;
  map.setPaintProperty("demographics-heatmap", "heatmap-weight",
    ["interpolate", ["linear"], ["get", f.mid], 0, 0, 50, 1]);
}

export function toggleStops(visible) {
  // Controls all stops (internal + context) together
  _setVisibility("stops-layer", visible ? "visible" : "none");
}

export function toggleDemographics(visible) {
  _setVisibility("demographics-heatmap", visible ? "visible" : "none");
}

export function toggleParks(visible) {
  const v = visible ? "visible" : "none";
  _setVisibility("parks-fill", v);
  _setVisibility("parks-line", v);
}


export function toggleInteriorOnly(interiorOnly) {
  const segLayers = [
    "segments-aggregate",
    "segments-working_age",
    "segments-elderly",
    "segments-children",
  ];
  const filter = interiorOnly ? ["==", ["get", "interior"], true] : null;
  for (const layer of segLayers) {
    if (map.getLayer(layer)) {
      map.setFilter(layer, filter);
    }
  }
}

// ── Dynamic color ramp ───────────────────────────────────────────────────────

// Low scores → orange, high scores → blue (orange = underserved, blue = well-served)
function _buildRamp(field) {
  if (_rampLo === null) return ["get", field]; // fallback before domain is set
  const at = (t) => _rampLo + (_rampHi - _rampLo) * t;
  return [
    "interpolate", ["linear"], ["get", field],
    at(0.0),  "#ff6700",  // pumpkin-spice — low / underserved
    at(0.25), "#ebebeb",  // platinum
    at(0.5),  "#c0c0c0",  // silver
    at(0.75), "#3a6ea5",  // cornflower-ocean
    at(1.0),  "#004e98",  // steel-azure — high / well-served
  ];
}

function _applyDynamicRamp(features) {
  const vals = features.map(f => +f.properties.score_health_combined).filter(v => !isNaN(v));
  if (!vals.length) return;
  vals.sort((a, b) => a - b);
  _rampLo = vals[0];
  _rampHi = vals[vals.length - 1];

  if (map.getLayer("segments-aggregate"))   map.setPaintProperty("segments-aggregate",   "line-color", _buildRamp("score_health_combined"));
  if (map.getLayer("segments-working_age")) map.setPaintProperty("segments-working_age", "line-color", _buildRamp("score_health_working_age"));
  if (map.getLayer("segments-elderly"))     map.setPaintProperty("segments-elderly",     "line-color", _buildRamp("score_health_elderly"));
  if (map.getLayer("segments-children"))    map.setPaintProperty("segments-children",    "line-color", _buildRamp("score_health_children"));

  _applyStopRamp("aggregate");
  _updateLegend();
  _dynamicRampApplied = true;
}

function _applyStopRamp(group) {
  if (!map.getLayer("stops-layer") || _rampLo === null) return;
  const field = STOP_SCORE_FIELD[group] || STOP_SCORE_FIELD.aggregate;
  map.setPaintProperty("stops-layer", "circle-color", [
    "case", ["get", "context"],
    "#c0c0c0",        // context stops stay silver
    _buildRamp(field),
  ]);
}

function _updateLegend() {
  const bar = document.querySelector("#legend .gradient");
  if (bar) bar.style.background =
    "linear-gradient(to right, #ff6700, #ebebeb, #c0c0c0, #3a6ea5, #004e98)";
  const minEl = document.getElementById("legend-min");
  const maxEl = document.getElementById("legend-max");
  if (minEl) minEl.textContent = "Low";
  if (maxEl) maxEl.textContent = "High";
}

// ── Cross-component API ───────────────────────────────────────────────────────

/** Returns the data-driven ramp domain so scatter.js can use identical colors. */
export function getRampDomain() { return { lo: _rampLo, hi: _rampHi }; }

/** Trigger a MapLibre resize (call after the map container changes dimensions). */
export function resizeMap() { if (map) requestAnimationFrame(() => map.resize()); }

/** Register a callback fired when the user clicks a stop on the map. */
export function setStopSelectCallback(fn) { _stopSelectCallback = fn; }

/** Highlight a stop on the map by stop_id (pass null to clear). */
export function highlightMapStop(stopId) {
  if (!map.getLayer("stops-highlight")) return;
  map.setFilter("stops-highlight",
    stopId != null
      ? ["==", ["get", "stop_id"], stopId]
      : ["==", ["get", "stop_id"], ""]
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function _setVisibility(layerId, visibility) {
  if (map.getLayer(layerId)) {
    map.setLayoutProperty(layerId, "visibility", visibility);
  }
}

function _lockMap() {
  map.scrollZoom.disable();
  map.dragPan.disable();
  map.dragRotate.disable();
  map.doubleClickZoom.disable();
  map.touchZoomRotate.disable();
  map.keyboard.disable();
}

function _unlockMap() {
  map.scrollZoom.enable();
  map.dragPan.enable();
  map.dragRotate.enable();
  map.doubleClickZoom.enable();
  map.touchZoomRotate.enable();
  map.keyboard.enable();
}

function _hideAllScoreLayers() {
  for (const layer of [
    "segments-aggregate",
    "segments-working_age",
    "segments-elderly",
    "segments-children",
    "bus-routes-context",
    "footprints-layer",
  ]) {
    _setVisibility(layer, "none");
  }
}

// Animated catchment ring using a MapLibre GeoJSON source updated on each frame
let _ringAnimFrame = null;
let _ringSource = null;

function _animateCatchmentRing(center) {
  _removeCatchmentRing();

  if (!map.getSource("catchment-src")) {
    map.addSource("catchment-src", { type: "geojson", data: _circleGeoJSON(center, 0) });
    map.addLayer({
      id: "catchment-layer",
      type: "line",
      source: "catchment-src",
      paint: {
        "line-color": "#2171b5",
        "line-width": 2,
        "line-dasharray": [4, 2],
        "line-opacity": 0.7,
      },
    });
  }

  let radiusM = 0;
  const MAX_R = 600;
  const STEP = 6;

  function frame() {
    radiusM = Math.min(radiusM + STEP, MAX_R);
    map.getSource("catchment-src").setData(_circleGeoJSON(center, radiusM));
    if (radiusM < MAX_R) {
      _ringAnimFrame = requestAnimationFrame(frame);
    }
  }
  _ringAnimFrame = requestAnimationFrame(frame);
}

function _removeCatchmentRing() {
  if (_ringAnimFrame) {
    cancelAnimationFrame(_ringAnimFrame);
    _ringAnimFrame = null;
  }
  if (map.getLayer("catchment-layer")) map.removeLayer("catchment-layer");
  if (map.getSource("catchment-src")) map.removeSource("catchment-src");
}

function _circleGeoJSON(center, radiusM) {
  // Approximate circle in WGS84 degrees using lat-corrected metre conversion
  const pts = 64;
  const latRad = (center[1] * Math.PI) / 180;
  const mPerDegLng = (Math.PI / 180) * 6371000 * Math.cos(latRad);
  const mPerDegLat = (Math.PI / 180) * 6371000;
  const coords = [];
  for (let i = 0; i <= pts; i++) {
    const angle = (2 * Math.PI * i) / pts;
    coords.push([
      center[0] + (Math.cos(angle) * radiusM) / mPerDegLng,
      center[1] + (Math.sin(angle) * radiusM) / mPerDegLat,
    ]);
  }
  return { type: "Feature", geometry: { type: "LineString", coordinates: coords } };
}

// ── Step illustration overlay (driven by scroll position via scroll.js) ──────

export function showStepOverlay(svgHtml, fullscreen = false) {
  removeStepOverlay();
  _stepOverlay = document.createElement("div");
  _stepOverlay.id = "step-illustration";
  if (fullscreen) _stepOverlay.classList.add("illu-full");
  _stepOverlay.innerHTML = svgHtml;
  document.getElementById("map").appendChild(_stepOverlay);
}

export function removeStepOverlay() {
  if (_stepOverlay) {
    _stepOverlay.remove();
    _stepOverlay = null;
  }
}

// ── Narrative image panel (base image + scroll-driven layers) ─────────────────

export function showImageOverlay(config) {
  const mapEl = document.getElementById("map");

  // If panel already exists with the same base, just swap the active layer
  if (_imagePanel && _imagePanel.dataset.base === config.base) {
    _imagePanel.querySelectorAll(".illu-layer").forEach((el) => {
      el.classList.toggle("illu-layer--active", el.dataset.id === config.activeId);
    });
    return;
  }

  // Build a fresh panel with all layers pre-loaded
  removeImagePanel();
  _imagePanel = document.createElement("div");
  _imagePanel.id = "illustration-panel";
  _imagePanel.dataset.base = config.base;

  const layersHtml = config.layers
    .map((l) => `<img class="illu-layer${l.id === config.activeId ? " illu-layer--active" : ""}"
         data-id="${l.id}" src="${l.src}" alt="">`)
    .join("\n");

  _imagePanel.innerHTML = `
    <div class="illu-image-stack">
      <img class="illu-base" src="${config.base}" alt="">
      ${layersHtml}
    </div>`;

  mapEl.appendChild(_imagePanel);
}

export function removeImagePanel() {
  if (_imagePanel) {
    _imagePanel.remove();
    _imagePanel = null;
  }
}
