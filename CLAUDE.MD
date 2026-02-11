# Nørrebro Data MVP - Project Checklist

## Project Overview

Building an MVP for Nørrebro neighbourhood in Copenhagen that integrates multiple official data sources for urban health analysis.

**Data Format**: GeoPackage (.gpkg)
**Visualization**: QGIS
**Area of Interest**: Nørrebro, Copenhagen

---

## Phase 1: Data Collection & Exploration

### 1. Define Study Area Boundary

- [x] Obtain official Nørrebro neighbourhood boundary
  - Source: Copenhagen Municipality administrative boundaries
- [x] Create `norrebro_boundary.gpkg` in data/processed folder
  - [x] Manually sliced the Nørrebro district boundary to match with the granular population data (neighbourhood level)
  - 5 sub-neighbourhoods identified, each with a unique `gm_id`
- [ ] **EXPLORE IN QGIS**: Verify all layers align within boundary

**Notes**:

- Raw boundary downloaded from OpenData.dk WFS: `raw/boundary/opendata_copenhagen_bydele_20260210.gpkg`
- Boundary was created early as the foundation for clipping all other datasets

---

### 2. Population & Demographics

- [x] Downloaded population data at most granular level: neighbourhood for the Nørrebro District
  - Source: Statistics Denmark (Danmarks Statistik) - https://www.dst.dk/
  - Downloaded tables at the neighbourhood level (bydel) for the Nørrebro district:
    - KKBEF8 (population by age)
    - KKBOL2 (dwellings by type and household size)
- [x] Cleaned and saved to `norrebro_neighbourhoods_population.csv` and `norrebro_neighbourhoods_dwellings.csv`
  - [x] Assigned additional neighbourhood id (`gm_id`) to match with manual neighbourhood boundary layer
- [ ] Spatial join of demographics CSV to boundary GeoPackage (pending — first integration step)

**Notes**:

- Raw data: `raw/demographics/2025_KKBEF8.xlsx` and `raw/demographics/2025_KKBOL2.xlsx`
- Population data covers 5 Nørrebro sub-neighbourhoods with age group breakdowns
- Dwellings data covers dwelling types and household sizes
- Joining demographics to boundary is the immediate next step to unblock visualization

---

### 3. Building Footprints & Built Environment

- [x] Download building footprints for Nørrebro
  - Source: INSPIRE building footprints (manually downloaded)
  - File: `data/buildings/building_inspire.gpkg` (2.6 GB full dataset)
  - Clipped: `data/processed/norrebro_building_footprints.gpkg` (1.0 MB)
- [x] Download BBR building attributes
  - Source: Datafordeleren BBR WFS API
  - File: `data/raw/bbr/norrebro_bbr_buildings.gpkg` (3,439 buildings, 2.0 MB)
  - Script: `scripts/download_bbr_dar.py`
- [x] Download DAR building entrance points
  - Source: Datafordeleren DAR File Download API
  - File: `data/raw/dar/norrebro_dar_adressepunkt.gpkg` (11,911 access points, 4.8 MB)
  - Script: `scripts/download_bbr_dar.py`
- [ ] Spatial join BBR attributes to INSPIRE footprints
- [ ] **EXPLORE IN QGIS**: Open all building layers, verify alignment
  - BBR points should fall within/near INSPIRE footprints
  - DAR entrance points should be at building doors (TD) or roads (V0)
  - Verify land use distribution (140 = multi-dwelling residential dominates)

**BBR (Bygnings- og Boligregistret) — Building Attributes**:

- **3,439 building points** in Nørrebro with comprehensive attributes
- Key attributes available:
  - `byg021BygningensAnvendelse`: Building use code (e.g., 140 = multi-dwelling residential, 930 = other buildings)
  - `byg038SamletBygningsareal`: Total built area (m²)
  - `byg026Opførelsesår`: Construction year
  - `byg054AntalEtager`: Number of floors
  - `byg039BygningensSamledeBoligAreal`: Residential area (m²)
  - `byg040BygningensSamledeErhvervsAreal`: Commercial area (m²)
  - `byg041BebyggetAreal`: Built footprint area (m²)
  - `husnummer`: UUID linking to DAR address register
