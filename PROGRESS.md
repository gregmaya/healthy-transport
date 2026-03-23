# Progress Tracker

**Current Phase**: Phase 5 active — bus route export pipeline complete; baseline scoring implemented; interactive tool wired with dynamic ramp, scatter plot, and demographics heatmap
**Last Updated**: March 2026

> This project follows the reorientation decisions documented in
> [`docs/REORIENTATION_BRIEF.md`](docs/REORIENTATION_BRIEF.md).
> Read that file before making any structural changes to the pipeline or output layers.

---

## Prioritised Next Steps

1. **Resolve edge-artifact problem** — 84.8% of live segments fall within 80m of the district boundary and have truncated catchments. Options: (a) extend analysis boundary by ~200m before scoring and clip back; (b) accept `interior=True` filter (only 1,265 fully-interior segments) for the final published layer; (c) document as a known limitation with a UI flag. Decision needed before final export.
2. **Extend bus scoring to low/high Contextual** — expand `SCENARIOS = ("low", "mid", "high")` in notebook 11; wire scenario rail in frontend to `score_{group}_{scenario}` columns.
3. **Implement scroll transition functions** — `showCatchmentRing`, `showBenefitCurves`, `showScoredNetwork`, `showGapAnalysis` are stubs; implement with `flyTo` / layer opacity animations.
4. **Find accurate rail entrance data** — evaluate Rejseplanen, DSB open data, or OpenStreetMap for metro/train entrance geometries (GTFS centroids are not entrance-level accurate).
5. **Segment hover/click popup** — show mid score + [low, high] range on hover in interactive mode.
6. **Promote notebook 11 to a script** — `scripts/score/score_segments.py`; save scored GeoPackage to `data/integrated/norrebro_bus_segments_scored.gpkg`.

---

## Phase 1: Data Collection & Exploration ✅

### 1. Study Area Boundary
- [x] Obtain official Nørrebro neighbourhood boundary
- [x] Create `norrebro_boundary.gpkg` (5 sub-neighbourhoods with `gm_id`)

### 2. Population & Demographics
- [x] Download population data (KKBEF8, KKBOL2) from Statistics Denmark
- [x] Clean and save CSVs with `gm_id` matching boundary layer
- [ ] Spatial join demographics CSV to boundary GeoPackage

### 3. Building Footprints & Built Environment
- [x] Download INSPIRE building footprints, clip to Nørrebro (5,915 polygons)
- [x] Download BBR building attributes (3,440 buildings via WFS)
- [x] Download DAR entrance points (11,911 via File Download API)
- [x] Process BBR + DAR into `norrebro_buildings.gpkg`
- [x] Explore BBR-DAR linking strategies (spatial join via INSPIRE recommended)
- [x] Verified in QGIS

### 4. Road Network
- [x] Download road centre lines (vejmidter — unsuitable for routing)
- [x] Download routable OSM network via osmnx (GraphML + GeoPackage)
- [x] Add walking travel times (1.4 m/s)
- [x] Verified in QGIS
- [ ] Document data quality and topology

### 5. Cycling Infrastructure
- [x] Download 3 datasets from Copenhagen Municipality WFS
- [x] Process into `norrebro_cycling.gpkg` (cykeldata + cykelstativ)
- [x] Verified in QGIS
- [ ] Document cycling infrastructure coverage

### 6. Public Transport Stops
- [x] Download national GTFS feed from Rejseplanen
- [x] Process stops and routes, classify by mode, clip to 10 km buffer
- [x] Verified in QGIS

### 7. Parks & Green Spaces
- [x] Download 3 datasets from Copenhagen Municipality WFS
- [x] Process into `norrebro_greenspaces.gpkg` (parks + playgrounds)
- [x] Verified in QGIS

### 8. Health Metrics
- [x] Research 5 health data sources
- [x] Identify granularity ceiling (municipality level)
- [x] Set up download infrastructure + manual guide
- [x] Download all sources (automated + manual)
- [x] Compute WHO HEAT input parameters
- [x] Process health data into 4 analysis-ready CSVs
- [x] Create exploratory notebook `05_health_metrics.ipynb`
- [ ] Process eSundhed chronic disease XLSX (deferred — complex multi-sheet format)
- [ ] Document limitations and methodological considerations

---

## Phase 2: Data Integration ✅

Output folder: `data/integrated/`

