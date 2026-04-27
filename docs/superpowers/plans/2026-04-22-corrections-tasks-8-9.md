# Corrections: Tasks 8–9 Right-Panel & Interactive Tool

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two bugs and ship eight UI improvements to the interactive tool panel, as listed in `docs/superpowers/2026-04-21-corrections_tasks_8_9.md`.

**Architecture:** All changes are isolated to `web/` — HTML structure, CSS, and three JS modules (`map.js`, `scatter.js`, `scroll.js`). One data pipeline fix (Frederiksberg parks) requires a processing script edit + re-export + re-score. No new files needed; all edits are in-place.

**Tech Stack:** MapLibre GL JS, Scrollama, vanilla JS ES modules, CSS custom properties.

---

## File Map

| File | Changes |
|---|---|
| `web/index.html` | Neighbourhood dropdown, distribution header, people+green block, left panel collapse btn, stop size control |
| `web/css/style.css` | Collapse btn affordance, neighbourhood dropdown title style, dist-nr-marker (black), people+green 70/30 layout, chart-panel min-width |
| `web/js/map.js` | Separate catchment ramp domain, neighbourhood polygon fill layer (grey), stop size by data |
| `web/js/scatter.js` | Fixed 0–1 axes, Y-axis label format, distribution redesign (% bars + Nørrebro marker) |
| `web/js/scroll.js` | People+green HTML rewrite + `_updatePeopleGreen` logic update |
| `scripts/process/process_greenspaces.py` (or equivalent) | Extend clip to 1000 m buffer for Frederiksberg parks |

---

## Task 1: Fix Stop Colour Ramp in Catchment Mode

**Bug:** `_rampLo`/`_rampHi` in `map.js` are computed from `score_health_combined` values. When baseline/catchment mode activates, `_buildRamp("score_catchment")` still uses the health domain → catchment scores all map to the same end of the ramp → all stops render blue.

**Files:**
- Modify: `web/js/map.js` — around lines 11–12 (`_rampLo/_rampHi`) and lines 670–684 (domain calculation)

- [ ] **Step 1: Add a second ramp domain pair for catchment scores**

In `map.js` at the top where `_rampLo` and `_rampHi` are declared (lines 11–12), add:

```javascript
let _rampLo = null;
let _rampHi = null;
let _catchRampLo = null;   // ← add
let _catchRampHi = null;   // ← add
```

- [ ] **Step 2: Compute the catchment domain alongside the health domain**

In the function that sets `_rampLo/_rampHi` from features (around line 670):

```javascript
// Existing: health domain from score_health_combined
const hVals = features.map(f => +f.properties.score_health_combined).filter(v => !isNaN(v));
if (!hVals.length) return;
hVals.sort((a, b) => a - b);
_rampLo = hVals[0];
_rampHi = hVals[hVals.length - 1];

// ← Add: catchment domain from score_catchment
const cVals = features.map(f => +f.properties.score_catchment).filter(v => !isNaN(v));
if (cVals.length) {
  cVals.sort((a, b) => a - b);
  _catchRampLo = cVals[0];
  _catchRampHi = cVals[cVals.length - 1];
}
```

- [ ] **Step 3: Update `_buildRamp` to select the right domain**

```javascript
function _buildRamp(field) {
  const isCatch = field === "score_catchment";
  const lo = isCatch ? _catchRampLo : _rampLo;
  const hi = isCatch ? _catchRampHi : _rampHi;
  if (lo === null) return ["get", field];
  const at = (t) => lo + (hi - lo) * t;
  return [
    "interpolate", ["linear"], ["get", field],
    at(0.0), "#ff6700",
    at(0.25), "#e8b86d",
    at(0.5),  "#b0b8c8",
    at(0.75), "#6b9fd4",
    at(1.0),  "#004e98",
  ];
}
```

(Preserve the existing colour stops — just fix the domain.)

- [ ] **Step 4: Verify in browser — switch to Catchment Score mode, stops should show gradient from orange → blue**

---

## Task 2: Fix Mode Toggle Float Not Visible

**Bug:** `#mode-toggle-float` is shown by `enterInteractiveTool()` (map.js:453) but is not appearing. Likely a CSS z-index or positioning conflict with the tab bar.

**Files:**
- Investigate: `web/css/style.css` — `#mode-toggle-float` block (around lines 1130–1177)
- Investigate: `web/index.html` — tab bar z-index

- [ ] **Step 1: Open the app, enter the interactive tool (Bus tab → "Explore the map →"), open browser DevTools, inspect `#mode-toggle-float`**

Check: Is the element present? Does it have `display:none`? Is it hidden behind another element?

