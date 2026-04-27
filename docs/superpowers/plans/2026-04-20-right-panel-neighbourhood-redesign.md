# Right Panel MVP + Neighbourhood Comparator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the interactive panel with a floating mode toggle, collapsible left panel, merged People + Green section with real population data, and a neighbourhood comparator that overlays context on the map, scatter, distribution, and KPI section without replacing district figures.

**Architecture:** All logic stays in existing JS files (no new files). `config.js` gains a `NEIGHBOURHOOD_POP` lookup. `state.js` gains two exported state variables. `map.js` gains a neighbourhood boundary layer + point-in-polygon helper. `scroll.js` owns all panel update logic. `scatter.js` gains a neighbourhood dim filter. HTML is restructured; CSS adds new rules.

**Tech Stack:** MapLibre GL JS, vanilla ES modules, SVG scatter, no build step (served directly via `bash scripts/dev.sh`).

**Dev server:** `bash scripts/dev.sh` → http://localhost:8000. Open after each task to verify visually.

---

## File map

| File | What changes |
|---|---|
| `web/js/config.js` | Add `NEIGHBOURHOOD_POP` constant (age breakdown per neighbourhood, keyed by `neighbourhood_name`) |
| `web/js/state.js` | Add `activeNeighbourhood` + `selectedStop` exported mutable state |
| `web/js/map.js` | Add neighbourhood source/layer; add `setNeighbourhoodBoundary(name)`; add `_pointInPolygon` helper; add `getNeighbourhoodFeatures()` |
| `web/index.html` | Add `#mode-toggle-float`; remove mode section from left panel; add collapse chevron; restructure `#chart-panel` header + People+Green block |
| `web/css/style.css` | Floating toggle styles; panel collapse animation; People+Green layout; neighbourhood accent styles |
| `web/js/scroll.js` | Re-wire mode toggle; replace `_updateGreenBlock` + `_updateDemoBars` with `_updatePeopleGreen`; wire neighbourhood selector |
| `web/js/scatter.js` | Add `filterByNeighbourhood(stopIdSet)`; add neighbourhood accent markers to distribution |

---

## Task 1: Add `NEIGHBOURHOOD_POP` to config.js

**Files:**
- Modify: `web/js/config.js`

- [ ] **Step 1: Add the constant** — append to the bottom of `web/js/config.js`:

```js
// Age breakdown per neighbourhood — keyed by neighbourhood_name from norrebro_neighbourhoods.geojson.
// Source: norrebro_neighbourhoods_population.csv, 2025Q4.
// Groups: children=0–14, working_age=15–64, elderly=65+.
export const NEIGHBOURHOOD_POP = {
  "Blagardskvarteret":   { children: 2104,  working_age: 11093, elderly: 1481,  total: 14678 },
  "Guldbergskvarteret":  { children: 2484,  working_age: 15230, elderly: 2047,  total: 19761 },
  "Stefansgade":         { children: 2562,  working_age: 13873, elderly: 1319,  total: 17754 },
  "Mimersgade-kvarteret":{ children: 2060,  working_age: 14256, elderly: 1056,  total: 17372 },
  "Haraldsgade-kvarteret":{ children: 1282, working_age: 8128,  elderly: 778,   total: 10188 },
};

// District totals (sum of above) — used for population bar percentages.
export const DISTRICT_POP = {
  children:    10492,
  working_age: 62580,
  elderly:      6681,
  total:       79753,
};
```

- [ ] **Step 2: Commit**

```bash
git add web/js/config.js
git commit -m "feat: add NEIGHBOURHOOD_POP and DISTRICT_POP constants to config.js"
```

---

## Task 2: Add `activeNeighbourhood` and `selectedStop` to state.js

**Files:**
- Modify: `web/js/state.js`

- [ ] **Step 1: Add exported state** — append to `web/js/state.js` after the existing scroll-lock functions:

```js
// Shared interactive-tool state — neighbourhood comparator and stop selection.
// Using getter/setter pattern so consumers always read the current value.

let _activeNeighbourhood = "";   // "" = All Nørrebro; otherwise neighbourhood_name string
let _selectedStop = null;         // stop_id string or null

export function getActiveNeighbourhood() { return _activeNeighbourhood; }
export function setActiveNeighbourhood(name) { _activeNeighbourhood = name || ""; }

export function getSelectedStop() { return _selectedStop; }
export function setSelectedStop(id) { _selectedStop = id ?? null; }
```

- [ ] **Step 2: Commit**

```bash
git add web/js/state.js
git commit -m "feat: add activeNeighbourhood and selectedStop state to state.js"
```

---

## Task 3: Add neighbourhood boundary layer to map.js

**Files:**
- Modify: `web/js/map.js`

- [ ] **Step 1: Add neighbourhood source in `_addSources()`** — find the line `map.addSource("parks-src", ...)` and add after it:

```js
  map.addSource("neighbourhoods-src", { type: "geojson", data: DATA.neighbourhoods });

  // Pre-fetch neighbourhood features for point-in-polygon stop assignment
  fetch(DATA.neighbourhoods).then(r => r.json()).then(d => {
    _neighbourhoodFeatures = d.features;
  });
```

- [ ] **Step 2: Declare `_neighbourhoodFeatures` at the top of the file** — add after the existing module-level `let` declarations (e.g. after `let _activeMode = "contextual";`):

```js
let _neighbourhoodFeatures = null;
```

- [ ] **Step 3: Add neighbourhood boundary layer in `_addLayers()`** — append at the end of `_addLayers()`, after the parks layers:

