# Design Decisions

Architectural rationale for non-obvious choices. For dataset details, see [data_catalogue.md](data_catalogue.md).

---

## Pedestrian Network: Two Output Formats

The network is saved in both GraphML and GeoPackage because they serve fundamentally different purposes:

- **GraphML** (`data/raw/network/`, WGS84): Preserves graph topology — which nodes connect to which edges, with weights (distance, travel time). Required for routing algorithms (shortest path, isochrones) via `networkx`/`osmnx`. GeoPackage cannot represent graph topology.
- **GeoPackage** (`data/processed/`, EPSG:25832): Flat geometry layers (points + lines) for QGIS visualization. Same data, different representation. QGIS cannot open GraphML files.

## Network Type: `all` Instead of Mode-Specific

`osmnx.graph_from_polygon(network_type='all')` downloads every OSM highway type (roads, footways, cycleways, paths). Mode-specific filtering (e.g. walking-only, cycling-only) is deferred to analysis time. This keeps the raw download flexible for both walking and cycling analyses without re-downloading.

## 800m Network Buffer

The network extends 800m beyond Norrebro boundary (`NETWORK_BUFFER_M = MAX_WALK_DISTANCE`). Without this, routing would dead-end at the boundary, making it impossible to calculate travel times to facilities just outside the study area. `truncate_by_edge=True` keeps complete edges that cross the boundary polygon, preventing artificial network breaks.

## Walking Travel Time Baseline

Pre-computed on each edge as `length / 1.4 m/s`. Uses constant pedestrian speed rather than OSM `maxspeed` tags (which are for vehicles). The 1.4 m/s is a population-average placeholder. At analysis time, travel times must be recalculated per demographic group — older adults, children, and mobility-impaired populations walk at significantly different speeds, which directly affects accessibility results and health benefit estimates.

## Cycling Layer: `cykeldata` over `cykelsti`

The `cykelsti` layer maps each side of a street separately (two lines where cycle lanes exist on both sides), creating duplicates in proximity/counting analysis. `cykeldata` represents one line per street with a `kategori` field to distinguish infrastructure types. Cleaner for measuring distance from building entrances to cycling infrastructure.

## GTFS: `shapes.txt` for Route Geometries

GTFS provides two ways to represent route paths:
- **`shapes.txt`** (what we use): Actual GPS traces along roads — high-resolution polylines following real route paths.
- **Stop-to-stop lines** (rejected): Straight lines connecting consecutive stops. Schematic and misleading on a map.

## GTFS: Early Spatial Filtering

The national GTFS feed is large (3.97M stop_times rows). Processing filters spatially first to avoid joining the full dataset:

1. Filter stops to 10 km buffer (36,800 → 2,677)
2. Filter stop_times to matching stop_ids (54% reduction: 3.97M → 1.82M)
3. Filter shapes to those intersecting buffer (6,860 → 734)
4. Then perform the joins

## GTFS: Mode Classification Chain

Stops don't have a transport mode directly. The join chain is:
`routes.txt` (has `route_type`) → `trips.txt` → `stop_times.txt` → `stops.txt`

Route types: bus=3, metro=1, train=2. Extended GTFS types (100-199, 400-499, 700-799) also handled.

## Transport Buffer: 10 km (vs 800m for Other Datasets)

Transit context is regional — bus routes, train lines, and metro connections extend far beyond Norrebro. The 10 km buffer (`TRANSPORT_BUFFER_M`) captures the broader transit network that residents actually use, while the 800m buffer for parks/cycling/buildings focuses on walkable proximity.

## BBR-DAR Joining Strategy

**Spatial join via INSPIRE footprints** is the recommended approach: BBR points fall within footprints, DAR entrance points are at doors.

- **DAR → Footprints**: Entrance points (TD) sometimes fall just outside polygon edges (they're at the door). A **2m buffer** on footprints improves match rate.
- **One-to-many**: Apartment buildings typically have multiple DAR entrances per footprint.
- **UUID linking** (BBR `husnummer` → national Husnummer entity → DAR): Requires 620 MB download. **Deferred** — spatial join via footprints is sufficient for current analysis. Explored in notebook `02b_buildings_processed.ipynb`.

## DAR Entrance Point Filtering

The DAR dataset contains ~50% road-based points (V0) and ~50% building entrance points (TD). For routing and accessibility analysis, always filter by `oprindelse_tekniskStandard`:

- **Use**: TD (entrance doors) + TK (building facade) = 5,643 points
- **Exclude**: V0-V9 (road points, 6,072), UF (provisional), TA (facilities without buildings)

A spatial join without filtering would incorrectly assign road-based points as building entrances.

## Health Data: Municipality-Level Granularity

Municipality level (all of Kobenhavn = 0101) is the finest publicly available health data. Sub-municipal data (Norrebro-specific) exists in underlying registers but requires:
1. Formal application to Region Hovedstaden or Sundhedsdatastyrelsen
2. Data Protection Authority approval
3. Institutional affiliation

The resolution gap itself is part of the project narrative — urban design decisions need granular data that doesn't exist publicly. Future path: apply via OsloMet credentials.
