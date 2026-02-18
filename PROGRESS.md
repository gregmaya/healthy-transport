# Progress Tracker

**Current Phase**: Phase 1 complete / Phase 2 starting
**Last Updated**: 2026-02-18

## Prioritised Next Steps

1. Spatial join demographics CSV → boundary GeoPackage (quick win, unblocks visualization)
2. Spatial join BBR attributes → INSPIRE footprints (Phase 2 integration)
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
- [x] Download INSPIRE building footprints, clip to Nørrebro
- [x] Download BBR building attributes (3,439 buildings via WFS)
- [x] Download DAR entrance points (11,911 via File Download API)
- [x] Process BBR + DAR into `norrebro_buildings.gpkg`
- [x] Explore BBR-DAR linking strategies (spatial join via INSPIRE recommended)
- [ ] Spatial join BBR attributes to INSPIRE footprints (Phase 2)
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

## Phase 2: Data Processing & Integration

### 9. Data Integration & Quality Assessment
- [ ] Create master GeoPackage: `norrebro_master.gpkg`
- [ ] Integrate all layers with consistent CRS (EPSG:25832)
- [ ] Topology validation
- [ ] Attribute completeness check
- [ ] Spatial alignment check
- [ ] Duplicate detection
- [ ] Visual QA in QGIS
- [ ] Document integration issues

### 10. Population Assignment to Buildings
- [ ] Identify residential buildings from land use
- [ ] Spatial join population data to building footprints
- [ ] Validate total population matches source data
- [ ] Apply demographic distributions to buildings
- [ ] Visualize and verify in QGIS

---

## Phase 3: Analysis Preparation

### 11. Network Analysis Setup
- [x] Build pedestrian network topology (osmnx graph)
- [x] Define walking impedance (1.4 m/s)
- [ ] Clean disconnected segments (if needed)
- [ ] Prepare cycling network for routing
- [ ] Define cycling impedance measures

### 12. Accessibility Analysis Framework
- [ ] Calculate distance/travel time from buildings to parks
- [ ] Calculate distance/travel time from buildings to transport stops
- [ ] Calculate distance/travel time from buildings to cycling infrastructure
- [ ] Create accessibility indicators

### 13. Health Analysis Framework
- [ ] Link health metrics to geographic units
- [ ] Develop methodology for health-environment correlations
- [ ] Identify analysis variables and indicators

---

## Technical Notes

- **CRS**: EPSG:25832 (ETRS89 / UTM zone 32N) for all processed data
- **File naming**: `norrebro_[category].gpkg`
- [ ] Create `norrebro_analysis.qgz` QGIS project file
- [ ] Save symbology and styles for each layer
