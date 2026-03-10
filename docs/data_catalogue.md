# Data Catalogue

Authoritative reference for every dataset in the project. For design rationale ("why"), see [design_decisions.md](design_decisions.md). For source URLs and APIs, see [data_sources.md](data_sources.md).

---

## 1. Study Area Boundary

**File**: `norrebro_boundary.gpkg` (layer: `norrebro_boundary`)
**Records**: 5 sub-neighbourhoods
**Source**: Copenhagen Municipality administrative boundaries via OpenData.dk WFS
**Raw**: `raw/boundary/opendata_copenhagen_bydele_20260210.gpkg`

Key attribute: `gm_id` — unique neighbourhood identifier used to join demographics data.

---

## 2. Population & Demographics

**Files**: `norrebro_neighbourhoods_population.csv`, `norrebro_neighbourhoods_dwellings.csv`
**Records**: 5 sub-neighbourhoods each
**Source**: Statistics Denmark — tables KKBEF8 (population by age) and KKBOL2 (dwellings by type/household size)
**Raw**: `raw/demographics/2025_KKBEF8.xlsx`, `raw/demographics/2025_KKBOL2.xlsx`

- Population CSV has age group breakdowns per neighbourhood
- Dwellings CSV has dwelling types and household sizes
- Both have `gm_id` for joining to boundary layer

---

## 3. Buildings

### BBR Building Attributes

**File**: `norrebro_buildings.gpkg`, layer `buildings`
**Records**: 3,440 building points (1.7 MB total GeoPackage)
**Source**: Datafordeleren BBR WFS API
**Raw**: `raw/bbr/norrebro_bbr_buildings.gpkg`
**Script**: `scripts/process/process_buildings.py`

14 translated columns + 4 derived columns:

| Original BBR field | English name | Description |
|---|---|---|
| `byg021BygningensAnvendelse` | `building_use` | Building use code (see use codes below) |
| `byg038SamletBygningsareal` | `total_area_m2` | Total built area (m2) |
| `byg026Opførelsesår` | `construction_year` | Year of construction |
| `byg054AntalEtager` | `num_floors` | Number of floors |
| `byg039BygningensSamledeBoligAreal` | `residential_area_m2` | Residential area (m2) |
| `byg040BygningensSamledeErhvervsAreal` | `commercial_area_m2` | Commercial area (m2) |
| `byg041BebyggetAreal` | `footprint_area_m2` | Built footprint area (m2) |
| `husnummer` | — | UUID linking to DAR address register |

Derived columns: `use_description`, `use_category`, `construction_era`, English material/heating labels.

**BBR Use Code Distribution (Norrebro)**:

| Category | Count | % | Examples |
|---|---|---|---|
| Residential | 1,669 | 48% | Code 140 (apartment building) dominates with 1,600+ |
| Accessory/Other | 968 | 28% | Garages, sheds, carports |
| Culture/Institutional | 319 | 9% | Schools, churches, daycare |
| Office/Retail | 231 | 7% | Offices, shops, warehouses |

All ~80 BBR use codes mapped to English per official documentation at https://teknik.bbr.dk/kodelister.

**Construction Eras** (7 periods):

| Era | Count | Context |
|---|---|---|
| 1850-1900 | 771 | Industrialisation, initial dense development |
| 1900-1930 | 806 | Continued urban expansion |
| After 2000 | 618 | Contemporary infill/renovation |

Material codes: 59% brick walls, 61% district heating.

### DAR Entrance Points

**File**: `norrebro_buildings.gpkg`, layer `entrances`
**Records**: 5,643 points (TD/TK only, within 800m buffer)
**Source**: Datafordeleren DAR File Download API
**Raw**: `raw/dar/norrebro_dar_adressepunkt.gpkg` (11,911 total before filtering)

**Technical Standard Codes** (`oprindelse_tekniskStandard`):

| Code | Count | % | Positioning Method | Use? |
|---|---|---|---|---|
| **TD** | 5,639 | 47.4% | At building entrance door | YES |
| TK | 4 | <0.1% | At building facade facing street | YES |
| TN | 158 | 1.3% | Within building perimeter | Moderate |
| **V0** | 5,749 | 48.3% | Road point (on street) | NO |
| V1-V9 | 220 | 1.8% | Various road point types | NO |
| UF | 134 | 1.1% | Unspecified/provisional | NO |
| TA | 7 | <0.1% | Facility without building | Context-dependent |