- Distribution: 1,600+ buildings are code 140 (multi-dwelling residential), consistent with dense urban neighborhood

**DAR (Danmarks Adresseregister) — Address/Entrance Points**:

- **11,911 address points** in Nørrebro (Copenhagen municipality download, clipped to boundary)
- **CRITICAL for routing/accessibility analysis**: Use `oprindelse_tekniskStandard` field to filter by positioning accuracy

**Technical Standard Codes (`oprindelse_tekniskStandard`)**:

| Code | Count | % | Positioning Method | Use for Analysis? |
|------|-------|---|-------------------|------------------|
| **TD** | 5,639 | 47.4% | "Adgangspunkt ved indgangsdør til bygning" — **at building entrance door** | ✅ **YES — use these for accurate building access** |
| TK | 4 | <0.1% | "Adgangspunkt ved bygningsfacade mod vej" — at building facade facing street | ✅ YES — acceptable alternative |
| TN | 158 | 1.3% | "Adgangspunkt inden for bygningsomrids" — within building perimeter | ⚠️ Moderate — less precise |
| **V0** | 5,749 | 48.3% | "Vejpunkt" — **road point** (on street, not building entrance) | ❌ **NO — road-based, not entrance** |
| V1-V9 | 220 | 1.8% | Various road point types with different risks/accuracy | ❌ NO — road-based |
| UF | 134 | 1.1% | "Adgangspunkt uspecificeret eller foreløbigt placeret" — unspecified/provisional | ❌ NO — provisional |
| TA | 7 | <0.1% | "Adgangspunkt til anlæg – uden bygning" — facility without building | ⚠️ Context-dependent |

**For accessibility/routing analysis**: Filter to `oprindelse_tekniskStandard IN ('TD', 'TK')` to get **5,643 accurate entrance points** (47.4% of total). This removes road-based V0 points that don't represent actual building access.

**Linking BBR ↔ DAR ↔ INSPIRE Footprints**:

- **Spatial join**: BBR points → INSPIRE polygons (most buildings should match)
- **Exact linking** (requires national Husnummer file, ~620 MB): BBR `husnummer` UUID → Husnummer entity → DAR Adressepunkt `id_lokalId`

**Data Sources**:

- BBR WFS API: `https://wfs.datafordeler.dk/BBR/BBR_WFS/1.0.0/WFS` (layer: `bbr_v001:bygning_current`)
- DAR File Download API: `https://api.datafordeler.dk/FileDownloads/GetFile` (entity: `Adressepunkt`, municipality: 0101)
- Technical standard documentation: <https://danmarksadresser.dk/adressedata/kodelister/teknisk-standard>
- Credentials: `DATAFORDELEREN_USERNAME` and `DATAFORDELEREN_PASSWORD` in `.env`

---

### 4. Road Network

