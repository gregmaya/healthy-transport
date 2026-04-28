# Progress Tracker

Last updated: 2026-04-28 (fix: UI polish + Frederiksberg parks pipeline + tooltip P+G mini-panel)

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

~~1. **Phase B data validation**~~ ✅ DONE — Findings: (a) Population columns exist only in `entrances_demographics` (correct by design); (b) boundary-adjacent scores look improved but see issue below; (c) no null/zero clusters. Critical bug found: `process_buildings.py` was using `mode='a'` without deleting the output file first, causing entrances to be appended on each re-run (43,037 rows / 4× duplication vs. 15,443 expected). Also found: DAR status=9 (deactivated/closed addresses) were not filtered, adding 477 spurious entrance points. Both fixed. Pipeline fully re-run 2026-04-19.

~~2. **Fix Frederiksberg DAR edge effect**~~ ✅ CLOSED — After deduplication and status=9 removal, processed entrances are 15,443 unique points (5,643 Nørrebro core + 9,800 buffer zone). Frederiksberg spatial coverage is a genuine data-density limitation of the raw DAR, not a pipeline artifact. No further supplementation planned; scores are now computed on clean data.

~~3. **Correlation check**~~ ✅ DONE — Pearson r(`score_catchment`, `score_health_combined`) on 85 internal stops = **−0.404**. Well below the 0.8 threshold. The negative value reflects that geometrically accessible corridors (high catchment) are often commercial/transit arteries with lower residential density, while high health-score zones are residential clusters with fewer but more meaningful connections. The two modes are genuinely differentiating.

### Active UI tasks

~~4. **Score mode naming unification**~~ ✅ DONE — Renamed Baseline → Catchment Score and Contextual → Health Score across all buttons, titles, chart axes, info panels, tooltips, and narrative text in index.html, map.js, scatter.js, scroll.js, and config.js. Internal `data-mode` values and JS variable names unchanged.

~~5. **Segment hover/click popup**~~ ✅ DONE — Hover over any scored segment shows a floating popup with the active score, band category, and group breakdown (Working-age / Elderly / Children) in Health Score mode. Popup tracks mouse position. Uses same popup CSS classes as the stop tooltip. Implemented in `_addPopups()` in map.js, attached to all four segment layers.

~~6. **Scroll transition stubs**~~ ✅ DONE — `showCatchmentRing` and `showBenefitCurves` now set NORREBRO_BOUNDS + footprints visible as background state, so when step 4 reveals the scored network there is no jump. Overlays (image panel / fullscreen SVG) still cover the map during these steps.

### MVP completeness block *(ship together)*

~~7. **Green Paths pipeline**~~ ✅ DONE — Four new columns on all 1,699 bus-route segments: `green_pct_catchment` (fraction of decay-weighted reachable network through parks; mean 13.9%, max 61.5%), `green_time_working_age / _elderly / _children` (green_pct × max_walk_minutes per group; mean ~1.4 / 1.1 / 1.0 min). Green fraction per edge computed as proportional intersection of primal edge with park polygon union. One CitySeer `compute_stats` pass (catchment decay). Parks overlay layer also enabled: `data/web/norrebro_parks.geojson` (77 features), wired to `toggle-parks` checkbox in the interactive panel. Segment hover popup now shows green metric in the active mode.

~~8. **Right panel MVP redesign**~~ ✅ DONE — Floating mode toggle (`#mode-toggle-float`) at top-centre of map viewport; collapsible left panel with localStorage persistence; merged People + Green section with real flat-decay population KPIs (`pop_*_reach_*`), stop KPI row (appears on stop click), green annotation per group bar. `NEIGHBOURHOOD_POP` + `DISTRICT_POP` added to `config.js`; `activeNeighbourhood` + `selectedStop` added to `state.js`.

~~9. **Neighbourhood highlighter**~~ ✅ DONE — Neighbourhood selector in chart-panel header drives: MapLibre boundary outline (`neighbourhood-boundary` layer via `setNeighbourhoodBoundary`), scatter dimming (`updateNeighbourhoodFilter`), distribution accent tick, People + Green comparison row and bar ticks. Client-side point-in-polygon (`neighbourhoodForPoint`) assigns stops to neighbourhoods.

