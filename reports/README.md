# Reports

Analysis outputs, visualizations, and final reports.

## Structure

```
reports/
├── figures/          # Charts, maps, plots
├── tables/           # Summary statistics, data tables
└── final/            # Final reports and presentations
```

## Naming Convention

Include date and descriptive name:
```
20260210_accessibility_analysis.pdf
20260210_building_density_map.png
population_by_building_summary.csv
```

## Guidelines

1. **Reproducible**: Generated programmatically from code
2. **Documented**: Include figure captions and data sources
3. **Version controlled**: Small files (< 1MB) can be committed
4. **High quality**: Use publication-ready formats (PNG 300dpi, PDF)

## Figure Standards

- **Maps**: Include north arrow, scale bar, legend, data source
- **Charts**: Clear labels, titles, data source footnote
- **Format**: PNG (raster), PDF (vector)
- **Resolution**: 300 DPI minimum for print

## Export from Notebooks

```python
import matplotlib.pyplot as plt

fig.savefig('reports/figures/20260210_accessibility_map.png',
            dpi=300, bbox_inches='tight')
```
