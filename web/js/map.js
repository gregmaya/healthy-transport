import { DATA, MAP_INIT, NORREBRO_BOUNDS, SCORE_RAMP, GROUP_RAMPS } from "./config.js";
import { disableScrollLock } from "./state.js";

let map;
let curvesPanel = null;

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
    attributionControl: false,
  });

  map.on("load", () => {
    _addSources();
    _addLayers();
    _addAttribution();
    // Trigger the initial narrative state so layers are visible from the start
    showOverview();
  });

  return map;
}

// ── Source registration ──────────────────────────────────────────────────────

function _addSources() {
  map.addSource("boundary-src", { type: "geojson", data: DATA.boundary });
  map.addSource("segments-src", { type: "geojson", data: DATA.segments });
  map.addSource("stops-src",    { type: "geojson", data: DATA.stops });
}

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

  // Scored segments (aggregate) — hidden initially
  map.addLayer({
    id: "segments-aggregate",
    type: "line",
    source: "segments-src",
    layout: { visibility: "none" },
    paint: {
      "line-color": SCORE_RAMP,
      "line-width": ["interpolate", ["linear"], ["zoom"], 12, 1.5, 16, 4],
      "line-opacity": [
        "case", ["==", ["get", "interior"], true], 1.0, 0.4,
      ],
    },
  });

  // Per-group segment layers (share from same source, different paint)
  for (const [group, ramp] of Object.entries(GROUP_RAMPS)) {
    if (group === "aggregate") continue;
    const scoreField = `score_${group}_mid_share`;
    map.addLayer({
      id: `segments-${group}`,
      type: "line",
      source: "segments-src",
      layout: { visibility: "none" },
      paint: {
        "line-color": ramp,
        "line-width": ["interpolate", ["linear"], ["zoom"], 12, 1.5, 16, 4],
        "line-opacity": [
          "case", ["==", ["get", "interior"], true], 1.0, 0.4,
        ],
      },
    });
  }

  // Existing bus stops — hidden initially
  map.addLayer({
    id: "stops-layer",
    type: "circle",
    source: "stops-src",
    layout: { visibility: "none" },
    paint: {
      "circle-radius": 5,
      "circle-color": "#08306b",
      "circle-stroke-width": 1.5,
      "circle-stroke-color": "#ffffff",
      "circle-opacity": 0.85,
    },
  });
}

function _addAttribution() {
  map.addControl(
    new maplibregl.AttributionControl({ compact: true }),
    "bottom-right"
  );
}

// ── Scroll-step transition functions ────────────────────────────────────────

export function showOverview() {
  _hideAllScoreLayers();
  _setVisibility("stops-layer", "visible");
  _removeCurvesPanel();
  map.fitBounds(NORREBRO_BOUNDS, { padding: 40, duration: 1200 });
}

export function showCatchmentRing() {
  _hideAllScoreLayers();
  _setVisibility("stops-layer", "none");
  _removeCurvesPanel();

  // Fly to a representative residential block in Nørrebro
  map.flyTo({ center: [12.545, 55.690], zoom: 15.5, duration: 1400 });

  // Animate a growing circle representing the catchment zone
  _animateCatchmentRing([12.545, 55.690]);
}

export function showBenefitCurves() {
  _hideAllScoreLayers();
  _setVisibility("stops-layer", "none");
  map.flyTo({ center: MAP_INIT.center, zoom: MAP_INIT.zoom, duration: 1000 });
  _showCurvesPanel();
}

export function showScoredNetwork() {
  _setVisibility("segments-aggregate", "visible");
  _setVisibility("stops-layer", "none");
  _removeCurvesPanel();
  _removeCatchmentRing();
  map.flyTo({ center: MAP_INIT.center, zoom: MAP_INIT.zoom, duration: 1000 });
}

export function showGapAnalysis() {
  _setVisibility("segments-aggregate", "visible");
  _setVisibility("stops-layer", "visible");
  _removeCurvesPanel();
}

export function enterInteractiveTool() {
  _setVisibility("segments-aggregate", "visible");
  _setVisibility("stops-layer", "visible");
  document.getElementById("tool-panel").classList.remove("hidden");
  document.body.classList.add("is-interactive");
  // Wait one frame for the fixed layout to apply before resizing the map
  requestAnimationFrame(() => map.resize());
}

