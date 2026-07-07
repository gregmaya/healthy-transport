# Data Architecture Handoff — Replicating for Spain

**Purpose**: This document describes the current (Copenhagen/Nørrebro) data architecture in enough detail that another team can rebuild the same pipeline for a Spanish study area, using Catastro and other Spanish open data in place of the Danish registers. It is a *source-mapping and schema* document, not a rewrite of the pipeline logic — the scoring model, network analysis approach, and web app are location-agnostic and travel unchanged (see [CLAUDE.md](../CLAUDE.md) for the model itself). What changes is exclusively **where the inputs come from and what shape they arrive in**.

For full current-state detail, cross-reference:
- [data_catalogue.md](data_catalogue.md) — per-dataset schemas, record counts, exact field lists
- [data_sources.md](data_sources.md) — URLs/APIs for the Danish sources
- [design_decisions.md](design_decisions.md) — why choices were made (mostly still valid for Spain)
- [CLAUDE.md](../CLAUDE.md) — binding design decisions and the B(d) health benefit model

---

## 1. Pipeline shape (unchanged for any country)

```
raw/  →  processed/  →  integrated/  →  scored/  →  web/
```

1. **Download**: pull raw data as-is, store per source, no transformation
2. **Process**: clip to study-area boundary, translate field names to English, standardize CRS, combine related layers into one GeoPackage per domain
3. **Integrate**: spatial joins across domains (buildings ↔ addresses ↔ population), fill gaps (KNN/nearest), produce the analysis-ready entrance/segment tables
4. **Score**: network-distance health-benefit model (CitySeer) on candidate segments — this stage is 100% portable, it only needs a pedestrian network graph + population points/table
5. **Web**: export scored layers to WGS84 GeoJSON for the MapLibre front end

The only stage requiring genuinely new logic per country is **Integrate** (Step 3), because it depends on matching each country's building/address/population register schema. Steps 1, 2, 4, 5 are mostly parameter swaps (URLs, field name maps, CRS code).

---

## 2. Domain-by-domain source mapping (Denmark → Spain)

### 2.1 Study area boundary

| | Denmark (current) | Spain (target) |
|---|---|---|
| Source | Copenhagen Municipality admin boundaries, OpenData.dk WFS | **IGN (Instituto Geográfico Nacional) / CNIG** admin boundary WFS, or **INE** municipal/district boundary shapefiles (Callejero/Cartografía censal) |
| Granularity used | 5 sub-neighbourhoods (`gm_id`) | Spain's closest equivalent to Danish "sub-neighbourhood" is the **INE sección censal** (census tract, ~1,000–2,500 people) — recommended unit for population joins, or **barrio** if the target city publishes barrio boundaries (many do via municipal open data portals, e.g. Madrid, Barcelona, Valencia ayuntamiento GIS portals) |
| Key join field | `gm_id` | INE `CUSEC` (census tract code) or `CUMUN` (municipality code) — becomes the new join key everywhere `gm_id` is used today |

**Action for Spain team**: pick the census-tract level (`sección censal`) as the demographic join unit — it is the finest population geography INE publishes freely, directly analogous to how `gm_id` sub-neighbourhoods are used here.

### 2.2 Buildings & addresses — the biggest architectural swap

This is the domain most specific to Denmark's BBR/DAR system, and the one place where Spain's own free source is actually *better* than what's used here: **Catastro** publishes both cadastral parcels/building footprints AND unit-level attributes in one open, machine-readable service — no separate "BBR vs DAR" split is needed.

