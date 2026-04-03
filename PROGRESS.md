# Progress Tracker

**Current Phase**: Phase 12 complete — score_catchment redesigned as B(t)-weighted reachable network length (exp decay, excluding motorway/trunk/cycleway/busway); pipeline re-run; scatter SVG updated
**Last Updated**: April 2026

> This project follows the reorientation decisions documented in
> [`docs/REORIENTATION_BRIEF.md`](docs/REORIENTATION_BRIEF.md).
> Read that file before making any structural changes to the pipeline or output layers.

---

## Prioritised Next Steps

1. **Resolve edge-artifact problem (Phase B — extend population to buffer zone)** — `all_districts_population.csv` is ready (68 sub-districts incl. Frederiksberg, `scripts/process/parse_kkbef8_all_districts.py` + `add_frederiksberg.py`). Remaining steps: (a) extend `integrate_population_typology.py` to spatially assign buffer-zone buildings to adjacent sub-districts via `copenhagen_kvartergrænser.gpkg` and load the new CSV; (b) re-run full pipeline.
2. **Validate in QGIS** — confirm park-adjacent segments (Fælledparken, Assistens Kirkegård) now score higher on `score_catchment` than before the Phase 12 redesign.
3. **Correlation check** — compute Pearson r(`score_catchment`, `score_health_combined`) on the 1,699 exported segments; should drop from ~0.8 (old area-based) to ~0.3 (new network-based).
4. **Implement scroll transition functions** — `showCatchmentRing`, `showBenefitCurves` are still stubs; `showScoredNetwork`, `showGapAnalysis` use `fitBounds(NORREBRO_BOUNDS)`.
5. **Find accurate rail entrance data** — evaluate Rejseplanen, DSB open data, or OpenStreetMap for metro/train entrance geometries (GTFS centroids are not entrance-level accurate).
6. **Segment hover/click popup** — show scores on hover in interactive mode.

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
- [x] `compute_stats` run with 56 distance bands (100m–1,200m, 20m steps), 9 population columns (3 groups × 3 scenarios) — produces cumulative unweighted sums `cc_{col}_sum_{d}_nw` (notebook 11, now superseded by script)
- [x] B(d) scoring: for each band (d1, d2): `B(d_mid) × max(0, cum_d2 − cum_d1)` summed across all bands
- [x] Local normalisation: denominator = group population within d_max (per node, not district total) — avoids penalising boundary segments for unreachable population
- [x] **Promoted to script** — `scripts/score/score_bus_routes.py` replaces notebook 11
  - Per-group walking speeds (m/s): working_age 1.40, elderly 0.90, children 1.00 (literature-grounded)
  - B(t) curves in time (minutes) anchored to WHO GAPPA 10-minute walk target
  - 24 distance thresholds (vs 61 in notebook); single `compute_stats` call with union of group distances
  - New score columns: `score_catchment`, `score_health_working_age`, `score_health_elderly`, `score_health_children`, `score_health_combined`
  - CitySeer dev branch installed via rustup; `decay_fn` parameter active — 4 traversals (vs 24) with Gaussian integral in Rust
- [x] **Script complete** — `scripts/score/score_bus_routes.py` replaces notebook 11; outputs validated in `data/web/`
- [ ] **Validate in QGIS** — confirm score distribution is spatially coherent along bus corridors
- [ ] Validate output in QGIS — confirm score distribution is spatially coherent along bus corridors
- [ ] **Save scored GeoPackage** to `data/integrated/norrebro_bus_segments_scored.gpkg`

### Cross-cutting: Two Scoring Modes

