# Right Panel MVP Redesign + Neighbourhood Comparator
**Date:** 2026-04-20
**Tasks:** PROGRESS.md #8 (Right panel MVP) + #9 (Neighbourhood highlighter)
**Status:** Approved for implementation

---

## Overview

Two tightly-coupled UI tasks delivered together:

- **Task 8** — consolidate the right chart panel into a cleaner layout with merged People + Green section and headline population KPIs using the new `pop_*_reach_*` columns
- **Task 9** — add a neighbourhood comparator that overlays neighbourhood-level context on every chart and the map without replacing the district-wide figures

---

## 1. Floating Mode Toggle (global, above map)

**Current state:** Mode toggle (Health Score / Catchment Score) lives inside the left tool panel, alongside a `data-info="score"` ⓘ button.

**New behaviour:**
- Absolutely positioned pill centred at the top of the map viewport (`position: fixed`, `z-index` above map, below popups)
- Layout: `[ Health Score  ·  Catchment Score ]  ⓘ` — active mode highlighted, inactive dimmed; ⓘ sits to the right of the pill
- The `data-info="score"` info popup and its content move here from the left panel — the popup anchors below the toggle and inherits the same z-index, so it appears above the map correctly
- Drives everything it currently drives (map layer, right panel, segment popup) — no change to existing state logic, just the DOM location of the buttons
- The existing mode toggle section (buttons + ⓘ + description paragraphs) is removed from the left panel entirely

---

## 2. Collapsible Left Panel

**Current state:** Left tool panel (`#tool-panel`) is always visible.

**New behaviour:**
- A `<` chevron button at the right edge of the panel collapses it to a narrow rail (icon only, ~40px wide)
- CSS `max-width` + `overflow: hidden` transition (~200ms ease)
- Collapsed state persists via `localStorage` key `toolPanelCollapsed`
- Content (group selector, overlays) is unchanged; only visibility changes

---

## 3. Right Panel Restructure

### 3a. Header row (replaces `#chart-mode-label`)

Single row containing:

- Left: **Neighbourhood selector** `<select>` — options: All Nørrebro + 5 sub-neighbourhoods, followed by a `data-info="neighbourhood"` ⓘ button
- Right: nothing (mode label removed — mode is now the floating toggle)

**`info-popup-neighbourhood` content:** "Select a neighbourhood to see how it compares to all of Nørrebro. District-wide figures stay visible — the neighbourhood is shown as an additional layer on the charts and map, not a filter."

The selector drives Tasks 8 and 9 effects described below.

### 3b. Distribution card — unchanged

### 3c. Scatter plot — unchanged

### 3d. People + Green section (replaces the two separate blocks)

**Structure (top to bottom):**

```
┌─────────────────────────────────────────────┐
│ Headline KPI row (district)                 │
│  [population icon]  X,XXX – X,XXX people    │  ← pop_wa/el/ch _reach_low/_high summed
│  [leaf icon]        X.X min / XX% green     │  ← green_time (Health) or green_pct (Catchment)
├─────────────────────────────────────────────┤
│ Stop KPI row (appears on stop click, hidden │
│ by default)                                 │
│  [stop icon]  X,XXX – X,XXX  ·  X.Xmin green│
├─────────────────────────────────────────────┤
│ Per-group rows                              │
│  Children    0–14   [====       ] 18%  1.0min│
│  Working-age 15–64  [=========  ] 74%  1.4min│
│  Elderly     65+    [==         ]  8%  0.8min│
└─────────────────────────────────────────────┘
```

**Headline KPI row (district-wide):**
- Population: sum of `pop_wa_reach_mid + pop_el_reach_mid + pop_ch_reach_mid` across all internal scored stops (district average), displayed as a range using `_low` / `_high` sums
- Green metric:
  - Health mode: mean `green_time_working_age` across internal stops (labelled "avg min in green")
  - Catchment mode: mean `green_pct_catchment` × 100 (labelled "% routes through parks")

**Stop KPI row (on stop click):**
- Population range for the selected stop: `pop_wa_reach_low + pop_el_reach_low + pop_ch_reach_low` → `…_high`
- Green metric for the selected stop (same mode-dependent column)
- Row is hidden by default; slides in when a stop is clicked; dismissed on map click elsewhere