| | Denmark (current) | Spain (target: Catastro) |
|---|---|---|
| Building attributes register | BBR WFS (`bbr_v001:bygning_current`) — use code, floors, construction year, areas, materials | **Sede Electrónica del Catastro — INSPIRE ATOM/WFS services** (`Catastro INSPIRE Buildings` — `CP:CadastralParcel`, `BU:Building`) — construction year, number of floors, use, gross floor area |
| Building footprints | INSPIRE building footprints, manually downloaded 2.6 GB national file | Catastro **already publishes INSPIRE-conformant building polygons** directly per municipality/province via its own ATOM feed — no separate manual download step needed; this replaces both the BBR WFS *and* the manual INSPIRE download in one source |
| Address/entrance points | DAR File Download API (`Adressepunkt`, TD/TK technical-standard filter for real entrance doors vs road points) | Catastro INSPIRE **Addresses (AD:Address)** service publishes entrance-level address points per building — check the `specification` / `locator designator` fields for an equivalent "positioned at entrance vs interpolated" flag; Spain's addresses do NOT have a codified technical-standard field like DAR's TD/TK/V0, so an equivalent geometric heuristic will likely be needed (e.g. snap-to-footprint-edge validation) |
| Building use classification | BBR `byg021BygningensAnvendelse` code list | Catastro `uso` (building use) field, standard national code list (residential/commercial/industrial/etc.) — published alongside INSPIRE Building data or via the classic Catastro "Consulta Descriptiva y Gráfica" bulk parcel data |
| Dwelling/unit counts | BBR Enhed layer (`bbr_v001:enhed_current`) → `antal_boliger` | Catastro **Cadastral Parcel + Building Unit (Bien Inmueble)** records include number of dwelling units per building in the bulk cadastral extract (`Catastro — Consulta descriptiva y gráfica` municipal file, or CSV bulk downloads via Sede Electrónica per province) |
| Construction year, floors, area | BBR fields | Catastro parcel record fields: `antiguedad`/`anyoConstruccion` (year built), `numeroPlantas` (floors), `superficieConstruida` (built area) |

**Practically**: for Spain, Catastro replaces BBR + DAR + the manual INSPIRE footprint download as a *single* source family. This actually simplifies `integrate_buildings.py` — no need for the current three-way BBR/DAR/INSPIRE spatial-join-plus-KNN-fallback dance, since Catastro ties parcel, footprint, and unit-level attributes together by cadastral reference (`referencia catastral`) already. The Spain team should treat `referencia catastral` as the new master join key, replacing the current `building_id` (BBR UUID).

**Caveat to flag to the Spain team**: Catastro's free bulk services differ by delivery mechanism — INSPIRE ATOM (polygon geometry + minimal attributes, always free, no auth) vs the "Sede Electrónica" descriptive CSV/XML per-municipality extract (fuller attributes, still free but requires per-municipality request or scraping the "Consulta descriptiva y gráfica" endpoint). Confirm which mechanism is used consistently, since attribute completeness differs.

**Entrance-point standard flag caution (carried over rule)**: This project's rule #1 in CLAUDE.md ("Always filter DAR `TD`/`TK`, never `V0`") has no direct Spanish equivalent field. The Spain team must define their own filter — likely: keep address points whose Catastro locator geometry sits on/near a building footprint boundary; discard points that fall only on street centerlines. This needs empirical validation against a sample, same as was done here originally for DAR.

### 2.3 Population & demographics

| | Denmark (current) | Spain (target) |
|---|---|---|
| Source | Statistics Denmark (KKBEF8: population by age; KKBOL2: dwellings by type/household size), per sub-neighbourhood | **INE (Instituto Nacional de Estadística)** — `Padrón continuo` / `Cifras de población` tables by **sección censal**, broken down by age group and sex, published free via INE's API (`INE Tempus3` / `INEbase`) or downloadable CSV |
| Dwelling data | KKBOL2: dwelling types, household sizes | INE **Censo de Población y Viviendas** (Population and Housing Census, most recent full run 2021) — dwelling type, household size, surface area distributions by census tract |
| Granularity ceiling | Municipality-level for health, sub-neighbourhood for population | INE section-tract level for population/housing is finer than Denmark's sub-neighbourhood — good news for the Spain rebuild, it can be *more* precise here |
| Age-group bins | 5 groups used in the typology model (0–14, 15–29, 30–64, 65–79, 80+) | INE publishes finer age bins (single-year or 5-year) — the Spain team should re-bin to match whatever age structure the B(d) curve groups need (children/working-age/elderly/reduced-mobility), not necessarily replicate Denmark's exact bin edges |