### 9. Buildings Integration
- [x] BBR → INSPIRE footprints spatial join (3,127 matched, 2,788 without BBR)
- [x] DAR entrances → building footprints (5,509 matched, 134 unlinked, 2m buffer)
- [x] Neighbourhood assignment (all 5,915 buildings in a sub-neighbourhood)
- [x] KNN attribute estimation for visualization (2,456 estimated, 332 unmatched)
- [x] Residential entrance guarantee (82 orphaned → nearest entrance fallback)
- [x] Exploratory notebook `06_buildings_integration.ipynb`
- [x] Reproducible script `scripts/integrate/integrate_buildings.py`
- [x] Verified in QGIS — entrance deduplication confirmed
- [x] Save to `data/integrated/norrebro_buildings.gpkg` (buildings + entrances layers)
- [x] Population typology model — dwelling-type tiers, low/mid/high scenarios, 5 age groups (notebook 07 + `scripts/integrate/integrate_population_typology.py`)
- [x] Two-round entrance matching: building_id join (84.8%) + spatial fallback sjoin_nearest 10m (89.5% total)
- [x] `entrances_demographics` layer: 11,367 rows, 18 population columns, saved to `data/integrated/norrebro_buildings.gpkg`

### 10. Remaining Integration
- [ ] Process eSundhed chronic disease XLSX (deferred — complex multi-sheet format)
- [ ] Document limitations and methodological considerations

---

## Phase 3a: Bus Stop Scoring ✅ (mid scenario validated; edge artifact + Baseline TBD)

*Primary deliverable: `data/integrated/norrebro_bus_segments_scored.gpkg` — 20m segments along bus routes scored with population-differentiated health benefit scores. Existing stop locations are not inputs; they are a comparison layer applied after scoring.*

### 11. Age-Disaggregated Population
- [x] Resolved using existing `entrances_demographics` layer — age bands aggregated into three scoring groups: `working_age` (15–64 = young_adults_15_29 + working_age_30_64), `elderly` (65+ = older_adults_65_79 + very_elderly_80plus), `children` (0–14). No additional data source required.
- [x] Totals verified: working_age mid=274,635 · elderly mid=29,940 · children mid=51,446 · district total mid=356,021

### 12. Benefit Curve Implementation
- [x] `src/health/benefit_curves.py` implemented — `B(d)` function parameterised per demographic group via `DEMOGRAPHIC_PARAMS` dict (mu, sigma, d_max)
- [x] Curves plotted and validated (notebook 08)

### 13. Bus Route Candidate Segments
- [x] 148 bus routes loaded from `norrebro_transport_stops.gpkg`; 15m buffer created
- [x] 8,328 live (bus-route) segments identified out of 34,054 dual-graph nodes (24.5% of network)
- [x] `live=False` pattern used on dual graph nodes — off-route segments still participate in routing (correct distances) but do not receive score columns
- [x] ⚠️ **Edge artifact**: 84.8% of live segments (7,063/8,328) fall within 80m of district boundary — truncated catchments produce artificially low scores. `interior` flag added. Decision on how to handle is a next step.

### 14. Network Graph for Scoring
- [x] CitySeer dual-graph approach: OSM edges decomposed to ≤20m primal segments → `nx_to_dual()` → each dual node is a 20m primal segment; geometry = primal_edge LineString
- [x] Graph stats: raw 10,435 nodes / 15,034 edges → after filler removal: 10,295 / 14,894 → after decompose: 29,455 / 34,054 → dual: 34,054 nodes / 51,766 edges
- [x] `network_structure_from_nx` built after live-node flagging (live flags baked into Rust backend)

### 15. Segment Scoring Loop
- [x] `compute_stats` run with 56 distance bands (100m–1,200m, 20m steps), 9 population columns (3 groups × 3 scenarios) — produces cumulative unweighted sums `cc_{col}_sum_{d}_nw`
- [x] B(d) scoring: for each band (d1, d2): `B(d_mid) × max(0, cum_d2 − cum_d1)` summed across all bands
- [x] Local normalisation: denominator = group population within d_max (per node, not district total) — avoids penalising boundary segments for unreachable population
- [x] Score columns: `score_{group}_mid`, `score_{group}_mid_share`, `score_aggregate_mid` on all 8,328 live segments
- [x] Mid-scenario score ranges — aggregate: 0–0.532 (mean 0.226); working_age share max 0.524; elderly share max 0.724; children share max 0.727
- [ ] **Extend to low/high scenarios** — `SCENARIOS = ("low", "mid", "high")`; blocked on edge-artifact decision
- [ ] **Save scored GeoPackage** to `data/integrated/norrebro_bus_segments_scored.gpkg`
- [ ] Validate output in QGIS — confirm score distribution is spatially coherent along bus corridors
- [ ] Overlay existing bus stops as a separate layer to identify gaps and over-served corridors
- [ ] **Promote to script** — `scripts/score/score_segments.py`

