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
  - Script: `scripts/download/download_bbr_dar.py`
- [x] Download DAR building entrance points
  - Source: Datafordeleren DAR File Download API
  - File: `data/raw/dar/norrebro_dar_adressepunkt.gpkg` (11,911 access points, 4.8 MB)
  - Script: `scripts/download/download_bbr_dar.py`
- [x] Process BBR + DAR into analysis-ready GeoPackage
  - Script: `scripts/process/process_buildings.py`
  - Output: `data/processed/norrebro_buildings.gpkg` (1.7 MB, EPSG:25832)
    - Layer `buildings`: 3,439 BBR building points — 14 translated columns + 4 derived (`use_description`, `use_category`, `construction_era`, English material/heating labels)
    - Layer `entrances`: 5,643 DAR entrance points (TD/TK only, 800m buffer)
  - All ~80 BBR use codes mapped to English descriptions per official BBR documentation (https://teknik.bbr.dk/kodelister)
  - Wall material, roof material, and heating type numeric codes mapped to English
  - Construction years grouped into 7 historical eras (Before 1850 → After 2000)
- [x] Explored BBR↔DAR linking strategies (notebook `02b_buildings_processed.ipynb`)
  - Spatial join via INSPIRE footprints is the recommended primary approach
  - UUID linking (husnummer_id → Husnummer entity → DAR) deferred — requires 620 MB download
- [ ] Spatial join BBR attributes to INSPIRE footprints (full integration — Phase 2)
- [x] **EXPLORE IN QGIS**: Opened all building layers, verified alignment
  - BBR points fall within/near INSPIRE footprints ✓
  - DAR entrance points (TD) are at building doors ✓
  - Land use distribution confirmed (140 = apartment building dominates with 1,600+)

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
- [x] Download routable road network
  - Source: OpenStreetMap via `osmnx.graph_from_polygon()` with `network_type='all'`
  - GraphML: `data/raw/network/norrebro_pedestrian_network.graphml` (12 MB, WGS84 — for routing via NetworkX)
  - GeoPackage: `data/processed/norrebro_pedestrian_network.gpkg` (5.0 MB, EPSG:25832 — for QGIS visualization)
  - Script: `scripts/download/download_pedestrian_network.py`
- [x] Process network data
  - Walking travel times added at 1.4 m/s (5 km/h)
  - Projected to EPSG:25832 for GeoPackage output
  - Boundary buffered by 800m to capture edges near study area boundary
- [x] **EXPLORE IN QGIS**: Load pedestrian network GeoPackage
  - Nodes + edges layers verified for connectivity ✓
  - Highway type distribution checked (residential, footway, cycleway, etc.) ✓
  - Buffer zone coverage beyond Nørrebro boundary confirmed ✓
- [ ] Document data quality and topology

**Two Output Formats**:

- **GraphML** (WGS84, in `data/raw/network/`): Preserves graph topology (node-edge connectivity). Required for routing algorithms (shortest path, isochrones) via `networkx` / `osmnx`. GeoPackage cannot represent graph topology.
- **GeoPackage** (EPSG:25832, in `data/processed/`): Flat geometry layers (nodes as points, edges as lines) for QGIS visualization. Same data, different representation.

**Notes**:

- The vejmidter download confirmed that Open Data DK road data lacks connectivity
- `network_type='all'` downloads every road and path type (driving, walking, cycling). Filtering by mode is done downstream during analysis
- Boundary buffered by 800m (`NETWORK_BUFFER_M` = `MAX_WALK_DISTANCE`) to capture network segments leading to facilities just outside Nørrebro
- `truncate_by_edge=True` keeps full edges that cross the boundary polygon
- Walking travel times pre-computed as `length / walking_speed` on each edge

---

### 5. Cycling Infrastructure

- [x] Download cycling infrastructure for Copenhagen
  - Source: Copenhagen Municipality WFS (`https://wfs-kbhkort.kk.dk/k101/ows`) — free, no authentication
  - Script: `scripts/download/download_cycling.py`
  - Three raw datasets downloaded (citywide, EPSG:25832):
    - `data/raw/cycling/kk_cykelsti.gpkg` (1,911 features, 0.8 MB) — physical cycle paths with type + width
    - `data/raw/cycling/kk_cykeldata.gpkg` (3,638 features, 1.3 MB) — broader cycling network
    - `data/raw/cycling/kk_cykelstativ.gpkg` (7,012 features, 2.0 MB) — bike parking with capacity
- [x] Process into analysis-ready GeoPackage
  - Script: `scripts/process/process_cycling.py`
  - Output: `data/processed/norrebro_cycling.gpkg` (3.0 MB)
    - Layer `cykeldata`: 3,638 cycling network lines (citywide, no clipping)
    - Layer `cykelstativ`: 1,664 bike parking points (clipped to 800m buffer around Nørrebro)
- [x] **EXPLORE IN QGIS**: Load cycling layers
  - Styled by `kategori` (Cykelsti, Supercykelsti, Grøn, Cykelmulighed, Cykelrute) ✓
  - Density and connectivity around Nørrebro checked ✓
  - Bike parking coverage within 800m buffer verified ✓
- [ ] Document cycling infrastructure coverage

**Dataset Choice: `cykeldata` over `cykelsti`**:

The `cykelsti` layer maps each side of a street separately (two lines per street where cycle lanes exist on both sides), which creates duplicates in proximity/counting analysis. The `cykeldata` layer represents one line per street with a cycling facility, with a `kategori` field to distinguish infrastructure types. This is cleaner for measuring distance from building entrances to cycling infrastructure.

**`cykeldata` Categories**:

| kategori | Count | Description |
|---|---|---|
| Cykelsti | 2,361 | Dedicated cycle paths |
| Cykelmulighed | 663 | Roads suitable for cycling (less protected) |
| Grøn | 307 | Green cycle routes through parks |
| Supercykelsti | 182 | Super cycle highways (premium commuter routes) |
| Cykelrute | 117 | Designated cycle routes |
| Other | 8 | Cykelgade, Lokal forbindelse |

**`cykelstativ` (Bike Parking)**:

- 7,012 points citywide, 1,664 within 800m of Nørrebro
- Attributes: capacity, type, owner, condition

**Data Source**: Copenhagen Municipality WFS at `wfs-kbhkort.kk.dk/k101/ows`. Also has `k101:blaa_cykelfelt` (324 blue-painted cycle crossings) if needed later.

---

### 6. Public Transport Stops

- [x] Download national GTFS feed
  - Source: Rejseplanen Labs (`https://www.rejseplanen.info/labs/GTFS.zip`)
  - File: `data/raw/transport/rejseplanen_gtfs.zip` (48.6 MB)
  - Script: `scripts/download/download_gtfs.py`
  - Contains all Danish public transport: buses (Movia), metro, trains (DSB/S-tog)
  - No authentication needed for download (free access via Rejseplanen Labs)
- [x] Process stops and routes, classify by mode, clip to 10 km buffer
  - Script: `scripts/process/process_transport_stops.py`
  - Output: `data/processed/norrebro_transport_stops.gpkg` (1.5 MB, EPSG:25832)
    - Layer `stops`: 2,687 features (2,581 bus, 62 train, 44 metro) — one row per (stop, mode) pair
    - Layer `routes`: 181 features (148 bus, 25 train, 8 metro) — actual GPS traces from GTFS `shapes.txt`
- [x] **EXPLORE IN QGIS**: Load transport stops GeoPackage
  - Stops styled by `transport_mode` (bus/metro/train) ✓
  - Route line geometries follow actual roads (from shapes.txt) ✓
  - Coverage within and around Nørrebro (10 km buffer) verified ✓
  - Multi-mode stations inspected ✓

**Data Architecture**:

- **Raw**: GTFS zip saved as-is in `data/raw/transport/` — no modifications
- **Processed**: Two-layer GeoPackage in EPSG:25832
  - `stops`: One row per (stop, transport_mode). A station served by bus + metro has two rows with same geometry, different `transport_mode` values. Attributes: `stop_id`, `stop_name`, `transport_mode`
  - `routes`: One row per (route, direction). Geometries from `shapes.txt` (GPS traces along roads), not schematic stop-to-stop lines. Attributes: `route_id`, `route_short_name`, `transport_mode`, `direction_id`

**Processing Details**:

- Early spatial filtering: stops filtered to 10 km buffered boundary before joining with stop_times (reduces 3.97M → 1.82M rows, 54% reduction)
- Mode classification via GTFS `route_type`: bus=3, metro=1, train=2 (+ extended types)
- Parent/child station handling: child stops rolled up to parent stations to avoid platform-level duplicates
- Route directionality: each route gets one line per direction (direction_id 0 and 1) since A→B→C may follow different roads than C→B→A
- 734 shape geometries (out of 6,860 nationally) intersect the 10 km buffer

**Notes**:

- GTFS feed covers all of Denmark (36,800 stops, 1,522 routes)
- 10 km buffer (`TRANSPORT_BUFFER_M`) captures regional transit context — much larger than the 800m pedestrian network buffer
- Shapes from `shapes.txt` provide real road-following geometries, not straight lines between stops

---

### 7. Parks & Green Spaces

- [x] Download parks and green spaces
  - Source: Copenhagen Municipality WFS (`https://wfs-kbhkort.kk.dk/k101/ows`) — same WFS as cycling data
  - Script: `scripts/download/download_greenspaces.py`
  - Three raw datasets downloaded (citywide, EPSG:25832):
    - `data/raw/greenspaces/kk_parkregister.gpkg` (361 features, 1.2 MB) — official park registry with polygons
    - `data/raw/greenspaces/kk_park_groent_omr_oversigtskort.gpkg` (1,448 features, 1.1 MB) — green areas overview polygons
    - `data/raw/greenspaces/kk_legeplads.gpkg` (135 features, 0.2 MB) — playground points
- [x] Download AS IS without filtering to explore in QGIS first
- [x] Process into analysis-ready GeoPackage
  - Script: `scripts/process/process_greenspaces.py`
  - Output: `data/processed/norrebro_greenspaces.gpkg` (0.3 MB)
    - Layer `parks`: 77 park polygons (clipped to 800m buffer around Nørrebro)
    - Layer `playgrounds`: 34 playground points (clipped to 800m buffer around Nørrebro)
  - All column names translated from Danish to English (e.g. `parktype` → `park_type`, `bydelsnavn` → `district`, `besoegstal` → `visitor_count`, `opland_300` → `catchment_pop_300m`)
- [x] **EXPLORE IN QGIS**: Load processed green spaces GeoPackage
  - Style parks by `park_type` (Lokale parker, Regionale parker, Naturområder, Idrætsanlæg, etc.)
  - Filter to Nørrebro: `"district" = 'Nørrebro'`
  - Check playground locations relative to parks
  - Verify catchment area attributes (`catchment_pop_300m`, `catchment_pop_875m`)
  - Assess completeness — any obvious missing parks?


**parkregister — Official Park Registry** (PRIMARY for health analysis):

- **361 park polygons** citywide, **33 in Nørrebro** (`bydelsnavn = 'Nørrebro'`)
- Key attributes:
  - `parktype`: Park type classification (see distribution below)
  - `navn_parker`: Park name
  - `bydelsnavn`: District name
  - `areal`: Area in m²
  - `besoegstal`: Annual visitor count
  - `opland_300` / `opland_875`: Catchment population at 300m and 875m walk distances
  - `ejerforhold` / `ejer`: Ownership
  - `fredning`: Protection status
  - `beskrivelse`: Description
- Park type distribution (citywide):

| parktype | Count | Description |
|---|---|---|
| Andet grønt område | 171 | Other green areas |
| Lokale parker | 71 | Local/neighbourhood parks |
| Vandflader | 27 | Water surfaces |
| Regionale parker | 24 | Regional parks |
| Naturområder | 20 | Nature areas |
| Idrætsanlæg | 17 | Sports facilities |
| Kirkegårde | 12 | Cemeteries |
| Planlagte grønne områder | 12 | Planned green areas |
| Haveanlæg | 7 | Garden facilities |

**park_groent_omr_oversigtskort — Green Areas Overview**:

- **1,448 polygon features** citywide, all classified as `objekt_type = 'Park'`
- Broader coverage than parkregister — likely includes smaller green patches
- Simpler attributes: `objekt_type`, `kommune`

**legeplads — Playgrounds**:

- **135 point features** citywide (108 regular + 27 staffed/"Bemandet")
- Attributes: `navn`, `bydel`, `legeplads_type`, `aldersgruppe` (target age group)
- Various age ranges: 0-16, 3-10, 0-14, 0-8, etc.

**Data Source**: Copenhagen Municipality WFS at `wfs-kbhkort.kk.dk/k101/ows` — no authentication required. Also available: `k101:park_groent_omr_omegn` (surrounding areas), `k101:gadetraer` (street trees) if needed later.

---
### BONUS: Translation

- [x] created a `translate_process.py` script to handle all Danish → English field name translations in one place for consistency across datasets
- [x] Translate key attribute fields from Danish to English during processing - E.g. `parktype` → `park_type`, `bydelsnavn` → `district`, `besoegstal` → `visitor_count` 
- [x] Document original Danish field names and translations in code comments and documentation for clarity

 **Notes**: 
 - Translation done in processing scripts (e.g. `process_greenspaces.py`) to maintain original raw data with Danish field names 
 - Key for readability and consistency across datasets during analysis 
 
 All further pipelines should follow the sequence of:
1. Getting the raw data as is
2. First storing it
3. Then in a second stage creating a process script that does any clipping necessary, all of the translation, and then combining similar data sets into different layers of the same GeoPackage(e.g. all green space datasets into `norrebro_greenspaces.gpkg` with layers for parks, playgrounds, etc.)    

 ---


### 8. Health Metrics

- [x] Research available health data sources
  - Sundhedsdatabanken (eSundhed) — chronic disease register
  - Danskernes Sundhed (danskernessundhed.dk) — national health profile survey
  - StatBank Denmark (DST) — causes of death, mortality by municipality
  - WHO HEAT Tool — health economic assessment framework for walking/cycling
- [x] Identify most granular geographic level available
  - **Municipality level (København = 0101) is the finest publicly available granularity**
  - Sub-municipal data (e.g., Nørrebro district) requires formal application to Region Hovedstaden with Data Protection Authority approval + institutional affiliation
  - Future: Apply via OSLOMET credentials for sub-municipal data
- [x] Set up download infrastructure
  - Script: `scripts/download/download_health.py`
    - Automated: StatBank Denmark tables (DODA1 causes of death, FOD207 deaths by municipality) via API
    - Manual verification: eSundhed XLSX, Sundhedsprofil CSV, WHO HEAT PDF
  - Guide: `docs/health_data_download_guide.md` — step-by-step instructions for all 5 sources
  - Raw data directory: `data/raw/health/`
- [x] Download manual datasets (Sources 1, 2, 5)
  - eSundhed XLSX: `data/raw/health/esundhed_kroniske_sygdomme_2010_2025.xlsx` (23 MB)
  - Danskernes Sundhed: 7 indicators in `data/raw/health/danskernessundhed/` (2021 per-kommune + 2023 per-age)
  - WHO HEAT guide: `data/raw/health/WHO_HEAT_user_guide_2024.pdf` (4.5 MB)
- [x] Run `scripts/download/download_health.py` — downloaded DODA1 (1.7 MB) and FOD207 (437 KB)
- [x] Compute WHO HEAT input parameters
  - Script: `scripts/process/process_heat_inputs.py`
  - Output: `data/processed/heat_inputs.json`
  - Reference: `docs/heat_assessment_inputs.md` — ready-to-use cheat sheet for HEAT web tool
- [x] Re-download physical activity per-age data from Danskernes Sundhed (fixed — proper sample sizes now)
- [x] Process health data into analysis-ready format
  - Script: `scripts/process/process_health.py`
  - Outputs: 4 CSVs in `data/processed/`:
    - `health_survey_by_age.csv` (126 rows — 7 indicators × 7 age groups × 2 genders)
    - `health_survey_by_municipality.csv` (174 rows — 6 indicators × 29 municipalities)
    - `health_causes_of_death.csv` (25,920 rows — DODA1 translated)
    - `health_deaths_by_municipality.csv` (12,120 rows — FOD207 translated)
  - Translations: Danish column names → English, gender values translated, percentages parsed to floats, total/summary rows dropped
- [x] Create exploratory notebook `05_health_metrics.ipynb`
  - 7 sections: population profile, national mortality (DODA1), Copenhagen mortality (FOD207), health behaviours (all 7 survey indicators), HEAT results, narrative summary
- [ ] Process eSundhed chronic disease XLSX (deferred — complex multi-sheet format)
- [ ] Document limitations and methodological considerations

**Data Sources (5 total)**:

| # | Source | Geographic Level | Content | Format | Access |
|---|--------|-----------------|---------|--------|--------|
| 1 | **Sundhedsdatabanken** (eSundhed) | Municipality | Chronic disease prevalence/incidence: Type 1&2 diabetes, COPD, asthma, osteoporosis, dementia, rheumatoid arthritis, schizophrenia. By age, sex. 2010–2025. | XLSX | Free, manual download |
| 2 | **Danskernes Sundhed** (danskernessundhed.dk) | Municipality | Survey: physical activity, BMI, self-rated health, smoking, stress, diet. 2010–2023. | Interactive viewer (manual extraction) | Free to browse |
| 3 | **StatBank Denmark** (DODA1) | National | 24 cause-of-death categories incl. heart disease, respiratory, diabetes. By age, sex. 2007–2022. | CSV via API | Free, automated |
| 4 | **StatBank Denmark** (FOD207) | Municipality | Deaths by municipality, age, sex. 2006–2025. Copenhagen + Region Hovedstaden + national. | CSV via API | Free, automated |
| 5 | **WHO HEAT Tool** | N/A (framework) | Economic value of walking/cycling health benefits. Inputs: population, modal share, mortality rate, air pollution. | PDF guide + web tool | Free |

**Geographic Granularity Ceiling**:

Municipality level (all of København) is the finest publicly available health data. Sub-municipal data (Nørrebro-specific) exists in underlying registers but requires: (1) formal application to Region Hovedstaden or Sundhedsdatastyrelsen, (2) Data Protection Authority approval, (3) institutional affiliation. The resolution gap itself is part of the project narrative — design decisions need granular data that doesn't exist publicly.

**Narrative Framework**:

The health data serves a top-down narrative connecting infrastructure to health prevention:

1. **National context** (DODA1): Heart disease and diabetes are leading causes of death in Denmark — both preventable through physical activity
2. **Copenhagen burden** (eSundhed): Municipality-level chronic disease prevalence shows the local disease landscape
3. **Lifestyle factors** (Danskernes Sundhed): Physical activity levels and BMI by age group — which populations are least active?
4. **Infrastructure connection** (project analysis): Walking/cycling accessibility from Nørrebro buildings to transit, parks, cycling infrastructure
5. **Economic valuation** (WHO HEAT): If infrastructure changes increase walking by X minutes/day, what is the economic health benefit?

**Key Evidence for Designers**:

- WHO recommends 150–300 min/week moderate physical activity for adults
- 30 min/day walking associated with 19% reduction in coronary heart disease risk
- WHO HEAT Tool (2024 update) provides standardised methodology for calculating health economic value of active transport infrastructure
- Age-differentiated impacts: older adults, children benefit differently — walking speeds already in config (WALKING_SPEED = 1.4 m/s is population average; demographic-specific speeds needed for analysis)

**Files**:

- Raw: `data/raw/health/` (see `docs/health_data_download_guide.md`)
  - `statbank_doda1_causes_of_death.csv` — automated via API
  - `statbank_fod207_deaths_by_municipality.csv` — automated via API
  - `esundhed_kroniske_sygdomme_2010_2025.xlsx` — manual download
  - `danskernessundhed/` — 7 indicator subdirectories with per-kommune (2021) + per-age (2023) CSVs
  - `WHO_HEAT_user_guide_2024.pdf` — manual download
- Processed:
  - `data/processed/heat_inputs.json` — all HEAT input parameters (population, mortality, modal share, air pollution, road crashes)
  - `data/processed/health_survey_by_age.csv` — 126 rows, 7 indicators × age group × gender (totals removed, granular rows only)
  - `data/processed/health_survey_by_municipality.csv` — 174 rows, 6 indicators × 29 Capital Region municipalities
  - `data/processed/health_causes_of_death.csv` — 25,920 rows, DODA1 translated to English
  - `data/processed/health_deaths_by_municipality.csv` — 12,120 rows, FOD207 translated to English
- Scripts: `scripts/download/download_health.py` + `scripts/process/process_heat_inputs.py` + `scripts/process/process_health.py`
- Notebook: `notebooks/05_health_metrics.ipynb` — exploratory analysis with 7 sections (population profile, mortality context, health behaviours, WHO HEAT results, narrative synthesis)
- Docs: `docs/health_data_download_guide.md` + `docs/heat_assessment_inputs.md` (HEAT web tool cheat sheet)
- Config: Health paths + `HEAT_INPUTS_OUTPUT` + 4 survey/mortality output paths in `src/utils/config.py`

**HEAT Computed Values** (from `process_heat_inputs.py`):

| Parameter | Value | Source |
|---|---|---|
| Nørrebro total population | 79,753 | `norrebro_neighbourhoods_population.csv` |
| Population aged 20-74 (walking) | 63,529 | Calculated from same CSV |
| Population aged 20-64 (cycling) | 59,605 | Calculated from same CSV |
| Copenhagen mortality rate (20-74) | 278.7 per 100,000 | FOD207 deaths (1,438) / FOLK1A population (515,913), year 2023 |
| HEAT default mortality (Denmark) | 500 per 100,000 | Built into HEAT tool |
| Modal share walking | 21% | DTU Transport Survey 2018 (Copenhagen) |
| Modal share cycling | 28% | DTU Transport Survey 2018 (Copenhagen) |
| PM2.5 annual mean | 9.8 µg/m³ | IQAir/EEA 2024 (Copenhagen) |
| Cycling fatality rate | 15.9 per billion km | ITF/OECD (Denmark) |

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

- [x] Prepare pedestrian network for routing
  - [x] Build network topology (provided by osmnx graph)
  - [x] Define walking impedance (travel time at 1.4 m/s)
  - [ ] Clean disconnected segments (if needed after inspection)
- [ ] Prepare cycling network for routing
- [ ] Define cycling impedance measures

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

### Health Data Sources

- **Sundhedsdatabanken** (eSundhed): https://sundhedsdatabank.dk/ - Chronic disease register (municipality level)
- **Danskernes Sundhed**: https://www.danskernessundhed.dk/ - National health profile survey (municipality level)
- **StatBank Denmark**: https://www.statbank.dk/ - Causes of death, mortality (national/municipality level)
- **WHO HEAT Tool**: https://www.heatwalkingcycling.org - Health economic assessment for walking/cycling
- **WHO HEAT 2024 Guide**: https://www.who.int/europe/publications/i/item/9789289058377

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

**Current Phase**: Phase 1 - Data Collection (complete) / Phase 2 - Data Processing & Integration (starting)
**Last Updated**: 2026-02-17

### Completed

- Study area boundary defined (5 sub-neighbourhoods with `gm_id`)
- Population and dwellings data downloaded, cleaned, and ID-matched
- Road centre lines downloaded (but found unsuitable for routing)
- **Building footprints downloaded**: INSPIRE dataset manually acquired, clipped to Nørrebro
- **BBR building attributes downloaded**: 3,439 buildings via WFS API with comprehensive attributes
- **DAR entrance points downloaded**: 11,911 address points via File Download API (5,639 accurate TD entrance doors)
- Download script created: `scripts/download/download_bbr_dar.py` with credentials management and caching
- **BBR + DAR processed**: `norrebro_buildings.gpkg` (1.7 MB) with `buildings` layer (3,439 features, English translations, use descriptions, construction eras, material/heating labels) + `entrances` layer (5,643 TD/TK points within 800m buffer)
- Script created: `scripts/process/process_buildings.py`
- **BBR↔DAR linking investigated**: Spatial join via INSPIRE footprints is the recommended approach. UUID linking deferred (requires 620 MB Husnummer download). Explored in notebook `02b_buildings_processed.ipynb`.
- **Pedestrian network downloaded**: OSM via osmnx, buffered 800m, with walking travel times (GraphML for routing + GeoPackage for QGIS)
- Download script created: `scripts/download/download_pedestrian_network.py`
- **Public transport stops & routes downloaded**: Rejseplanen GTFS feed, 10 km buffer, 2,687 stops + 181 route lines with GPS traces from shapes.txt
- Scripts created: `scripts/download/download_gtfs.py` + `scripts/process/process_transport_stops.py`
- **Cycling infrastructure downloaded & processed**: Copenhagen Municipality WFS (3 raw datasets), processed into `norrebro_cycling.gpkg` with `cykeldata` (3,638 citywide) + `cykelstativ` (1,664 clipped to 800m)
- Scripts created: `scripts/download/download_cycling.py` + `scripts/process/process_cycling.py`
- **Scripts reorganized**: `scripts/download/` (raw data fetching) and `scripts/process/` (raw → processed)
- **Green spaces downloaded & processed**: Copenhagen Municipality WFS (3 raw datasets), processed into `norrebro_greenspaces.gpkg` with `parks` (77 polygons clipped to 800m) + `playgrounds` (34 points clipped to 800m). Column names translated to English.
- Scripts created: `scripts/download/download_greenspaces.py` + `scripts/process/process_greenspaces.py`
- **PROJECT_ROOT bug fixed**: All scripts in `scripts/download/` and `scripts/process/` updated from `.parent.parent` to `.parent.parent.parent` after directory reorganization
- **All processed datasets explored in QGIS**: Buildings, network, cycling, transport, green spaces — spatial alignment and data quality verified
- **Exploratory notebooks created**: `00_style_guide`, `01_demographics`, `02_buildings` (raw), `02b_buildings_processed`, `03_transport_network`, `04_green_spaces`
- **Health data researched and infrastructure set up**: 5 data sources identified (eSundhed chronic disease register, Danskernes Sundhed survey, StatBank DODA1 causes of death, StatBank FOD207 deaths by municipality, WHO HEAT tool). Municipality level confirmed as finest public granularity. Download script + manual guide created.
- Scripts created: `scripts/download/download_health.py` + `docs/health_data_download_guide.md`
- **Health data downloaded**: All 5 sources acquired. StatBank tables (DODA1, FOD207) automated via API. Manual downloads completed: eSundhed chronic disease XLSX, Danskernes Sundhed survey CSVs (7 indicators, 2021 per-kommune + 2023 per-age), WHO HEAT user guide PDF.
- **WHO HEAT input parameters computed**: `scripts/process/process_heat_inputs.py` calculates all HEAT web tool inputs from project data + StatBank FOLK1A API. Output: `data/processed/heat_inputs.json`. Key result: Copenhagen mortality rate 278.7/100k (vs. HEAT default 500). Reference document: `docs/heat_assessment_inputs.md`.
- **Health data processed**: `scripts/process/process_health.py` combines 15 Danskernes Sundhed CSVs into 2 unified tables (by age + by municipality), translates StatBank DODA1/FOD207 columns to English. Outputs 4 CSVs in `data/processed/`. Total/summary rows removed from survey data — only granular gender × age group rows retained.
- **Health metrics notebook created**: `notebooks/05_health_metrics.ipynb` — 7-section exploratory analysis covering population profile, national mortality context, Copenhagen vs national comparison, health behaviours (7 indicators), WHO HEAT results, and narrative synthesis connecting preventive care to active transport infrastructure.

### Prioritised Next Steps

1. Join demographics to boundary GeoPackage spatially (quick win, unblocks visualization)
2. Spatial join BBR attributes to INSPIRE footprints (Phase 2 integration)
3. Process eSundhed chronic disease XLSX (deferred — complex multi-sheet workbook)

---

## Notes & Discoveries

### BBR & DAR Data (2026-02-11, updated 2026-02-14)

#### Key Discovery: DAR Entrance Point Technical Standards

The DAR Adressepunkt dataset contains ~50% road-based points (V0) and ~50% building entrance points (TD). For routing and accessibility analysis, **always filter by `oprindelse_tekniskStandard`**:

- **Use for analysis**: TD (entrance doors, 5,639 points) and TK (building facade, 4 points)
- **Exclude**: V0-V9 (road points, 6,072 points) — these are not actual building entrances

This distinction is critical for accurate network analysis. A spatial join without filtering would incorrectly assign many road-based points as building entrances.

#### BBR Building Use Codes (fully mapped)

All ~80 BBR use codes mapped to English descriptions in `process_buildings.py` per official documentation at <https://teknik.bbr.dk/kodelister>. Key Nørrebro distribution:

- **Residential**: 1,668 buildings (48%) — dominated by code 140 (Apartment building, 1,600+)
- **Accessory/Other**: 968 (28%) — garages, sheds, carports
- **Culture/Institutional**: 319 (9%) — schools, churches, daycare
- **Office/Retail**: 231 (7%) — offices, shops, warehouses

Material codes (wall, roof, heating) also mapped from numeric BBR codes to English. Nørrebro is 59% brick walls, 61% district heating.

#### Construction Eras

Buildings grouped into 7 historical periods. The two largest eras confirm Nørrebro's building history:

- **1850-1900**: 771 buildings (industrialisation, Nørrebro's initial dense development)
- **1900-1930**: 806 buildings (continued urban expansion)
- **After 2000**: 618 buildings (contemporary infill/renovation)

#### Data Joining Strategy

1. **BBR → INSPIRE footprints**: Spatial join works well (most BBR points fall within footprints). Confirmed in notebook `02b_buildings_processed.ipynb`.
2. **DAR → Footprints**: Entrance points (TD) are at the door, so some fall just outside polygon boundaries. A **2m buffer** on footprints improves match rate significantly.
3. **One-to-many**: Apartment buildings typically have multiple DAR entrance points per footprint polygon.
4. **BBR ↔ DAR exact linking**: Requires national Husnummer file (~620 MB) via `husnummer` UUID — **deferred**. Spatial join via footprints is sufficient for current analysis.

### Pedestrian Network (2026-02-11)

#### Two Output Formats

The network is saved in two formats because they serve fundamentally different purposes:

- **GraphML** (`data/raw/network/`): A graph serialization format that preserves **topology** — which nodes connect to which edges, with weights (distance, travel time). This is what routing algorithms need. Libraries like `networkx` and `osmnx` load this directly for shortest-path, isochrone, and accessibility calculations.
- **GeoPackage** (`data/processed/`): Flat geometry layers (points + lines) for **visualization** in QGIS. Same network data, but without graph topology. QGIS cannot open GraphML files.

#### Design Decisions

- **`network_type='all'`**: Downloads every OSM highway type (roads, footways, cycleways, paths). Mode-specific filtering is deferred to analysis time, keeping the raw download flexible for both walking and cycling analyses.
- **800m buffer**: Network extends 800m beyond Nørrebro boundary (`NETWORK_BUFFER_M` = `MAX_WALK_DISTANCE`). This captures streets leading to facilities just outside the study area — without it, routing would dead-end at the boundary.
- **Walking travel time**: Pre-computed on each edge as `length / 1.4 m/s` as a baseline. Uses constant speed rather than OSM `maxspeed` tags (which are for vehicles). Stored as `travel_time` attribute in seconds.
- **TODO — Age-differentiated travel times**: The 1.4 m/s baseline is a population-average placeholder. During analysis, travel times should be recalculated per demographic group — older adults, children, and mobility-impaired populations walk at significantly different speeds. This directly affects accessibility results and health benefit estimates across age groups. At analysis time, recompute edge travel times using demographic-specific walking speeds rather than relying on the pre-computed values.
- **`truncate_by_edge=True`**: Keeps complete edges that cross the boundary polygon, preventing artificial network breaks.

### Public Transport Data (2026-02-11)

#### Data Source: Rejseplanen GTFS

All Danish public transport is in a single GTFS feed from Rejseplanen Labs. No separate downloads per operator — Movia (buses), Metroselskabet (metro), and DSB (trains/S-tog) are all included. The zip is ~49 MB covering 36,800 stops and 1,522 routes nationally.

#### Key Design: shapes.txt for Route Geometries

GTFS provides two ways to represent route paths:
- **`shapes.txt`** (what we use): Actual GPS traces along roads — high-resolution polylines that follow the real route path. 3.48M shape points nationally.
- **Stop-to-stop lines** (rejected): Straight lines connecting consecutive stops. These are schematic and don't follow actual roads. Misleading on a map.

#### GTFS Structure for Mode Classification

Stops don't have a mode attribute directly. The join chain is:
`routes.txt` (has `route_type`) → `trips.txt` → `stop_times.txt` → `stops.txt`

Route types: bus=3, metro=1, train=2. Extended GTFS types (100-199, 400-499, 700-799) are also handled.

#### Early Filtering Strategy

The national GTFS is large (3.97M stop_times rows). Processing order:
1. Filter stops spatially first (36,800 → 2,677 in 10 km buffer)
2. Filter stop_times to matching stop_ids (54% reduction)
3. Filter shapes to those intersecting buffer (6,860 → 734)
4. Only then do the joins

This avoids loading and joining the full national dataset.