```js
  // Neighbourhood boundary — hidden by default, shown when selector is active
  map.addLayer({
    id: "neighbourhood-boundary",
    type: "line",
    source: "neighbourhoods-src",
    filter: ["==", ["get", "neighbourhood_name"], ""],   // nothing matches → hidden
    paint: {
      "line-color": "#ff6700",
      "line-width": 2,
      "line-dasharray": [4, 3],
      "line-opacity": 0.85,
    },
  });
```

- [ ] **Step 4: Add `setNeighbourhoodBoundary` export** — add after the `toggleParks` function:

```js
/** Show the boundary outline for a neighbourhood by name; pass "" to hide. */
export function setNeighbourhoodBoundary(name) {
  if (!map.getLayer("neighbourhood-boundary")) return;
  map.setFilter("neighbourhood-boundary",
    name
      ? ["==", ["get", "neighbourhood_name"], name]
      : ["==", ["get", "neighbourhood_name"], ""]
  );
}
```

- [ ] **Step 5: Add `getNeighbourhoodFeatures` export and point-in-polygon helper** — add after `setNeighbourhoodBoundary`:

```js
/** Returns loaded neighbourhood GeoJSON features (null until fetched). */
export function getNeighbourhoodFeatures() { return _neighbourhoodFeatures; }

/**
 * Returns the neighbourhood_name of the polygon containing [lng, lat],
 * or null if none match. Uses ray-casting on the first ring of each polygon.
 */
export function neighbourhoodForPoint(lngLat) {
  if (!_neighbourhoodFeatures) return null;
  for (const feat of _neighbourhoodFeatures) {
    const coords = feat.geometry.type === "Polygon"
      ? feat.geometry.coordinates[0]
      : feat.geometry.coordinates[0][0];  // MultiPolygon
    if (_pointInPolygon(lngLat, coords)) return feat.properties.neighbourhood_name;
  }
  return null;
}

function _pointInPolygon([x, y], ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if (((yi > y) !== (yj > y)) && (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi)) {
      inside = !inside;
    }
  }
  return inside;
}
```

- [ ] **Step 6: Commit**

```bash
git add web/js/map.js
git commit -m "feat: add neighbourhood boundary layer, setNeighbourhoodBoundary, and point-in-polygon helper to map.js"
```

---

## Task 4: Float the mode toggle + remove from left panel

**Files:**
- Modify: `web/index.html`
- Modify: `web/css/style.css`
- Modify: `web/js/scroll.js`

This task moves the mode toggle from `#tool-panel` to a new `#mode-toggle-float` div above the map, and updates all related JS.

- [ ] **Step 1: Add `#mode-toggle-float` to `index.html`** — find the line `<div id="map">` and insert immediately after it (before `<div id="tool-panel"`):

```html
    <!-- ── Floating mode toggle (global, top-centre of map viewport) ──────── -->
    <div id="mode-toggle-float" class="hidden">
      <div class="mode-toggle">
        <button class="mode-btn active" data-mode="contextual">Health Score</button>
        <button class="mode-btn" data-mode="baseline">Catchment Score</button>
      </div>
      <button class="btn-icon" data-info="score" aria-label="About score modes">ⓘ</button>
      <div class="info-popup hidden" id="info-popup-score">
        <p><strong>Health Score</strong> — weights each street by the actual age mix of nearby residents. Elderly, children, and working-age adults each have different optimal walk distances. Reveals where a stop benefits the most people given today's population.</p>
        <p><strong>Catchment Score</strong> — scores streets on network reach alone: how many address points fall within walking distance, every resident counted equally. Useful for identifying locations with broad physical reach, independent of today's demographics.</p>
      </div>
    </div>
```

- [ ] **Step 2: Remove the `<!-- ── SCORE MODE ──` section from `#tool-panel`** — delete the entire `<div class="ctrl-section">` block that contains `ctrl-label">Score mode`, the `info-popup-score` div, the `mode-toggle` div, and the two `mode-active-desc` paragraphs. The section ends just before `<!-- ── DEMOGRAPHIC GROUP`.

- [ ] **Step 3: Show `#mode-toggle-float` when entering interactive tool** — in `map.js`, find `enterInteractiveTool()` and add after `document.getElementById("chart-panel").classList.remove("hidden");`:

```js
  document.getElementById("mode-toggle-float").classList.remove("hidden");
```

Also add the reverse in `backToNarrative()`, after `document.getElementById("chart-panel").classList.add("hidden");`:

```js
  document.getElementById("mode-toggle-float").classList.add("hidden");
```

- [ ] **Step 4: Update mode toggle event wiring in `scroll.js`** — find the comment `// Score mode pill toggle` and replace the block (lines that reference `mode-active-desc` and `chart-mode-label`) with:

```js
  // Score mode pill toggle — buttons live in #mode-toggle-float
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const mode = btn.dataset.mode;
      setScoreMode(mode);
      updateScatterMode();
      _updatePeopleGreen(getStopFeatures(), getSelectedStop(), getActiveNeighbourhood());
    });
  });
```

(Note: `_updatePeopleGreen` is defined in Task 8. For now you can leave a TODO comment and add it in Task 8.)

- [ ] **Step 5: Update info popup positioning in `scroll.js`** — find the block `const inChartPanel = !!btn.closest("#chart-panel");` and extend it to handle the floating toggle:

```js
        const inChartPanel  = !!btn.closest("#chart-panel");
        const inFloatToggle = !!btn.closest("#mode-toggle-float");
        if (inFloatToggle) {
          // Anchor below the toggle, horizontally centred
          const popupW = 288;
          const floatRect = document.getElementById("mode-toggle-float").getBoundingClientRect();
          popup.style.left = `${Math.max(4, floatRect.left + (floatRect.width - popupW) / 2)}px`;
          popup.style.top  = `${btnRect.bottom + 8}px`;
        } else if (inChartPanel) {
          const popupW = 288;
          popup.style.left = `${Math.max(4, btnRect.left - popupW - 8)}px`;
        } else {
          const panelRect = document.getElementById("tool-panel").getBoundingClientRect();
          popup.style.left = `${panelRect.right + 8}px`;
        }
        popup.style.top = inFloatToggle ? popup.style.top : `${top}px`;
```

