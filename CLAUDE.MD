# Nørrebro Healthy Transport — AI Instructions

Multi-outcome urban health analysis for Nørrebro, Copenhagen. Four parallel analysis tracks — **Bus Stops**, **Rail**, **Cycling**, **Green Spaces** — each with a scrollytelling narrative sharing one persistent MapLibre map. All tracks expose a two-mode scoring toggle: **Baseline** (pure network geometry, working-age B(d) curve, equal node weight, no population weighting) vs **Contextual** (demographic-weighted by actual residents, with low/mid/high uncertainty bands).

> **Before making any structural changes to the pipeline or output layers, read [`docs/REORIENTATION_BRIEF.md`](docs/REORIENTATION_BRIEF.md).**

> **Before every `git commit`**: update both `PROGRESS.md` and `CLAUDE.MD` to reflect the current project state. A `.git/hooks/pre-commit` hook enforces this by blocking commits where neither file is staged.

---

## Binding Design Decisions

These constraints are non-negotiable and must be respected in all pipeline and front-end work:

1. **Candidate segments are those lying on bus routes only** — not every segment in the network. Filter to segments within a 15m buffer of GTFS bus route lines before scoring. This is both computationally efficient and conceptually correct: a bus stop can only exist where a bus runs.

2. **Existing stop locations are a benchmark, not an input** — they are never used to compute scores. The scoring model asks: *"if a stop were placed at this segment, how much health benefit would it generate?"* Existing stops are overlaid afterwards to reveal where current provision aligns with or diverges from the high-scoring zones.

3. **Primary output layer is scored bus-route segments** — not address points or building footprints. Address point scores are an intermediate calculation only. The intervention space for the tool's audience (planners, designers, policy makers) is the public realm.

4. **Health benefit model uses population-differentiated curves** — one curve per demographic group (working-age adults 18–64, elderly 65+, children under 15, reduced mobility). The output is a *range* of optimal stop locations, not a single point.

5. **Web app structure is four-tab scrollytelling → interactive GIS tool** — tabs: Bus Stops / Rail / Cycling / Green Spaces. Each tab is a self-contained scrollytelling narrative built with MapLibre GL JS and Scrollama, sharing one persistent map canvas.

6. **Network distance, not Euclidean** — all distance calculations use graph shortest-path distance through the pedestrian network. Crow-flies distance is never used for scoring.

7. **Two scoring modes — Baseline and Contextual** — Baseline uses the working-age B(d) curve with equal weight per network node (no population count; represents geometric quality of a location). Contextual uses B(d) × age-disaggregated population from `entrances_demographics` with three scenarios (low/mid/high). Both modes are available on all tracks. The toggle is in every interactive panel. The Contextual uncertainty band must be displayed: a scenario rail `[ Low · Mid · High ]` and a popup showing the score range.

8. **Rail tab scores existing entrances only** — no candidate segment analysis along rail routes (unlike bus). Origin = actual entrance location per existing stop. Output: one scored point per entrance. Both Baseline and Contextual modes apply.

9. **Cycling tab is a placeholder** — methodology TBD. Tab structure exists in the UI; no scoring pipeline is defined yet.

10. **Green Spaces scores are on 20m network segments** — consistent with the bus output layer. For each segment midpoint: network distance to nearest park polygon + nearest playground. Score = B(d) × population per segment (Baseline + Contextual).

11. **Interactive tool defaults** — on entering the interactive panel, the interior filter is applied silently (only well-covered segments shown; no toggle exposed to the user). The "Bus stops" overlay is ON by default. The score mode defaults to Baseline. Overlays for Parks, Demographics (neighbourhood), and Demographics (buildings) are present as disabled placeholders.

---

## Data Pipeline Convention

All pipelines follow this sequence:

1. **Download** raw data as-is → store in `data/raw/<category>/`
2. **Process** in a separate script → clip to boundary, translate Danish → English field names, combine related datasets into layers of a single GeoPackage → save to `data/processed/`
3. **Integrate** — join/combine processed datasets (spatial joins, population interpolation) → save to `data/integrated/`
4. **Score** — compute segment-level health benefit scores → save to `data/integrated/` → export to `data/web/`
5. **Explore** in notebooks or QGIS for validation at each stage

