# Nørrebro Data MVP - Project Checklist

## Project Overview
Building an MVP for Nørrebro neighbourhood in Copenhagen that integrates multiple official data sources for urban health analysis.

**Data Format**: GeoPackage (.gpkg)
**Visualization**: QGIS
**Area of Interest**: Nørrebro, Copenhagen

---

## Phase 1: Data Collection & Exploration

### 1. Building Footprints & Built Environment
- [ ] Download building footprints for Nørrebro
  - Source: OpenStreetMap Denmark or Danish Agency for Data Supply and Infrastructure (SDFI/Dataforsyningen)
  - Required attributes: building polygons, land use, height
  - Look for: total built area (gross floor area/GFA)
- [ ] Download building entrance points
  - Source: SDFI Dataforsyningen (bygningspunkter)
- [ ] Process and save to `norrebro_buildings.gpkg`
- [ ] **EXPLORE IN QGIS**: Open the building layer, check attributes, verify coverage
  - Verify land use categories
  - Check if height data is present
  - Identify residential vs. commercial buildings
- [ ] Document data quality and gaps in this file

**Notes**:
- SDFI GeoDanmark has comprehensive building data
- If total built area missing, calculate from footprint × floors/height

---

### 2. Road Network
- [x] Download road centre lines for Nørrebro
  - Source: Open Data Denmark (https://www.opendata.dk/)
    - 'vejmidter' dataset is missing connectivity, so not suitable for routing
    - stored as `raw/road_center_line/vejmidter.geojson`
  - Alternative: OpenStreetMap or SDFI (to explore)
  - Required: road network with connectivity for routing
- [ ] Process and save to `norrebro_roads.gpkg`
- [ ] **EXPLORE IN QGIS**: Load road network layer
  - Check network connectivity
  - Verify road classifications (primary, secondary, residential)
  - Test for gaps or disconnections
- [ ] Document data quality and topology

**Notes**:
- Need connected network for shortest path calculations
- Consider downloading slightly larger area than Nørrebro for proper network analysis

---

### 3. Cycling Infrastructure
- [ ] Download cycle paths (separate cycling infrastructure)
  - Source: Open Data Denmark / Geodata-info.dk
  - Alternative: OpenStreetMap (cycleway tags)
- [ ] Download cycle routes (on-road cycling routes)
  - Look for designated cycle route networks
- [ ] Process and save to `norrebro_cycling.gpkg`
- [ ] **EXPLORE IN QGIS**: Load cycling layers
  - Distinguish between protected cycle paths and shared roads
  - Check density and connectivity
  - Identify gaps in cycling network
- [ ] Document cycling infrastructure coverage

**Notes**:
- City of Copenhagen has comprehensive cycling data
- May need to combine multiple datasets

---

### 4. Population & Demographics
- [x] Downloaded population data at most granular level : neighbourhood for the Nørrebro District
  - Source: Statistics Denmark (Danmarks Statistik) - https://www.dst.dk/
  - downloaded tables at the neighbourhood level (bydel) for the Nørrebro district:
    - KKBEF8 (population by age)
    - KKBOL2 (dwellings by type and household size)
- [x] cleaned and saved to `norrebro_neighbourhoods_population.csv` and `norrebro_neighbourhoods_dwellings.csv`
  - [x] Assigned additional neighbourhood id (`gm_id`) to match with manual neighbourhood boundary layer 

**Notes**:
- further joining is still pending.
---

### 5. Health Metrics (CRITICAL - Most Challenging)
- [ ] Research available health data sources
  - Danish Health Data Authority (Sundhedsdatastyrelsen)
  - Public Health registries
  - Academic research datasets
- [ ] Identify most granular geographic level available
  - Municipality level?
  - Postal code level?
  - Statistical district level?
  - Grid level?
- [ ] Download health metrics data
  - **Priority**: Cardiovascular disease prevalence/incidence
  - Non-communicable diseases (NCDs)
  - Diabetes, respiratory diseases
  - Mental health indicators if available
  - Health risk factors (obesity, physical inactivity)
- [ ] Process and save to `norrebro_health.gpkg` or CSV with geographic identifiers
- [ ] **EXPLORE IN QGIS**: Load health data layer
  - Check geographic resolution
  - Assess data completeness
  - Identify any privacy/aggregation constraints
- [ ] Document limitations and methodological considerations

**Notes**:
- Health data likely most aggregated due to privacy
- May need to use proxy indicators or modeled data
- Consider OpenData.dk for public health statistics
- Contact: Region Hovedstaden (Capital Region) for regional health data

---

### 6. Public Transport Stops
- [ ] Download bus stops for Nørrebro area
  - Source: Movia (public transport authority) or Open Data DK
  - Alternative: OpenStreetMap (public_transport=stop)
- [ ] Download metro stations
  - Copenhagen Metro data
- [ ] Download train/S-train stations
  - DSB or national rail data
- [ ] Process and save to `norrebro_transport.gpkg`
- [ ] **EXPLORE IN QGIS**: Load transport stops
  - Verify stop locations
  - Check attribute data (routes, frequency if available)
  - Calculate accessibility coverage
- [ ] Document public transport coverage

**Notes**:
- Rejseplanen API may have comprehensive stop data
- Include stop names and route information

---

### 7. Parks & Open Spaces
- [ ] Download parks and green spaces
  - Source: OpenStreetMap (leisure=park, landuse=grass, etc.)
  - Alternative: Copenhagen Municipality open space data
  - Include: parks, squares, playgrounds, urban forests
- [ ] Download recreational facilities if available
- [ ] Process and save to `norrebro_greenspaces.gpkg`
- [ ] **EXPLORE IN QGIS**: Load green spaces layer
  - Check coverage and classification
  - Verify accessibility
  - Identify different types of green spaces
- [ ] Document green space availability

**Notes**:
- Quality vs. quantity - consider park amenities
- Small pocket parks vs. large parks

---

## Phase 2: Data Processing & Integration

### 8. Define Nørrebro Boundary
- [x] Obtain official Nørrebro neighbourhood boundary
  - Source: Copenhagen Municipality administrative boundaries
- [x] Create `norrebro_boundary.gpkg` in data/processed folder
  - [x] Manually sliced of the Nørrebro district boundary to match with the granular population data (neighbourhood level)
- [ ] Clip all datasets to boundary
- [ ] **EXPLORE IN QGIS**: Verify all layers align within boundary

---

### 9. Data Integration & Quality Assessment
- [ ] Create master GeoPackage: `norrebro_master.gpkg`
- [ ] Integrate all layers with consistent CRS (EPSG:25832 - ETRS89 / UTM zone 32N for Denmark)
- [ ] Perform data quality checks:
  - [ ] Topology validation
  - [ ] Attribute completeness
  - [ ] Spatial alignment
  - [ ] Duplicate detection
- [ ] **EXPLORE IN QGIS**: Load complete integrated dataset
  - Visual QA of all layers together
  - Check spatial relationships
- [ ] Document integration issues and resolutions

---

### 10. Population Assignment to Buildings
- [ ] Identify residential buildings from land use
- [ ] Spatial join population data to building footprints
- [ ] Validate total population matches source data
- [ ] Apply demographic distributions to buildings
- [ ] **EXPLORE IN QGIS**: Visualize population per building
  - Check for unrealistic values
  - Verify residential density patterns

---

## Phase 3: Analysis Preparation

### 11. Network Analysis Setup
- [ ] Prepare road network for routing
  - [ ] Build network topology
  - [ ] Clean disconnected segments
- [ ] Prepare cycling network for routing
- [ ] Define impedance measures (distance, time)

---

### 12. Accessibility Analysis Framework
- [ ] Calculate distance/travel time from buildings to:
  - [ ] Parks and green spaces
  - [ ] Public transport stops
  - [ ] Cycling infrastructure
- [ ] Create accessibility indicators

---

### 13. Health Analysis Framework
- [ ] Link health metrics to geographic units
- [ ] Develop methodology for health-environment correlations
- [ ] Identify analysis variables and indicators

---

## Data Sources Reference

### Primary Sources
- **Dataforsyningen (SDFI)**: https://dataforsyningen.dk/ - Official Danish geographic data
- **Open Data DK**: https://www.opendata.dk/ - National open data portal
- **Statistics Denmark**: https://www.dst.dk/ - Population and demographics
- **OpenStreetMap Denmark**: https://www.openstreetmap.org/
- **Copenhagen Municipality**: https://data.kk.dk/ - City open data

### Health Data Sources (To Research)
- Sundhedsdatastyrelsen (Health Data Authority)
- Region Hovedstaden (Capital Region)
- Public health registries
- Academic data sources

---

## Technical Notes

### Coordinate Reference System
- Use EPSG:25832 (ETRS89 / UTM zone 32N) for all Danish data
- Reproject as needed for consistency

### File Naming Convention
- `norrebro_[category].gpkg`
- Document layers within each GeoPackage

### QGIS Project
- [ ] Create `norrebro_analysis.qgz` project file
- [ ] Save symbology and styles for each layer
- [ ] Document in QGIS for reproducibility

---

## Progress Tracking

**Current Phase**: Phase 1 - Data Collection
**Last Updated**: 2026-02-10
**Next Step**: Begin with building footprints download

---

## Notes & Discoveries
(Add notes here as you progress through the checklist)

