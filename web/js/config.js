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
  footprints:    "data/web/norrebro_building_footprints.geojson",
  rail_stops:    "data/web/norrebro_rail_stops_scored.geojson",   // not yet generated
  green_spaces:  "data/web/norrebro_greenspace_access.geojson",   // not yet generated
  parks:         "data/web/norrebro_parks.geojson",
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
  "interpolate", ["linear"], ["get", "score_health_combined"],
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
  working_age: _groupRamp("score_health_working_age"),
  elderly:     _groupRamp("score_health_elderly"),
  children:    _groupRamp("score_health_children"),
  aggregate:   SCORE_RAMP,
};

// Score mode descriptions shown below the Catchment Score / Health Score toggle
export const SCORE_MODE_DESCRIPTIONS = {
  baseline:   "Network reach only — no population weighting. Uses working-age walk curve with equal weight per network node.",
  contextual: "Weighted by who lives nearby. Scores reflect actual age-disaggregated population (modelled estimates).",
};

// ── Tab definitions ───────────────────────────────────────────────────────────

export const STEPS_BUS = [
  {
    id: "overview",
    tag: "The Problem",
    title: "Placement is a public health decision",
    body: "Where a stop sits on a street matters more than planners typically assume. <strong>The difference between a well-placed and a poorly-placed stop isn't just convenience — it's the amount of daily walking it generates.</strong> And the path between home and that stop isn't neutral either: walking through green space along the way amplifies the health benefit further.",
    mapFn: "showOverview",
    images: {
      base: "images/narrative/bus_base.png",
      layers: [
        { id: "layer1", src: "images/narrative/bus_layer1.png" },
        { id: "layer2", src: "images/narrative/bus_layer2.png" },
      ],
      activeId: "layer1",
    },
    svg: `<svg class="step-svg" viewBox="0 0 220 70" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <line x1="110" y1="4" x2="110" y2="62" stroke="#e0e8f0" stroke-width="1"/>
  <rect x="12" y="14" width="8" height="8" rx="1" fill="#c6dbef"/>
  <rect x="24" y="8" width="8" height="8" rx="1" fill="#c6dbef"/>
  <rect x="34" y="16" width="8" height="8" rx="1" fill="#c6dbef"/>
  <rect x="14" y="28" width="8" height="8" rx="1" fill="#c6dbef"/>
  <rect x="28" y="26" width="8" height="8" rx="1" fill="#c6dbef"/>
  <rect x="40" y="22" width="8" height="8" rx="1" fill="#c6dbef"/>
  <line x1="88" y1="54" x2="88" y2="34" stroke="#6baed6" stroke-width="1.5"/>
  <circle cx="88" cy="30" r="5" fill="#6baed6"/>
  <text x="55" y="65" font-size="7.5" fill="#aab8c8" font-family="sans-serif" text-anchor="middle">stop too far</text>
  <rect x="143" y="14" width="8" height="8" rx="1" fill="#2171b5"/>
  <rect x="156" y="8" width="8" height="8" rx="1" fill="#2171b5"/>
  <rect x="170" y="10" width="8" height="8" rx="1" fill="#2171b5"/>
  <rect x="181" y="18" width="8" height="8" rx="1" fill="#2171b5"/>
  <rect x="183" y="32" width="8" height="8" rx="1" fill="#2171b5"/>
  <rect x="170" y="40" width="8" height="8" rx="1" fill="#2171b5"/>
  <rect x="153" y="38" width="8" height="8" rx="1" fill="#2171b5"/>
  <rect x="141" y="30" width="8" height="8" rx="1" fill="#2171b5"/>
  <line x1="166" y1="54" x2="166" y2="34" stroke="#004e98" stroke-width="1.5"/>
  <circle cx="166" cy="30" r="5" fill="#004e98"/>
  <text x="166" y="65" font-size="7.5" fill="#aab8c8" font-family="sans-serif" text-anchor="middle">stop well placed</text>
</svg>`,
  },
  {
    id: "catchment",
    tag: "The Evidence",
    title: "Ten minutes, twice a day",
    body: "WHO guidelines ask for 150 minutes of moderate activity per week. <strong>Ten minutes of brisk walking to a transit stop and back, twice daily, gets most people there.</strong> But there's a catch: a stop placed too close and you don't accumulate enough walking minutes to matter; too far and people are deterred from using the bus at all. The sweet spot is a precise range — and it's not the same for everyone.",
    mapFn: "showCatchmentRing",
    images: {
      base: "images/narrative/bus_base.png",
      layers: [
        { id: "layer1", src: "images/narrative/bus_layer1.png" },
        { id: "layer2", src: "images/narrative/bus_layer2.png" },
      ],
      activeId: "layer2",
    },
    svg: `<svg class="step-svg" viewBox="0 0 210 80" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M100,8 C124,6 152,16 162,36 C170,52 160,68 138,72 C116,76 82,75 62,68 C42,60 38,44 44,30 C50,16 76,8 100,8 Z"
        fill="#c6dbef" fill-opacity="0.25" stroke="#6baed6" stroke-width="0.8" stroke-dasharray="3,2"/>
  <path d="M100,20 C116,18 136,24 144,38 C150,50 142,62 124,64 C106,66 84,65 72,58 C58,50 56,38 62,28 C68,18 86,20 100,20 Z"
        fill="#6baed6" fill-opacity="0.18" stroke="#6baed6" stroke-width="0.8" stroke-dasharray="3,2"/>
  <path d="M100,32 C108,30 118,34 122,42 C126,50 120,58 110,60 C100,62 88,60 82,54 C76,48 78,38 84,34 C88,30 94,33 100,32 Z"
        fill="#2171b5" fill-opacity="0.2" stroke="#2171b5" stroke-width="0.8"/>
  <circle cx="100" cy="44" r="4" fill="#004e98"/>
  <text x="167" y="36" font-size="7" fill="#8aa8c0" font-family="sans-serif">15 min</text>
  <text x="151" y="44" font-size="7" fill="#8aa8c0" font-family="sans-serif">10 min</text>
  <text x="127" y="48" font-size="7" fill="#2171b5" font-family="sans-serif">5 min</text>
</svg>`,
  },
  {
    id: "curves",
    tag: "The Model",
    title: "Different people, different distances",
    body: "A retired resident and a working-age commuter don't share the same walking comfort zone. <strong>We model three demographic groups — elderly, working-age, children — each with its own benefit curve:</strong> peaking at a different walk time, falling to zero at a different threshold. The score for any location sums those weighted benefits for the people who actually live nearby.",
    mapFn: "showBenefitCurves",
    svgFullscreen: true,
    svg: `<svg class="step-svg" viewBox="0 0 300 196" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">

  <!-- Title -->
  <text x="150" y="14" font-size="10" font-weight="600" fill="#1a2a3a" font-family="sans-serif" text-anchor="middle">Finding the Sweet Spot</text>

  <!-- Zone annotations above the chart (grey to match zone shading) -->
  <text x="49" y="27" font-size="6.5" fill="#888" font-family="sans-serif" text-anchor="middle">too close to</text>
  <text x="49" y="36" font-size="6.5" fill="#888" font-family="sans-serif" text-anchor="middle">generate benefit</text>
  <text x="245" y="27" font-size="6.5" fill="#888" font-family="sans-serif" text-anchor="middle">too far to</text>
  <text x="245" y="36" font-size="6.5" fill="#888" font-family="sans-serif" text-anchor="middle">induce demand</text>

  <g transform="translate(38,44)">

    <!-- Gradient for right zone: fades in to solid by the working-age cutoff (10 min = x=217) -->
    <!-- Right rect spans x=152–262 (110 units). Working-age cutoff at x=217 → 59% of rect width -->
    <defs>
      <linearGradient id="zone-right-fade" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0%"   stop-color="#e0e0e0" stop-opacity="0"/>
        <stop offset="59%"  stop-color="#e0e0e0" stop-opacity="0.55"/>
        <stop offset="100%" stop-color="#e0e0e0" stop-opacity="0.55"/>
      </linearGradient>
    </defs>

    <!-- Zone shading: clipped to chart area (y=0 to y=108), grey -->
    <rect x="0"   y="0" width="22"  height="108" fill="#e0e0e0" opacity="0.55"/>
    <rect x="152" y="0" width="110" height="108" fill="url(#zone-right-fade)"/>

    <!-- Axes (black) -->
    <line x1="0" y1="108" x2="262" y2="108" stroke="#222" stroke-width="1"/>
    <line x1="0" y1="0"   x2="0"   y2="108" stroke="#222" stroke-width="1"/>

    <!-- Y-axis qualitative labels -->
    <text x="-2" y="7"   font-size="5.5" fill="#777" font-family="sans-serif" text-anchor="end">High</text>
    <text x="-2" y="14"  font-size="5.5" fill="#777" font-family="sans-serif" text-anchor="end">benefit</text>
    <text x="-2" y="106" font-size="5.5" fill="#777" font-family="sans-serif" text-anchor="end">Low</text>
    <text x="-2" y="113" font-size="5.5" fill="#777" font-family="sans-serif" text-anchor="end">benefit</text>

    <!-- x-axis time labels (260 units = 12 min). Scale: 21.67 units/min -->
    <!-- Parameters: children peak=3.5min, cutoff=7min; elderly peak=4min, cutoff=8min; working-age peak=5min, cutoff=10min -->
    <text x="0"   y="121" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">0</text>
    <text x="65"  y="121" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">3 min</text>
    <text x="130" y="121" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">6 min</text>
    <text x="195" y="121" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">9 min</text>
    <text x="262" y="121" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">12 min</text>

    <!-- Curves: symmetric two-segment beziers for smooth peaks and tails -->
    <!-- Children (back/lightest): speed=1.0m/s, peak=3.5min→x=76, cutoff=7min→x=152 -->
    <path d="M0,107 C30,107 61,5 76,5 C91,5 122,107 152,107 L262,107"
          fill="none" stroke="#c6dbef" stroke-width="2" stroke-dasharray="3,3"/>

    <!-- Elderly (middle): speed=0.9m/s, peak=4min→x=87, cutoff=8min→x=173 -->
    <path d="M0,107 C35,107 70,5 87,5 C104,5 138,107 173,107 L262,107"
          fill="none" stroke="#6baed6" stroke-width="2" stroke-dasharray="6,3"/>

    <!-- Working-age (front): speed=1.4m/s, peak=5min→x=108, cutoff=10min→x=217 -->
    <path d="M0,107 C43,107 86,5 108,5 C130,5 174,107 217,107 L262,107"
          fill="none" stroke="#2171b5" stroke-width="2"/>

    <!-- Legend -->
    <line x1="5"   y1="143" x2="22"  y2="143" stroke="#c6dbef" stroke-width="2" stroke-dasharray="3,3"/>
    <text x="25"  y="147" font-size="7.5" fill="#555" font-family="sans-serif">Children (0–14, 7 min)</text>
    <line x1="5"   y1="155" x2="22"  y2="155" stroke="#6baed6" stroke-width="2" stroke-dasharray="6,3"/>
    <text x="25"  y="159" font-size="7.5" fill="#555" font-family="sans-serif">Elderly (65+, 8 min)</text>
    <line x1="5"   y1="167" x2="22"  y2="167" stroke="#2171b5" stroke-width="2"/>
    <text x="25"  y="171" font-size="7.5" fill="#555" font-family="sans-serif">Working-age (15–64, 10 min)</text>

  </g>
</svg>`,
  },
  {
    id: "scoring",
    tag: "The Data",
    title: "Nørrebro, at building resolution",
    body: "Nørrebro is a young, dense district. Rather than relying on census-zone averages, <strong>we interpolated age-group populations down to individual building entrances</strong> — over 11,000 of them — using dwelling typology and sub-neighbourhood breakdowns. <strong>Every bus-route segment in the network receives a health benefit score grounded in who lives within walking distance of it.</strong>",
    mapFn: "showScoredNetwork",
  },
  {
    id: "gaps",
    tag: "The Analysis",
    title: "What the scores reveal — and what they don't",
    body: "High-scoring segments with no current stop are the most actionable opportunities. But a low score doesn't mean a misplaced stop: a bus stop near a university or a hospital serves a high-demand location with few nearby residents. High network reach, low residential density. <strong>That's exactly why comparing the Catchment Score (network reach) against the Health Score (with actual population distribution) is the core analytical move.</strong>",
    mapFn: "showGapAnalysis",
    // COUPLING NOTE: this SVG is a static snapshot of the Catchment vs Health scatter
    // rendered in the interactive tool (scatter.js). Data source: norrebro_stops.geojson,
    // internal stops only (context=false). X = score_catchment, Y = score_health_combined,
    // both normalised to the shared range [0.020, 0.941]. (Phase B+Frederiksberg)
    // Regenerate with: python3 scripts/web/generate_scatter_svg.py
    // See also: docs/design_decisions.md § Narrative–Interactive Scatter Coupling
    svg: `<svg class="step-svg" viewBox="-28 -42 258 268" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- Title: two lines, centered over chart area -->
  <text font-size="8.5" font-weight="600" fill="#1a2a3a" font-family="sans-serif" text-anchor="middle">
    <tspan x="86" y="-25">Does network reach translate</tspan>
    <tspan x="86" dy="11">to health benefit?</tspan>
  </text>
  <!-- Diagonal reference line -->
  <line x1="0.0" y1="160.0" x2="200.0" y2="0.0" stroke="#c6dbef" stroke-width="1" stroke-dasharray="4,3"/>
  <!-- Generated from 85 internal stops. X=score_catchment, Y=score_health_combined. lo=0.0168 hi=0.9406 -->
  <circle cx="139.2" cy="160.0" r="2.2" fill="#ff6700" fill-opacity="0.8"/>
  <circle cx="139.8" cy="159.8" r="2.2" fill="#ff6801" fill-opacity="0.8"/>
  <circle cx="152.1" cy="154.1" r="2.2" fill="#fc7a22" fill-opacity="0.8"/>
  <circle cx="151.3" cy="152.9" r="2.2" fill="#fb7e2a" fill-opacity="0.8"/>
  <circle cx="155.6" cy="152.8" r="2.2" fill="#fb7f2a" fill-opacity="0.8"/>
  <circle cx="119.6" cy="152.8" r="2.2" fill="#fb7f2b" fill-opacity="0.8"/>
  <circle cx="124.8" cy="152.3" r="2.2" fill="#fb802d" fill-opacity="0.8"/>
  <circle cx="158.5" cy="150.9" r="2.2" fill="#fa8536" fill-opacity="0.8"/>
  <circle cx="195.4" cy="149.0" r="2.2" fill="#f98b41" fill-opacity="0.8"/>
  <circle cx="156.3" cy="149.0" r="2.2" fill="#f98b41" fill-opacity="0.8"/>
  <circle cx="132.1" cy="146.3" r="2.2" fill="#f89450" fill-opacity="0.8"/>
  <circle cx="177.3" cy="146.3" r="2.2" fill="#f89450" fill-opacity="0.8"/>
  <circle cx="200.0" cy="145.7" r="2.2" fill="#f89654" fill-opacity="0.8"/>
  <circle cx="164.0" cy="144.2" r="2.2" fill="#f79b5d" fill-opacity="0.8"/>
  <circle cx="146.9" cy="143.7" r="2.2" fill="#f79d60" fill-opacity="0.8"/>
  <circle cx="180.3" cy="142.8" r="2.2" fill="#f6a065" fill-opacity="0.8"/>
  <circle cx="128.4" cy="142.1" r="2.2" fill="#f6a269" fill-opacity="0.8"/>
  <circle cx="165.1" cy="141.8" r="2.2" fill="#f6a36b" fill-opacity="0.8"/>
  <circle cx="153.6" cy="141.7" r="2.2" fill="#f6a46c" fill-opacity="0.8"/>
  <circle cx="156.6" cy="140.7" r="2.2" fill="#f5a771" fill-opacity="0.8"/>
  <circle cx="152.1" cy="138.4" r="2.2" fill="#f4ae7f" fill-opacity="0.8"/>
  <circle cx="122.2" cy="138.1" r="2.2" fill="#f4af81" fill-opacity="0.8"/>
  <circle cx="152.9" cy="137.8" r="2.2" fill="#f4b082" fill-opacity="0.8"/>
  <circle cx="153.9" cy="137.6" r="2.2" fill="#f4b184" fill-opacity="0.8"/>
  <circle cx="161.8" cy="137.1" r="2.2" fill="#f4b387" fill-opacity="0.8"/>
  <circle cx="128.2" cy="136.1" r="2.2" fill="#f3b68c" fill-opacity="0.8"/>
  <circle cx="124.9" cy="135.1" r="2.2" fill="#f3b992" fill-opacity="0.8"/>
  <circle cx="159.1" cy="134.7" r="2.2" fill="#f2ba94" fill-opacity="0.8"/>
  <circle cx="127.3" cy="132.1" r="2.2" fill="#f1c3a4" fill-opacity="0.8"/>
  <circle cx="146.4" cy="132.0" r="2.2" fill="#f1c3a5" fill-opacity="0.8"/>
  <circle cx="157.7" cy="130.0" r="2.2" fill="#f0cab0" fill-opacity="0.8"/>
  <circle cx="166.4" cy="129.3" r="2.2" fill="#f0ccb4" fill-opacity="0.8"/>
  <circle cx="121.5" cy="129.1" r="2.2" fill="#f0cdb6" fill-opacity="0.8"/>
  <circle cx="111.2" cy="129.0" r="2.2" fill="#f0cdb6" fill-opacity="0.8"/>
  <circle cx="141.2" cy="128.9" r="2.2" fill="#efceb7" fill-opacity="0.8"/>
  <circle cx="99.5" cy="128.8" r="2.2" fill="#efceb7" fill-opacity="0.8"/>
  <circle cx="115.1" cy="128.6" r="2.2" fill="#efcfb9" fill-opacity="0.8"/>
  <circle cx="128.8" cy="128.5" r="2.2" fill="#efcfb9" fill-opacity="0.8"/>
  <circle cx="115.5" cy="127.4" r="2.2" fill="#efd2bf" fill-opacity="0.8"/>
  <circle cx="111.6" cy="126.2" r="2.2" fill="#eed7c7" fill-opacity="0.8"/>
  <circle cx="111.6" cy="126.2" r="2.2" fill="#eed7c7" fill-opacity="0.8"/>
  <circle cx="128.5" cy="122.1" r="2.2" fill="#ece4de" fill-opacity="0.8"/>
  <circle cx="146.7" cy="120.5" r="2.2" fill="#ebe9e8" fill-opacity="0.8"/>
  <circle cx="126.8" cy="118.9" r="2.2" fill="#eaeaea" fill-opacity="0.8"/>
  <circle cx="161.3" cy="118.5" r="2.2" fill="#e9e9e9" fill-opacity="0.8"/>
  <circle cx="161.3" cy="118.5" r="2.2" fill="#e9e9e9" fill-opacity="0.8"/>
  <circle cx="150.6" cy="117.3" r="2.2" fill="#e8e8e8" fill-opacity="0.8"/>
  <circle cx="142.6" cy="115.6" r="2.2" fill="#e6e6e6" fill-opacity="0.8"/>
  <circle cx="149.4" cy="115.5" r="2.2" fill="#e6e6e6" fill-opacity="0.8"/>
  <circle cx="143.2" cy="115.4" r="2.2" fill="#e6e6e6" fill-opacity="0.8"/>
  <circle cx="146.6" cy="114.4" r="2.2" fill="#e5e5e5" fill-opacity="0.8"/>
  <circle cx="104.1" cy="113.8" r="2.2" fill="#e4e4e4" fill-opacity="0.8"/>
  <circle cx="141.5" cy="112.8" r="2.2" fill="#e3e3e3" fill-opacity="0.8"/>
  <circle cx="116.2" cy="112.6" r="2.2" fill="#e3e3e3" fill-opacity="0.8"/>
  <circle cx="116.2" cy="112.6" r="2.2" fill="#e3e3e3" fill-opacity="0.8"/>
  <circle cx="122.3" cy="112.3" r="2.2" fill="#e3e3e3" fill-opacity="0.8"/>
  <circle cx="131.9" cy="112.2" r="2.2" fill="#e3e3e3" fill-opacity="0.8"/>
  <circle cx="136.2" cy="111.8" r="2.2" fill="#e2e2e2" fill-opacity="0.8"/>
  <circle cx="147.5" cy="111.5" r="2.2" fill="#e2e2e2" fill-opacity="0.8"/>
  <circle cx="129.1" cy="111.4" r="2.2" fill="#e2e2e2" fill-opacity="0.8"/>
  <circle cx="126.5" cy="110.4" r="2.2" fill="#e1e1e1" fill-opacity="0.8"/>
  <circle cx="133.6" cy="110.4" r="2.2" fill="#e1e1e1" fill-opacity="0.8"/>
  <circle cx="128.0" cy="109.9" r="2.2" fill="#e0e0e0" fill-opacity="0.8"/>
  <circle cx="130.1" cy="109.4" r="2.2" fill="#e0e0e0" fill-opacity="0.8"/>
  <circle cx="117.6" cy="108.8" r="2.2" fill="#dfdfdf" fill-opacity="0.8"/>
  <circle cx="131.9" cy="108.5" r="2.2" fill="#dfdfdf" fill-opacity="0.8"/>
  <circle cx="117.1" cy="108.2" r="2.2" fill="#dedede" fill-opacity="0.8"/>
  <circle cx="117.7" cy="107.7" r="2.2" fill="#dedede" fill-opacity="0.8"/>
  <circle cx="139.6" cy="106.4" r="2.2" fill="#dcdcdc" fill-opacity="0.8"/>
  <circle cx="119.4" cy="105.6" r="2.2" fill="#dbdbdb" fill-opacity="0.8"/>
  <circle cx="106.5" cy="104.5" r="2.2" fill="#dadada" fill-opacity="0.8"/>
  <circle cx="118.9" cy="101.8" r="2.2" fill="#d7d7d7" fill-opacity="0.8"/>
  <circle cx="134.9" cy="100.2" r="2.2" fill="#d6d6d6" fill-opacity="0.8"/>
  <circle cx="124.6" cy="98.1" r="2.2" fill="#d3d3d3" fill-opacity="0.8"/>
  <circle cx="124.6" cy="98.1" r="2.2" fill="#d3d3d3" fill-opacity="0.8"/>
  <circle cx="120.4" cy="97.3" r="2.2" fill="#d3d3d3" fill-opacity="0.8"/>
  <circle cx="117.1" cy="96.5" r="2.2" fill="#d2d2d2" fill-opacity="0.8"/>
  <circle cx="140.7" cy="95.5" r="2.2" fill="#d1d1d1" fill-opacity="0.8"/>
  <circle cx="137.5" cy="95.1" r="2.2" fill="#d0d0d0" fill-opacity="0.8"/>
  <circle cx="141.7" cy="87.9" r="2.2" fill="#c9c9c9" fill-opacity="0.8"/>
  <circle cx="134.8" cy="87.0" r="2.2" fill="#c8c8c8" fill-opacity="0.8"/>
  <circle cx="136.5" cy="84.0" r="2.2" fill="#c4c4c4" fill-opacity="0.8"/>
  <circle cx="142.5" cy="83.4" r="2.2" fill="#c4c4c4" fill-opacity="0.8"/>
  <circle cx="138.9" cy="77.8" r="2.2" fill="#b9bcbf" fill-opacity="0.8"/>
  <circle cx="145.5" cy="77.1" r="2.2" fill="#b6babe" fill-opacity="0.8"/>
  <!-- X axis -->
  <line x1="0" y1="160" x2="200" y2="160" stroke="#888" stroke-width="0.8"/>
  <text x="100" y="176" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">Catchment Score</text>
  <!-- Y axis -->
  <line x1="0" y1="0" x2="0" y2="160" stroke="#888" stroke-width="0.8"/>
  <text x="-8" y="80" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle" transform="rotate(-90,-8,80)">Health score (combined)</text>
</svg>`,
  },
  {
    id: "explore",
    tag: "Explore",
    title: "Dig into the data",
    body: `<p>The same map, now yours to explore. Two scores sit behind every stop — see where they agree and where they diverge.</p>
<p><strong>Neither score alone is enough to justify moving a stop — the decision requires both lenses.</strong></p>
<ul>
  <li><strong>Health score</strong> — weighted by who lives nearby; shifts with the demographic group you select.</li>
  <li><strong>Catchment score</strong> — geometry only; reveals well-connected but low-density locations.</li>
  <li><strong>Green surroundings</strong> — journeys to and from stops that pass through green areas carry additional benefits: better mental health outcomes and lower exposure to air pollution.</li>
</ul>`,
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
    body: "Compare Catchment Score (network geometry) and Health Score (actual residents) to see where rail provision aligns with — or diverges from — population need.",
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
  { id: "bus",     label: "Bus",          steps: STEPS_BUS,     ready: true  },
  { id: "rail",    label: "Rail",         steps: STEPS_RAIL,    ready: false },
  { id: "cycling", label: "Cycling",      steps: STEPS_CYCLING, ready: false },
  { id: "green",   label: "Green Spaces", steps: STEPS_GREEN,   ready: false },
];