### Cross-cutting: Two Scoring Modes

- [x] **Baseline scoring (bus)** — `score_baseline` implemented in notebook 11: working-age B(d) curve, `weight_baseline = 1.0` per entrance (equal weight, no population count); column auto-exported via `score_*` pickup in export script
- [ ] **Contextual low/high scenarios** — expand `SCENARIOS = ("low", "mid", "high")` in notebook 11 (bus); apply same to all other tracks
- [ ] **Column naming enforced across all layers**: `score_{group}_baseline`, `score_{group}_low`, `score_{group}_mid`, `score_{group}_high`, `score_{group}_mid_share`
- [ ] **Segment popup**: on hover/click show mid score + `[low, high]` range for active group

---

## Phase 3b: Rail Stop Scoring ⏸ (blocked on data)

- [ ] **Prerequisite**: find accurate rail entrance dataset — evaluate Rejseplanen, DSB open data, OpenStreetMap (current GTFS centroids are not entrance-level accurate)
- [ ] Filter to metro + train modes; load entrance geometries
- [ ] CitySeer + `compute_stats` with origin = each entrance location (no candidate segment analysis)
- [ ] Apply B(d) scoring: Baseline (working-age curve, equal node weight) + Contextual (demographic, low/mid/high)
- [ ] Output: one scored point per entrance
- [ ] Export: `data/web/norrebro_rail_stops_scored.geojson`

---

## Phase 3c: Cycling 📋 (placeholder — methodology TBD)

- [ ] Tab structure exists in frontend; no pipeline work until methodology is defined in a future planning session

---

## Phase 3d: Green Space Access

- [ ] For each 20m network segment midpoint: compute network distance to nearest park polygon + nearest playground (`norrebro_greenspaces.gpkg`)
- [ ] Score = B(d) × population per segment — same CitySeer pipeline as bus, Baseline + Contextual
- [ ] Output layer: scored segments (consistent with bus layer), not entrance points
- [ ] Export: `data/web/norrebro_greenspace_access.geojson`
- [ ] Deferred: fraction of transit trips routing through a green space buffer

---

## Phase 4: Web Data Export ✅

*Output: pre-baked static files in `data/web/` for the MapLibre GL JS front end.*

- [x] Scored segments exported to GeoJSON (WGS84) → `data/web/norrebro_bus_segments_scored.geojson` (1,699 bus-route segments, 946 KB, includes `score_baseline`)
- [x] Nørrebro boundary exported → `data/web/norrebro_boundary.geojson` (16 KB)
- [x] Existing bus stops exported → `data/web/norrebro_stops.geojson` (552 stops, 332 KB, includes all `score_*` columns)
- [x] Bus route context geometry → `data/web/norrebro_bus_routes_context.geojson` (68 dissolved route geometries, 149 KB)
- [x] Demographics heatmap data → `data/web/norrebro_demographics.geojson` (10,175 entrance points, 7.7 MB, includes low/high/unc_pct columns)
- [x] Neighbourhoods → `data/web/norrebro_neighbourhoods.geojson` (5 features, 33 KB — generated but not used in frontend)
- [x] Export script → `scripts/export/export_bus_route_segments.py` (new; handles route snapping, segment decomposition, score remapping)
- [ ] **⚠️ Re-export needed** once edge-artifact decision is made (interior filter or extended boundary)
- [ ] Evaluate PMTiles conversion for demographics layer (7.7 MB is borderline for production)
- [ ] Document web data schema and update data catalogue

---

## Phase 5: Scrollytelling Web App 🔄

*Four-tab structure (Bus / Rail / Cycling / Green Spaces), each tab a Scrollama-driven narrative sharing one MapLibre map canvas.*