Expected cause: the tab bar (`#tab-nav` or similar) is `position:fixed` with a higher `z-index` than 120, covering the toggle at `top:14px`.

- [ ] **Step 2: Find the tab bar z-index in `style.css`** and raise `#mode-toggle-float`'s z-index above it:

```css
#mode-toggle-float {
  /* existing props … */
  z-index: 650;          /* ← raise above tab bar + tool-panel (600) */
  top: 14px;
}
```

If the tab bar is at e.g. `top: 0; height: 48px`, also adjust:

```css
#mode-toggle-float {
  top: 58px;   /* clear the tab bar */
}
```

- [ ] **Step 3: Verify the toggle appears and is clickable when in interactive mode**

- [ ] **Step 4: Verify it disappears when returning to scrollytelling (`backToNarrative`)**

---

## Task 3: Fix Scatter Axes — Fixed 0–1 Domain, 0.25 Ticks

**Files:**
- Modify: `web/js/scatter.js` — `drawScatter` function (lines 199–320), `GROUP_LABEL` map (top of file)

- [ ] **Step 1: Update `GROUP_LABEL` to use the new Y-axis label format**

```javascript
const GROUP_LABEL = {
  aggregate:   "Health Score (All)",
  working_age: "Health Score (Working age)",
  elderly:     "Health Score (Elderly)",
  children:    "Health Score (Children)",
};
```

- [ ] **Step 2: Replace dynamic domain with fixed 0–1 in `drawScatter`**

Replace lines 212–222 (dynamic domain calculation + `px`/`py` functions):

```javascript
// Fixed domain: always 0–1
const xDomMin = 0, xDomMax = 1;
const yDomMin = 0, yDomMax = 1;

const px = v => ML + v * PW;
const py = v => MT + PH * (1 - v);
```

- [ ] **Step 3: Update grid/ticks to fixed 0, 0.25, 0.5, 0.75, 1.0**

Replace the NTICKS loop (lines 244–253) with:

```javascript
for (let i = 0; i <= 4; i++) {
  const t = i / 4;   // 0, 0.25, 0.5, 0.75, 1.0
  svg.appendChild(el("line", { x1: px(t), y1: MT, x2: px(t), y2: MT + PH, stroke: "#f0f0f0", "stroke-width": 1 }));
  svg.appendChild(el("line", { x1: ML, y1: py(t), x2: ML + PW, y2: py(t), stroke: "#f0f0f0", "stroke-width": 1 }));
  svg.appendChild(el("text", { x: px(t), y: MT + PH + 11, "font-size": 8.5, fill: "#888", "text-anchor": "middle" }, t.toFixed(2)));
  svg.appendChild(el("text", { x: ML - 4, y: py(t) + 3,   "font-size": 8.5, fill: "#888", "text-anchor": "end"    }, t.toFixed(2)));
}
```

- [ ] **Step 4: Update the diagonal line to span the full [0,1] plot**

```javascript
svg.appendChild(el("line", {
  x1: px(0), y1: py(0),
  x2: px(1), y2: py(1),
  stroke: "#ccc", "stroke-width": 1, "stroke-dasharray": "4,3",
}));
```

- [ ] **Step 5: Update X-axis label text**

```javascript
svg.appendChild(el("text", {
  x: ML + PW / 2, y: H - 2,
  "font-size": 9, fill: "#555", "text-anchor": "middle",
}, "Catchment Score"));
```

And Y-axis (already uses `yLabel` from `GROUP_LABEL[group]` — no change needed there).

- [ ] **Step 6: Open browser, switch demographic groups, verify axes are always 0–0.25–0.5–0.75–1.0**

---

## Task 4: Neighbourhood Polygon Layer — Grey Fill, No Border

**Files:**
- Modify: `web/js/map.js` — `neighbourhood-boundary` layer setup (around line 260) and `setNeighbourhoodBoundary` function

- [ ] **Step 1: Replace the line layer with a fill layer, inserted before data layers**

Find the `neighbourhood-boundary` layer setup (around line 260). Replace it with:

```javascript
// Grey fill polygon — must be added BEFORE segment/stop layers so it sits behind data
map.addLayer({
  id: "neighbourhood-fill",
  type: "fill",
  source: "neighbourhoods-src",
  filter: ["==", ["get", "neighbourhood_name"], ""],
  paint: {
    "fill-color": "#9ca3af",   // neutral grey
    "fill-opacity": 0.18,
  },
}, "segments-aggregate");   // second arg = layer to insert BEFORE
```

(Remove the old `neighbourhood-boundary` line layer entirely.)

