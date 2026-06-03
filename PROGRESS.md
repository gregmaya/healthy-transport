# Progress Tracker

Last updated: 2026-05-11

---

## Phases Ahead

Prune as phases complete.

### Phase 3b — Rail *(blocked on data)*

Download and process official station geometry from the Copenhagen Municipality WFS (`k101:station_oversigtskort`, same endpoint as parks/cycling, no credentials required):

1. **Download** — `scripts/download/download_rail_stations.py`
   - Source: `https://wfs-kbhkort.kk.dk/k101/ows`, layer `k101:station_oversigtskort`
   - Fetch all 133 station points (45 Metrostation, 80 S-station, 8 Anden station)
   - Fields: `id`, `objekt_type`, `navn`, `kommune`
   - Output: `data/raw/transport/rail_stations_kk.geojson` (WGS84)

2. **Process** — `scripts/process/process_rail_stations.py`
   - Reproject to EPSG:25832
   - Clip to 2km buffer around Nørrebro boundary
   - Add `mode` column derived from `objekt_type`: `metro` / `s-tog` / `other`
   - Output: `data/processed/norrebro_rail_stations.gpkg`, layer `stations`
   - Validate in QGIS: overlay on basemap, confirm points sit at correct station locations

3. **Score** — new script `scripts/score/score_rail_stations.py`
   - Origin = station point (one score per station)
   - Same CitySeer B(d) pipeline as bus, same `entrances_demographics` population source
   - Same score columns: `score_catchment`, `score_health_working_age`, `score_health_elderly`, `score_health_children`, `score_health_combined`
   - Note: no candidate-segment filtering (rail line geometry is irrelevant — we score where stations already are)
   - Output: `data/integrated/norrebro_rail_stations_scored.gpkg`

4. **Export** — `scripts/web/export_rail_stations.py`
   - Convert to WGS84 GeoJSON
   - Output: `data/web/norrebro_rail_stops_scored.geojson`

5. **Wire to frontend** — implement `showRailPlaceholder` map functions in `map.js` following the bus pattern; set `ready: true` for the rail tab in `config.js`

---

### Phase 3c — Cycling *(methodology TBD — placeholder)*

---

### Phase 3d — Green Spaces tab

- For each 20m segment midpoint: compute network distance to nearest park polygon + nearest playground (`norrebro_greenspaces.gpkg`)
- Score = B(d) × population per segment, Catchment Score + Health Score modes
- Export `data/web/norrebro_greenspace_access.geojson` for Green Spaces tab narrative

---

### Phase 5 — Scrollytelling remaining

- Map transitions: `showCatchmentRing`, `showBenefitCurves` (currently stubs)
- Wire scenario rail to low/high score columns once computed
- UX items:
  - Score mode → clean toggle control (replace pill buttons)
  - Info popup z-index fix (popups greyed out behind opacity layer — must sit above it)
  - Floating narrative cards on full-bleed map for steps 4–6 (cards as overlays, map full viewport)
  - Map tooltip redesign: wide table with population labels as column headers, scores as a single row

---

### Phase 6 — Interactive tool

- Benefit curve parameter sliders (peak distance, decay steepness) — map updates reactively
- Headline walking-minutes metric panel (total daily walking-minutes for current stop configuration)
- Post-MVP: "drop a hypothetical stop" marginal benefit interaction (requires pre-computed lookup grid or backend)

---

### Phase 7 — Hardening

- Performance optimisation (tile loading, render performance)
- Mobile responsiveness
- Accessibility (WCAG AA)
- Final copy editing
- Deploy to GitHub Pages / Netlify; update README with live URL

---

## Technical Notes

- **CRS**: EPSG:25832 for all processed/integrated data; WGS84 for web exports (GeoJSON)
- **File naming**: `norrebro_[category].gpkg`
- **Data tiers**: `raw/` → `processed/` → `integrated/` → `web/`
- **Routing**: CitySeer for all network setup and routing
- **Score columns**: `score_catchment` · `score_health_working_age` · `score_health_elderly` · `score_health_children` · `score_health_combined`
- **Walking speeds**: working_age 1.40 m/s · elderly 0.90 m/s · children 1.00 m/s
- **Meta files**: CLAUDE.md, PROGRESS.md — keep in sync on every commit (enforced by pre-commit hook)
