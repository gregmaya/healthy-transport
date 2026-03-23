_to test locally run_
> bash scripts/dev.sh

Then open http://localhost:8000. The script copies web/ + data/web/*.geojson into a dist/ folder and serves it from there

# Healthy Transport - Nørrebro MVP

Urban health analysis for Copenhagen's Nørrebro neighbourhood integrating multiple official data sources.

## Project Structure

```text
healthy-transport/
├── CLAUDE.MD              # AI instructions and data model
├── PROGRESS.md            # Project checklist and phase status
├── README.md              # This file
├── data/
│   ├── raw/              # Raw downloaded data (NOT in version control)
│   │   ├── buildings/    # Building footprints (INSPIRE)
│   │   ├── bbr/          # BBR building attributes
│   │   ├── dar/          # DAR entrance points
│   │   ├── network/      # Pedestrian network (GraphML)
│   │   ├── cycling/      # Cycle paths and routes
│   │   ├── transport/    # GTFS public transport
│   │   ├── greenspaces/  # Parks and open spaces
│   │   ├── health/       # Health metrics
│   │   └── boundary/     # Nørrebro boundary
│   ├── processed/        # Cleaned per-category data (NOT in version control)
│   └── integrated/       # Joined cross-category datasets (NOT in version control)
├── notebooks/            # Jupyter notebooks for exploration and validation
├── src/                  # Source code modules
├── scripts/
│   ├── download/         # Data download scripts
│   ├── process/          # Per-category processing scripts
│   └── integrate/        # Cross-dataset integration scripts
├── docs/                 # Documentation and design decisions
├── reports/              # Analysis outputs, figures, final reports
└── requirements.txt      # Python dependencies
```

## Data Storage

- **Format**: GeoPackage (.gpkg) for geospatial data, CSV for tabular
- **CRS**: EPSG:25832 (ETRS89 / UTM zone 32N — Denmark standard)
- **Version Control**: Data files are excluded from Git (see .gitignore)
- **Pipeline**: `raw/` → `processed/` → `integrated/` → `web/` (future)

## Workflow

1. **Download** raw data to `data/raw/[category]/`
2. **Process** per category — clip to boundary, translate Danish → English → `data/processed/`
3. **Integrate** — spatial joins across categories → `data/integrated/`
4. **Explore** in notebooks and QGIS at each stage
5. **Analyse** — network accessibility, population modelling (Phase 3)

## Key Data Sources

- [Dataforsyningen (SDFI)](https://dataforsyningen.dk/) - Official Danish geographic data
- [Open Data DK](https://www.opendata.dk/) - National open data portal
- [Statistics Denmark](https://www.dst.dk/) - Population and demographics
- [Copenhagen Municipality](https://data.kk.dk/) - City open data
- OpenStreetMap Denmark

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Review `CLAUDE.MD` for data model and conventions
3. See `PROGRESS.md` for current phase status
4. See `docs/` for design decisions, data catalogue, and source documentation

## License

[MIT License](LICENSE)
Copyright (c) 2026 Greg Maya