- [ ] **Step 6: Add CSS for `#mode-toggle-float`** — add to `web/css/style.css`:

```css
/* ── Floating mode toggle ─────────────────────────────────────────────────── */
#mode-toggle-float {
  position: fixed;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 120;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 8px 4px 10px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}

#mode-toggle-float.hidden { display: none; }

#mode-toggle-float .mode-toggle {
  display: flex;
  gap: 0;
  margin: 0;
  border: none;
  padding: 0;
}

#mode-toggle-float .mode-btn {
  font-size: 0.75rem;
  padding: 4px 12px;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
  transition: background 0.15s, color 0.15s;
}

#mode-toggle-float .mode-btn.active {
  background: var(--text);
  color: #fff;
}

#mode-toggle-float .mode-btn + .mode-btn {
  border-left: 1px solid var(--border);
  border-radius: 999px;
}
```

- [ ] **Step 7: Verify** — run `bash scripts/dev.sh`, click "Explore it yourself", confirm the floating toggle appears at top-centre and both buttons change the map/charts correctly. The left panel should no longer have a Score mode section.

- [ ] **Step 8: Commit**

```bash
git add web/index.html web/css/style.css web/js/map.js web/js/scroll.js
git commit -m "feat: move mode toggle to floating top-centre pill; remove from left panel"
```

---

## Task 5: Collapsible left panel

**Files:**
- Modify: `web/index.html`
- Modify: `web/css/style.css`
- Modify: `web/js/scroll.js`

- [ ] **Step 1: Add collapse chevron button to `index.html`** — as the first child inside `<div id="tool-panel">`, before the first `<div class="ctrl-section">`:

```html
      <button id="tool-panel-collapse" aria-label="Collapse panel" title="Collapse panel">‹</button>
```

- [ ] **Step 2: Add CSS** — add to `web/css/style.css`:

```css
/* ── Left panel collapse ──────────────────────────────────────────────────── */
#tool-panel {
  transition: max-width 0.2s ease, padding 0.2s ease;
  overflow: hidden;
}

#tool-panel.collapsed {
  max-width: 40px;
  padding: 8px 0;
}

#tool-panel.collapsed .ctrl-section,
#tool-panel.collapsed .ctrl-section-header span,
#tool-panel.collapsed .group-buttons,
#tool-panel.collapsed .toggle-row {
  display: none;
}

#tool-panel-collapse {
  position: absolute;
  right: -14px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  color: var(--muted);
  transition: transform 0.2s;
}

#tool-panel.collapsed #tool-panel-collapse {
  transform: translateY(-50%) rotate(180deg);
}
```

- [ ] **Step 3: Add collapse JS to `scroll.js`** — add inside `_initInteractiveTool()`, after the parks checkbox listener:

```js
  // Left panel collapse toggle
  const collapseBtn = document.getElementById("tool-panel-collapse");
  const toolPanel   = document.getElementById("tool-panel");
  if (collapseBtn && toolPanel) {
    const stored = localStorage.getItem("toolPanelCollapsed");
    if (stored === "true") toolPanel.classList.add("collapsed");

    collapseBtn.addEventListener("click", () => {
      const isCollapsed = toolPanel.classList.toggle("collapsed");
      localStorage.setItem("toolPanelCollapsed", isCollapsed);
      resizeMap();
    });
  }
```

- [ ] **Step 4: Verify** — `bash scripts/dev.sh`, enter interactive mode, click the `‹` button. Panel collapses to rail, chevron flips to `›`. Reload page — collapsed state persists.

- [ ] **Step 5: Commit**

```bash
git add web/index.html web/css/style.css web/js/scroll.js
git commit -m "feat: collapsible left panel with localStorage persistence"
```

---

## Task 6: Restructure right panel HTML + CSS

This task replaces the existing Green Path Access block and Population stat block with a single People + Green block, and adds the neighbourhood selector to the chart-panel header.

**Files:**
- Modify: `web/index.html`
- Modify: `web/css/style.css`

- [ ] **Step 1: Replace the chart-panel header** — find `<div class="chart-panel-header">` and replace the entire div (which contains `<span id="chart-mode-label">Health Score</span>`) with:

```html
    <div class="chart-panel-header">
      <select id="neighbourhood-select" class="neighbourhood-panel-sel">
        <option value="">All Nørrebro</option>
        <option value="Blagardskvarteret">Blågårdskvarteret</option>
        <option value="Guldbergskvarteret">Guldbergskvarteret</option>
        <option value="Stefansgade">Stefansgade</option>
        <option value="Mimersgade-kvarteret">Mimersgade-kvarteret</option>
        <option value="Haraldsgade-kvarteret">Haraldsgade-kvarteret</option>
      </select>
      <button class="btn-icon" data-info="neighbourhood" aria-label="About neighbourhood comparison">ⓘ</button>
      <div class="info-popup hidden" id="info-popup-neighbourhood">
        <p>Select a neighbourhood to see how it compares to all of Nørrebro. District-wide figures stay visible — the neighbourhood is shown as an additional layer on the charts and map, not a filter.</p>
      </div>
    </div>
```

- [ ] **Step 2: Remove the two old blocks** — delete the entire `<div class="chart-block" id="green-path-block">` block (Green Path Access) and the entire `<div class="chart-block">` block that contains `kpi-population` and the demographic bars. Both are replaced by the new block below.

