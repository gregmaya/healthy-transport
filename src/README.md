# Source Code

Reusable Python modules for the Nørrebro analysis project.

## Structure

```
src/
├── __init__.py
├── data/
│   ├── __init__.py
│   ├── loaders.py       # Functions to load data from raw/processed
│   ├── processors.py    # Data cleaning and transformation
│   └── validators.py    # Data quality checks
├── analysis/
│   ├── __init__.py
│   ├── network.py       # Network analysis (shortest paths)
│   ├── accessibility.py # Accessibility calculations
│   └── spatial.py       # Spatial operations and joins
├── health/
│   ├── __init__.py
│   └── metrics.py       # Health indicator calculations
└── utils/
    ├── __init__.py
    ├── geo.py           # GIS utilities (CRS, geometry operations)
    └── config.py        # Configuration and constants
```

## Guidelines

1. **Modular**: Each module should have a single, clear purpose
2. **Documented**: Use docstrings (Google or NumPy style)
3. **Tested**: Write unit tests in `tests/` directory
4. **Type hints**: Use type annotations for function signatures
5. **Dependencies**: Keep imports minimal and explicit

## Example

```python
from src.data.loaders import load_buildings
from src.analysis.accessibility import calculate_distance_to_parks

buildings = load_buildings('processed')
distances = calculate_distance_to_parks(buildings, parks)
```

## Development

- Run tests: `pytest tests/`
- Code style: Follow PEP 8
- Format: Use `black` or `ruff`
- Lint: Use `ruff` or `pylint`