**Note on the population typology model** (`integrate_population_typology.py`): the dwelling-tier → household-size → age-share calibration matrices used here are Denmark-specific priors (calibrated against Danish neighbourhood totals). For Spain, either recalibrate equivalent matrices against INE census-tract-level age/dwelling cross-tabs (may exist directly in INE data without needing the same low/mid/high perturbation approach — Spain's finer geography may make the pycnophylactic estimation step unnecessary if section-tract-level age data is available directly), or keep the same modeling approach if the Spanish city's population data isn't available at the same resolution as buildings.

### 2.4 Pedestrian network

| | Denmark (current) | Spain (target) |
|---|---|---|
| Source | OpenStreetMap via `osmnx.graph_from_polygon(network_type='all')` | **Unchanged — OpenStreetMap** is equally complete for Spanish cities. Same `osmnx` download script, same CitySeer graph-construction pipeline. This is the one domain that requires zero source-swap. |
| CRS | EPSG:25832 (ETRS89 / UTM 32N) | Spain spans multiple UTM zones — use **EPSG:25830** (ETRS89 / UTM 30N, mainland Spain default for most of the peninsula), or 25829/25831 depending on longitude of the target city (Galicia → 25829, Catalonia/Balearics → 25831). Pick per-city, not a single national constant. |

### 2.5 Public transport (bus/rail/metro)

| | Denmark (current) | Spain (target) |
|---|---|---|
| Source | Rejseplanen national GTFS feed | Spain has **no single national GTFS feed** — GTFS is published per operator/region. Candidates: **EMT** (Madrid), **TMB** (Barcelona), **regional consortiums** (Consorcio Regional de Transportes de Madrid, AMB Barcelona, EMT Valencia, etc.) each publish their own GTFS, often via their open-data portals or via the national **transit.land** / **NAP (National Access Point) España** aggregator (`nap.transportes.gob.es`) which is the closest Spanish equivalent to Rejseplanen and should be the first thing to check per target city. |
| Route/stop mode classification | GTFS `route_type` (bus=3, metro=1, train=2) | Unchanged — GTFS `route_type` is a standard field, same mapping logic applies regardless of country. |

### 2.6 Cycling infrastructure

| | Denmark (current) | Spain (target) |
|---|---|---|
| Source | Copenhagen Municipality WFS (`k101:cykeldata`, `k101:cykelstativ`) | City-specific open data portal — most large Spanish cities publish a `carriles bici` (cycle lane) layer via their municipal open-data portal (e.g. Madrid's `datos.madrid.es`, Barcelona's `opendata-ajuntament.barcelona.cat`, Valencia's `valencia.opendatasoft.com`). No national equivalent exists; this is a per-city WFS/GeoJSON discovery task, same pattern as the current `k101` scripts but pointed at a different portal. OSM `cycleway=*` tags are a usable fallback if a city has no dedicated open-data cycling layer. |

Note: cycling scoring methodology is itself still a placeholder in this project (CLAUDE.md rule #9) — so this domain only needs a *download* path for Spain, not a scoring pipeline yet.

### 2.7 Parks & green spaces

| | Denmark (current) | Spain (target) |
|---|---|---|
| Source | Copenhagen Municipality WFS (`k101:parkregister`, `k101:legeplads`) | Per-city municipal open-data portal again (parks/green-area layers, playground layers) — same discovery pattern as cycling. Fallback: **OSM `leisure=park`/`leisure=playground`** tags, which are generally well-mapped in Spanish cities and can substitute if no official municipal layer exists. |

### 2.8 Health data (used for narrative/context, not scoring)

| | Denmark (current) | Spain (target) |
|---|---|---|
| Chronic disease prevalence | eSundhed (municipality level) | **Instituto de Salud Carlos III** / Ministerio de Sanidad `ENSE` (Encuesta Nacional de Salud de España) — national survey, some regional breakdowns; regional health institutes (e.g. Madrid's `Instituto de Salud Pública`) may publish finer data |
| Mortality by cause | StatBank DODA1 | INE **Estadística de Defunciones según la Causa de Muerte** |
| Deaths by municipality/age/sex | StatBank FOD207 | INE **Movimiento Natural de la Población** tables, or regional health department mortality registries |
| Physical activity / lifestyle survey | Danskernes Sundhed | ENSE includes physical activity, BMI, self-rated health, smoking — same indicator families, national rather than per-municipality granularity by default |
| Economic valuation | WHO HEAT Tool | **Unchanged** — WHO HEAT tool is Europe-wide, same tool and methodology apply with Spanish national defaults instead of Danish ones (mortality rate, modal share inputs must be re-sourced from Spanish equivalents — INE / DGT for modal share, similar to how DTU Transport Survey was used here) |

---

## 3. CRS & projection notes for Spain

- Processed outputs currently standardize on **EPSG:25832** (ETRS89/UTM32N, correct for Denmark). For Spain, the correct ETRS89/UTM zone depends on longitude of the study city:
  - Most of mainland Spain (including Madrid): **EPSG:25830**
  - Galicia and western Spain: **EPSG:25829**
  - Catalonia, Balearics, eastern Spain: **EPSG:25831**
  - Canary Islands: **EPSG:25828** (REGCAN95 / UTM 28N is also common there — verify local convention)
- Web exports remain **EPSG:4326 (WGS84)** — unchanged, this is a universal rule not a Danish-specific one.
- GraphML routing graphs stay in WGS84 for osmnx/CitySeer compatibility — unchanged.

---

## 4. What is genuinely portable vs. what needs rebuilding

**Portable as-is (parameter/URL swap only):**
- Pedestrian network download + CitySeer graph construction
- B(d)/B(t) health benefit curve math and the four demographic groups' walking-speed literature basis (Bohannon/Lusardi/Plaut are not Denmark-specific — though a Spain team may want to check if Spanish-population-specific walking speed literature exists and is preferred)
- Candidate-segment filtering logic (bus-route buffer intersection)
- Scoring script (`score_bus_routes.py`) — takes segments + population points as input, doesn't care about country
- Web export format and MapLibre/Scrollama front end
- GTFS route-type mode classification

**Needs a genuine rebuild per new source schema:**
- `integrate_buildings.py` — currently written around BBR ↔ DAR ↔ INSPIRE three-way join; Catastro's more unified schema means this script should get *simpler*, not just re-pointed, since footprint + attributes + address arrive from one family of services
- `integrate_population_typology.py` — recalibrate priors against INE data; may not need the same low/mid/high pycnophylactic perturbation if INE section-tract age data is already fine-grained enough
- The entrance-point quality filter (DAR TD/TK equivalent) — needs new empirical validation against whatever Catastro/INE address geometry convention Spain uses
- `add_frederiksberg*.py` equivalents — these exist here only because Nørrebro's study buffer crosses a municipal boundary (Frederiksberg) with a different data regime; whether Spain needs an analogous "crosses admin boundary" patch depends entirely on the chosen study area's geography

**Needs new discovery work per target city (no single national source):**
- Cycling infrastructure layer
- Parks/green space layer
- Bus/metro/rail GTFS feed (check NAP España first)

---

## 5. Recommended first steps for the Spain team

1. **Pick the target Spanish city/district** and confirm its UTM zone (25829/25830/25831).
2. **Confirm Catastro INSPIRE service coverage** for that municipality (ATOM feed vs. Sede Electrónica descriptive extract) and sample a handful of building records to check which of the BBR-equivalent fields (use, floors, year, area) are actually populated — coverage/completeness can vary by province.
3. **Confirm INE section-tract (`sección censal`) boundaries and age-band population tables** are available for the target area at the resolution needed for the B(d) model's four demographic groups.
4. **Check NAP España** (`nap.transportes.gob.es`) for a GTFS feed covering the target city before assuming a per-operator scrape is needed.
5. Re-run `docs/data_catalogue.md`-equivalent documentation once real Spanish sample data is in hand — record counts, field completeness %, and any code-list translations (Catastro `uso` codes, etc.) the same way this project documents BBR use codes.
