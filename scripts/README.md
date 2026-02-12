# Scripts

Standalone utility scripts for data download and processing.

## Structure

```
scripts/
├── download/          # Fetch raw data from external sources → data/raw/
│   ├── download_bbr_dar.py
│   ├── download_copenhagen_districts.py
│   ├── download_cycling.py
│   ├── download_gtfs.py
│   └── download_pedestrian_network.py
├── process/           # Transform raw data → data/processed/
│   ├── clip_building_footprints.py
│   ├── process_cycling.py
│   └── process_transport_stops.py
└── README.md
```

## Usage

```bash
# Download raw data
python scripts/download/download_cycling.py

# Process into analysis-ready format
python scripts/process/process_cycling.py
```

## Guidelines

1. **Standalone**: Scripts should run independently
2. **Logging**: Include progress and error messages
3. **Config**: Import paths and constants from `src/utils/config.py`
4. **Documentation**: Include docstring with description, outputs, and usage