**Per-group rows:**
- Bar width = group share of total population (unchanged from current)
- Secondary annotation right-aligned = green time for that group in Health mode, or group's share of `green_pct_catchment` in Catchment mode
- Annotation updates when neighbourhood selector changes (shows neighbourhood group share, not district)

**People + Green ⓘ button** (`data-info="people-green"`) sits in the section header. Content: "Population figures show residents reachable within each group's maximum walk time on the pedestrian network (working-age: 10 min / 840m; elderly: 8 min / 432m; children: 7 min / 420m). Everyone within the threshold counts equally — no distance weighting. The range (low–high) reflects uncertainty in the population model, not distance. Green time shows the average minutes of that walk spent through park space."

---

## 4. Neighbourhood Comparator (Task 9)

### Data source

`norrebro_neighbourhoods.geojson` — 5 polygon features with `neighbourhood_name` + `pop_total`. Per-group age breakdown computed client-side from `norrebro_neighbourhoods_population.csv` baked into `config.js` as a lookup object at build time.

Neighbourhood assignment for stops: client-side point-in-polygon check using the neighbourhood polygons (85 internal stops × 5 polygons — trivial cost).

### Selector behaviour

When a neighbourhood is selected (any value other than "All Nørrebro"):

**Map:**
- Add a discrete polygon outline layer (`neighbourhood-boundary` source) showing the selected neighbourhood boundary — dashed stroke, no fill, accent colour
- No change to segment colours or stop colours

**Distribution chart:**
- Existing bars show district distribution (unchanged)
- Add a small accent marker (vertical tick or dot) on each band showing where the neighbourhood average sits within that band
- Neighbourhood average computed as mean score across stops whose centroid falls within the neighbourhood polygon (client-side containment)

**Scatter plot:**
- Out-of-neighbourhood internal stops: opacity reduced to 0.2
- In-neighbourhood stops: full opacity, slightly larger dot radius
- No axis change, no second series

**People + Green section:**
- Headline KPI row shows district figures (unchanged)
- A second compact row appears below it showing neighbourhood figures in a muted accent colour: `N,NNN – N,NNN people · X.Xmin green`
- Per-group bar rows: add a small accent tick on each bar at the neighbourhood group share, so you can see the neighbourhood mix vs the district mix on the same bar

### "All Nørrebro" (default):
- Neighbourhood boundary layer hidden
- Scatter: all stops full opacity
- Distribution: no accent markers
- People + Green: no secondary row, no bar ticks

---

## 5. Data flow summary

```
norrebro_stops.geojson          → stop scores, pop_*_reach_*, green_* columns
norrebro_neighbourhoods.geojson → boundary polygons, pop_total per neighbourhood
config.js (NEIGHBOURHOOD_POP)   → age breakdown per neighbourhood (baked from CSV)
state.js (activeMode,           → drives all rendering
          activeGroup,
          selectedStop,
          activeNeighbourhood)
```

All neighbourhood filtering is client-side. No new GeoJSON files needed.

---

## 6. Files changed

| File | Changes |
|---|---|
| `web/index.html` | Add floating toggle div (with relocated `data-info="score"` popup); add collapsible panel chevron; restructure chart-panel HTML (header row with neighbourhood ⓘ; People + Green merge with new `data-info="people-green"` popup) |
| `web/js/map.js` | Move mode toggle event wiring to new DOM element; add neighbourhood boundary source/layer; point-in-polygon helper; neighbourhood filter for scatter opacity |
| `web/js/scatter.js` | Accept neighbourhood filter, dim out-of-neighbourhood stops |
| `web/js/config.js` | Add `NEIGHBOURHOOD_POP` lookup (age breakdown per neighbourhood from CSV) |
| `web/js/state.js` | Add `activeNeighbourhood` state; add `selectedStop` state |
| `web/css/style.css` | Floating toggle styles; panel collapse animation; People + Green section layout; neighbourhood accent styles |

No new JS files. No pipeline changes.

---

## 7. Out of scope

- Scenario rail (low/mid/high toggle) — deferred to Phase 5
- Benefit curve sliders — Phase 6
- Cycling / Rail / Green Spaces tabs — separate phases
- Mobile responsiveness — Phase 7