Translation happens only in processing scripts — raw data keeps original Danish field names. Related datasets become layers in one GeoPackage (e.g. parks + playgrounds → `norrebro_greenspaces.gpkg`).

**Integration approach**: Use left joins throughout. Inspect unmatched rows in notebooks before deciding how to handle them. Explore in notebooks first, convert to scripts once the approach is validated.

---

## Current Data Model

All outputs are EPSG:25832 unless noted. Paths defined in `src/utils/config.py`.

### Processed (`data/processed/`)

| File | Layers / Content |
|---|---|
| `norrebro_boundary.gpkg` | `norrebro_boundary`: district outline · `neighbourhoods`: 5 sub-neighbourhood polygons |
| `norrebro_buildings.gpkg` | `buildings`: 3,440 BBR points (14 translated cols + 4 derived) · `entrances`: 5,643 DAR points (TD/TK only) |
| `norrebro_building_footprints.gpkg` | INSPIRE polygons clipped to Nørrebro |
| `norrebro_pedestrian_network.gpkg` | `nodes` + `edges` (flat geometry for QGIS) |
| `norrebro_pedestrian_network.graphml` | Graph topology for routing (WGS84, in `data/raw/network/`) |
| `norrebro_transport_stops.gpkg` | `stops`: 2,687 (bus/metro/train) · `routes`: 181 GPS-traced lines |
| `norrebro_cycling.gpkg` | `cykeldata`: 3,638 cycling network lines (citywide) · `cykelstativ`: 1,664 bike parking points |
| `norrebro_greenspaces.gpkg` | `parks`: 77 polygons · `playgrounds`: 34 points |
| `norrebro_neighbourhoods_population.csv` | 5 sub-neighbourhoods, age group breakdowns |
| `norrebro_neighbourhoods_dwellings.csv` | Dwelling types and household sizes |
| `heat_inputs.json` | All WHO HEAT web tool input parameters |
| `health_survey_by_age.csv` | 126 rows (7 indicators x age x gender) |
| `health_survey_by_municipality.csv` | 174 rows (6 indicators x 29 municipalities) |
| `health_causes_of_death.csv` | 25,920 rows (DODA1 translated) |
| `health_deaths_by_municipality.csv` | 12,120 rows (FOD207 translated) |

### Integrated (`data/integrated/`)

| File | Layers / Content |
|---|---|
| `norrebro_buildings.gpkg` | `buildings`: 5,915 INSPIRE footprint polygons with BBR attributes + KNN estimates + `attributes_source` flag (bbr/estimated/unmatched) · `entrances`: 11,367 DAR points with linked BBR attributes + `entrance_source` flag (spatial_join/nearest) · `entrances_demographics`: 11,367 entrance points + 18 population columns (5 age groups × low/mid/high scenarios + totals) + `dwelling_typology` / `dominant_group` |

### Scored (`data/integrated/` → export to `data/web/`)

| File | Content | Status |
|---|---|---|
| `norrebro_bus_segments_scored.geojson` | 1,699 bus-route segments (GTFS geometry, ≤20m), mid-scenario scores + `score_baseline` + `interior` flag (WGS84, 946 KB) | ✅ exists |
| `norrebro_boundary.geojson` | District boundary (WGS84, 16 KB) | ✅ exists |
| `norrebro_stops.geojson` | 552 bus stops benchmark layer with all `score_*` columns (WGS84, 332 KB) | ✅ exists |
| `norrebro_bus_routes_context.geojson` | 68 dissolved GTFS bus route geometries for context display (WGS84, 149 KB) | ✅ exists |
| `norrebro_demographics.geojson` | 10,175 entrance points for demographics heatmap; includes low/high/unc_pct columns (WGS84, 7.7 MB) | ✅ exists |
| `norrebro_neighbourhoods.geojson` | 5 sub-neighbourhood polygons (WGS84, 33 KB) — exported but not used in frontend | ✅ exists |
| `norrebro_bus_segments_scored.gpkg` | Same segments as GeoJSON, GeoPackage format for QGIS | Not yet — pending edge-artifact decision |
| `norrebro_rail_stops_scored.geojson` | One scored point per metro/train entrance (Baseline + Contextual) | Not yet — blocked on data source |
| `norrebro_greenspace_access.geojson` | 20m segments scored by network distance to parks/playgrounds | Not yet |

