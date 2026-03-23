// Data paths — relative to index.html in the assembled dist/
// Local dev:  bash scripts/dev.sh  → http://localhost:8000
// Production: GitHub Actions assembles the same structure → gh-pages branch
export const DATA = {
  segments:      "data/web/norrebro_bus_segments_scored.geojson",
  busContext:    "data/web/norrebro_bus_routes_context.geojson",
  boundary:      "data/web/norrebro_boundary.geojson",
  stops:         "data/web/norrebro_stops.geojson",
  neighbourhoods:"data/web/norrebro_neighbourhoods.geojson",
  demographics:  "data/web/norrebro_demographics.geojson",
  rail_stops:    "data/web/norrebro_rail_stops_scored.geojson",   // not yet generated
  green_spaces:  "data/web/norrebro_greenspace_access.geojson",   // not yet generated
};

// Nørrebro bounding box [lng_min, lat_min, lng_max, lat_max]
export const NORREBRO_BOUNDS = [12.520, 55.675, 12.580, 55.710];

// Initial map centre + zoom
export const MAP_INIT = {
  center: [12.549, 55.692],
  zoom: 13.5,
};

// Design tokens
export const PALETTE = {
  pumpkinSpice:     "#ff6700",   // high scores — vivid orange
  platinum:         "#ebebeb",   // low scores  — near-white grey
  silver:           "#c0c0c0",   // low-mid     — grey
  cornflowerOcean:  "#3a6ea5",   // mid         — medium blue
  steelAzure:       "#004e98",   // upper-mid   — deep blue
};

// Score ramp: platinum → silver → cornflower → steel → pumpkin
// Upper range (0.75–1.0) transitions to orange so high-scoring zones pop.
export const SCORE_RAMP = [
  "interpolate", ["linear"], ["get", "score_aggregate_mid"],
  0.0,  "#ebebeb",   // platinum   — low
  0.3,  "#c0c0c0",   // silver
  0.55, "#3a6ea5",   // cornflower-ocean
  0.75, "#004e98",   // steel-azure
  1.0,  "#ff6700",   // pumpkin-spice — high
];

// Per-group ramps use the same palette with the group-specific field.
const _groupRamp = (field) => [
  "interpolate", ["linear"], ["get", field],
  0.0,  "#ebebeb",
  0.3,  "#c0c0c0",
  0.55, "#3a6ea5",
  0.75, "#004e98",
  1.0,  "#ff6700",
];
export const GROUP_RAMPS = {
  working_age: _groupRamp("score_working_age_mid_share"),
  elderly:     _groupRamp("score_elderly_mid_share"),
  children:    _groupRamp("score_children_mid_share"),
  aggregate:   SCORE_RAMP,
};

// Score mode descriptions shown below the Baseline / Contextual toggle
export const SCORE_MODE_DESCRIPTIONS = {
  baseline:   "Network quality only — no population weighting. Uses working-age walk curve with equal weight per network node.",
  contextual: "Weighted by who lives nearby. Scores reflect actual age-disaggregated population (modelled estimates).",
};

// ── Tab definitions ───────────────────────────────────────────────────────────

export const STEPS_BUS = [
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
    mapFn: "showGapAnalysis",
  },
];

export const STEPS_RAIL = [
  {
    id: "rail-overview",
    title: "Rail in Nørrebro",
    body: "Metro and S-tog stations anchor the district's public transport spine. Unlike bus stops, rail infrastructure is fixed — but we can still ask: how well do existing entrances serve the people living nearby?",
    mapFn: "showRailPlaceholder",
  },
  {
    id: "rail-curves",
    title: "The same health logic applies",
    body: "The walk to a train or metro entrance carries the same health benefit as a walk to a bus stop. The B(d) benefit curves apply equally — but rail catchments are typically wider, reflecting longer journeys.",
    mapFn: "showRailPlaceholder",
  },
  {
    id: "rail-scores",
    title: "How well-placed are existing entrances?",
    body: "Each entrance is scored by the population-weighted benefit it delivers to nearby residents. High-scoring entrances serve dense residential areas at the right walk distance. Low-scoring ones may be poorly positioned relative to where people actually live.",
    mapFn: "showRailPlaceholder",
  },
  {
    id: "rail-explore",
    title: "Explore rail coverage",
    body: "Compare Baseline (network geometry) and Contextual (actual residents) scores to see where rail provision aligns with — or diverges from — population need.",
    mapFn: "showRailPlaceholder",
  },
];

export const STEPS_CYCLING = [
  {
    id: "cycling-overview",
    title: "Cycling is the most efficient health investment",
    body: "Copenhagen already has an extensive cycling network. But gaps in protected infrastructure create barriers — especially for children, elderly, and less confident riders. Where would new protection deliver the most benefit?",
    mapFn: "showCyclingPlaceholder",
  },
  {
    id: "cycling-gaps",
    title: "Where is protection missing?",
    body: "Not all streets with high cycling potential have protected infrastructure. Methodology for identifying and scoring these gaps is currently in development.",
    mapFn: "showCyclingPlaceholder",
  },
  {
    id: "cycling-scores",
    title: "Scoring the gaps",
    body: "Scoring pipeline in development. This tab will show which unprotected streets, if upgraded, would deliver the greatest population health benefit.",
    mapFn: "showCyclingPlaceholder",
  },
  {
    id: "cycling-explore",
    title: "Explore cycling potential",
    body: "Interactive cycling analysis coming soon.",
    mapFn: "showCyclingPlaceholder",
  },
];

export const STEPS_GREEN = [
  {
    id: "green-overview",
    title: "Green space is health infrastructure",
    body: "Parks and playgrounds are not amenities — they are public health facilities. Access to green space reduces stress, encourages physical activity, and supports healthy development in children.",
    mapFn: "showGreenPlaceholder",
  },
  {
    id: "green-distance",
    title: "How far is your nearest park?",
    body: "Network distance to the nearest park or playground varies dramatically across Nørrebro's sub-neighbourhoods. Streets with long walk distances to green space are candidates for intervention.",
    mapFn: "showGreenPlaceholder",
  },
  {
    id: "green-transit",
    title: "Transit and nature",
    body: "Does the journey to your bus or metro stop pass through a green corridor? Routes that combine active travel with green space exposure amplify health benefits.",
    mapFn: "showGreenPlaceholder",
  },
  {
    id: "green-explore",
    title: "Explore green access",
    body: "Interactive green space access analysis coming soon.",
    mapFn: "showGreenPlaceholder",
  },
];

export const TABS = [
  { id: "bus",     label: "Bus Stops",    steps: STEPS_BUS,     ready: true  },
  { id: "rail",    label: "Rail",         steps: STEPS_RAIL,    ready: false },
  { id: "cycling", label: "Cycling",      steps: STEPS_CYCLING, ready: false },
  { id: "green",   label: "Green Spaces", steps: STEPS_GREEN,   ready: false },
];
