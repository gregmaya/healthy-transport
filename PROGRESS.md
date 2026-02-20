# Progress Tracker

**Current Phase**: Phase 2 in progress (buildings integration complete)
**Last Updated**: 2026-02-19

## Prioritised Next Steps

1. Population typology model — assign age-specific population to buildings (see `docs/population_typology_brief.md`)
2. Set up CitySeer network for accessibility analysis (Phase 3)
3. Process eSundhed chronic disease XLSX (deferred — complex multi-sheet format)

---

## Phase 1: Data Collection & Exploration

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
- [ ] Process eSundhed chronic disease XLSX (deferred)
- [ ] Document limitations and methodological considerations

---

## Phase 2: Data Integration

Output folder: `data/integrated/` (distinct from `data/processed/`)

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
- [ ] Population typology model (deferred — see `docs/population_typology_brief.md`)

### 10. Remaining Integration

- [ ] Process eSundhed chronic disease XLSX (deferred — complex multi-sheet format)
- [ ] Document limitations and methodological considerations

---

## Phase 3: Network Analysis (CitySeer)

Using [CitySeer](https://cityseer.benchmarkurbanism.com/) for all routing and accessibility analysis.

- [ ] Set up CitySeer network from Nørrebro boundary (`osm_graph_from_poly`)
- [ ] Compute accessibility metrics (parks, transport, cycling) per building
- [ ] Integrate accessibility scores into building layer

---

## Phase 4: Web App

Scrollytelling narrative → interactive map explorer (SvelteKit + MapLibre GL JS).

- [ ] Set up SvelteKit project with MapLibre GL JS
- [ ] Create web data export script (integrated → GeoJSON/JSON in WGS84)
- [ ] Build narrative scrollytelling sections
- [ ] Build interactive map explorer
- [ ] Deploy to Vercel/Netlify

---

## Technical Notes

- **CRS**: EPSG:25832 (ETRS89 / UTM zone 32N) for all processed data
- **File naming**: `norrebro_[category].gpkg`
- **Data tiers**: `raw/` → `processed/` → `integrated/` → `web/` (future)
- **Meta files**: README.md, CLAUDE.MD, PROGRESS.md, docs/design_decisions.md, docs/data_catalogue.md, docs/data_sources.md — keep in sync for every commit
- [ ] Create `norrebro_analysis.qgz` QGIS project file
- [ ] Save symbology and styles for each layer