- [ ] **Step 2: Update `setNeighbourhoodBoundary` to filter the new fill layer**

```javascript
export function setNeighbourhoodBoundary(name) {
  _neighbourhoodFeatures = name ? ... : null;
  const filter = name
    ? ["==", ["get", "neighbourhood_name"], name]
    : ["==", ["get", "neighbourhood_name"], ""];
  if (map.getLayer("neighbourhood-fill"))
    map.setFilter("neighbourhood-fill", filter);
}
```

- [ ] **Step 3: Verify: selecting a neighbourhood shows a light grey polygon behind all data layers**

---

## Task 5: Neighbourhood Dropdown — Title Style, No Box

**Files:**
- Modify: `web/index.html` — neighbourhood select element
- Modify: `web/css/style.css` — `.neighbourhood-panel-sel`

- [ ] **Step 1: Update the select CSS to look like a plain title with a native dropdown arrow**

In `style.css`, replace the `.neighbourhood-panel-sel` block:

```css
.neighbourhood-panel-sel {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  padding: 0 1.2rem 0 0;
  cursor: pointer;
  appearance: auto;   /* keep native dropdown arrow */
  flex: 1;
  outline: none;
  letter-spacing: 0.01em;
}

.neighbourhood-panel-sel:hover {
  border-bottom-color: var(--border);
}
```

- [ ] **Step 2: Verify: the dropdown looks like a bold heading with a native arrow; clicking still opens the neighbourhood list**

---

## Task 6: Distribution Section — Remove Header, Add Nørrebro Marker

**Files:**
- Modify: `web/index.html` — distribution `chart-block`
- Modify: `web/css/style.css` — add `.dist-nr-marker`
- Modify: `web/js/scatter.js` — `drawDistribution`, `updateNeighbourhoodFilter`

- [ ] **Step 1: Remove the "Distribution" header text from HTML**

In `index.html`, find the distribution `chart-block-header`:

```html
<div class="chart-block-header">
  Distribution
  <button class="btn-icon" data-info="distribution" ...>ⓘ</button>
</div>
<p class="chart-subtitle">What share of stops are optimally placed?</p>
```

Change to (keep only the ⓘ button, remove text and subtitle):

```html
<div class="chart-block-header">
  <button class="btn-icon" data-info="distribution" aria-label="About score distribution">ⓘ</button>
</div>
```

- [ ] **Step 2: Add black marker CSS for the Nørrebro baseline line**

In `style.css`, find the `.dist-nb-tick` rule and add a new `.dist-nr-marker` rule:

```css
.dist-nr-marker {
  position: absolute;
  top: 0;
  width: 2px;
  height: 100%;
  background: #111827;   /* var(--text) — near-black */
  border-radius: 1px;
  pointer-events: none;
}
```

- [ ] **Step 3: Redesign `drawDistribution` in `scatter.js` — bars show % not count/maxCount; add Nørrebro marker when neighbourhood active**

The function currently takes `(group, nbAvgScore)`. Change signature to `(group)` — it reads `_neighbourStopIds` from module state (already stored at line 292).

```javascript
function drawDistribution(group) {
  const container = document.getElementById("distribution-container");
  if (!container || !_features?.length) return;

  const isBaseline = document.querySelector(".mode-btn.active")?.dataset.mode === "baseline";
  const scoreKey   = isBaseline ? "score_catchment" : (GROUP_Y_FIELD[group] || GROUP_Y_FIELD.aggregate);

  const allVals  = _features.map(f => _normalize(+(f.properties[scoreKey]) || 0));
  const n        = allVals.length;

  // Nørrebro-wide band percentages
  const nrCounts = BANDS.map(b => allVals.filter(v => v >= b.lo && v < (b.hi === Infinity ? 2 : b.hi)).length);
  const nrPcts   = nrCounts.map(c => n > 0 ? Math.round((c / n) * 100) : 0);

  // Neighbourhood band percentages (if selected)
  let nbPcts = null;
  if (_neighbourStopIds?.size) {
    const nbVals = _features
      .filter(f => _neighbourStopIds.has(String(f.properties.stop_id)))
      .map(f => _normalize(+(f.properties[scoreKey]) || 0));
    const nbN = nbVals.length;
    const nbCounts = BANDS.map(b => nbVals.filter(v => v >= b.lo && v < (b.hi === Infinity ? 2 : b.hi)).length);
    nbPcts = nbCounts.map(c => nbN > 0 ? Math.round((c / nbN) * 100) : 0);
  }

  container.innerHTML = BANDS.map((b, i) => {
    const displayPct = nbPcts ? nbPcts[i] : nrPcts[i];
    const color = scoreColor(i / (BANDS.length - 1));

    // Black Nørrebro marker (only when neighbourhood is active)
    const nrMarker = nbPcts
      ? `<div class="dist-nr-marker" style="left:${nrPcts[i]}%"></div>`
      : "";

    return `<div class="dist-row">
      <span class="dist-label" style="color:${b.textColor}">${b.label}</span>
      <div class="dist-track" style="position:relative">
        <div class="dist-fill" style="width:${displayPct}%;background:${color}"></div>
        ${nrMarker}
      </div>
      <span class="dist-pct">${displayPct}%</span>
    </div>`;
  }).join("");
}
```