- [ ] **Step 3: Insert the new People + Green block** — add after the scatter chart block and before `</div><!-- #chart-panel -->`:

```html
    <!-- People + Green (merged) -->
    <div class="chart-block" id="people-green-block">
      <div class="chart-block-header">
        People + Green Access
        <button class="btn-icon" data-info="people-green" aria-label="About population reach">ⓘ</button>
      </div>
      <div class="info-popup hidden" id="info-popup-people-green">
        <p>Population figures show residents reachable within each group's maximum walk time on the pedestrian network (working-age: 10 min / 840m; elderly: 8 min / 432m; children: 7 min / 420m). Everyone within the threshold counts equally — no distance weighting. The range (low–high) reflects uncertainty in the population model, not distance. Green time shows the average minutes of that walk spent through park space.</p>
      </div>

      <!-- District headline KPIs -->
      <div class="pg-kpi-row" id="kpi-district-row">
        <div class="pg-kpi-item">
          <span class="pg-kpi-icon">&#128101;</span>
          <span class="pg-kpi-value" id="kpi-pop-range">—</span>
          <span class="pg-kpi-label">people within walking distance</span>
        </div>
        <div class="pg-kpi-item">
          <span class="pg-kpi-icon">&#127807;</span>
          <span class="pg-kpi-value" id="kpi-green-district">—</span>
          <span class="pg-kpi-label" id="kpi-green-district-label">avg min in green</span>
        </div>
      </div>

      <!-- Neighbourhood comparison row (hidden when no neighbourhood selected) -->
      <div class="pg-kpi-row pg-kpi-nb hidden" id="kpi-neighbourhood-row">
        <span class="pg-nb-name" id="kpi-nb-name">—</span>
        <span id="kpi-nb-pop">—</span>
        <span class="pg-sep">·</span>
        <span id="kpi-nb-green">—</span>
      </div>

      <!-- Stop KPI row (hidden until stop clicked) -->
      <div class="pg-kpi-row pg-kpi-stop hidden" id="kpi-stop-row">
        <span class="pg-kpi-icon">&#128652;</span>
        <span id="kpi-stop-name" class="pg-stop-name">—</span>
        <span id="kpi-stop-pop">—</span>
        <span class="pg-sep">·</span>
        <span id="kpi-stop-green">—</span>
        <button class="pg-stop-close" id="kpi-stop-close" aria-label="Clear stop">×</button>
      </div>

      <!-- Per-group bars -->
      <div class="demo-bars-section">
        <div class="demo-bar-row">
          <span class="demo-bar-label">Children<span class="demo-bar-age"> 0–14</span></span>
          <div class="demo-bar-track">
            <div class="demo-bar-fill" id="bar-children" style="width:13%;background:#c6dbef"></div>
            <div class="demo-bar-nb-tick hidden" id="nb-tick-children"></div>
          </div>
          <span class="demo-bar-pct" id="pct-children">13%</span>
          <span class="demo-bar-green" id="green-ann-children">—</span>
        </div>
        <div class="demo-bar-row">
          <span class="demo-bar-label">Working-age<span class="demo-bar-age"> 15–64</span></span>
          <div class="demo-bar-track">
            <div class="demo-bar-fill" id="bar-working-age" style="width:78%;background:#2171b5"></div>
            <div class="demo-bar-nb-tick hidden" id="nb-tick-working-age"></div>
          </div>
          <span class="demo-bar-pct" id="pct-working-age">78%</span>
          <span class="demo-bar-green" id="green-ann-working-age">—</span>
        </div>
        <div class="demo-bar-row">
          <span class="demo-bar-label">Elderly<span class="demo-bar-age"> 65+</span></span>
          <div class="demo-bar-track">
            <div class="demo-bar-fill" id="bar-elderly" style="width:8%;background:#6baed6"></div>
            <div class="demo-bar-nb-tick hidden" id="nb-tick-elderly"></div>
          </div>
          <span class="demo-bar-pct" id="pct-elderly">8%</span>
          <span class="demo-bar-green" id="green-ann-elderly">—</span>
        </div>
      </div>
      <p class="age-bar-note">Population model estimates · <a href="#" style="color:inherit">methodology</a></p>
    </div>
```

- [ ] **Step 4: Add CSS for People + Green layout** — add to `web/css/style.css`:

```css
/* ── People + Green block ─────────────────────────────────────────────────── */
.pg-kpi-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-subtle);
  flex-wrap: wrap;
}

.pg-kpi-row.hidden { display: none; }

.pg-kpi-item {
  display: flex;
  align-items: baseline;
  gap: 4px;
  flex: 1 1 45%;
}

.pg-kpi-icon {
  font-size: 0.85rem;
  flex-shrink: 0;
}

.pg-kpi-value {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
  font-family: var(--font-mono);
  white-space: nowrap;
}

.pg-kpi-label {
  font-size: 0.68rem;
  color: var(--muted);
  line-height: 1.2;
}

/* Neighbourhood comparison row */
.pg-kpi-nb {
  font-size: 0.78rem;
  color: #a35c00;
  border-left: 2px solid #ff6700;
  padding-left: 6px;
  margin-left: 4px;
  gap: 4px;
}

.pg-nb-name {
  font-weight: 600;
  margin-right: 4px;
}

.pg-sep { color: var(--muted); }

/* Stop KPI row */
.pg-kpi-stop {
  font-size: 0.78rem;
  color: var(--text);
  background: var(--border-subtle);
  border-radius: 4px;
  padding: 4px 8px;
  margin: 4px 0;
  gap: 6px;
}

.pg-stop-name {
  font-weight: 600;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pg-stop-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--muted);
  font-size: 1rem;
  line-height: 1;
  padding: 0 2px;
  margin-left: auto;
}

/* Green annotation on per-group bar rows */
.demo-bar-row {
  display: grid;
  grid-template-columns: 90px 1fr 34px 44px;
  align-items: center;
  gap: 4px;
  padding: 3px 0;
}

.demo-bar-green {
  font-size: 0.7rem;
  color: #2e7d32;
  text-align: right;
  font-family: var(--font-mono);
  white-space: nowrap;
}

/* Neighbourhood tick inside bar track */
.demo-bar-track { position: relative; }

.demo-bar-nb-tick {
  position: absolute;
  top: 0;
  width: 2px;
  height: 100%;
  background: #ff6700;
  border-radius: 1px;
  opacity: 0.8;
}

.demo-bar-nb-tick.hidden { display: none; }

/* Chart panel header with neighbourhood selector */
.neighbourhood-panel-sel {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 3px 6px;
  background: #fff;
  color: var(--text);
  cursor: pointer;
  flex: 1;
}
```