**Score column naming convention** (all scored layers):
- `score_{group}_baseline` — working-age B(d) curve, equal node weight, no demographics
- `score_{group}_low` / `_mid` / `_high` — Contextual, three demographic scenarios
- `score_{group}_mid_share` — Contextual mid normalised to local population within d_max
- `score_aggregate_mid` — equal-weighted mean of three group share scores

---

## Routing & Network Analysis

### Library: CitySeer

- **CitySeer** is used for network setup, graph construction, and node/edge preparation:

```python
from cityseer.tools import io, graphs
G = io.osm_graph_from_poly(boundary_polygon, to_crs_code=25832)
G = graphs.nx_remove_dangling_nodes(G)
G = graphs.nx_consolidate_nodes(G)
nodes_gdf, edges_gdf, network_structure = io.network_structure_from_nx(G)
```

- **CitySeer** is used for both network setup and the segment scoring loop — computing shortest-path distances from each segment midpoint to all address points within 1,500m. CitySeer is chosen over NetworkX for its performance and its native support for urban network analysis.

The existing osmnx GraphML + GeoPackage remain valid for QGIS visualisation only.

---

## Health Benefit Model

### B(d) Function

Scoring applies only to **candidate segments** — those lying on bus routes. For each candidate segment, health benefit is computed as:

```
score = Σ [ B(d_i) × population_i ]   for all address points i within 1,500m
```

Where `d_i` is the network distance from the segment midpoint to address point `i`, and `B(d)` is the population-group-specific benefit curve.

**Candidate segment filter:** intersect the 20m pedestrian network with a 15m buffer around GTFS bus route lines. Only matching segments enter the scoring loop. Existing bus stop locations play no role in this computation — they are a comparison layer only.

### Population Segment Parameters

| Segment | Peak Zone | Zero Beyond | Notes |
|---|---|---|---|
| Working-age adults (18–64) | 400–700m | ~1,200m | Widest curve. Highest cardiovascular benefit per trip. |
| Elderly (65+) | 200–400m | ~700m | Curve shifts left. Deterrence rises sharply beyond 500m. |
| Children (under 15) | 150–350m | ~600m | Safety quality dominates. Habit-formation benefit. |
| Reduced mobility | 0–200m | ~350m | Very narrow. Most transit-dependent group. |

### Curve Shape

Each curve is a modified Gaussian / beta distribution with three zones:
- **Ramp-up** (0–150m): benefit rises from near-zero
- **Peak plateau** (150m to group peak): aligns with WHO 10-min walk target
- **Decay** (peak to zero threshold): deterrence rises, self-selection dominates

Three parameters are exposed as interactive sliders in the web tool: peak distance, decay steepness, zero-benefit threshold.

### Key Literature

- Lars Bo Andersen et al. — Danish active travel dose-response and all-cause mortality
- WHO Global Action Plan on Physical Activity 2018–2030
- Besser & Dannenberg (2005); Lachapelle & Frank (2009) — walk-to-transit distributions

---

## Critical Analysis Rules

These non-obvious rules affect code correctness — follow them always:

1. **DAR entrance filtering**: Always filter `oprindelse_tekniskStandard IN ('TD', 'TK')`. Never use V0 road-based points as building entrances.
2. **Network formats**: GraphML (raw/) is for routing via networkx/osmnx/CitySeer. GeoPackage (processed/) is for QGIS only — it has no graph topology.
3. **CRS**: All processed outputs must be EPSG:25832. GraphML stays WGS84 for osmnx compatibility. Web exports (GeoJSON) must be WGS84.
4. **Cycling layer**: Use `cykeldata` (one line per street) for proximity analysis, not `cykelsti` (duplicates per side of street).
5. **Walking speed**: 1.4 m/s baseline is a population average. Must be recalculated per demographic group at analysis time.
6. **Health data granularity**: Municipality level (all of København) is the finest publicly available. Sub-municipal data requires formal application.
7. **Spatial join strategy**: BBR → INSPIRE footprints via spatial join. DAR entrance points need a 2m buffer on footprints (doors fall just outside polygon edges).
8. **Candidate segments are bus-route segments only** — always filter the pedestrian network to segments within 15m of GTFS bus route lines before running the scoring loop. Never score the full network.
9. **Existing stop locations are never scoring inputs** — they are a benchmark overlay applied after scoring to compare current provision against optimal zones. Using existing stops as inputs would merely evaluate the status quo rather than identify improvements.
10. **Age-disaggregated population**: If address-level age data is unavailable, apply census-zone age distributions as weights. This assumption must be flagged clearly in the tool UI and in any output documentation.