- [ ] **Step 4: Update all callers of `drawDistribution` — remove the second argument everywhere**

Search scatter.js for `drawDistribution(` and remove any second argument.

- [ ] **Step 5: Verify — selecting "Guldbergskvarteret" shows narrower bars with a black vertical line at Nørrebro's position**

---

## Task 7: Improve Collapse Button Affordance

**Files:**
- Modify: `web/index.html` — `#tool-panel-collapse`
- Modify: `web/css/style.css` — collapse button styles

- [ ] **Step 1: Update the button HTML to include a text label**

In `index.html`, find `#tool-panel-collapse`:

```html
<button id="tool-panel-collapse" aria-label="Collapse panel" title="Collapse panel">‹</button>
```

Replace with:

```html
<button id="tool-panel-collapse" aria-label="Collapse panel">
  <span class="collapse-arrow">‹</span>
  <span class="collapse-label">Hide</span>
</button>
```

- [ ] **Step 2: Style the updated button**

In `style.css`, replace the `#tool-panel-collapse` block with:

```css
#tool-panel-collapse {
  position: absolute;
  right: -28px;
  top: 12px;
  display: flex;
  align-items: center;
  gap: 3px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 3px 6px;
  cursor: pointer;
  color: var(--muted);
  font-size: 0.68rem;
  font-family: var(--font-mono);
  line-height: 1;
  z-index: 10;
  white-space: nowrap;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  transition: color 0.15s, border-color 0.15s;
}

#tool-panel-collapse:hover {
  color: var(--text);
  border-color: var(--text);
}

#tool-panel-collapse .collapse-arrow {
  font-size: 1rem;
  line-height: 1;
  transition: transform 0.2s;
}

#tool-panel.collapsed #tool-panel-collapse .collapse-arrow {
  transform: rotate(180deg);
}

#tool-panel.collapsed #tool-panel-collapse .collapse-label {
  display: none;   /* hide "Hide" text when collapsed to save space */
}
```

- [ ] **Step 3: Verify: panel shows a small "‹ Hide" tab; when collapsed, shows just "›"**

---

## Task 8: Redesign People + Green Block

**Files:**
- Modify: `web/index.html` — `#people-green-block` section
- Modify: `web/css/style.css` — new 70/30 layout styles
- Modify: `web/js/scroll.js` — `_updatePeopleGreen` to match new HTML

- [ ] **Step 1: Increase default chart panel width to prevent column stacking**

In `style.css`, find `--chart-panel-w` default (likely in `:root` or `.interactive-layout`):

```css
:root {
  --chart-panel-w: 340px;   /* was 280px — needs to be wider for 70/30 layout */
}
```

Also update the drag-resize minimum in scroll.js:

```javascript
const newW = Math.max(320, Math.min(520, _startW + (_startX - ev.clientX)));
```

- [ ] **Step 2: Rewrite `#people-green-block` HTML**

Replace the entire `<div class="chart-block" id="people-green-block">` with:

```html
<div class="chart-block" id="people-green-block">
  <!-- ⓘ button only, no title -->
  <div class="pg-header">
    <button class="btn-icon" data-info="people-green" aria-label="About population reach">ⓘ</button>
  </div>
  <div class="info-popup hidden" id="info-popup-people-green">
    <p>Population figures show residents reachable within each group's maximum walk time on the pedestrian network (working-age: 10 min / 840m; elderly: 8 min / 432m; children: 7 min / 420m). The range (low–high) reflects uncertainty in the population model. Green time shows average minutes of that walk spent through park space.</p>
  </div>

  <!-- Fixed row: district / neighbourhood headline -->
  <div class="pg-row pg-row--headline" id="pg-headline-row">
    <div class="pg-col-people">
      <div class="pg-big-num" id="pg-headline-pop">—</div>
      <div class="pg-big-label" id="pg-headline-label">people in Nørrebro</div>
    </div>
    <div class="pg-col-green">
      <div class="pg-big-num" id="pg-headline-green">—</div>
      <div class="pg-big-label" id="pg-headline-green-label">avg min in green</div>
    </div>
  </div>

  <!-- Click-based row: selected stop (hidden until stop clicked) -->
  <div class="pg-row pg-row--stop hidden" id="pg-stop-row">
    <div class="pg-col-people">
      <div class="pg-stop-num" id="pg-stop-pop">—</div>
      <div class="pg-stop-label">
        <span id="pg-stop-name">—</span> catchment
        <button class="pg-stop-close" id="pg-stop-close" aria-label="Clear stop">×</button>
      </div>
    </div>
    <div class="pg-col-green">
      <div class="pg-stop-num" id="pg-stop-green">—</div>
      <div class="pg-stop-label">avg min in green</div>
    </div>
  </div>

  <!-- Per-group rows -->
  <div class="pg-groups">
    <div class="pg-group-row" id="pg-group-children">
      <div class="pg-col-people">
        <div class="pg-group-label">Children <span class="pg-group-age">0–14</span></div>
        <div class="pg-group-bar-wrap">
          <div class="pg-group-bar-track">
            <div class="pg-group-bar-fill" id="pgbar-children" style="width:13%"></div>
          </div>
          <span class="pg-group-pct" id="pg-pct-children">13%</span>
          <span class="pg-group-unc" id="pg-unc-children"></span>
        </div>
      </div>
      <div class="pg-col-green">
        <div class="pg-group-green-val" id="pg-green-children">—</div>
        <div class="pg-group-green-sub" id="pg-greenpath-children">—</div>
      </div>
    </div>

    <div class="pg-group-row" id="pg-group-working-age">
      <div class="pg-col-people">
        <div class="pg-group-label">Working age <span class="pg-group-age">15–64</span></div>
        <div class="pg-group-bar-wrap">
          <div class="pg-group-bar-track">
            <div class="pg-group-bar-fill" id="pgbar-working-age" style="width:78%"></div>
          </div>
          <span class="pg-group-pct" id="pg-pct-working-age">78%</span>
          <span class="pg-group-unc" id="pg-unc-working-age"></span>
        </div>
      </div>
      <div class="pg-col-green">
        <div class="pg-group-green-val" id="pg-green-working-age">—</div>
        <div class="pg-group-green-sub" id="pg-greenpath-working-age">—</div>
      </div>
    </div>

    <div class="pg-group-row" id="pg-group-elderly">
      <div class="pg-col-people">
        <div class="pg-group-label">Elderly <span class="pg-group-age">65+</span></div>
        <div class="pg-group-bar-wrap">
          <div class="pg-group-bar-track">
            <div class="pg-group-bar-fill" id="pgbar-elderly" style="width:8%"></div>
          </div>
          <span class="pg-group-pct" id="pg-pct-elderly">8%</span>
          <span class="pg-group-unc" id="pg-unc-elderly"></span>
        </div>
      </div>
      <div class="pg-col-green">
        <div class="pg-group-green-val" id="pg-green-elderly">—</div>
        <div class="pg-group-green-sub" id="pg-greenpath-elderly">—</div>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Add CSS for the new 70/30 layout**

In `style.css`, after the existing people+green CSS block, add:

```css
/* People+Green redesign — 70/30 two-column, no divider */
.pg-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 0.25rem;
}

.pg-row {
  display: grid;
  grid-template-columns: 70% 30%;
  gap: 0;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.pg-row.hidden { display: none; }

.pg-col-people,
.pg-col-green {
  padding: 0 4px;
}

.pg-big-num {
  font-size: 1.4rem;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text);
  line-height: 1.1;
}

.pg-big-label {
  font-size: 0.67rem;
  color: var(--muted);
  margin-top: 1px;
}

.pg-stop-num {
  font-size: 1.1rem;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--muted);
  line-height: 1.1;
}

.pg-stop-label {
  font-size: 0.65rem;
  color: var(--muted);
  margin-top: 1px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.pg-stop-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--muted);
  font-size: 0.8rem;
  padding: 0 2px;
  line-height: 1;
}

.pg-groups {
  margin-top: 4px;
}

.pg-group-row {
  display: grid;
  grid-template-columns: 70% 30%;
  padding: 4px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.pg-group-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: #2e7d32;
  margin-bottom: 3px;
}

.pg-group-age {
  font-weight: 400;
  color: var(--muted);
}

.pg-group-bar-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pg-group-bar-track {
  flex: 1;
  height: 5px;
  background: var(--border-subtle);
  border-radius: 3px;
  overflow: hidden;
}