- [x] Download road centre lines for Nørrebro
  - Source: Open Data Denmark (https://www.opendata.dk/)
    - 'vejmidter' dataset is missing connectivity, so not suitable for routing
    - Stored as `raw/road_center_line/vejmidter.geojson`
  - Required: road network with connectivity for routing
- [ ] Download routable road network
- [ ] Process and save to `norrebro_roads.gpkg`
- [ ] **EXPLORE IN QGIS**: Load road network layer
  - Check network connectivity
  - Verify road classifications (primary, secondary, residential)
  - Test for gaps or disconnections
- [ ] Document data quality and topology

**Approach**: Use `osmnx.graph_from_polygon()` to download a routable network graph directly from OSM. This replaces the unusable vejmidter dataset and gives a proper topology for shortest path calculations.

**Notes**:

- The vejmidter download confirmed that Open Data DK road data lacks connectivity
- `osmnx` is already in requirements.txt and provides network analysis out of the box
- Consider downloading slightly larger area than Nørrebro for proper network analysis at edges

---

### 5. Cycling Infrastructure

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

**Approach**: OSM via `osmnx.features_from_polygon()` with `tags={'cycleway': True, 'highway': 'cycleway'}`. Also check Copenhagen Municipality data at data.kk.dk for official cycling infrastructure layers.

**Notes**:

- City of Copenhagen has comprehensive cycling data
- May need to combine multiple datasets

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

**Approach**: Try Rejseplanen GTFS feed for comprehensive stop data with route info. Alternatively, OSM via `tags={'public_transport': 'stop_position'}` or `{'highway': 'bus_stop'}`.

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

**Approach**: OSM via `osmnx.features_from_polygon()` with `tags={'leisure': 'park', 'landuse': ['grass', 'recreation_ground'], 'leisure': ['playground', 'garden']}`. Check data.kk.dk for official municipal green space layers.

**Notes**:

- Quality vs. quantity - consider park amenities
- Small pocket parks vs. large parks

---

### 8. Health Metrics (CRITICAL - Most Challenging)

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

**Approach**: Start with Copenhagen Health Profile (Sundhedsprofil) from Region Hovedstaden — most accessible public health data at regional level. For finer granularity, explore proxy indicators (e.g., GP visit rates, prescription data) or contact Region Hovedstaden directly.

**Notes**:

- Health data likely most aggregated due to privacy
- May need to use proxy indicators or modeled data
- Consider OpenData.dk for public health statistics
- Contact: Region Hovedstaden (Capital Region) for regional health data
- Start researching early — this has the longest lead time of all datasets

---

## Phase 2: Data Processing & Integration

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

**Notes**:

- First integration step: join demographics CSV to boundary GeoPackage (can be done now)
- Full integration depends on completing Phase 1 data collection

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

**Current Phase**: Phase 1 - Data Collection (partially complete)
**Last Updated**: 2026-02-11

### Completed

- Study area boundary defined (5 sub-neighbourhoods with `gm_id`)
- Population and dwellings data downloaded, cleaned, and ID-matched
- Road centre lines downloaded (but found unsuitable for routing)
- **Building footprints downloaded**: INSPIRE dataset manually acquired, clipped to Nørrebro
- **BBR building attributes downloaded**: 3,439 buildings via WFS API with comprehensive attributes
- **DAR entrance points downloaded**: 11,911 address points via File Download API (5,639 accurate TD entrance doors)
- Download script created: `scripts/download_bbr_dar.py` with credentials management and caching

### Prioritised Next Steps

1. **Spatial join BBR attributes to INSPIRE footprints** (unlock building-level analysis)
2. Join demographics to boundary GeoPackage spatially (quick win, unblocks visualization)
3. Download routable road network via osmnx (replaces vejmidter)
4. Begin health data research (longest lead time — start early)
5. Download remaining layers: cycling, transport, green spaces (independent, any order)

---

## Notes & Discoveries

### BBR & DAR Data (2026-02-11)

#### Key Discovery: DAR Entrance Point Technical Standards

The DAR Adressepunkt dataset contains ~50% road-based points (V0) and ~50% building entrance points (TD). For routing and accessibility analysis, **always filter by `oprindelse_tekniskStandard`**:

- **Use for analysis**: TD (entrance doors, 5,639 points) and TK (building facade, 4 points)
- **Exclude**: V0-V9 (road points, 6,072 points) — these are not actual building entrances

This distinction is critical for accurate network analysis. A spatial join without filtering would incorrectly assign many road-based points as building entrances.

#### BBR Building Use Codes

- Code 140 (multi-dwelling residential) dominates with 1,600+ buildings in Nørrebro
- Use `byg021BygningensAnvendelse` for land use classification
- `byg038SamletBygningsareal` provides total built area for density calculations

#### Data Joining Strategy

1. **BBR → INSPIRE footprints**: Spatial join (most BBR points fall within/near footprints)
2. **DAR → Buildings**: Filter to TD/TK first, then spatial join for entrance locations
3. **BBR ↔ DAR exact linking**: Requires national Husnummer file (~620 MB) via `husnummer` UUID — defer unless exact address matching is needed
