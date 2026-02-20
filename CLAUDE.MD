# Nørrebro Healthy Transport — AI Instructions

Urban health analysis MVP for Nørrebro, Copenhagen. Integrates official Danish data sources to measure walking/cycling accessibility from buildings to parks, transport, and cycling infrastructure.

## Data Pipeline Convention

All pipelines must follow this sequence:

1. **Download** raw data as-is → store in `data/raw/<category>/`
2. **Process** in a separate script → clip to boundary, translate Danish → English field names, combine related datasets into layers of a single GeoPackage → save to `data/processed/`
3. **Integrate** — join/combine processed datasets (spatial joins, population interpolation) → save to `data/integrated/`
4. **Explore** in notebooks or QGIS for validation at each stage

Translation happens only in processing scripts — raw data keeps original Danish field names. Related datasets become layers in one GeoPackage (e.g. parks + playgrounds → `norrebro_greenspaces.gpkg`).

**Integration approach**: Use left joins throughout. Inspect unmatched rows in notebooks before deciding how to handle them. Explore in notebooks first, convert to scripts once the approach is validated.

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
| `norrebro_buildings.gpkg` | `buildings`: 5,915 INSPIRE footprint polygons with BBR attributes + KNN estimates + `attributes_source` flag (bbr/estimated/unmatched) · `entrances`: 5,725 DAR points with linked BBR attributes + `entrance_source` flag (spatial_join/nearest) |

## Routing & Network Analysis: CitySeer

Use [CitySeer](https://cityseer.benchmarkurbanism.com/) for all routing and accessibility analysis (not osmnx/networkx).

```python
from cityseer.tools import io, graphs
G = io.osm_graph_from_poly(boundary_polygon, to_crs_code=25832)
G = graphs.nx_remove_dangling_nodes(G)
G = graphs.nx_consolidate_nodes(G)
nodes_gdf, edges_gdf, network_structure = io.network_structure_from_nx(G)
```

The existing osmnx GraphML + GeoPackage remain valid for QGIS visualisation only.

## Critical Analysis Rules

These non-obvious rules affect code correctness — follow them always:

1. **DAR entrance filtering**: Always filter `oprindelse_tekniskStandard IN ('TD', 'TK')`. Never use V0 road-based points as building entrances.
2. **Network formats**: GraphML (raw/) is for routing via networkx/osmnx. GeoPackage (processed/) is for QGIS only — it has no graph topology.
3. **CRS**: All processed outputs must be EPSG:25832. GraphML stays WGS84 for osmnx compatibility.
4. **Cycling layer**: Use `cykeldata` (one line per street) for proximity analysis, not `cykelsti` (duplicates per side of street).
5. **Walking speed**: 1.4 m/s baseline is a population average. Must be recalculated per demographic group at analysis time.
6. **Health data granularity**: Municipality level (all of København) is the finest publicly available. Sub-municipal data requires formal application.
7. **Spatial join strategy**: BBR → INSPIRE footprints via spatial join. DAR entrance points need a 2m buffer on footprints (doors fall just outside polygon edges).

## Immediate Next Steps

1. Population typology model — assign age-specific population to residential buildings (see `docs/population_typology_brief.md`)
2. Set up CitySeer network for accessibility analysis (Phase 3)
3. Process eSundhed chronic disease XLSX (deferred — complex multi-sheet format)

## Reference Documents

- [PROGRESS.md](PROGRESS.md) — project checklist and phase status
- [docs/data_catalogue.md](docs/data_catalogue.md) — per-dataset attributes, record counts, schemas
- [docs/design_decisions.md](docs/design_decisions.md) — architectural rationale ("why" behind choices)
- [docs/data_sources.md](docs/data_sources.md) — URLs, APIs, credentials, download scripts
- [docs/population_typology_brief.md](docs/population_typology_brief.md) — dwelling-to-population model design prompt
- [docs/health_data_download_guide.md](docs/health_data_download_guide.md) — manual download instructions for health data
- [docs/heat_assessment_inputs.md](docs/heat_assessment_inputs.md) — WHO HEAT web tool cheat sheet

## Narrative Framework

The health data serves a top-down narrative connecting infrastructure to health prevention:

1. **National context** (DODA1): Heart disease and diabetes are leading causes of death — both preventable through physical activity
2. **Copenhagen burden** (eSundhed): Municipality-level chronic disease prevalence
3. **Lifestyle factors** (Danskernes Sundhed): Physical activity and BMI by age group
4. **Infrastructure connection** (project analysis): Walking/cycling accessibility from buildings to transit, parks, cycling infrastructure
5. **Economic valuation** (WHO HEAT): Economic health benefit of increased walking/cycling