~~10. **Corrections to tasks 8+9**~~ ✅ DONE — 11 targeted fixes: (1) separate catchment ramp domain so stops colour correctly in catchment mode; (2) mode-toggle-float z-index raised above tab bar + positioned below it; (3) scatter axes fixed 0–1 with 0.25 ticks, Y labels → "Health Score (All/…)"; (4) neighbourhood polygon layer changed from orange line to grey fill (0.18 opacity) behind data; (5) neighbourhood dropdown styled as plain bold title; (6) distribution bars show actual %, black Nørrebro baseline marker when neighbourhood selected, "Distribution" header removed; (7) collapse button shows "‹ Hide" label with arrow; (8) People+Green block redesigned to 70/30 layout, no emojis, uncertainty ±%, green column; (9) stop size radio buttons (uniform / people in catchment / green time); (10) maxZoom tightened to 17; (11) parks clip extended to 1000m buffer (+9 parks covering Frederiksberg), scoring re-run.

~~11. **Task 1: wire group-button clicks to _updatePeopleGreen**~~ ✅ DONE — Added `_updatePeopleGreen` call to group-button click handler (line 244); read active group at start of `_updatePeopleGreen` function (line 301) to enable subsequent tasks to access the selected demographic group.

~~12. **Task 2: headline shows census count for selected group**~~ ✅ DONE — Replaced hardcoded `hPopLow`/`hPopHigh` range with district or neighbourhood census counts keyed to `activeGroup`. Headline label now shows "children in [neighbourhood]" / "working-age adults in Nørrebro" etc. Uses `NEIGHBOURHOOD_POP` and `DISTRICT_POP` from config.js.

~~13. **Task 3: green time uses population-weighted average**~~ ✅ DONE — Baseline mode still shows "routes through parks" (%), Health Score mode now shows `(waPop × green_time_working_age + elPop × green_time_elderly + chPop × green_time_children) / totalReach` — population-weighted mean across all three groups, not hardcoded working-age. Label changed from "avg min in green (WA)" to "avg min in green".

~~14. **Task 4(c): grey background on stop-detail row**~~ ✅ DONE — Added `.pg-row--stop:not(.hidden)` rule in style.css with subtle grey background (#f3f4f6), rounded corners, and padding to visually distinguish the stop-detail panel row when it appears on stop click.

~~15. **Task 5(d): single Time in Green column header**~~ ✅ DONE — Added `.pg-groups-header` row above group rows with "Population" and "Time in Green" labels styled as monospace uppercase tags; cleared per-row subtext by setting `greenSubEl.textContent = ""` in `_updatePeopleGreen`.

~~16. **Task 7: stop-detail row responds to active demographic group**~~ ✅ DONE — Stop-detail row (`#pg-stop-row`) now uses group-specific population field (`pop_ch_reach_mid` / `pop_wa_reach_mid` / `pop_el_reach_mid`) instead of summing all three groups' low–high ranges. Green time uses group-specific field (`green_time_children` / `green_time_working_age` / `green_time_elderly`) or population-weighted average for aggregate mode. Display format changed from `fmtK()` range to `toLocaleString("en-DK")` integer. Implemented in scroll.js lines 352–408.

~~17. **UI polish + Frederiksberg parks + tooltip P+G mini-panel**~~ ✅ DONE — Six changes in one session:

- **Burger icon collapse**: restructured `#tool-panel-collapse` as an in-flow button inside `#tool-panel-header`; shows `‹` chevron when expanded, `☰` when collapsed (CSS-only toggle via `.icon-collapse-open` / `.icon-collapse-closed`). Was previously clipped by `overflow: hidden`.
- **Stop size visibility**: `#stop-size-section` now hidden when Bus Stops overlay is toggled off; shown when on. Wired to `#toggle-stops` change handler in scroll.js.
- **Water bodies in light blue**: `parks-fill` and `parks-line` layers use a MapLibre `match` expression on `park_type` — `"Vandflader"` → `#b3d4f5` / `#5a9fd4` (blue); all other park types remain green.
- **Scatter/distribution in Catchment mode**: exported `getCatchRampDomain()` from map.js; `scatter.js` now normalises catchment scores using the catchment domain (not health score domain) when in baseline mode. `updateScatterMode()` now also redraws scatter dots (was missing).
- **Tooltip P+G mini-panel**: segment hover and stop click popups now share a unified layout via `_buildPopupHeader()` + `_buildMiniPG()`. Stop tooltips show per-group catchment population with `± confidence band`; segment tooltips show per-group health scores. Single score line at top (`modeName · value`), no duplicate labels.
- **Frederiksberg parks pipeline**: `process_greenspaces.py` now supplements the KK park register with 23 Frederiksberg polygons from `kk_park_groent_omr_oversigtskort.gpkg` (within 1 km buffer). Total parks: 86 → 109. Scoring (`score_bus_routes.py`) and web exports re-run; `green_pct_catchment` updated. P+G area bars now show plain census count (no `±`); stop-specific row shows `± halfRange` from low/high interpolation scenarios.

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