- [ ] **Step 5: Verify** — `bash scripts/dev.sh`, enter interactive mode. The right panel should show the neighbourhood selector in the header, and the People + Green block. KPIs will show `—` until Task 8 wires the data.

- [ ] **Step 6: Commit**

```bash
git add web/index.html web/css/style.css
git commit -m "feat: restructure right panel — neighbourhood selector header, merged People+Green block"
```

---

## Task 7: Update scatter.js — neighbourhood dimming + distribution accent

**Files:**
- Modify: `web/js/scatter.js`

- [ ] **Step 1: Add `_neighbourStopIds` module variable** — add after the existing `let _scatterSelectCallback = null;` line:

```js
let _neighbourStopIds = null;   // Set of stop_id strings in the active neighbourhood; null = show all
```

- [ ] **Step 2: Add `filterByNeighbourhood` export** — add after `setScatterSelectCallback`:

```js
/**
 * Dim stops outside the given Set of stop_ids.
 * Pass null to restore full opacity for all stops.
 */
export function filterByNeighbourhood(stopIdSet) {
  _neighbourStopIds = stopIdSet;
  _dotElements.forEach((circ, id) => {
    const inNb = !stopIdSet || stopIdSet.has(id);
    circ.setAttribute("fill-opacity", inNb ? 0.75 : 0.12);
    circ.setAttribute("r", inNb && id === _selectedId ? 4.5 : inNb ? 2.2 : 1.8);
  });
}
```

- [ ] **Step 3: Apply neighbourhood filter when re-drawing scatter** — in `drawScatter`, at the end of the loop where circles are created (just before `g.appendChild(circle)`), add:

```js
    if (_neighbourStopIds) {
      const inNb = _neighbourStopIds.has(stopId);
      circle.setAttribute("fill-opacity", inNb ? 0.75 : 0.12);
    }
```

- [ ] **Step 4: Add neighbourhood accent to distribution** — add a `_nbAvgScore` parameter to `drawDistribution` and draw a tick. Replace the current `function drawDistribution(group)` signature and `container.innerHTML` block:

```js
function drawDistribution(group, nbAvgScore = null) {
  const container = document.getElementById("distribution-container");
  if (!container || !_features?.length) return;

  const isBaseline = document.querySelector(".mode-btn.active")?.dataset.mode === "baseline";
  const scoreKey   = isBaseline ? "score_catchment" : (GROUP_Y_FIELD[group] || GROUP_Y_FIELD.aggregate);

  const rawVals = _features.map(f => +(f.properties[scoreKey]) || 0);
  const vals    = rawVals.map(v => _normalize(v));
  const n       = vals.length;

  const counts = BANDS.map(b => vals.filter(v => v >= b.lo && v < b.hi).length);
  const maxCnt = Math.max(...counts, 1);

  container.innerHTML = BANDS.map((b, i) => {
    const pct   = n > 0 ? Math.round((counts[i] / n) * 100) : 0;
    const color = scoreColor(i / (BANDS.length - 1));
    const barW  = Math.round((counts[i] / maxCnt) * 100);
    const rangeTitle = `${b.lo.toFixed(2)}–${b.hi === Infinity ? "1.0+" : b.hi.toFixed(2)}`;

    // Neighbourhood accent: tick showing where nb average falls within this band
    let nbTick = "";
    if (nbAvgScore != null) {
      const normNb = _normalize(nbAvgScore);
      if (normNb >= b.lo && normNb < (b.hi === Infinity ? 2 : b.hi)) {
        const posWithinBand = b.hi === Infinity ? 0.5 : (normNb - b.lo) / (b.hi - b.lo);
        const tickPct = Math.round(posWithinBand * barW);
        nbTick = `<div class="dist-nb-tick" style="left:${tickPct}%"></div>`;
      }
    }

    return `<div class="dist-row">
      <span class="dist-label" style="color:${b.textColor}" title="${rangeTitle}">${b.label}</span>
      <div class="dist-track" style="position:relative">
        <div class="dist-fill" style="width:${barW}%;background:${color}"></div>
        ${nbTick}
      </div>
      <span class="dist-pct">${pct}%</span>
    </div>`;
  }).join("");
}
```

- [ ] **Step 5: Update callers of `drawDistribution`** — there are three call sites. All should pass `_nbAvgScore`:

```js
// Add module-level variable after _neighbourStopIds
let _nbAvgScore = null;
```