.pg-group-bar-fill {
  height: 100%;
  border-radius: 3px;
  background: #4caf50;
  transition: width 0.3s ease;
}

.pg-group-pct {
  font-size: 0.65rem;
  font-family: var(--font-mono);
  color: #2e7d32;
  white-space: nowrap;
}

.pg-group-unc {
  font-size: 0.6rem;
  color: var(--muted);
  white-space: nowrap;
}

.pg-group-green-val {
  font-size: 0.8rem;
  font-weight: 600;
  font-family: var(--font-mono);
  color: #2e7d32;
}

.pg-group-green-sub {
  font-size: 0.63rem;
  color: var(--muted);
}
```

- [ ] **Step 4: Rewrite `_updatePeopleGreen` in `scroll.js` to target the new element IDs**

Replace the entire `_updatePeopleGreen` function (lines 290–398) with:

```javascript
function _updatePeopleGreen(stopFeatures, selectedStopId, nbName) {
  if (!stopFeatures) return;
  const isBaseline = document.querySelector(".mode-btn.active")?.dataset.mode === "baseline";
  const internal = stopFeatures.filter(f => !f.properties.context);

  const sum  = (col) => internal.reduce((s, f) => s + (+f.properties[col] || 0), 0);
  const avg  = (col) => internal.length ? sum(col) / internal.length : 0;
  const fmtK = (n) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(Math.round(n));
  const fmtPct = (n) => `${(n * 100).toFixed(0)}%`;
  const fmtMin = (n) => `${n.toFixed(1)} min`;

  // ── Headline row (district or neighbourhood) ──────────────────────────────
  const source = nbName && NEIGHBOURHOOD_POP[nbName] ? "nb" : "district";
  const headlineStops = source === "nb"
    ? internal.filter(f => neighbourhoodForPoint(f.geometry.coordinates) === nbName)
    : internal;

  const hsAvg = (col) => headlineStops.length
    ? headlineStops.reduce((s, f) => s + (+f.properties[col] || 0), 0) / headlineStops.length : 0;
  const hPopLow  = headlineStops.reduce((s, f) => s + (+f.properties.pop_wa_reach_low  || 0) + (+f.properties.pop_el_reach_low  || 0) + (+f.properties.pop_ch_reach_low  || 0), 0) / (headlineStops.length || 1);
  const hPopHigh = headlineStops.reduce((s, f) => s + (+f.properties.pop_wa_reach_high || 0) + (+f.properties.pop_el_reach_high || 0) + (+f.properties.pop_ch_reach_high || 0), 0) / (headlineStops.length || 1);

  const popEl    = document.getElementById("pg-headline-pop");
  const labelEl  = document.getElementById("pg-headline-label");
  const greenEl  = document.getElementById("pg-headline-green");
  const gLabelEl = document.getElementById("pg-headline-green-label");

  if (popEl)    popEl.textContent   = `${fmtK(hPopLow)}–${fmtK(hPopHigh)}`;
  if (labelEl)  labelEl.textContent = source === "nb" ? `people in ${nbName.replace("-kvarteret", "")}` : "people in Nørrebro";
  if (greenEl) {
    greenEl.textContent = isBaseline
      ? fmtPct(hsAvg("green_pct_catchment"))
      : fmtMin(hsAvg("green_time_working_age"));
  }
  if (gLabelEl) gLabelEl.textContent = isBaseline ? "routes through parks" : "avg min in green (WA)";

  // ── Stop row ─────────────────────────────────────────────────────────────
  const stopRow = document.getElementById("pg-stop-row");
  if (stopRow) {
    if (selectedStopId) {
      const feat = internal.find(f => f.properties.stop_id === selectedStopId);
      if (feat) {
        const p = feat.properties;
        const sLow  = (+p.pop_wa_reach_low  || 0) + (+p.pop_el_reach_low  || 0) + (+p.pop_ch_reach_low  || 0);
        const sHigh = (+p.pop_wa_reach_high || 0) + (+p.pop_el_reach_high || 0) + (+p.pop_ch_reach_high || 0);
        document.getElementById("pg-stop-pop")?.setAttribute("textContent", `${fmtK(sLow)}–${fmtK(sHigh)}`);
        document.getElementById("pg-stop-pop").textContent = `${fmtK(sLow)}–${fmtK(sHigh)}`;
        document.getElementById("pg-stop-name").textContent = p.stop_name || p.stop_id;
        const stopGreenEl = document.getElementById("pg-stop-green");
        if (stopGreenEl) stopGreenEl.textContent = isBaseline
          ? fmtPct(+p.green_pct_catchment || 0)
          : fmtMin(+p.green_time_working_age || 0);
        stopRow.classList.remove("hidden");
      }
    } else {
      stopRow.classList.add("hidden");
    }
  }

  // ── Per-group bars ────────────────────────────────────────────────────────
  const tot = DISTRICT_POP.total;
  for (const [suffix, field, waField, lowField, highField] of [
    ["children",    "children",    "green_time_children",    "pop_ch_reach_low",  "pop_ch_reach_high"],
    ["working-age", "working_age", "green_time_working_age", "pop_wa_reach_low",  "pop_wa_reach_high"],
    ["elderly",     "elderly",     "green_time_elderly",     "pop_el_reach_low",  "pop_el_reach_high"],
  ]) {
    const share = Math.round((DISTRICT_POP[field] / tot) * 100);
    const avgLow  = avg(lowField);
    const avgHigh = avg(highField);
    const uncPct  = avgLow > 0 ? Math.round(((avgHigh - avgLow) / (2 * ((avgLow + avgHigh) / 2))) * 100) : 0;

    document.getElementById(`pgbar-${suffix}`)?.style.setProperty("width", `${share}%`);
    const pctEl = document.getElementById(`pg-pct-${suffix}`);
    if (pctEl) pctEl.textContent = `${share}%`;
    const uncEl = document.getElementById(`pg-unc-${suffix}`);
    if (uncEl && uncPct > 0) uncEl.textContent = `± ${uncPct}%`;

    const greenValEl  = document.getElementById(`pg-green-${suffix}`);
    const greenSubEl  = document.getElementById(`pg-greenpath-${suffix}`);
    if (greenValEl) greenValEl.textContent = isBaseline
      ? fmtPct(avg("green_pct_catchment"))
      : fmtMin(avg(waField));
    if (greenSubEl) greenSubEl.textContent = isBaseline ? "routes in parks" : "avg min in green";
  }
}
```

- [ ] **Step 5: Wire `#pg-stop-close` in `initToolPanel`**