- [x] Project structure: plain HTML/JS + Scrollama + MapLibre GL JS (`web/index.html`, `web/js/`, `web/css/`)
- [x] Bus tab: 6 scroll steps defined with copy in `web/js/config.js`
- [x] Map sources and layers registered (boundary, segments, stops, basemap)
- [x] Aggregate + per-group colour ramps defined (`SCORE_RAMP`, `GROUP_RAMPS`)
- [x] Tab nav (Bus / Rail / Cycling / Green Spaces) — Rail/Cycling/Green show "coming soon" badge
- [x] Score-mode toggle (Baseline / Contextual radio inputs) + scenario rail (Low · Mid · High, Contextual only) in tool panel
- [x] Placeholder step arrays for Rail, Cycling, Green Spaces tabs
- [x] `switchTab()` — tears down Scrollama, rebuilds steps, re-inits scroll
- [x] **Site title** — "Healthy Transport" wordmark in tab nav (rightmost, uppercase, `--blue-4`)
- [x] **Scroll endpoint** — Bus step 6 (`showGapAnalysis`) no longer auto-fires interactive tool; only "Explore the map →" button triggers it; `enterInteractiveTool` removed from `TRANSITION_FNS`
- [x] **Non-bus interactive panels** — `enterInteractiveToolBasemap()` hides all data layers; only basemap + boundary visible for Rail / Cycling / Green tabs
- [x] **Tool panel redesign** — three ctrl-sections (Score Mode, Demographic Group, Overlays), each with ⓘ button; Baseline listed first with inline description; mode selection via radio inputs; panel width 210px
- [x] **Floating info popups** — per-category ⓘ buttons open fixed-position overlays to the right of the tool panel; `#modal-backdrop` blocks other interactions; backdrop click closes popup
- [x] **Benefit curves in demographic popup** — annotated SVG with all three B(d) curves (Working-age, Elderly, Children) embedded in the Demographic Group info popup
- [x] **Overlays redesign** — "Bus stops" ON by default; "Reliable data only" removed (interior filter applied silently on enter); Parks placeholder disabled; Demographics overlay wired to heatmap
- [x] **Right-hand chart panel** (`#chart-panel`) — appears in interactive mode only (fixed, right side, 280px); KPI grid (1,699 scored segments, 356k population); Baseline vs Contextual scatter plot (SVG, reactive to group selection)
- [x] **Map layout in interactive mode** — map fixed with `right: var(--chart-panel-w)` to accommodate chart panel
- [x] **Dynamic color ramp** — domain computed from actual data range (0.117–0.530); orange=low (#ff6700), blue=high (#004e98); applied to segments, stops, and scatter plot dots
- [x] **Baseline mode** — score mode toggle hides demographic group selector; segments/stops recolor to `score_baseline`; legend title switches to "Network coverage"
- [x] **Contextual mode** — group selector visible; segments/stops recolor to selected group's `score_*_mid_share`; legend title shows "Health benefit score"
- [x] **Demographics heatmap** — B&W color scheme, opacity 0.60, zoom-independent (exponential base-2 radius), no slider; wired to "Demographics" checkbox
- [x] **Scatter plot** — SVG, vanilla JS; X axis fixed to `score_baseline` ("Network coverage"), Y axis follows selected demographic group; dots colored by aggregate contextual score
- [x] **Group buttons wired to scatter** — selecting a group updates both map layer colors and scatter Y axis simultaneously
- [ ] **Map transition functions** — `showCatchmentRing`, `showBenefitCurves`, `showScoredNetwork`, `showGapAnalysis` are stubs; implement with `flyTo` / layer opacity animations
- [ ] Wire scenario rail to `score_{group}_{scenario}` columns (low/high not yet computed)
- [ ] Segment hover/click popup: mid score + [low, high] range
- [ ] Integrate top-down health data visualisations (DODA1, HEAT, lifestyle factors)
- [ ] Review and sign off Bus narrative before building Rail/Green interactive layers

---

## Phase 6: Interactive GIS Tool

*Full interactive tool — the landing point of the scrollytelling narrative.*

- [ ] Scored segment layer as primary display, coloured by aggregate health benefit
- [ ] Population group toggle (working-age / elderly / children / reduced mobility)
- [ ] Existing stop overlay (toggle on/off)
- [ ] Benefit curve parameter sliders (peak distance, decay steepness) — map updates reactively
- [ ] Headline metric panel: total daily walking-minutes for current stop configuration
- [ ] Seamless handoff from scrollytelling narrative
- [ ] *(Post-MVP)* "Drop a hypothetical stop" — marginal benefit of a new stop location

---

## Phase 7: Hardening & Deployment

- [ ] Performance optimisation (tile loading, render performance)
- [ ] Mobile responsiveness
- [ ] Accessibility (WCAG AA)
- [ ] Final copy editing
- [ ] Create `norrebro_analysis.qgz` QGIS project file with symbology for all layers
- [ ] Deploy to GitHub Pages or Netlify
- [ ] Update README with live URL

---

## Technical Notes

- **CRS**: EPSG:25832 for all processed/integrated data; WGS84 for web exports (GeoJSON)
- **File naming**: `norrebro_[category].gpkg`
- **Data tiers**: `raw/` → `processed/` → `integrated/` → `web/`
- **Routing**: CitySeer for all network setup and routing
- **Meta files**: README.md, CLAUDE.MD, PROGRESS.md, docs/ — keep in sync on every commit