---

## Narrative Framework

The scrollytelling narrative connects infrastructure to health prevention across two levels:

### Top-down health context (data already collected)
1. **National context** (DODA1): Heart disease and diabetes are leading causes of death — both preventable through physical activity
2. **Copenhagen burden** (eSundhed): Municipality-level chronic disease prevalence
3. **Lifestyle factors** (Danskernes Sundhed): Physical activity and BMI by age group
4. **Economic valuation** (WHO HEAT): Economic health benefit of increased walking/cycling

### Four-tab structure

Each tab is a self-contained scrollytelling narrative (4–6 steps) that hands off to an interactive map panel. Tabs share one MapLibre map canvas.

| Tab | Status | Narrative theme |
|---|---|---|
| Bus Stops | Active | Optimal placement; scoring candidate segments; gap analysis vs current provision |
| Rail | Placeholder | Quality assessment of existing metro/train entrances |
| Cycling | Placeholder | Infrastructure gap analysis (methodology TBD) |
| Green Spaces | Placeholder | Network-segment accessibility to parks/playgrounds |

### Bus Stops scrollytelling arc (6 steps — implemented)
| Step | Title | Map State |
|---|---|---|
| 1 | The hidden cost of bad stop placement | Nørrebro overview, existing stops shown |
| 2 | Walking is medicine | Zoom to residential block; animate catchment ring |
| 3 | The sweet spot is a range, not a point | Family of population curves animating over the map |
| 4 | Scoring the streets | Segment scoring layer fades in across the district |
| 5 | Where the current network leaves gaps | Existing stops overlay; highlight gap areas |
| 6 | Explore it yourself | Full interactive tool loads |

---

## Immediate Next Steps

1. **Resolve edge-artifact problem** — 84.8% of bus-route segments are within 80m of the district boundary (truncated catchments). Options: (a) extend scoring boundary by ~200m and clip back; (b) use `interior=True` filter for published layer; (c) document as limitation with UI flag. Decision gates low/high scenario export.
2. **Extend bus scoring to low/high Contextual** — `score_baseline` is done; expand `SCENARIOS = ("low", "mid", "high")` in notebook 11; wire scenario rail in frontend to `score_{group}_{scenario}` columns.
3. **Implement map scroll transition functions** — `showCatchmentRing`, `showBenefitCurves`, `showScoredNetwork`, `showGapAnalysis` are currently stubs; implement with `map.flyTo` / layer opacity / data animations.
4. **Segment hover/click popup** — show mid score + [low, high] range for the active demographic group in interactive mode.
5. **Find accurate rail entrance data** — evaluate Rejseplanen, DSB open data, or OpenStreetMap for metro/train entrance geometries more precise than GTFS stop centroids.
6. **Wire neighbourhood dropdown to map** — `#neighbourhood-select` updates population bars (done); needs `map.fitBounds()` + polygon highlight when demographics overlay is on.
7. **Replace population dummy data** — demographic bars use hardcoded estimates; replace with real age-group percentages from `norrebro_neighbourhoods_population.csv` once frontend data pipeline is extended.

---

## Reference Documents

- [PROGRESS.md](PROGRESS.md) — project checklist and phase status
- [docs/REORIENTATION_BRIEF.md](docs/REORIENTATION_BRIEF.md) — strategic decisions and rationale
- [docs/data_catalogue.md](docs/data_catalogue.md) — per-dataset attributes, record counts, schemas
- [docs/design_decisions.md](docs/design_decisions.md) — architectural rationale ("why" behind choices)
- [docs/data_sources.md](docs/data_sources.md) — URLs, APIs, credentials, download scripts
- [docs/population_typology_brief.md](docs/population_typology_brief.md) — dwelling-to-population model design
- [docs/health_data_download_guide.md](docs/health_data_download_guide.md) — manual download instructions for health data
- [docs/heat_assessment_inputs.md](docs/heat_assessment_inputs.md) — WHO HEAT web tool cheat sheet