Update `initScatter`:
```js
export function initScatter(features) {
  const seen = new Set();
  _features = features.filter(f => {
    if (f.properties.context) return false;
    const key = f.properties.stop_id ?? `${f.geometry.coordinates}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  drawScatter(_currentGroup);
  drawDistribution(_currentGroup, _nbAvgScore);
}
```

Update `updateScatterGroup`:
```js
export function updateScatterGroup(group) {
  _currentGroup = group;
  drawScatter(group);
  drawDistribution(group, _nbAvgScore);
}
```

Update `updateScatterMode`:
```js
export function updateScatterMode() {
  drawDistribution(_currentGroup, _nbAvgScore);
}
```

- [ ] **Step 6: Add `updateNeighbourhoodFilter` export** — this is the single entry point called from scroll.js when the neighbourhood selector changes:

```js
/**
 * Apply neighbourhood filter to both scatter and distribution.
 * @param {Set<string>|null} stopIdSet  — Set of stop_id strings; null = clear filter
 * @param {number|null}      avgScore   — neighbourhood average score for distribution tick
 */
export function updateNeighbourhoodFilter(stopIdSet, avgScore) {
  _neighbourStopIds = stopIdSet;
  _nbAvgScore       = avgScore ?? null;
  drawScatter(_currentGroup);
  drawDistribution(_currentGroup, _nbAvgScore);
}
```

- [ ] **Step 7: Add CSS for distribution neighbourhood tick** — add to `web/css/style.css`:

```css
.dist-nb-tick {
  position: absolute;
  top: 0;
  width: 3px;
  height: 100%;
  background: #ff6700;
  border-radius: 1px;
  opacity: 0.9;
  pointer-events: none;
}
```

- [ ] **Step 8: Verify** — `bash scripts/dev.sh`, enter interactive mode. Scatter and distribution should look identical to before (neighbourhood filter not yet wired). No JS errors in console.

- [ ] **Step 9: Commit**

```bash
git add web/js/scatter.js web/css/style.css
git commit -m "feat: add neighbourhood dimming and distribution accent to scatter.js"
```

---

## Task 8: Update scroll.js — `_updatePeopleGreen` + stop selection + neighbourhood wiring

This is the largest task. It replaces the two old update functions (`_updateGreenBlock`, `_updateDemoBars`) with a unified `_updatePeopleGreen`, adds stop selection state, and wires the neighbourhood selector to all components.

**Files:**
- Modify: `web/js/scroll.js`

- [ ] **Step 1: Add new imports** — find the existing import block at the top of `scroll.js` and add:

```js
import {
  NEIGHBOURHOOD_POP, DISTRICT_POP
} from "./config.js";
import {
  getActiveNeighbourhood, setActiveNeighbourhood,
  getSelectedStop, setSelectedStop
} from "./state.js";
import {
  setNeighbourhoodBoundary, getNeighbourhoodFeatures, neighbourhoodForPoint
} from "./map.js";
import { updateNeighbourhoodFilter } from "./scatter.js";
```

- [ ] **Step 2: Delete `_updateGreenBlock` and `_updateDemoBars`** — remove both function definitions and the `NEIGHBOURHOOD_DATA` constant from `_initInteractiveTool`.

- [ ] **Step 3: Add `_updatePeopleGreen`** — add this function inside `_initInteractiveTool`, before the stop-select callbacks:

```js
  function _updatePeopleGreen(stopFeatures, selectedStopId, nbName) {
    if (!stopFeatures) return;
    const isBaseline = document.querySelector(".mode-btn.active")?.dataset.mode === "baseline";
    const internal = stopFeatures.filter(f => !f.properties.context);

    // ── Headline district KPIs ───────────────────────────────────────────────
    const sum = (col) => internal.reduce((s, f) => s + (+f.properties[col] || 0), 0);
    const avg = (col) => internal.length ? sum(col) / internal.length : 0;

    const popLow  = Math.round(sum("pop_wa_reach_low")  + sum("pop_el_reach_low")  + sum("pop_ch_reach_low"))  / internal.length;
    const popMid  = Math.round(sum("pop_wa_reach_mid")  + sum("pop_el_reach_mid")  + sum("pop_ch_reach_mid"))  / internal.length;
    const popHigh = Math.round(sum("pop_wa_reach_high") + sum("pop_el_reach_high") + sum("pop_ch_reach_high")) / internal.length;

    const fmtK  = (n) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(Math.round(n));
    const popRangeEl = document.getElementById("kpi-pop-range");
    if (popRangeEl) popRangeEl.textContent = `${fmtK(popLow)}–${fmtK(popHigh)}`;

    const greenDistEl    = document.getElementById("kpi-green-district");
    const greenLabelEl   = document.getElementById("kpi-green-district-label");
    if (greenDistEl) {
      if (isBaseline) {
        greenDistEl.textContent = `${(avg("green_pct_catchment") * 100).toFixed(0)}%`;
        if (greenLabelEl) greenLabelEl.textContent = "routes through parks";
      } else {
        greenDistEl.textContent = `${avg("green_time_working_age").toFixed(1)} min`;
        if (greenLabelEl) greenLabelEl.textContent = "avg min in green (WA)";
      }
    }

    // ── Per-group bars (census share + green annotation) ────────────────────
    const tot = DISTRICT_POP.total;
    for (const [suffix, field, waField, color] of [
      ["children",    "children",    "green_time_children",    "#c6dbef"],
      ["working-age", "working_age", "green_time_working_age", "#2171b5"],
      ["elderly",     "elderly",     "green_time_elderly",     "#6baed6"],
    ]) {
      const share = Math.round((DISTRICT_POP[field] / tot) * 100);
      const fillEl  = document.getElementById(`bar-${suffix}`);
      const pctEl   = document.getElementById(`pct-${suffix}`);
      const greenEl = document.getElementById(`green-ann-${suffix}`);
      if (fillEl)  { fillEl.style.width = `${share}%`; fillEl.style.background = color; }
      if (pctEl)   pctEl.textContent = `${share}%`;
      if (greenEl) {
        if (isBaseline) {
          greenEl.textContent = `${(avg("green_pct_catchment") * 100).toFixed(0)}%`;
        } else {
          greenEl.textContent = `${avg(waField).toFixed(1)}m`;
        }
      }
    }

    // ── Stop KPI row ─────────────────────────────────────────────────────────
    const stopRowEl = document.getElementById("kpi-stop-row");
    if (stopRowEl) {
      if (selectedStopId) {
        const feat = internal.find(f => f.properties.stop_id === selectedStopId);
        if (feat) {
          const p = feat.properties;
          const sPopLow  = (+p.pop_wa_reach_low  || 0) + (+p.pop_el_reach_low  || 0) + (+p.pop_ch_reach_low  || 0);
          const sPopHigh = (+p.pop_wa_reach_high || 0) + (+p.pop_el_reach_high || 0) + (+p.pop_ch_reach_high || 0);
          const stopNameEl = document.getElementById("kpi-stop-name");
          const stopPopEl  = document.getElementById("kpi-stop-pop");
          const stopGreenEl= document.getElementById("kpi-stop-green");
          if (stopNameEl)  stopNameEl.textContent = p.stop_name || p.stop_id;
          if (stopPopEl)   stopPopEl.textContent  = `${fmtK(sPopLow)}–${fmtK(sPopHigh)} people`;
          if (stopGreenEl) {
            stopGreenEl.textContent = isBaseline
              ? `${(+p.green_pct_catchment * 100 || 0).toFixed(0)}% green`
              : `${(+p.green_time_working_age || 0).toFixed(1)} min green`;
          }
          stopRowEl.classList.remove("hidden");
        }
      } else {
        stopRowEl.classList.add("hidden");
      }
    }

    // ── Neighbourhood comparison row ─────────────────────────────────────────
    const nbRowEl = document.getElementById("kpi-neighbourhood-row");
    if (nbRowEl) {
      if (nbName && NEIGHBOURHOOD_POP[nbName]) {
        const nb   = NEIGHBOURHOOD_POP[nbName];
        const nbStops = internal.filter(f => {
          const [lng, lat] = f.geometry.coordinates;
          return neighbourhoodForPoint([lng, lat]) === nbName;
        });
        const nbAvg = (col) => nbStops.length
          ? nbStops.reduce((s, f) => s + (+f.properties[col] || 0), 0) / nbStops.length
          : 0;
        const nbPopLow  = nbStops.reduce((s, f) => s + (+f.properties.pop_wa_reach_low  || 0) + (+f.properties.pop_el_reach_low  || 0) + (+f.properties.pop_ch_reach_low  || 0), 0) / (nbStops.length || 1);
        const nbPopHigh = nbStops.reduce((s, f) => s + (+f.properties.pop_wa_reach_high || 0) + (+f.properties.pop_el_reach_high || 0) + (+f.properties.pop_ch_reach_high || 0), 0) / (nbStops.length || 1);

        const nbNameEl  = document.getElementById("kpi-nb-name");
        const nbPopEl   = document.getElementById("kpi-nb-pop");
        const nbGreenEl = document.getElementById("kpi-nb-green");
        if (nbNameEl)  nbNameEl.textContent  = nbName.replace("-kvarteret", "");
        if (nbPopEl)   nbPopEl.textContent   = `${fmtK(nbPopLow)}–${fmtK(nbPopHigh)} people`;
        if (nbGreenEl) {
          nbGreenEl.textContent = isBaseline
            ? `${(nbAvg("green_pct_catchment") * 100).toFixed(0)}% green`
            : `${nbAvg("green_time_working_age").toFixed(1)} min green`;
        }
        nbRowEl.classList.remove("hidden");

        // Neighbourhood bar ticks — shows nb group share vs district share
        for (const [suffix, field] of [
          ["children", "children"], ["working-age", "working_age"], ["elderly", "elderly"]
        ]) {
          const nbShare  = Math.round((nb[field] / nb.total) * 100);
          const tickEl   = document.getElementById(`nb-tick-${suffix}`);
          if (tickEl) {
            tickEl.style.left = `${nbShare}%`;
            tickEl.classList.remove("hidden");
          }
        }
      } else {
        nbRowEl.classList.add("hidden");
        ["children", "working-age", "elderly"].forEach(s => {
          document.getElementById(`nb-tick-${s}`)?.classList.add("hidden");
        });
      }
    }
  }