export function backToNarrative() {
  disableScrollLock();
  document.getElementById("tool-panel").classList.add("hidden");
  document.body.classList.remove("is-interactive");
  requestAnimationFrame(() => {
    map.resize();
    window.scrollTo({ top: 0, behavior: "smooth" });
    showOverview();
  });
}

// ── Interactive tool: group toggle ──────────────────────────────────────────

export function setActiveGroup(group) {
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
}

export function toggleStops(visible) {
  _setVisibility("stops-layer", visible ? "visible" : "none");
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

// ── Helpers ──────────────────────────────────────────────────────────────────

function _setVisibility(layerId, visibility) {
  if (map.getLayer(layerId)) {
    map.setLayoutProperty(layerId, "visibility", visibility);
  }
}

function _hideAllScoreLayers() {
  for (const layer of [
    "segments-aggregate",
    "segments-working_age",
    "segments-elderly",
    "segments-children",
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

// SVG benefit-curve panel (step 3)
function _showCurvesPanel() {
  _removeCurvesPanel();
  curvesPanel = document.createElement("div");
  curvesPanel.id = "curves-overlay";
  curvesPanel.innerHTML = `
    <h4>Health benefit B(d) by group</h4>
    <svg viewBox="0 0 300 160" xmlns="http://www.w3.org/2000/svg">
      <g transform="translate(30,10)">
        <!-- Axes -->
        <line x1="0" y1="120" x2="260" y2="120" stroke="#aaa" stroke-width="1"/>
        <line x1="0" y1="0"   x2="0"   y2="120" stroke="#aaa" stroke-width="1"/>
        <!-- x labels -->
        <text x="0"   y="133" font-size="8" fill="#666" text-anchor="middle">0</text>
        <text x="65"  y="133" font-size="8" fill="#666" text-anchor="middle">300m</text>
        <text x="130" y="133" font-size="8" fill="#666" text-anchor="middle">600m</text>
        <text x="195" y="133" font-size="8" fill="#666" text-anchor="middle">900m</text>
        <text x="260" y="133" font-size="8" fill="#666" text-anchor="middle">1200m</text>
        <!-- Working age (peaks ~500m, d_max 1200m) -->
        <path d="M0,117 C30,115 50,100 65,60 C80,20 95,5 108,5 C121,5 136,20 152,60 C175,110 200,117 260,117"
              fill="none" stroke="#2171b5" stroke-width="2"/>
        <!-- Elderly (peaks ~300m, d_max 700m) -->
        <path d="M0,115 C20,105 40,60 65,10 C80,2 90,2 100,10 C120,40 145,105 152,117 C200,117 260,117 260,117"
              fill="none" stroke="#6baed6" stroke-width="2" stroke-dasharray="6,3"/>
        <!-- Children (peaks ~250m, d_max 600m) -->
        <path d="M0,116 C15,108 35,65 55,12 C65,3 75,3 85,12 C100,40 120,110 130,117 C200,117 260,117 260,117"
              fill="none" stroke="#c6dbef" stroke-width="2" stroke-dasharray="3,3"/>
        <!-- Legend -->
        <line x1="5"  y1="145" x2="25" y2="145" stroke="#2171b5" stroke-width="2"/>
        <text x="28" y="148" font-size="8" fill="#333">Working-age</text>
        <line x1="90" y1="145" x2="110" y2="145" stroke="#6baed6" stroke-width="2" stroke-dasharray="6,3"/>
        <text x="113" y="148" font-size="8" fill="#333">Elderly</text>
        <line x1="160" y1="145" x2="180" y2="145" stroke="#c6dbef" stroke-width="2" stroke-dasharray="3,3"/>
        <text x="183" y="148" font-size="8" fill="#333">Children</text>
      </g>
    </svg>`;
  document.getElementById("map").appendChild(curvesPanel);
}

function _removeCurvesPanel() {
  if (curvesPanel) {
    curvesPanel.remove();
    curvesPanel = null;
  }
}
