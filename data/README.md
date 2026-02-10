# Data Directory

**⚠️ Note**: Data files are excluded from version control. Only this README is tracked.

## Structure

### `raw/`
Contains original, unmodified data as downloaded from sources. Organized by category:
- `buildings/` - Building footprints, entrances, heights, land use
- `roads/` - Road network centre lines
- `cycling/` - Cycle paths and cycle routes
- `population/` - Population counts and demographics
- `health/` - Health metrics and indicators
- `transport/` - Public transport stops (bus, metro, train)
- `greenspaces/` - Parks and open spaces
- `boundary/` - Nørrebro neighbourhood boundary

### `processed/`
Contains cleaned, transformed, and analysis-ready datasets:
- Clipped to Nørrebro boundary
- Standardized CRS (EPSG:25832)
- Quality validated
- Integrated datasets ready for analysis

## Data Format

- **Primary**: GeoPackage (.gpkg) for geospatial data
- **Tabular**: CSV, Parquet for non-spatial data
- **CRS**: EPSG:25832 (ETRS89 / UTM zone 32N)

## Workflow

1. Download data → `raw/[category]/`
2. Document source, date, metadata
3. Explore in QGIS
4. Process and validate
5. Save to `processed/`
6. Document processing steps in notebooks

## File Naming Convention

- Raw: `[source]_[dataset]_[date].[ext]`
  - Example: `sdfi_bygninger_20260210.gpkg`
- Processed: `norrebro_[category].[ext]`
  - Example: `norrebro_buildings.gpkg`