For analysis: filter to TD + TK only (5,643 accurate entrance points).

### INSPIRE Building Footprints

**File**: `norrebro_building_footprints.gpkg`
**Records**: 5,915 polygons, clipped to Norrebro (1.0 MB)
**Source**: INSPIRE building footprints (manually downloaded)
**Raw**: `data/buildings/building_inspire.gpkg` (2.6 GB full dataset)
**Script**: `scripts/process/clip_building_footprints.py`

### Integrated Buildings

**File**: `data/integrated/norrebro_buildings.gpkg` (12.3 MB)
**Scripts**: `scripts/integrate/integrate_buildings.py`, `scripts/integrate/integrate_population_typology.py`
**Notebooks**: `notebooks/06_buildings_integration.ipynb`, `notebooks/07_population_typology.ipynb`

Joins BBR attributes onto INSPIRE footprints, links DAR entrances, fills unmatched footprints via KNN, guarantees every residential building has an entrance, and assigns age-specific population to each entrance point.

#### Layer: `buildings` (5,915 footprint polygons — visualization dataset)

All INSPIRE footprints with BBR attributes where available, KNN-estimated where nearby, or unmatched.

| Column | Description |
|---|---|
| `building_id` | BBR UUID (null for unmatched) |
| `use_code`, `use_description`, `use_category` | Building use classification |
| `construction_year`, `construction_era` | When built |
| `floors` | Number of floors |
| `total_area_m2`, `residential_area_m2`, `commercial_area_m2`, `footprint_area_m2` | Area metrics |
| `wall_material`, `roof_material`, `heating_type` | Building materials |
| `gm_id`, `neighbourhood_name` | Sub-neighbourhood (1-5) |
| `attributes_source` | `bbr` (3,127) / `estimated` (2,456) / `unmatched` (332) |

#### Layer: `entrances` (5,725 points — model/analysis dataset)

DAR entrance points enriched with BBR attributes from linked footprints. Unit of analysis for accessibility routing.

| Column | Description |
|---|---|
| `entrance_id` | DAR entrance UUID |
| `positioning_type`, `status` | DAR metadata |
| `building_id` through `heating_type` | BBR attributes from linked footprint |
| `gm_id`, `neighbourhood_name` | Sub-neighbourhood |
| `has_building` | Whether entrance linked to a BBR-enriched footprint |
| `entrance_source` | `spatial_join` (5,509) / `nearest` (82) / null (134 unlinked) |

#### Layer: `entrances_demographics` (11,367 points — population model output)

All DAR entrance points (from the integrated `entrances` layer) enriched with age-specific population estimates. Script: `scripts/integrate/integrate_population_typology.py`.

**Matching coverage**: 89.5% of entrances have demographics assigned (10,175/11,367). The two-round strategy:
- **Round 1** (84.8%): key join on `building_id` — entrances whose INSPIRE footprint has a BBR match
- **Round 2** (4.7%): `sjoin_nearest` with `max_distance=10m` — entrances in KNN-estimated footprints matched to the nearest residential polygon
- **Unmatched** (10.5%): predominantly non-residential (Culture/Institutional, Office/Retail); only ~34 genuinely residential entrances (0.3%) remain without demographics

**Population columns** (18 total):

| Column pattern | Description |
|---|---|
| `pop_children_0_14_<low/mid/high>` | Children age 0–14 (3 scenarios) |
| `pop_young_adults_15_29_<low/mid/high>` | Young adults 15–29 (3 scenarios) |
| `pop_working_age_30_64_<low/mid/high>` | Working age 30–64 (3 scenarios) |
| `pop_older_adults_65_79_<low/mid/high>` | Older adults 65–79 (3 scenarios) |
| `pop_very_elderly_80plus_<low/mid/high>` | Very elderly 80+ (3 scenarios) |
| `pop_total_low`, `pop_total_mid`, `pop_total_high` | Total population (3 scenarios) |

**Dwelling typology columns**:

| Column | Description |
|---|---|
| `n_dwelling_units` | Residential unit count (BBR Enhed or KNN-estimated) |
| `avg_unit_m2` | Average unit size in m² (`residential_area_m2 / n_dwelling_units`) |
| `dwelling_typology` | Tier: `studio` (≤50 m²/unit), `small` (≤80), `medium` (≤110), `family` (>110) |
| `dominant_group` | Most populous age group at the mid scenario |

**Scenario methodology**: Mid = calibrated prior matrices mapping dwelling tiers → household sizes → age shares, constrained to match neighbourhood totals (pycnophylactic). Low/high = ±40% perturbation toward uniform distribution, row-sum preserved.

---

## 4. Pedestrian Network

**Files**:
- `norrebro_pedestrian_network.graphml` — graph topology for routing (WGS84, in `data/raw/network/`, 12 MB)
- `norrebro_pedestrian_network.gpkg` — flat geometry for QGIS (EPSG:25832, 5.0 MB)

**Source**: OpenStreetMap via `osmnx.graph_from_polygon()` with `network_type='all'`
**Script**: `scripts/download/download_pedestrian_network.py`

- Boundary buffered by 800m to capture edges near study area
- Walking travel time pre-computed: `length / 1.4 m/s` stored as `travel_time` (seconds)
- `truncate_by_edge=True` keeps complete edges crossing boundary
- GeoPackage has `nodes` (points) + `edges` (lines) layers

Also downloaded: `raw/road_center_line/vejmidter.geojson` (Open Data DK) — lacks connectivity, unsuitable for routing.

---

## 5. Cycling Infrastructure

**File**: `norrebro_cycling.gpkg` (3.0 MB)
**Source**: Copenhagen Municipality WFS
**Scripts**: `scripts/download/download_cycling.py` + `scripts/process/process_cycling.py`

### Layer: `cykeldata` (3,638 features, citywide — not clipped)

One line per street with cycling facility. Categories:

| kategori | Count | Description |
|---|---|---|
| Cykelsti | 2,361 | Dedicated cycle paths |
| Cykelmulighed | 663 | Roads suitable for cycling |
| Gron | 307 | Green cycle routes through parks |
| Supercykelsti | 182 | Super cycle highways |
| Cykelrute | 117 | Designated cycle routes |
| Other | 8 | Cykelgade, Lokal forbindelse |

### Layer: `cykelstativ` (1,664 features, clipped to 800m buffer)

Bike parking points. Attributes: capacity, type, owner, condition.

**Raw datasets** (3 total):
- `raw/cycling/kk_cykelsti.gpkg` (1,911 features) — physical paths with type + width (not used for analysis — duplicates per side of street)
- `raw/cycling/kk_cykeldata.gpkg` (3,638 features) — cycling network
- `raw/cycling/kk_cykelstativ.gpkg` (7,012 features) — bike parking

---

## 6. Public Transport

**File**: `norrebro_transport_stops.gpkg` (1.5 MB)
**Source**: Rejseplanen GTFS national feed (48.6 MB zip, all Danish transit)
**Scripts**: `scripts/download/download_gtfs.py` + `scripts/process/process_transport_stops.py`

### Layer: `stops` (2,687 features)

One row per (stop, transport_mode) pair. A station served by bus + metro has two rows.

| Mode | Count |
|---|---|
| Bus | 2,581 |
| Train | 62 |
| Metro | 44 |

Attributes: `stop_id`, `stop_name`, `transport_mode`

### Layer: `routes` (181 features)

One row per (route, direction). Geometries from `shapes.txt` (real GPS traces along roads).

| Mode | Count |
|---|---|
| Bus | 148 |
| Train | 25 |
| Metro | 8 |

Attributes: `route_id`, `route_short_name`, `transport_mode`, `direction_id`

Mode classification via GTFS `route_type`: bus=3, metro=1, train=2 (+ extended types).

---

## 7. Parks & Green Spaces

**File**: `norrebro_greenspaces.gpkg` (0.3 MB)
**Source**: Copenhagen Municipality WFS
**Scripts**: `scripts/download/download_greenspaces.py` + `scripts/process/process_greenspaces.py`

### Layer: `parks` (77 polygons, clipped to 800m buffer)

