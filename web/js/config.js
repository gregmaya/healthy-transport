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
    body: "A retired resident and a working-age commuter don't share the same walking comfort zone. <strong>We model three demographic groups — elderly, working-age, children — each with its own benefit curve:</strong> peaking at a different distance, falling to zero at a different threshold. The score for any location sums those weighted benefits for the people who actually live nearby.",
    mapFn: "showBenefitCurves",
    svgFullscreen: true,
    svg: `<svg class="step-svg" viewBox="0 0 300 196" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">

  <!-- Title -->
  <text x="150" y="14" font-size="10" font-weight="600" fill="#1a2a3a" font-family="sans-serif" text-anchor="middle">Finding the Sweet Spot</text>

  <!-- Zone annotations above the chart (grey to match zone shading) -->
  <text x="49" y="27" font-size="6.5" fill="#888" font-family="sans-serif" text-anchor="middle">too close to</text>
  <text x="49" y="36" font-size="6.5" fill="#888" font-family="sans-serif" text-anchor="middle">generate benefit</text>
  <text x="214" y="27" font-size="6.5" fill="#888" font-family="sans-serif" text-anchor="middle">too far to</text>
  <text x="214" y="36" font-size="6.5" fill="#888" font-family="sans-serif" text-anchor="middle">induce demand</text>

  <g transform="translate(38,44)">

    <!-- Gradient for right zone: transparent at 13 min entry, solid by ~13 min mark -->
    <!-- Right rect spans x=92–262 (170 units). 13 min = x=169 → 45% of rect width -->
    <defs>
      <linearGradient id="zone-right-fade" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0%"   stop-color="#e0e0e0" stop-opacity="0"/>
        <stop offset="45%"  stop-color="#e0e0e0" stop-opacity="0.55"/>
        <stop offset="100%" stop-color="#e0e0e0" stop-opacity="0.55"/>
      </linearGradient>
    </defs>

    <!-- Zone shading: clipped to chart area (y=0 to y=108), grey -->
    <rect x="0"   y="0" width="22"  height="108" fill="#e0e0e0" opacity="0.55"/>
    <rect x="92"  y="0" width="170" height="108" fill="url(#zone-right-fade)"/>

    <!-- Axes (black) -->
    <line x1="0" y1="108" x2="262" y2="108" stroke="#222" stroke-width="1"/>
    <line x1="0" y1="0"   x2="0"   y2="108" stroke="#222" stroke-width="1"/>

    <!-- Y-axis qualitative labels -->
    <text x="-2" y="7"   font-size="5.5" fill="#777" font-family="sans-serif" text-anchor="end">High</text>
    <text x="-2" y="14"  font-size="5.5" fill="#777" font-family="sans-serif" text-anchor="end">benefit</text>
    <text x="-2" y="106" font-size="5.5" fill="#777" font-family="sans-serif" text-anchor="end">Low</text>
    <text x="-2" y="113" font-size="5.5" fill="#777" font-family="sans-serif" text-anchor="end">benefit</text>

    <!-- x-axis time labels (260 units = 20 min = 1 680 m at 1.4 m/s) -->
    <text x="0"   y="121" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">0</text>
    <text x="65"  y="121" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">5 min</text>
    <text x="130" y="121" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">10 min</text>
    <text x="195" y="121" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">15 min</text>
    <text x="262" y="121" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">20 min</text>

    <!-- Curves: symmetric two-segment beziers for smooth peaks and tails -->
    <!-- Children (back/lightest): peak x=39, d_max x=91 -->
    <path d="M0,107 C8,107 20,5 39,5 C58,5 85,107 91,107 L262,107"
          fill="none" stroke="#c6dbef" stroke-width="2" stroke-dasharray="3,3"/>

    <!-- Elderly (middle): peak x=46, d_max x=108 -->
    <path d="M0,107 C10,107 26,5 46,5 C66,5 100,107 108,107 L262,107"
          fill="none" stroke="#6baed6" stroke-width="2" stroke-dasharray="6,3"/>

    <!-- Working-age (front): peak x=78, d_max x=182 -->
    <path d="M0,107 C20,107 58,5 78,5 C98,5 160,107 182,107 L262,107"
          fill="none" stroke="#2171b5" stroke-width="2"/>

    <!-- Legend -->
    <line x1="5"   y1="143" x2="22"  y2="143" stroke="#c6dbef" stroke-width="2" stroke-dasharray="3,3"/>
    <text x="25"  y="147" font-size="7.5" fill="#555" font-family="sans-serif">Children</text>
    <line x1="83"  y1="143" x2="100" y2="143" stroke="#6baed6" stroke-width="2" stroke-dasharray="6,3"/>
    <text x="103" y="147" font-size="7.5" fill="#555" font-family="sans-serif">Elderly</text>
    <line x1="155" y1="143" x2="172" y2="143" stroke="#2171b5" stroke-width="2"/>
    <text x="175" y="147" font-size="7.5" fill="#555" font-family="sans-serif">Working-age</text>

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
    body: "High-scoring segments with no current stop are the most actionable opportunities. But a low score doesn't mean a misplaced stop: a bus stop near a university or a hospital serves a high-demand location with few nearby residents. High network reach, low residential density. <strong>That's exactly why comparing the Baseline score (catchment areas) against the Health score (with actual population distribution) is the core analytical move.</strong>",
    mapFn: "showGapAnalysis",
    // COUPLING NOTE: this SVG is a static snapshot of the Baseline vs Contextual scatter
    // rendered in the interactive tool (scatter.js). Data source: norrebro_stops.geojson,
    // internal stops only (context=false). X = score_baseline, Y = score_aggregate_mid,
    // both normalised to the shared range [lo=0.1371, hi=0.5205].
    // If the scoring pipeline re-runs, regenerate with: python3 scripts/web/generate_scatter_svg.py
    // See also: docs/design_decisions.md § Narrative–Interactive Scatter Coupling
    svg: `<svg class="step-svg" viewBox="-28 -42 258 268" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- Title: two lines, centered over chart area -->
  <text font-size="8.5" font-weight="600" fill="#1a2a3a" font-family="sans-serif" text-anchor="middle">
    <tspan x="86" y="-25">Does network reach translate</tspan>
    <tspan x="86" dy="11">to health benefit?</tspan>
  </text>
  <!-- Diagonal reference line -->
  <line x1="0" y1="160" x2="200" y2="0" stroke="#c6dbef" stroke-width="1" stroke-dasharray="4,3"/>
  <!-- 85 internal stops: color = scoreColor(normalize(score_aggregate_mid)), matches scatter.js STOPS ramp -->
  <circle cx="148.5" cy="4.6" r="2.2" fill="#07529a" fill-opacity="0.8"/>
  <circle cx="148.3" cy="3.5" r="2.2" fill="#055199" fill-opacity="0.8"/>
  <circle cx="138.8" cy="35.3" r="2.2" fill="#336aa3" fill-opacity="0.8"/>
  <circle cx="143.8" cy="20.1" r="2.2" fill="#1d5e9f" fill-opacity="0.8"/>
  <circle cx="76.3" cy="27.0" r="2.2" fill="#2764a1" fill-opacity="0.8"/>
  <circle cx="91.1" cy="44.6" r="2.2" fill="#4977a8" fill-opacity="0.8"/>
  <circle cx="96.3" cy="33.4" r="2.2" fill="#3069a3" fill-opacity="0.8"/>
  <circle cx="104.0" cy="26.4" r="2.2" fill="#2663a1" fill-opacity="0.8"/>
  <circle cx="101.4" cy="14.4" r="2.2" fill="#155a9d" fill-opacity="0.8"/>
  <circle cx="105.0" cy="21.8" r="2.2" fill="#205f9f" fill-opacity="0.8"/>
  <circle cx="104.2" cy="26.9" r="2.2" fill="#2764a1" fill-opacity="0.8"/>
  <circle cx="120.0" cy="39.8" r="2.2" fill="#3a6ea5" fill-opacity="0.8"/>
  <circle cx="114.9" cy="37.4" r="2.2" fill="#366ca4" fill-opacity="0.8"/>
  <circle cx="143.9" cy="32.4" r="2.2" fill="#2f68a3" fill-opacity="0.8"/>
  <circle cx="145.4" cy="31.7" r="2.2" fill="#2e67a2" fill-opacity="0.8"/>
  <circle cx="92.0" cy="40.3" r="2.2" fill="#3b6fa5" fill-opacity="0.8"/>
  <circle cx="163.1" cy="21.3" r="2.2" fill="#1f5f9f" fill-opacity="0.8"/>
  <circle cx="163.1" cy="21.3" r="2.2" fill="#1f5f9f" fill-opacity="0.8"/>
  <circle cx="147.2" cy="43.6" r="2.2" fill="#4675a7" fill-opacity="0.8"/>
  <circle cx="143.5" cy="51.5" r="2.2" fill="#6086ad" fill-opacity="0.8"/>
  <circle cx="118.4" cy="52.3" r="2.2" fill="#6387ad" fill-opacity="0.8"/>
  <circle cx="137.4" cy="62.6" r="2.2" fill="#869cb4" fill-opacity="0.8"/>
  <circle cx="137.4" cy="62.6" r="2.2" fill="#869cb4" fill-opacity="0.8"/>
  <circle cx="108.4" cy="24.7" r="2.2" fill="#2462a0" fill-opacity="0.8"/>
  <circle cx="108.8" cy="15.9" r="2.2" fill="#175b9d" fill-opacity="0.8"/>
  <circle cx="200.0" cy="17.2" r="2.2" fill="#195c9e" fill-opacity="0.8"/>
  <circle cx="189.2" cy="11.1" r="2.2" fill="#10579c" fill-opacity="0.8"/>
  <circle cx="174.6" cy="15.0" r="2.2" fill="#165a9d" fill-opacity="0.8"/>
  <circle cx="181.2" cy="10.2" r="2.2" fill="#0f569b" fill-opacity="0.8"/>
  <circle cx="180.4" cy="9.5" r="2.2" fill="#0e569b" fill-opacity="0.8"/>
  <circle cx="113.2" cy="62.7" r="2.2" fill="#869cb4" fill-opacity="0.8"/>
  <circle cx="143.6" cy="56.8" r="2.2" fill="#7290b0" fill-opacity="0.8"/>
  <circle cx="100.6" cy="70.7" r="2.2" fill="#a1adba" fill-opacity="0.8"/>
  <circle cx="119.8" cy="56.8" r="2.2" fill="#7290b0" fill-opacity="0.8"/>
  <circle cx="122.8" cy="45.7" r="2.2" fill="#4d7aa9" fill-opacity="0.8"/>
  <circle cx="122.9" cy="34.9" r="2.2" fill="#336aa3" fill-opacity="0.8"/>
  <circle cx="121.5" cy="33.5" r="2.2" fill="#3169a3" fill-opacity="0.8"/>
  <circle cx="119.9" cy="27.1" r="2.2" fill="#2764a1" fill-opacity="0.8"/>
  <circle cx="124.7" cy="33.4" r="2.2" fill="#3069a3" fill-opacity="0.8"/>
  <circle cx="85.7" cy="39.1" r="2.2" fill="#396da5" fill-opacity="0.8"/>
  <circle cx="85.0" cy="36.1" r="2.2" fill="#346ba4" fill-opacity="0.8"/>
  <circle cx="116.2" cy="25.6" r="2.2" fill="#2563a0" fill-opacity="0.8"/>
  <circle cx="131.9" cy="34.4" r="2.2" fill="#3269a3" fill-opacity="0.8"/>
  <circle cx="73.3" cy="89.9" r="2.2" fill="#cbcbcb" fill-opacity="0.8"/>
  <circle cx="77.2" cy="59.5" r="2.2" fill="#7b96b2" fill-opacity="0.8"/>
  <circle cx="61.8" cy="86.8" r="2.2" fill="#c7c7c7" fill-opacity="0.8"/>
  <circle cx="27.8" cy="160.0" r="2.2" fill="#ff6700" fill-opacity="0.8"/>
  <circle cx="29.7" cy="158.6" r="2.2" fill="#fe6c08" fill-opacity="0.8"/>
  <circle cx="125.6" cy="77.6" r="2.2" fill="#b8bbbe" fill-opacity="0.8"/>
  <circle cx="101.1" cy="106.0" r="2.2" fill="#dcdcdc" fill-opacity="0.8"/>
  <circle cx="122.9" cy="26.2" r="2.2" fill="#2663a1" fill-opacity="0.8"/>
  <circle cx="131.4" cy="35.2" r="2.2" fill="#336aa3" fill-opacity="0.8"/>
  <circle cx="148.0" cy="17.5" r="2.2" fill="#195c9e" fill-opacity="0.8"/>
  <circle cx="160.5" cy="10.3" r="2.2" fill="#0f569b" fill-opacity="0.8"/>
  <circle cx="177.4" cy="21.2" r="2.2" fill="#1f5f9f" fill-opacity="0.8"/>
  <circle cx="137.1" cy="72.1" r="2.2" fill="#a6b0bb" fill-opacity="0.8"/>
  <circle cx="174.8" cy="24.9" r="2.2" fill="#2462a0" fill-opacity="0.8"/>
  <circle cx="131.0" cy="73.2" r="2.2" fill="#a9b2bb" fill-opacity="0.8"/>
  <circle cx="127.1" cy="50.4" r="2.2" fill="#5d83ac" fill-opacity="0.8"/>
  <circle cx="148.3" cy="26.4" r="2.2" fill="#2663a1" fill-opacity="0.8"/>
  <circle cx="108.7" cy="29.8" r="2.2" fill="#2b66a2" fill-opacity="0.8"/>
  <circle cx="108.7" cy="29.8" r="2.2" fill="#2b66a2" fill-opacity="0.8"/>
  <circle cx="118.8" cy="26.8" r="2.2" fill="#2763a1" fill-opacity="0.8"/>
  <circle cx="144.9" cy="38.4" r="2.2" fill="#386da4" fill-opacity="0.8"/>
  <circle cx="144.7" cy="41.4" r="2.2" fill="#3f71a6" fill-opacity="0.8"/>
  <circle cx="183.3" cy="41.3" r="2.2" fill="#3e71a6" fill-opacity="0.8"/>
  <circle cx="193.3" cy="42.3" r="2.2" fill="#4273a7" fill-opacity="0.8"/>
  <circle cx="121.8" cy="34.9" r="2.2" fill="#336aa3" fill-opacity="0.8"/>
  <circle cx="121.8" cy="34.9" r="2.2" fill="#336aa3" fill-opacity="0.8"/>
  <circle cx="165.5" cy="19.0" r="2.2" fill="#1c5d9e" fill-opacity="0.8"/>
  <circle cx="164.7" cy="19.4" r="2.2" fill="#1c5e9e" fill-opacity="0.8"/>
  <circle cx="81.6" cy="45.3" r="2.2" fill="#4c79a9" fill-opacity="0.8"/>
  <circle cx="92.3" cy="46.4" r="2.2" fill="#507ba9" fill-opacity="0.8"/>
  <circle cx="83.6" cy="47.2" r="2.2" fill="#527daa" fill-opacity="0.8"/>
  <circle cx="143.6" cy="24.6" r="2.2" fill="#2462a0" fill-opacity="0.8"/>
  <circle cx="132.4" cy="29.8" r="2.2" fill="#2b66a2" fill-opacity="0.8"/>
  <circle cx="148.0" cy="18.8" r="2.2" fill="#1b5d9e" fill-opacity="0.8"/>
  <circle cx="65.5" cy="76.8" r="2.2" fill="#b5b9be" fill-opacity="0.8"/>
  <circle cx="55.7" cy="85.2" r="2.2" fill="#c6c6c6" fill-opacity="0.8"/>
  <circle cx="120.3" cy="106.9" r="2.2" fill="#dddddd" fill-opacity="0.8"/>
  <circle cx="104.7" cy="100.0" r="2.2" fill="#d5d5d5" fill-opacity="0.8"/>
  <circle cx="140.9" cy="28.8" r="2.2" fill="#2a65a1" fill-opacity="0.8"/>
  <circle cx="130.7" cy="52.9" r="2.2" fill="#6588ae" fill-opacity="0.8"/>
  <circle cx="138.3" cy="50.1" r="2.2" fill="#5c83ac" fill-opacity="0.8"/>
  <circle cx="144.8" cy="57.3" r="2.2" fill="#7491b1" fill-opacity="0.8"/>
  <!-- Axes -->
  <line x1="0" y1="160" x2="200" y2="160" stroke="#222" stroke-width="1"/>
  <line x1="0" y1="0"   x2="0"   y2="160" stroke="#222" stroke-width="1"/>
  <!-- Ring highlight + "bus stop" callout on a middle-cluster point -->
  <circle cx="85.7" cy="39.1" r="5" fill="none" stroke="#444" stroke-width="1.2"/>
  <line x1="82" y1="35" x2="60" y2="21" stroke="#aaa" stroke-width="0.8"/>
  <text x="58" y="20" font-size="6.5" fill="#555" font-family="sans-serif" text-anchor="end">bus stop</text>
  <!-- Axis labels -->
  <text x="100" y="178" font-size="7.5" fill="#555" font-family="sans-serif" text-anchor="middle">Baseline (catchment coverage)</text>
  <text x="-18" y="80" font-size="7.5" fill="#555" font-family="sans-serif" text-anchor="middle" transform="rotate(-90,-18,80)">Combined Health benefit</text>
  <!-- Combined legend strip (replaces the standalone #legend element) -->
  <text x="0" y="194" font-size="6.5" fill="#777" font-family="sans-serif">Health benefit score</text>
  <defs>
    <linearGradient id="scatter-leg" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0%"   stop-color="#ff6700"/>
      <stop offset="25%"  stop-color="#ebebeb"/>
      <stop offset="50%"  stop-color="#c0c0c0"/>
      <stop offset="75%"  stop-color="#3a6ea5"/>
      <stop offset="100%" stop-color="#004e98"/>
    </linearGradient>
  </defs>
  <rect x="0" y="198" width="200" height="7" rx="2" fill="url(#scatter-leg)"/>
  <text x="0"   y="213" font-size="6" fill="#999" font-family="sans-serif">Low</text>
  <text x="200" y="213" font-size="6" fill="#999" font-family="sans-serif" text-anchor="end">High</text>
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
  { id: "bus",     label: "Bus",          steps: STEPS_BUS,     ready: true  },
  { id: "rail",    label: "Rail",         steps: STEPS_RAIL,    ready: false },
  { id: "cycling", label: "Cycling",      steps: STEPS_CYCLING, ready: false },
  { id: "green",   label: "Green Spaces", steps: STEPS_GREEN,   ready: false },
];