```javascript
document.getElementById("pg-stop-close")?.addEventListener("click", () => {
  setSelectedStop(null);
  highlightMapStop(null);
  highlightScatterStop(null);
  _updatePeopleGreen(getStopFeatures(), null, getActiveNeighbourhood());
});
```

(Remove the old `#kpi-stop-close` listener.)

- [ ] **Step 6: Remove stale element ID references — search `scroll.js` for `kpi-pop-range`, `kpi-green-district`, `kpi-nb-`, `kpi-stop-` and verify none remain**

- [ ] **Step 7: Open browser, verify layout doesn't stack at default panel width (340px), test: no stop selected, stop clicked, neighbourhood selected**

---

## Task 9: Stop Size Control

**Files:**
- Modify: `web/index.html` — left panel `#tool-panel`
- Modify: `web/js/map.js` — `_applyStopSize` function
- Modify: `web/js/scroll.js` — `initToolPanel` wiring

- [ ] **Step 1: Add radio buttons to the left panel in `index.html`**

After the overlays `ctrl-section`, add:

```html
<div class="ctrl-section">
  <div class="ctrl-section-header">
    <span class="ctrl-label">Stop size</span>
  </div>
  <label class="toggle-row">
    <input type="radio" name="stop-size" value="none" checked /> Uniform
  </label>
  <label class="toggle-row">
    <input type="radio" name="stop-size" value="people" /> People in catchment
  </label>
  <label class="toggle-row">
    <input type="radio" name="stop-size" value="green" /> Green time
  </label>
</div>
```

- [ ] **Step 2: Add `setStopSizeMode` to `map.js`**

```javascript
export function setStopSizeMode(mode) {
  if (!map.getLayer("stops-layer")) return;
  if (mode === "none") {
    map.setPaintProperty("stops-layer", "circle-radius",
      ["case", ["get", "context"], 3.5, 5]);
    return;
  }

  const field = mode === "people" ? "pop_wa_reach_mid" : "green_time_working_age";
  // Use a simple interpolate on the raw value; clamp to [3, 12] px for internal stops
  const stops = _stopFeatures?.filter(f => !f.properties.context) ?? [];
  if (!stops.length) return;
  const vals = stops.map(f => +f.properties[field] || 0).filter(v => v > 0);
  if (!vals.length) return;
  vals.sort((a, b) => a - b);
  const lo = vals[0], hi = vals[vals.length - 1];

  map.setPaintProperty("stops-layer", "circle-radius", [
    "case", ["get", "context"], 3.5,
    ["interpolate", ["linear"], ["get", field], lo, 3, hi, 12],
  ]);
}
```