From parkregister (361 citywide, 33 in Norrebro). Column names translated to English.

Key attributes: `park_type`, `name`, `district`, `area_m2`, `visitor_count`, `catchment_pop_300m`, `catchment_pop_875m`, `ownership`, `protection_status`

**Park type distribution** (citywide):

| park_type | Count | Description |
|---|---|---|
| Andet gront omrade | 171 | Other green areas |
| Lokale parker | 71 | Local/neighbourhood parks |
| Vandflader | 27 | Water surfaces |
| Regionale parker | 24 | Regional parks |
| Naturomrader | 20 | Nature areas |
| Idraetsanlaeg | 17 | Sports facilities |
| Kirkegarde | 12 | Cemeteries |
| Planlagte gronne omrader | 12 | Planned green areas |
| Haveanlaeg | 7 | Garden facilities |

### Layer: `playgrounds` (34 points, clipped to 800m buffer)

From legeplads (135 citywide). Attributes: name, district, type (regular/staffed), target age group.

**Raw datasets** (3 total):
- `raw/greenspaces/kk_parkregister.gpkg` (361 features)
- `raw/greenspaces/kk_park_groent_omr_oversigtskort.gpkg` (1,448 features) — broader green area coverage
- `raw/greenspaces/kk_legeplads.gpkg` (135 features)

---

## 8. Health Data

### Processed CSVs

| File | Rows | Content |
|---|---|---|
| `health_survey_by_age.csv` | 126 | 7 indicators x 7 age groups x 2 genders |
| `health_survey_by_municipality.csv` | 174 | 6 indicators x 29 Capital Region municipalities |
| `health_causes_of_death.csv` | 25,920 | DODA1 — 24 cause-of-death categories, translated |
| `health_deaths_by_municipality.csv` | 12,120 | FOD207 — deaths by municipality/age/sex, translated |

**Script**: `scripts/process/process_health.py`

Survey indicators (Danskernes Sundhed): physical activity, BMI, self-rated health, smoking, stress, diet, alcohol.

### WHO HEAT Input Parameters

**File**: `heat_inputs.json`
**Script**: `scripts/process/process_heat_inputs.py`
**Reference**: `docs/heat_assessment_inputs.md`

| Parameter | Value | Source |
|---|---|---|
| Norrebro total population | 79,753 | Population CSV |
| Population aged 20-74 (walking) | 63,529 | Calculated |
| Population aged 20-64 (cycling) | 59,605 | Calculated |
| Copenhagen mortality rate (20-74) | 278.7 per 100,000 | FOD207/FOLK1A, 2023 |
| HEAT default mortality (Denmark) | 500 per 100,000 | Built into HEAT tool |
| Modal share walking | 21% | DTU Transport Survey 2018 |
| Modal share cycling | 28% | DTU Transport Survey 2018 |
| PM2.5 annual mean | 9.8 ug/m3 | IQAir/EEA 2024 |
| Cycling fatality rate | 15.9 per billion km | ITF/OECD |

### Health Data Sources

| # | Source | Level | Content | Format |
|---|---|---|---|---|
| 1 | eSundhed | Municipality | Chronic disease prevalence (diabetes, COPD, asthma, etc.) 2010-2025 | XLSX |
| 2 | Danskernes Sundhed | Municipality | Survey: physical activity, BMI, health, smoking, stress | CSV |
| 3 | StatBank DODA1 | National | 24 cause-of-death categories by age/sex, 2007-2022 | CSV via API |
| 4 | StatBank FOD207 | Municipality | Deaths by municipality/age/sex, 2006-2025 | CSV via API |
| 5 | WHO HEAT Tool | Framework | Economic value of walking/cycling health benefits | Web tool |

**Geographic granularity ceiling**: Municipality (all of Kobenhavn) is the finest publicly available. Sub-municipal data requires formal application to Region Hovedstaden + Data Protection Authority approval + institutional affiliation.

### Key Evidence for Designers

- WHO recommends 150-300 min/week moderate physical activity for adults
- 30 min/day walking associated with 19% reduction in coronary heart disease risk
- WHO HEAT Tool (2024 update) provides standardised methodology for health economic valuation of active transport
