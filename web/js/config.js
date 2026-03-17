// Data paths — relative to project root.
// Serve with: python -m http.server 8000  (from project root, not from web/)
// Then open: http://localhost:8000/web/index.html
export const DATA = {
  segments: "data/web/norrebro_bus_segments_scored.geojson",
  boundary: "data/web/norrebro_boundary.geojson",
  stops:    "data/web/norrebro_stops.geojson",
};

// Nørrebro bounding box [lng_min, lat_min, lng_max, lat_max]
export const NORREBRO_BOUNDS = [12.520, 55.675, 12.580, 55.710];

// Initial map centre + zoom
export const MAP_INIT = {
  center: [12.549, 55.692],
  zoom: 13.5,
};

// Blue colour ramp for score layers (0 → near-white, 1 → deep navy)
export const SCORE_RAMP = [
  "interpolate", ["linear"], ["get", "score_aggregate_mid"],
  0.0, "#f7fbff",
  0.2, "#c6dbef",
  0.4, "#6baed6",
  0.7, "#2171b5",
  1.0, "#08306b",
];

// Per-group score colours (single saturated blue for each group layer)
export const GROUP_RAMPS = {
  working_age: [
    "interpolate", ["linear"], ["get", "score_working_age_mid_share"],
    0.0, "#f7fbff", 0.4, "#6baed6", 1.0, "#08306b",
  ],
  elderly: [
    "interpolate", ["linear"], ["get", "score_elderly_mid_share"],
    0.0, "#f7fbff", 0.4, "#6baed6", 1.0, "#08306b",
  ],
  children: [
    "interpolate", ["linear"], ["get", "score_children_mid_share"],
    0.0, "#f7fbff", 0.4, "#6baed6", 1.0, "#08306b",
  ],
  aggregate: SCORE_RAMP,
};

// Scrollytelling step definitions
export const STEPS = [
  {
    id: "overview",
    title: "The hidden cost of bad stop placement",
    body: "Most transit stops are placed for operational convenience, not population health. A stop too close or too far from where people live generates almost no walking benefit.",
    mapFn: "showOverview",
  },
  {
    id: "catchment",
    title: "Walking is medicine",
    body: "10–15 minutes of brisk walking twice a day meets WHO physical activity guidelines. Transit is one of the most scalable delivery mechanisms for active travel in a dense city.",
    mapFn: "showCatchmentRing",
  },
  {
    id: "curves",
    title: "The sweet spot is a range, not a point",
    body: "Different people have different optimal walk distances. Elderly residents and children benefit most from stops closer to home. Working-age adults can walk further. The right question is not where is the best stop — but where is the zone where the most people benefit the most?",
    mapFn: "showBenefitCurves",
  },
  {
    id: "scoring",
    title: "Scoring the streets",
    body: "Every street segment in Nørrebro that lies on a bus route can be scored for its potential health benefit as a stop location. Darker blue = higher population-weighted benefit across all age groups.",
    mapFn: "showScoredNetwork",
  },
  {
    id: "gaps",
    title: "Where the current network leaves gaps",
    body: "Comparing existing stops against the scored segments reveals both over-served corridors and underserved pockets — streets where a new or relocated stop would deliver significant health benefit.",
    mapFn: "showGapAnalysis",
  },
  {
    id: "explore",
    title: "Explore it yourself",
    body: "Switch between demographic groups to see how the optimal zone shifts. Toggle the existing stops overlay to compare current provision against the model.",
    mapFn: "enterInteractiveTool",
  },
];
