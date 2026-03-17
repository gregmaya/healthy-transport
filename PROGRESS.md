# Progress Tracker

**Current Phase**: Phase 2 complete — moving to Phase 3 (Health Model & Segment Scoring)
**Last Updated**: March 2026

> This project follows the reorientation decisions documented in
> [`docs/REORIENTATION_BRIEF.md`](docs/REORIENTATION_BRIEF.md).
> Read that file before making any structural changes to the pipeline or output layers.

---

## Prioritised Next Steps

1. **Confirm age-disaggregated population availability** — Statistics Denmark and data.kk.dk (blocking for Phase 3)
2. **Implement benefit curves** — `src/health/benefit_curves.py`, one curve per demographic group, validated in a notebook
3. **Reframe pipeline output** — scored 20m segments are the primary deliverable from this point forward

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

## Phase 3: Health Model & Segment Scoring 🔄

*Primary deliverable: `data/integrated/norrebro_bus_segments_scored.gpkg` — 20m segments along bus routes scored with population-differentiated health benefit scores. Existing stop locations are not inputs; they are a comparison layer applied after scoring.*

### 11. Age-Disaggregated Population
- [ ] Query Statistics Denmark for address-level age band data
- [ ] Query data.kk.dk for finer-grained breakdowns
- [ ] If address-level unavailable: apply census-zone age distributions as weights and document assumption
- [ ] Join age bands to `entrances_demographics` layer

### 12. Benefit Curve Implementation
- [ ] Write `src/health/benefit_curves.py` with `B(d)` function parameterised per demographic group
- [ ] Parameters: peak distance, decay steepness, zero-benefit threshold
- [ ] Plot all four curves on the same axes
- [ ] Validate parameter choices against Lars Bo Andersen literature
- [ ] Commit as exploratory notebook `08_benefit_curves.ipynb`

### 13. Bus Route Candidate Segments
- [ ] Filter GTFS routes to bus mode only (exclude metro, train, ferry)
- [ ] Create 15m buffer around bus route lines
- [ ] Intersect buffered bus routes with 20m pedestrian network segments
- [ ] Output: `candidate_segments` layer — the only segments that will be scored
- [ ] Validate candidate segments in QGIS — confirm coverage matches expected bus corridors
- [ ] Filter existing bus stop locations into a separate benchmark layer (`norrebro_bus_stops.gpkg`) — these are **not** scoring inputs; they are used only for comparison after scoring

### 14. Network Graph for Scoring
- [ ] Set up CitySeer network from Nørrebro boundary (`osm_graph_from_poly`)
- [ ] Validate graph connectivity; identify and handle isolated subgraphs
- [ ] Extract midpoints of candidate bus-route segments as hypothetical stop locations

### 15. Segment Scoring Loop
- [ ] For each candidate segment midpoint: compute network distances to all address points within 1,500m (CitySeer)
- [ ] Apply `B(d)` × population for each demographic group
- [ ] Sum scores per group; store as segment attributes: `score_aggregate`, `score_working_age`, `score_elderly`, `score_children`, `score_reduced_mobility`
- [ ] Output: `data/integrated/norrebro_bus_segments_scored.gpkg`
- [ ] Validate output in QGIS — confirm score distribution is spatially coherent along bus corridors
- [ ] Overlay existing bus stops as a separate layer to identify gaps and over-served corridors
- [ ] Commit as reproducible script `scripts/score/score_segments.py`

---

## Phase 4: Web Data Export

*Output: pre-baked static files in `data/web/` for the MapLibre GL JS front end.*

- [ ] Convert scored segments to GeoJSON (WGS84) → `data/web/bus_segments_scored.geojson`
- [ ] Evaluate PMTiles conversion for production performance
- [ ] Decide: raw segment layer vs H3 hex aggregation (resolution 9) — or both as a toggle
- [ ] Export existing bus stop locations to GeoJSON → `data/web/bus_stops.geojson` (benchmark layer)
- [ ] Export Nørrebro boundary → `data/web/boundary.geojson`
- [ ] Document web data schema and update data catalogue

---

## Phase 5: Scrollytelling Narrative

*Scrollama-driven narrative, 6 scroll steps, built before the interactive tool.*

- [ ] Set up project structure (SvelteKit or plain HTML/JS + Scrollama + MapLibre GL JS)
- [ ] Define 6 scroll steps and corresponding map states (see CLAUDE.MD narrative arc)
- [ ] Write section copy for each scroll step
- [ ] Implement map transitions between narrative states
- [ ] Integrate top-down health data visualisations (DODA1, HEAT, lifestyle factors)
- [ ] Review and sign off narrative before building interactive layer

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