- [x] **Catchment score** — `score_catchment`: B(t) × total_area_m2 per building (deduped by building_id); normalised share; replaces `score_baseline`
- [x] **Health scores** — `score_health_{working_age|elderly|children}` + `score_health_combined`; mid scenario only
- [ ] **Extend to low/high scenarios** — add low/high population scenario variants
- [x] **Update frontend** — replaced `score_baseline` → `score_catchment`, `score_aggregate_mid` → `score_health_combined`, `score_*_mid_share` → `score_health_*` in `config.js`, `map.js`, `scatter.js`
- [ ] **Segment popup**: on hover/click show score + description for active score type

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
- [x] **Score-mode pill toggle** — Contextual/Baseline pill buttons (replaced radio inputs); active mode's short description shown inline; Contextual is default on tool entry; ⓘ popup updated with clearer copy
- [x] Placeholder step arrays for Rail, Cycling, Green Spaces tabs
- [x] `switchTab()` — tears down Scrollama, rebuilds steps, re-inits scroll
- [x] **Site title** — "Healthy Transport" wordmark in tab nav (rightmost, uppercase, `--blue-4`)
- [x] **Scroll endpoint** — Bus step 6 (`showGapAnalysis`) no longer auto-fires interactive tool; only "Explore the map →" button triggers it; `enterInteractiveTool` removed from `TRANSITION_FNS`
- [x] **Non-bus interactive panels** — `enterInteractiveToolBasemap()` hides all data layers; only basemap + boundary visible for Rail / Cycling / Green tabs
- [x] **Tool panel** — three ctrl-sections (Score Mode, Demographic Group, Overlays), each with ⓘ button; all infobox texts updated; panel width 210px
- [x] **Floating info popups** — per-category ⓘ buttons open fixed-position overlays to the right of the tool panel; `#modal-backdrop` blocks other interactions; backdrop click closes popup
- [x] **Benefit curves in demographic popup** — annotated SVG with all three B(d) curves (Working-age, Elderly, Children) embedded in the Demographic Group info popup
- [x] **Overlays redesign** — "Bus stops" ON by default; interior filter applied silently on enter; Parks placeholder disabled; Demographics overlay wired to heatmap
- [x] **Map bounds & zoom** — `minZoom: 11`, `maxZoom: 18`, `maxBounds` ~20km box around Nørrebro
- [x] **Right-hand chart panel** (`#chart-panel`) — appears in interactive mode only (fixed, right side, 280px)
- [x] **Score distribution card** — top of chart panel; 5 score bands (0–0.15 "Poorly placed" → 0.60+ "Optimal") with colour-matched horizontal bars and %; reactive to demographic group
- [x] **Scatter plot** — SVG, vanilla JS; X=`score_baseline`, Y=selected group; dots domain-normalised to match map ramp; context stops excluded; deduplication by `stop_id`; click on dot ↔ map stop mutually highlights
- [x] **Map layout in interactive mode** — map fixed with `right: var(--chart-panel-w)` to accommodate chart panel
- [x] **Dynamic color ramp** — domain computed from actual data range (0.117–0.530); orange=low (#ff6700), blue=high (#004e98); applied to segments, stops, and scatter plot dots
- [x] **Baseline mode** — score mode toggle hides demographic group selector; segments/stops recolor to `score_baseline`; legend title switches to "Network coverage"
- [x] **Contextual mode** — group selector visible; segments/stops recolor to selected group's `score_*_mid_share`; legend title shows "Health benefit score"
- [x] **Demographics heatmap** — grey → near-black ramp (no yellow); opacity 0.60; threshold slider removed
- [x] **Context stops** — stops outside district boundary (`context=true`) not clickable, excluded from scatter/distribution
- [x] **Population stat** — inline "Population in [neighbourhood ▼]" dropdown (no box); three horizontal demographic bars (Children/Working-age/Elderly) in blue shades; dummy data updates on neighbourhood select
- [x] **UI polish round 1** — score distribution card with ⓘ, 6-band thresholds, colour-coded labels, scatter subtitle, dashed diagonal, decimal scores, age bar, green spaces placeholder card, panel resize, left panel semi-transparent
- [x] **UI polish round 2** — bands reduced 6→5 (0–0.2/0.4/0.6/0.8/1); tooltip redesigned (dynamic category from active group+mode, structured score rows, mode label); drag-to-resize chart panel (JS handle replaces broken CSS resize); info popups fixed (backdrop-filter stacking context removed from tool-panel); popup positioning aware of left/right panel context; overlays reordered (Bus stops → Population → Green spaces, "Demographics" renamed "Population"); distribution card renamed + subtitle + % values; scatter stop-name annotation on selected dot; scatter font sizes +1pt; legend moved to bottom-left; "Population in [select]" inline label
- [x] **Phase 9: Bus narrative redesign** — Tab renamed "Bus Stops"→"Bus"; step tag pills (THE PROBLEM / THE EVIDENCE / THE MODEL / THE DATA / THE ANALYSIS / EXPLORE); all 6 steps rewritten with accessible but technically credible copy; `buildSteps()` supports block-level HTML bodies; step 3 fullscreen SVG (benefit curves: grey zones, linearGradient right fade, symmetric beziers, Y-axis labels, title); step 4 adds greyscale building footprints layer + `norrebro_building_footprints.geojson` export; step 5 scatter SVG pre-computed from real `norrebro_stops.geojson` data (85 internal stops, STOPS color ramp, diagonal reference, legend strip, ring callout on middle-cluster point, left-aligned box); step 6 body replaced SVG with intro + bold equilibrium sentence + 3 bullets (Health/Catchment/Green); map locked during narrative (`_lockMap`/`_unlockMap`), unlocked only on entering interactive tool; `showScoredNetwork`/`showGapAnalysis` use `fitBounds(NORREBRO_BOUNDS)` for viewport-adaptive framing; steps 1–2 image panel with 22% top/bottom fade overlay; scroll lock on last step deferred to card-bottom position so CTA is reachable; active tab button returns to chapter 1 from interactive mode
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

### UI Wishlist (deferred upgrades)

- [ ] **Adjustable legend midpoint (Baseline mode)** — legend slider that lets the user drag the diverging colour midpoint up/down for `score_catchment`; useful for tuning contrast in dense vs sparse areas. The current ramp is a fixed domain; this would rescale it client-side without re-fetching data. Contextual (health) mode is harder (three separate group ramps) — defer or implement independently.
- [ ] **Stop colours match active score mode** — stops are currently coloured by a fixed column regardless of the Baseline/Contextual toggle. They should recolour to `score_catchment` in Baseline mode and to the selected group's `score_health_*` in Contextual mode, using the same ramp as the segment layer so the two representations are visually consistent.
- [ ] **Pedestrian network overlay** — an additional toggle in the Overlays section that renders the full walking network used for scoring (from `norrebro_pedestrian_network.gpkg` edges, exported to GeoJSON). Thin grey lines, low opacity; helps users understand why certain segments score high (dense grid) vs low (sparse connectivity). Note: file is large (~2 MB) — may need simplification or tile conversion before shipping.

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
