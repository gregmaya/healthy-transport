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
let _catchRampLo = null;
let _catchRampHi = null;
let _stopSelectCallback = null;
let _activeGroup = "aggregate";
let _activeMode  = "contextual";
let _neighbourhoodFeatures = null;

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
    maxZoom: 17,
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
  map.addSource("neighbourhoods-src", { type: "geojson", data: DATA.neighbourhoods });

  // Pre-fetch neighbourhood features for point-in-polygon stop assignment
  fetch(DATA.neighbourhoods).then(r => r.json()).then(d => {
    _neighbourhoodFeatures = d.features;
  });

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
  // Vandflader (water bodies) rendered in blue; all other park types in green.
  map.addLayer({
    id: "parks-fill",
    type: "fill",
    source: "parks-src",
    layout: { visibility: "none" },
    paint: {
      "fill-color": ["match", ["get", "park_type"], "Vandflader", "#b3d4f5", "#4caf50"],
      "fill-opacity": ["match", ["get", "park_type"], "Vandflader", 0.45, 0.25],
    },
  });
  map.addLayer({
    id: "parks-line",
    type: "line",
    source: "parks-src",
    layout: { visibility: "none" },
    paint: {
      "line-color": ["match", ["get", "park_type"], "Vandflader", "#5a9fd4", "#2e7d32"],
      "line-width": 1,
      "line-opacity": 0.6,
    },
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

  // Neighbourhood fill — grey highlight, sits behind all data layers; hidden by default
  map.addLayer({
    id: "neighbourhood-fill",
    type: "fill",
    source: "neighbourhoods-src",
    filter: ["==", ["get", "neighbourhood_name"], ""],
    paint: {
      "fill-color": "#9ca3af",
      "fill-opacity": 0.18,
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

const _PG_GROUPS = [
  { key: "children",    label: "Children",    color: "#81c784",
    popMid: "pop_ch_reach_mid", popLow: "pop_ch_reach_low", popHigh: "pop_ch_reach_high",
    scoreField: "score_health_children",    greenField: "green_time_children"    },
  { key: "working_age", label: "Working-age", color: "#4caf50",
    popMid: "pop_wa_reach_mid", popLow: "pop_wa_reach_low", popHigh: "pop_wa_reach_high",
    scoreField: "score_health_working_age", greenField: "green_time_working_age" },
  { key: "elderly",     label: "Elderly",     color: "#2e7d32",
    popMid: "pop_el_reach_mid", popLow: "pop_el_reach_low", popHigh: "pop_el_reach_high",
    scoreField: "score_health_elderly",     greenField: "green_time_elderly"     },
];

function _fmtMin(n) {
  n = +n || 0;
  const m = Math.floor(n);
  const s = Math.round((n - m) * 60);
  return `${m}:${String(s).padStart(2, "0")}'`;
}

/**
 * Build the mini People+Green rows for a segment or stop popup.
 * isStop: true → bars use actual pop_*_reach_mid with ±confidence; false → health scores.
 */
function _buildMiniPG(p, isStop) {
  const isBaseline = _activeMode === "baseline";

  const barVals = _PG_GROUPS.map(g => isStop ? (+(p[g.popMid]) || 0) : (+(p[g.scoreField]) || 0));
  const maxBar  = Math.max(...barVals, 1);

  const colLabel = isStop ? "People in catchment" : "Per-group benefit";
  const greenLabel = isBaseline && p.green_pct_catchment != null
    ? `${(+(p.green_pct_catchment) * 100).toFixed(1)}% green`
    : "Green";

  const rows = _PG_GROUPS.map((g, i) => {
    const barPct = Math.round((barVals[i] / maxBar) * 100);

    let valStr;
    if (isStop) {
      const mid  = +(p[g.popMid])  || 0;
      const lo   = +(p[g.popLow])  || 0;
      const hi   = +(p[g.popHigh]) || 0;
      const half = Math.round((hi - lo) / 2);
      valStr = half > 0
        ? `${Math.round(mid).toLocaleString("en-DK")}<span class="popup-pg-band"> ±${half.toLocaleString("en-DK")}</span>`
        : Math.round(mid).toLocaleString("en-DK");
    } else {
      valStr = barVals[i] > 0 ? barVals[i].toFixed(3) : "—";
    }

    const greenVal = p[g.greenField] != null ? _fmtMin(+p[g.greenField]) : "—";

    return `
      <div class="popup-pg-row">
        <span class="popup-pg-label" style="color:${g.color}">${g.label}</span>
        <div class="popup-pg-bar-track">
          <div class="popup-pg-bar-fill" style="width:${barPct}%;background:${g.color}"></div>
        </div>
        <span class="popup-pg-count">${valStr}</span>
        <span class="popup-pg-green-val">${greenVal}</span>
      </div>`;
  }).join("");

  return `
    <div class="popup-pg-mini">
      <div class="popup-pg-col-header"><span>${colLabel}</span><span>${greenLabel}</span></div>
      ${rows}
    </div>`;
}

/** Shared HTML header for both segment and stop popups. */
function _buildPopupHeader(title, subtitle, band, modeName, rawScore) {
  const scoreStr = rawScore != null ? (+rawScore).toFixed(3) : "—";
  return `
    <div class="popup-header-row">
      <div class="popup-header-title">${title}</div>
      <div class="popup-category" style="color:${band.color}">${band.label}</div>
    </div>
    ${subtitle ? `<div class="popup-type-label">${subtitle}</div>` : ""}
    <div class="popup-score-line">
      <span class="popup-score-mode">${modeName}</span>
      <span class="popup-score-value">${scoreStr}</span>
    </div>
    <hr class="popup-hr">`;
}

function _addPopups() {
  // ── Segment hover/click popup ──────────────────────────────────────────────
  const _segPopup = new maplibregl.Popup({ maxWidth: "270px", closeButton: false, closeOnClick: false });

  SEG_LAYERS.forEach(layerId => {
    map.on("mouseenter", layerId, (e) => {
      map.getCanvas().style.cursor = "pointer";
      const p = e.features[0].properties;
      const isBaseline = _activeMode === "baseline";
      const activeField = isBaseline
        ? "score_catchment"
        : (STOP_SCORE_FIELD[_activeGroup] || STOP_SCORE_FIELD.aggregate);
      const rawScore = +(p[activeField]) || 0;
      const _lo = isBaseline ? _catchRampLo : _rampLo;
      const _hi = isBaseline ? _catchRampHi : _rampHi;
      const normScore = (_lo !== null && _hi !== _lo)
        ? Math.max(0, Math.min(1, (rawScore - _lo) / (_hi - _lo)))
        : rawScore;
      const band = _getBand(normScore);
      const modeName = isBaseline ? "Catchment Score" : "Health Score";

      _segPopup
        .setLngLat(e.lngLat)
        .setHTML(
          _buildPopupHeader("Bus-route segment", null, band, modeName, rawScore) +
          _buildMiniPG(p, false)
        )
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

    // Use active group + mode to determine the category label
    const scoreField = _activeMode === "baseline"
      ? "score_catchment"
      : (STOP_SCORE_FIELD[_activeGroup] || STOP_SCORE_FIELD.aggregate);
    const rawScore = +(p[scoreField]) || 0;
    const isBaselineStop = _activeMode === "baseline";
    const _lo = isBaselineStop ? _catchRampLo : _rampLo;
    const _hi = isBaselineStop ? _catchRampHi : _rampHi;
    const normScore = (_lo !== null && _hi !== _lo)
      ? Math.max(0, Math.min(1, (rawScore - _lo) / (_hi - _lo)))
      : rawScore;
    const band = _getBand(normScore);
    const modeName = isBaselineStop ? "Catchment Score" : "Health Score";

    const subtitle = p.route_names ? `Routes: ${p.route_names}` : null;
    new maplibregl.Popup({ maxWidth: "270px" })
      .setLngLat(e.lngLat)
      .setHTML(
        _buildPopupHeader(`<strong>${p.stop_name || "Bus stop"}</strong>`, subtitle, band, modeName, rawScore) +
        _buildMiniPG(p, true)
      )
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
  document.getElementById("mode-toggle-float").classList.remove("hidden");
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
  document.getElementById("mode-toggle-float").classList.add("hidden");
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

/** Show the boundary outline for a neighbourhood by name; pass "" to hide. */
export function setNeighbourhoodBoundary(name) {
  if (!map.getLayer("neighbourhood-fill")) return;
  map.setFilter("neighbourhood-fill",
    name
      ? ["==", ["get", "neighbourhood_name"], name]
      : ["==", ["get", "neighbourhood_name"], ""]
  );
}

/** Returns loaded neighbourhood GeoJSON features (null until fetched). */
export function getNeighbourhoodFeatures() { return _neighbourhoodFeatures; }

/**
 * Returns the neighbourhood_name of the polygon containing [lng, lat],
 * or null if none match. Uses ray-casting on the first ring of each polygon.
 */
export function neighbourhoodForPoint(lngLat) {
  if (!_neighbourhoodFeatures) return null;
  for (const feat of _neighbourhoodFeatures) {
    const coords = feat.geometry.type === "Polygon"
      ? feat.geometry.coordinates[0]
      : feat.geometry.coordinates[0][0];  // MultiPolygon
    if (_pointInPolygon(lngLat, coords)) return feat.properties.neighbourhood_name;
  }
  return null;
}

function _pointInPolygon([x, y], ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (((yi > y) !== (yj > y)) && (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi)) {
      inside = !inside;
    }
  }
  return inside;
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
  const isCatch = field === "score_catchment";
  const lo = isCatch ? _catchRampLo : _rampLo;
  const hi = isCatch ? _catchRampHi : _rampHi;
  if (lo === null) return ["get", field]; // fallback before domain is set
  const at = (t) => lo + (hi - lo) * t;
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

  const cVals = features.map(f => +f.properties.score_catchment).filter(v => !isNaN(v));
  if (cVals.length) {
    cVals.sort((a, b) => a - b);
    _catchRampLo = cVals[0];
    _catchRampHi = cVals[cVals.length - 1];
  }

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

/** Returns the health-score ramp domain so scatter.js can use identical colors. */
export function getRampDomain() { return { lo: _rampLo, hi: _rampHi }; }

/** Returns the catchment-score ramp domain for use in catchment/baseline mode. */
export function getCatchRampDomain() { return { lo: _catchRampLo, hi: _catchRampHi }; }

/**
 * Set the circle-radius paint property for the stops layer.
 * mode: "none" → uniform size; "people" → scaled by pop_wa_reach_mid;
 * "green" → scaled by green_time_working_age.
 */
export function setStopSizeMode(mode) {
  if (!map.getLayer("stops-layer")) return;
  if (mode === "none") {
    map.setPaintProperty("stops-layer", "circle-radius",
      ["case", ["get", "context"], 3.5, 5]);
    return;
  }
  const field = mode === "people" ? "pop_wa_reach_mid" : "green_time_working_age";
  const stops = _stopFeatures?.filter(f => !f.properties.context) ?? [];
  if (!stops.length) return;
  const vals = stops.map(f => +f.properties[field] || 0).filter(v => v > 0);
  if (!vals.length) return;
  vals.sort((a, b) => a - b);
  const lo = vals[0], hi = vals[vals.length - 1];
  if (lo === hi) return;
  map.setPaintProperty("stops-layer", "circle-radius", [
    "case", ["get", "context"], 3.5,
    ["interpolate", ["linear"], ["get", field], lo, 3, hi, 12],
  ]);
}

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
