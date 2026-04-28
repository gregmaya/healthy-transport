_To run locally:_
> bash scripts/dev.sh

Then open http://localhost:8000. The script copies `web/` + `data/web/*.geojson` into a `dist/` folder and serves it from there.

# Healthy Transport — Nørrebro

Urban health analysis for Copenhagen's Nørrebro neighbourhood. Quantifies the health benefit of public transport infrastructure using network accessibility scoring and demographic-weighted population models.

## What it does

A scrollytelling web tool with four analysis tracks (Bus Stops, Rail, Cycling, Green Spaces), each handing off to an interactive GIS panel. One persistent MapLibre GL JS map canvas underlies all tabs.

**Two scoring modes** (toggle in every panel):

| Mode | What it measures |
|------|-----------------|
| **Catchment Score** | Pure network geometry — how much street network is reachable from a stop location, weighted by an exponential decay curve. No population data. |
| **Health Score** | Demographic-weighted benefit — catchment reach × age-specific B(d) dose-response curve × actual resident population (low / mid / high uncertainty scenarios). |

**Bus Stops tab (active):** Scores all 20m pedestrian network segments that lie on bus routes. Shows where current stop provision aligns with or diverges from high-scoring zones.

**Rail, Cycling, Green Spaces tabs:** Placeholder structure implemented; scoring pipelines pending.

## People + Green panel

Right panel shows population and green-space access metrics for the selected area:

- **Headline row** — census total for the selected demographic group (district or neighbourhood), plus population-weighted avg time in green space (format: `1:30'`)
- **Stop detail row** — per-stop catchment population for the selected group ± uncertainty from low/high scenarios, shown with grey background when a stop is selected
- **Per-group rows** (Children / Working Age / Elderly) — demographic share bar with district comparison marker when neighbourhood selected, avg catchment reach ± half-range, group-specific green time

## Project structure

```text
healthy-transport/
├── CLAUDE.MD              # AI instructions, data model, binding decisions
├── PROGRESS.md            # Project checklist and phase status
├── README.md              # This file
├── data/
│   ├── raw/               # Raw downloaded data (NOT in version control)
│   ├── processed/         # Cleaned per-category GeoPackages (NOT in version control)
│   ├── integrated/        # Cross-dataset joined layers (NOT in version control)
│   └── web/               # GeoJSON exports served to the browser
├── web/
│   ├── index.html
│   ├── js/
│   │   ├── map.js         # MapLibre init, score mode, layer management
│   │   ├── scroll.js      # Scrollytelling, interactive panel, _updatePeopleGreen
│   │   ├── scatter.js     # Scatter plot and distribution histogram
│   │   ├── state.js       # Shared scroll/selection state
│   │   └── config.js      # Data paths, palette, DISTRICT_POP, NEIGHBOURHOOD_POP
│   └── css/style.css      # Geometric Minimal+ design system
├── scripts/
│   ├── download/          # Data download scripts
│   ├── process/           # Per-category processing scripts
│   ├── integrate/         # Cross-dataset integration scripts
│   ├── score/             # Segment scoring pipeline
│   └── web/               # GeoJSON export + scatter SVG generation
├── src/utils/config.py    # All path constants and analysis parameters
├── notebooks/             # Jupyter notebooks for exploration and validation
└── docs/                  # Design decisions, data catalogue, source documentation
```

## Data pipeline

```
raw/ → processed/ → integrated/ → scored → data/web/ → browser
```

1. **Download** raw data to `data/raw/[category]/`
2. **Process** — clip to boundary, translate Danish → English field names → `data/processed/`
3. **Integrate** — spatial joins, population typology model → `data/integrated/`
4. **Score** — CitySeer network shortest-path scoring per 20m segment → `data/integrated/`
5. **Export** — GeoJSON for browser, scatter SVG for narrative → `data/web/`

If the scoring pipeline reruns, regenerate the narrative SVG:
```bash
python3 scripts/web/generate_scatter_svg.py
```

## Key data sources

- [Dataforsyningen (SDFI)](https://dataforsyningen.dk/) — INSPIRE building footprints, DAR entrances, boundary
- [Open Data DK](https://www.opendata.dk/) — GTFS public transport, BBR building register
- [Statistics Denmark](https://www.dst.dk/) — Population by age and sub-district
- [Copenhagen Municipality](https://data.kk.dk/) — Cycling infrastructure, green spaces
- OpenStreetMap — Pedestrian network (via osmnx/CitySeer)

## Design system

`web/css/style.css` uses **Geometric Minimal+**:
- Fonts: Outfit (headings) · Work Sans (body) · Space Mono (labels)
- Data-viz colours: `--blue-2/3/4` and `--accent (#ff6700)` only
- UI chrome: neutral variables only — no blue tints

## Reference docs

- [`CLAUDE.MD`](CLAUDE.MD) — binding decisions, data model, score column conventions
- [`PROGRESS.md`](PROGRESS.md) — current phase status and ordered task list
- [`docs/design_decisions.md`](docs/design_decisions.md) — architectural rationale
- [`docs/data_catalogue.md`](docs/data_catalogue.md) — per-dataset schemas and record counts
- [`docs/data_sources.md`](docs/data_sources.md) — download URLs and credentials

## License

[MIT License](LICENSE) — Copyright (c) 2026 Greg Maya