- [ ] **Step 3: Wire radio buttons in `scroll.js` `initToolPanel`**

```javascript
document.querySelectorAll("input[name='stop-size']").forEach(radio => {
  radio.addEventListener("change", () => {
    if (radio.checked) setStopSizeMode(radio.value);
  });
});
```

Add `setStopSizeMode` to the import from `./map.js`.

- [ ] **Step 4: Verify: default = uniform; switching to "People in catchment" scales stops by population; "Green time" scales by green_time_working_age**

---

## Task 10: Tighten Zoom-In Cap

**Files:**

- Modify: `web/js/map.js` — map constructor `maxZoom` option (around line 52)

- [ ] **Step 1: Reduce `maxZoom` by one level**

```javascript
// Change:
maxZoom: 18,
// To:
maxZoom: 17,
```

MapLibre's NavigationControl + button is automatically disabled at `maxZoom` — no extra handler needed.

- [ ] **Step 2: Open browser, zoom in, confirm + button becomes disabled at zoom level 17**

---

## Task 11: Extend Parks Data to Include Frederiksberg

**Bug:** Green park polygons are clipped to Nørrebro boundary only, missing Frederiksberg parks visible through the scoring buffer zone. This underestimates `green_pct_catchment` for stops near the Frederiksberg border.

**Files:**

- Modify: the parks processing script (find via step 1)
- Re-export: `data/web/norrebro_parks.geojson`
- Re-score: `scripts/score/score_bus_routes.py` + `scripts/export/export_bus_route_segments.py`

- [ ] **Step 1: Find the parks processing script**

```bash
grep -r "parks\|greenspaces" scripts/process/ --include="*.py" -l
```

- [ ] **Step 2: Open the script and extend the clip boundary to the 1000 m buffer zone**

Current likely code clips to `norrebro_boundary`. Change to:

```python
from shapely.ops import unary_union
boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER)
clip_poly = unary_union(boundary.geometry.buffer(1000))
parks_gdf = parks_gdf[parks_gdf.geometry.intersects(clip_poly)]
```

- [ ] **Step 3: Verify the raw parks source covers Frederiksberg**

```bash
ls data/raw/greenspaces/
```

If the raw OSM extract was clipped to Nørrebro only, a new wider download is needed — check `docs/data_sources.md` for the parks data source URL.

- [ ] **Step 4: Re-run the parks processing script; verify Frederiksberg parks appear in the output layer**

- [ ] **Step 5: Re-export the parks web layer**

```bash
python3 scripts/export/export_parks.py   # or whichever script writes norrebro_parks.geojson
```

Verify `data/web/norrebro_parks.geojson` now contains polygons in the Frederiksberg area.

- [ ] **Step 6: Re-run segment scoring to update `green_pct_catchment`**

```bash
python3 scripts/score/score_bus_routes.py
python3 scripts/export/export_bus_route_segments.py
```

- [ ] **Step 7: Open browser, enable Parks overlay, confirm park polygons visible in Frederiksberg area**

---

## Verification

After all tasks:

1. **Dev server**: `bash scripts/dev.sh`
2. **Bus tab → scroll to step 6 → "Explore the map →"**
3. Check: Mode toggle float appears at top-centre
4. Switch to Catchment Score → stops show orange–blue gradient (not all blue)
5. Scatter: X and Y axes show 0 / 0.25 / 0.50 / 0.75 / 1.00; Y label says "Health Score (All)"
6. Switch demographic group → Y label updates to "Health Score (Children)" etc.
7. Left panel collapse button → shows "‹ Hide" when open, "›" when collapsed
8. Select neighbourhood → polygons on map turn light grey (no orange); distribution bars show neighbourhood % with black Nørrebro marker; people+green headline updates
9. People+Green block → 70/30 layout, no emojis, ±% uncertainty on group rows, green column
10. Click a stop → grey stop row appears in people+green block; × closes it
11. Stop size radio → switching shows size-scaled circles
12. Enable Parks overlay → parks visible including Frederiksberg area
13. Zoom in to max → + button disabled or map stops zooming

---

## Single Commit (after all tasks pass)

```bash
git add web/index.html web/css/style.css web/js/map.js web/js/scatter.js web/js/scroll.js \
        scripts/process/ data/web/norrebro_parks.geojson \
        data/web/norrebro_bus_segments_scored.geojson data/web/norrebro_stops.geojson
git commit -m "fix+feat: corrections to tasks 8-9 — catchment ramp, mode toggle, scatter axes, neighbourhood fill, distribution %, People+Green redesign, stop size control, Frederiksberg parks"
```