```

- [ ] **Step 4: Update stop-select callbacks** — replace the two `setStopSelectCallback` / `setScatterSelectCallback` blocks with:

```js
  setStopSelectCallback(id => {
    setSelectedStop(id);
    highlightScatterStop(id);
    _updatePeopleGreen(getStopFeatures(), id, getActiveNeighbourhood());
  });
  setScatterSelectCallback(id => {
    setSelectedStop(id);
    highlightMapStop(id);
    _updatePeopleGreen(getStopFeatures(), id, getActiveNeighbourhood());
  });
```

- [ ] **Step 5: Wire stop close button** — add after the callbacks:

```js
  document.getElementById("kpi-stop-close")?.addEventListener("click", () => {
    setSelectedStop(null);
    highlightMapStop(null);
    highlightScatterStop(null);
    _updatePeopleGreen(getStopFeatures(), null, getActiveNeighbourhood());
  });
```

- [ ] **Step 6: Update `enterBtn` callback** — replace the existing `tryInit` block inside the enter button listener:

```js
      const tryInit = () => {
        const features = getStopFeatures();
        if (features) {
          initScatter(features);
          _updatePeopleGreen(features, null, "");
        } else {
          setTimeout(tryInit, 200);
        }
      };
      tryInit();
```

- [ ] **Step 7: Wire neighbourhood selector** — replace the existing `nSel.addEventListener` block with:

```js
  const nSel = document.getElementById("neighbourhood-select");
  if (nSel) {
    nSel.addEventListener("change", () => {
      const nbName = nSel.value;
      setActiveNeighbourhood(nbName);
      setNeighbourhoodBoundary(nbName);

      const features = getStopFeatures();
      if (nbName && features) {
        const internal  = features.filter(f => !f.properties.context);
        const nbStopIds = new Set(
          internal
            .filter(f => neighbourhoodForPoint(f.geometry.coordinates) === nbName)
            .map(f => String(f.properties.stop_id))
        );
        const isBaseline = document.querySelector(".mode-btn.active")?.dataset.mode === "baseline";
        const scoreKey   = isBaseline ? "score_catchment" : "score_health_combined";
        const nbStopArr  = internal.filter(f => nbStopIds.has(String(f.properties.stop_id)));
        const nbAvg      = nbStopArr.length
          ? nbStopArr.reduce((s, f) => s + (+f.properties[scoreKey] || 0), 0) / nbStopArr.length
          : null;
        updateNeighbourhoodFilter(nbStopIds, nbAvg);
      } else {
        updateNeighbourhoodFilter(null, null);
      }

      _updatePeopleGreen(features, getSelectedStop(), nbName);
    });
  }
