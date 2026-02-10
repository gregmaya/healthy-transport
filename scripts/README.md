# Scripts

Standalone utility scripts for data processing and automation.

## Purpose

Scripts are for one-time or command-line tasks:
- Data download automation
- Batch processing
- Data format conversions
- Setup and configuration

## Naming Convention

Use descriptive names with action verbs:
```
download_osm_data.py
process_buildings.py
clip_to_boundary.py
export_to_qgis.py
```

## Usage

Scripts should be executable from the command line:

```bash
python scripts/download_osm_data.py --area norrebro --output data/raw/
```

## Guidelines

1. **Standalone**: Scripts should run independently
2. **CLI arguments**: Use `argparse` for parameters
3. **Logging**: Include progress and error messages
4. **Reusable logic**: Import from `src/` modules when possible
5. **Documentation**: Include docstring with usage examples

## Example Structure

```python
"""
Download building data from SDFI Dataforsyningen.

Usage:
    python scripts/download_buildings.py --bbox "12.5,55.6,12.6,55.7"
"""
import argparse
from src.data.loaders import download_sdfi_buildings

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bbox', required=True, help='Bounding box')
    args = parser.parse_args()

    download_sdfi_buildings(args.bbox)

if __name__ == '__main__':
    main()
```
