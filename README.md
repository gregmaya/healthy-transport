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
│   │   ├── buildings/    # Building footprints, entrances, land use
│   │   ├── roads/        # Road centre lines
│   │   ├── cycling/      # Cycle paths and routes
│   │   ├── population/   # Population and demographics
│   │   ├── health/       # Health metrics
│   │   ├── transport/    # Bus, metro, train stops
│   │   ├── greenspaces/  # Parks and open spaces
│   │   └── boundary/     # Nørrebro boundary
│   └── processed/        # Cleaned and processed data (NOT in version control)
├── notebooks/            # Jupyter notebooks for exploration and visualization
├── src/                  # Source code modules
├── scripts/              # Utility scripts for data processing
├── tests/                # Unit tests
├── docs/                 # Documentation
├── reports/              # Analysis outputs, figures, final reports
└── requirements.txt      # Python dependencies
```

## Data Storage

- **Format**: GeoPackage (.gpkg) for geospatial data
- **CRS**: EPSG:25832 (ETRS89 / UTM zone 32N - Denmark standard)
- **Version Control**: Data files are excluded from Git (see .gitignore)

## Workflow

1. Follow the checklist in `CLAUDE.MD`
2. Download raw data to `data/raw/[category]/`
3. Explore in QGIS before proceeding to next category
4. Process and save to `data/processed/`
5. Document findings in notebooks

## Key Data Sources

- [Dataforsyningen (SDFI)](https://dataforsyningen.dk/) - Official Danish geographic data
- [Open Data DK](https://www.opendata.dk/) - National open data portal
- [Statistics Denmark](https://www.dst.dk/) - Population and demographics
- [Copenhagen Municipality](https://data.kk.dk/) - City open data
- OpenStreetMap Denmark

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Review CLAUDE.MD for detailed workflow
3. Begin with Section 1: Building Footprints

## License

[MIT License](LICENSE)
Copyright (c) 2026 Greg Maya