```

- [ ] **Step 8: Update mode toggle handler** — find the mode button event listener added in Task 4 and replace the `_updatePeopleGreen` call placeholder:

```js
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const mode = btn.dataset.mode;
      setScoreMode(mode);
      updateScatterMode();
      _updatePeopleGreen(getStopFeatures(), getSelectedStop(), getActiveNeighbourhood());
    });
  });
```

- [ ] **Step 9: Verify** — `bash scripts/dev.sh`, enter interactive mode:
  - Population KPI row shows a range (e.g. "19.5k–20.1k")
  - Green metric shows min or %
  - Click a stop → stop KPI row slides in with that stop's data, × button dismisses it
  - Select a neighbourhood → boundary outline appears on map, scatter dims out-of-neighbourhood stops, neighbourhood comparison row appears in People + Green

- [ ] **Step 10: Commit**

```bash
git add web/js/scroll.js web/js/state.js
git commit -m "feat: unified _updatePeopleGreen, stop selection state, neighbourhood selector wiring"
```

---

## Task 9: Update PROGRESS.md + CLAUDE.md

- [ ] **Step 1: Mark tasks 8 and 9 complete in PROGRESS.md** — update the two items:

```markdown
~~8. **Right panel MVP redesign**~~ ✅ DONE — Floating mode toggle, collapsible left panel, merged People + Green section with real flat-decay population data (pop_*_reach_*), stop KPI row, neighbourhood comparison row.

~~9. **Neighbourhood highlighter**~~ ✅ DONE — Neighbourhood selector in chart-panel header drives: map boundary outline, scatter dimming, distribution accent tick, People + Green comparison row and bar ticks.
```

- [ ] **Step 2: Update CLAUDE.md** — update the "Immediate Next Steps" section to remove tasks 8 and 9 and advance to the next priority.

- [ ] **Step 3: Commit**

```bash
git add PROGRESS.md CLAUDE.md
git commit -m "docs: mark tasks 8+9 complete in PROGRESS.md and CLAUDE.md"
```

---

## Self-review

**Spec coverage check:**
- ✅ Floating mode toggle top-centre — Task 4
- ✅ `data-info="score"` popup relocated to float toggle — Task 4
- ✅ Collapsible left panel with localStorage — Task 5
- ✅ Right panel header: neighbourhood selector + `data-info="neighbourhood"` — Task 6
- ✅ People + Green merged section with `data-info="people-green"` — Task 6
- ✅ Headline KPI row (population range + green metric) — Task 8
- ✅ Stop KPI row on stop click with × close — Task 8
- ✅ Per-group bars with green annotation — Task 8
- ✅ Neighbourhood comparison row — Task 8
- ✅ Neighbourhood bar ticks — Task 8
- ✅ Map boundary layer — Task 3
- ✅ Scatter dimming — Task 7
- ✅ Distribution accent tick — Task 7
- ✅ `NEIGHBOURHOOD_POP` in config.js — Task 1
- ✅ Point-in-polygon for stop containment — Task 3
- ✅ Existing `data-info="group"`, `data-info="overlays"`, `data-info="distribution"`, `data-info="scatter"` — untouched, continue working

**Type consistency check:**
- `neighbourhoodForPoint([lng, lat])` — used in scroll.js Tasks 8 step 3 and step 7. Import added in Task 8 step 1. ✅
- `filterByNeighbourhood` in scatter.js replaced by `updateNeighbourhoodFilter` which is the exported function. scroll.js calls `updateNeighbourhoodFilter`. ✅
- `getStopFeatures()` returns `_stopFeatures` from map.js. Already exported. ✅
- `nb-tick-working-age` (HTML id) vs `nb-tick-working_age` (underscore in loop) — **FIXED**: loop uses `"working-age"` with hyphen to match the HTML id `nb-tick-working-age`. ✅
- `demo-bar-green` CSS class vs `green-ann-{suffix}` id — CSS targets `.demo-bar-green` (the class), JS targets `#green-ann-{suffix}` (the id). Both present on the same element in Task 6 HTML. ✅
- `getStopFeatures()` called before features are loaded → returns null, `_updatePeopleGreen` guards with `if (!stopFeatures) return`. ✅
