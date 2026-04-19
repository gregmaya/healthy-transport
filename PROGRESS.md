# Progress Tracker

*Last updated: 2026-04-19*

> This project follows the reorientation decisions documented in
> [`docs/archive/REORIENTATION_BRIEF.md`](docs/archive/REORIENTATION_BRIEF.md).
> Read that file before making any structural changes to the pipeline or output layers.

---

## Strategic Orientation

**Why segments, not addresses** — the intervention space for planners is the public realm. Scored 20m bus-route segments answer "where should the stop go?", not "who lives near it?". Address point scores are an intermediate calculation only. A coloured street network is immediately legible and actionable to a planner in a way that a scored building layer is not.

**Why a range, not a point** — different demographic groups have genuinely different dose-response curves (working-age adults, elderly, children). The output is a band of optimal stop locations differentiated by population group, not a single optimum. This is more honest and more useful as a planning input. It turns the question from "where is the best stop?" to "where is the zone where the most people benefit the most?"

**Why scrollytelling → interactive tool** — the reader must arrive at the map already understanding what they're looking at. Narrative builds context; the interactive tool rewards it. The tool is positioned as public health infrastructure, not just a transport planning aid — framing transit investment in terms of healthcare cost savings and active travel dose-response opens different funding channels and creates a more compelling policy narrative.

*If work deviates from these three principles, stop and question why before proceeding.*

---

## Now

Ordered working list. Delete items when done.

### QA / Validation (one-time)

1. **Phase B data validation** — open `norrebro_bus_segments_scored.geojson` + `norrebro_buildings.gpkg` and answer: (a) Do buffer-zone entrance points have non-null population columns? (b) Do boundary-adjacent segments score visibly higher on `score_health_*` than interior segments of similar geometry? (c) Are there spatial clusters of null or zero scores that shouldn't exist? → Result of (b) determines whether point 2 is needed.

2. **Fix Frederiksberg DAR edge effect** — actioned only if point 1 confirms under-scoring at boundary. The 89 DAR entrance points added by `add_frederiksberg_dar.py` are too sparse relative to actual building density, causing truncated catchments and artificially low scores for boundary-adjacent segments. Fix: supplement entrance density so all three population groups interpolate correctly across the boundary zone.

3. **Correlation check** — compute Pearson r(`score_catchment`, `score_health_combined`) on 552 stops; expect r < 0.8 (if the two modes are nearly identical, population weighting is not adding meaningful differentiation); note result and close.

### Active UI tasks

4. **Score mode naming unification** — rename Baseline → Catchment Score and Contextual → Health Score consistently across all buttons, titles, chart axes, info panels, and tooltips throughout the web app.

5. **Segment hover/click popup** — add interactivity to scored segment lines on the map: on hover/click, show the active score value and group breakdown for that segment. Differs from stop tooltip — no route or stop name; segment-level scores only; must adapt to the active score mode.

6. **Scroll transition stubs** — implement `showCatchmentRing` and `showBenefitCurves` (currently stubs); `showScoredNetwork` and `showGapAnalysis` already use `fitBounds(NORREBRO_BOUNDS)`.

### MVP completeness block *(ship together)*

7. **Green Paths pipeline** — for each bus-route segment: compute the length of the segment falling within green area polygons (`norrebro_greenspaces.gpkg`); use cityseer `compute_stats` to derive total path length and green path length per stop; apply per-group walking speeds (working_age 1.40 m/s, elderly 0.90 m/s, children 1.00 m/s) to compute journey time and time in green per group. Output: two metrics per stop — average green walking time (Health Score mode) and % of paths through green (Catchment mode).

8. **Right panel MVP redesign** — consolidates the population section and Green Paths into one pane. Ships after point 7 pipeline is complete. Layout (top to bottom):
   - **Row 0:** Mode toggle (Health · Catchment) + Neighbourhood selector — drives everything below and the map
   - **Score distribution card** — unchanged
   - **Scatter plot** — unchanged
   - **People + Green section:**
     - Headline KPIs: total population (KPI 1) + green metric (KPI 2: time in green for Health mode / % paths through green for Catchment mode)
     - On stop selection: second KPI row appears showing catchment population + green metric for that stop
     - Population bars (Children / Working-age / Elderly) each paired with their group's share of green walking time (computed per group walking speed)

9. **Neighbourhood highlighter** — built after 7 + 8. The neighbourhood selector (row 0) acts as a district-wide comparator, not a filter: highlights neighbourhood boundary + its stops on the map; shows neighbourhood band within district-wide distribution card; dims non-neighbourhood stops in scatter; updates People + Green KPIs to reflect the neighbourhood. Can be deferred if implementation complexity is high.

---

## Phases Ahead

Prune as phases complete.

### Phase 3a — Bus pipeline loose ends
- Re-export `norrebro_bus_segments_scored.gpkg` to `data/integrated/` once edge-artifact decision is confirmed
- Extend health scores to low/high population scenarios
- Green Paths pipeline (feeds MVP block point 7 above)

### Phase 3b — Rail *(blocked on data)*
- Find accurate entrance geometries (evaluate Rejseplanen, DSB open data, OSM — GTFS centroids are not entrance-level accurate)
- Once data confirmed: CitySeer scoring, B(d) Baseline + Contextual modes, export `data/web/norrebro_rail_stops_scored.geojson`

### Phase 3c — Cycling *(methodology TBD — placeholder)*

### Phase 3d — Green Spaces tab
- For each 20m segment midpoint: compute network distance to nearest park polygon + nearest playground (`norrebro_greenspaces.gpkg`)
- Score = B(d) × population per segment, Baseline + Contextual modes
- Export `data/web/norrebro_greenspace_access.geojson` for Green Spaces tab narrative

### Phase 5 — Scrollytelling remaining
- Map transitions: `showCatchmentRing`, `showBenefitCurves` (currently stubs)
- Wire scenario rail to low/high score columns once computed
- UX items:
  - Scatter axes static 0–1 with 0.25 increments (currently dynamic/rescaling)
  - Score mode → clean toggle control (replace pill buttons)
  - Info popup z-index fix (popups greyed out behind opacity layer — must sit above it)
  - Floating narrative cards on full-bleed map for steps 4–6 (cards as overlays, map full viewport)
  - Map tooltip redesign: wide table with population labels as column headers, scores as a single row

### Phase 6 — Interactive tool
- Benefit curve parameter sliders (peak distance, decay steepness) — map updates reactively
- Headline walking-minutes metric panel (total daily walking-minutes for current stop configuration)
- Post-MVP: "drop a hypothetical stop" marginal benefit interaction (requires pre-computed lookup grid or backend)

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
