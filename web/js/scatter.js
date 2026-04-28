/**
 * Baseline vs Contextual scatter plot for the bus analysis panel.
 * X axis: always score_catchment (network coverage, no demographics)
 * Y axis: contextual score for the currently selected demographic group
 * Colour: selected group's contextual score (matches Y axis)
 */

import { getRampDomain, getCatchRampDomain } from "./map.js";

export const BANDS = [
  { lo: 0,    hi: 0.20,     label: "Low benefit", textColor: "#c94e00" },
  { lo: 0.20, hi: 0.40,     label: "Moderate",    textColor: "#7a7a7a" },
  { lo: 0.40, hi: 0.60,     label: "Good",        textColor: "#3a6ea5" },
  { lo: 0.60, hi: 0.80,     label: "High",        textColor: "#1d5490" },
  { lo: 0.80, hi: Infinity, label: "Optimal",     textColor: "#004e98" },
];

const GROUP_Y_FIELD = {
  aggregate:   "score_health_combined",
  working_age: "score_health_working_age",
  elderly:     "score_health_elderly",
  children:    "score_health_children",
};

const GROUP_LABEL = {
  aggregate:   "Health Score (All)",
  working_age: "Health Score (Working age)",
  elderly:     "Health Score (Elderly)",
  children:    "Health Score (Children)",
};

// Design palette — matches map.js _buildRamp (orange=low, blue=high)
const STOPS = [
  [0.0,  0xff, 0x67, 0x00],  // pumpkin-spice — low
  [0.25, 0xeb, 0xeb, 0xeb],  // platinum
  [0.5,  0xc0, 0xc0, 0xc0],  // silver
  [0.75, 0x3a, 0x6e, 0xa5],  // cornflower-ocean
  [1.0,  0x00, 0x4e, 0x98],  // steel-azure — high
];

function scoreColor(val) {
  val = Math.max(0, Math.min(1, val || 0));
  for (let i = 0; i < STOPS.length - 1; i++) {
    const [t0, r0, g0, b0] = STOPS[i];
    const [t1, r1, g1, b1] = STOPS[i + 1];
    if (val <= t1) {
      const t = (val - t0) / (t1 - t0);
      return `rgb(${Math.round(r0 + (r1 - r0) * t)},${Math.round(g0 + (g1 - g0) * t)},${Math.round(b0 + (b1 - b0) * t)})`;
    }
  }
  return "rgb(0,78,152)";
}

/** Normalize a raw score value to [0,1] using the appropriate domain for the current mode. */
function _normalize(val, isBaseline) {
  const { lo, hi } = isBaseline ? getCatchRampDomain() : getRampDomain();
  if (lo == null || hi === lo) return val;
  return Math.max(0, Math.min(1, (val - lo) / (hi - lo)));
}

function _isBaseline() {
  return document.querySelector(".mode-btn.active")?.dataset.mode === "baseline";
}

const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs = {}, text = null) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
  if (text != null) e.textContent = text;
  return e;
}

const W = 250, H = 200;
const ML = 32, MB = 32, MR = 8, MT = 10;
const PW = W - ML - MR;
const PH = H - MT - MB;

/** Format a score value as a decimal string. */
function fmt(v) { return (+v).toFixed(2); }

let _features = null;
let _currentGroup = "aggregate";
let _dotElements = new Map();   // stop_id → <circle> element
let _selectedId   = null;
let _scatterSelectCallback = null;
let _neighbourStopIds = null;   // Set of stop_id strings in the active neighbourhood; null = show all
let _nbAvgScore = null;

export function setScatterSelectCallback(fn) { _scatterSelectCallback = fn; }

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

/**
 * Apply neighbourhood filter to both scatter and distribution.
 * @param {Set<string>|null} stopIdSet  — Set of stop_id strings; null = clear filter
 * @param {number|null}      avgScore   — neighbourhood average score for distribution tick
 */
export function updateNeighbourhoodFilter(stopIdSet, avgScore) {
  _neighbourStopIds = stopIdSet;
  _nbAvgScore       = avgScore ?? null;
  drawScatter(_currentGroup);
  drawDistribution(_currentGroup);
}

export function highlightScatterStop(stopId) {
  _selectedId = stopId != null ? String(stopId) : null;
  _dotElements.forEach((circ, id) => {
    if (id === _selectedId) {
      circ.setAttribute("r", 4.5);
      circ.setAttribute("stroke", "#ffffff");
      circ.setAttribute("stroke-width", 1.5);
    } else {
      circ.setAttribute("r", 2.2);
      circ.setAttribute("stroke", "none");
      circ.setAttribute("stroke-width", 0);
    }
  });
  _updateStopLabel();
}

function _updateStopLabel() {
  const svg = document.querySelector("#scatter-container svg");
  if (!svg) return;
  svg.querySelector(".scatter-stop-label")?.remove();
  if (!_selectedId || !_features) return;
  const feat = _features.find(f => String(f.properties.stop_id ?? "") === _selectedId);
  const circ = _dotElements.get(_selectedId);
  if (!feat || !circ) return;
  const name  = feat.properties.stop_name || _selectedId;
  const cx    = +circ.getAttribute("cx");
  const cy    = +circ.getAttribute("cy");
  // Nudge label left if too close to right edge
  const anchor = cx > ML + PW - 50 ? "end" : "start";
  const offsetX = anchor === "end" ? -7 : 7;
  const label = el("text", {
    x: cx + offsetX,
    y: cy - 5,
    "font-size": 8.5,
    fill: "#222",
    "font-weight": "500",
    "text-anchor": anchor,
    "class": "scatter-stop-label",
    "pointer-events": "none",
  }, name);
  svg.appendChild(label);
}

function drawDistribution(group) {
  const container = document.getElementById("distribution-container");
  if (!container || !_features?.length) return;

  const isBaseline = document.querySelector(".mode-btn.active")?.dataset.mode === "baseline";
  const scoreKey   = isBaseline ? "score_catchment" : (GROUP_Y_FIELD[group] || GROUP_Y_FIELD.aggregate);

  const allVals  = _features.map(f => _normalize(+(f.properties[scoreKey]) || 0, isBaseline));
  const n        = allVals.length;

  // Nørrebro-wide band percentages
  const nrCounts = BANDS.map(b => allVals.filter(v => v >= b.lo && v < (b.hi === Infinity ? 2 : b.hi)).length);
  const nrPcts   = nrCounts.map(c => n > 0 ? Math.round((c / n) * 100) : 0);

  // Neighbourhood band percentages (if selected)
  let nbPcts = null;
  if (_neighbourStopIds?.size) {
    const nbVals = _features
      .filter(f => _neighbourStopIds.has(String(f.properties.stop_id)))
      .map(f => _normalize(+(f.properties[scoreKey]) || 0, isBaseline));
    const nbN = nbVals.length;
    const nbCounts = BANDS.map(b => nbVals.filter(v => v >= b.lo && v < (b.hi === Infinity ? 2 : b.hi)).length);
    nbPcts = nbCounts.map(c => nbN > 0 ? Math.round((c / nbN) * 100) : 0);
  }

  container.innerHTML = BANDS.map((b, i) => {
    const displayPct = nbPcts ? nbPcts[i] : nrPcts[i];
    const color = scoreColor(i / (BANDS.length - 1));
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

function drawScatter(group) {
  const container = document.getElementById("scatter-container");
  if (!container || !_features?.length) return;

  _dotElements.clear();

  const isBaseline = _isBaseline();
  const yKey   = GROUP_Y_FIELD[group] || GROUP_Y_FIELD.aggregate;
  const yLabel = GROUP_LABEL[group]   || "All groups";
  const props  = _features.map(f => f.properties);
  const xVals   = props.map(p => +(p["score_catchment"]) || 0);
  const yVals   = props.map(p => +(p[yKey]) || 0);
  const aggVals = props.map(p => +(p["score_health_combined"]) || 0); // z-order only
  // In catchment mode, color dots by catchment score to match the map ramp.
  const colorVals = isBaseline ? xVals : yVals;

  const px = v => ML + v * PW;
  const py = v => MT + PH * (1 - v);

  container.innerHTML = "";
  const svg = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}` });
  svg.style.display = "block";
  svg.style.overflow = "visible";

  // Axis lines
  svg.appendChild(el("line", { x1: ML, y1: MT, x2: ML, y2: MT + PH, stroke: "#ddd", "stroke-width": 1 }));
  svg.appendChild(el("line", { x1: ML, y1: MT + PH, x2: ML + PW, y2: MT + PH, stroke: "#ddd", "stroke-width": 1 }));

  // Diagonal reference line y = x (full [0,1] range)
  svg.appendChild(el("line", {
    x1: px(0), y1: py(0),
    x2: px(1), y2: py(1),
    stroke: "#ccc", "stroke-width": 1, "stroke-dasharray": "4,3",
  }));

  // Grid + ticks (fixed 0, 0.25, 0.5, 0.75, 1.0)
  for (let i = 0; i <= 4; i++) {
    const t = i / 4;
    svg.appendChild(el("line", { x1: px(t), y1: MT, x2: px(t), y2: MT + PH, stroke: "#f0f0f0", "stroke-width": 1 }));
    svg.appendChild(el("line", { x1: ML, y1: py(t), x2: ML + PW, y2: py(t), stroke: "#f0f0f0", "stroke-width": 1 }));
    svg.appendChild(el("text", { x: px(t), y: MT + PH + 11, "font-size": 8.5, fill: "#888", "text-anchor": "middle" }, t.toFixed(2)));
    svg.appendChild(el("text", { x: ML - 4, y: py(t) + 3,   "font-size": 8.5, fill: "#888", "text-anchor": "end"    }, t.toFixed(2)));
  }

  // Axis labels (no arrows)
  svg.appendChild(el("text", {
    x: ML + PW / 2, y: H - 2,
    "font-size": 9, fill: "#555", "text-anchor": "middle",
  }, "Catchment Score"));
  svg.appendChild(el("text", {
    x: 8, y: MT + PH / 2,
    "font-size": 9, fill: "#555", "text-anchor": "middle",
    transform: `rotate(-90, 8, ${MT + PH / 2})`,
  }, yLabel));

  // Points — sorted ascending by aggregate so high scores render on top
  const order = props.map((_, i) => i).sort((a, b) => aggVals[a] - aggVals[b]);
  const g = el("g", {});
  for (const i of order) {
    const stopId = String(_features[i].properties.stop_id ?? "");
    const isSelected = stopId === _selectedId;
    const circle = el("circle", {
      cx: px(xVals[i]), cy: py(yVals[i]),
      r: isSelected ? 4.5 : 2.2,
      fill: scoreColor(_normalize(colorVals[i], isBaseline)),
      "fill-opacity": 0.75,
      stroke: isSelected ? "#ffffff" : "none",
      "stroke-width": isSelected ? 1.5 : 0,
    });
    circle.style.cursor = "pointer";
    const title = document.createElementNS(NS, "title");
    title.textContent = `Catchment Score: ${fmt(xVals[i])}  ${yLabel}: ${fmt(yVals[i])}`;
    circle.appendChild(title);
    circle.addEventListener("click", (e) => {
      e.stopPropagation();
      const newId = _selectedId === stopId ? null : stopId;
      _selectedId = newId;
      highlightScatterStop(newId);
      if (_scatterSelectCallback) _scatterSelectCallback(newId);
    });
    if (_neighbourStopIds) {
      const inNb = _neighbourStopIds.has(stopId);
      circle.setAttribute("fill-opacity", inNb ? 0.75 : 0.12);
    }
    _dotElements.set(stopId, circle);
    g.appendChild(circle);
  }
  svg.appendChild(g);
  container.appendChild(svg);
}

export function initScatter(features) {
  const seen = new Set();
  _features = features.filter(f => {
    if (f.properties.context) return false;           // exclude context stops outside district
    const key = f.properties.stop_id ?? `${f.geometry.coordinates}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  drawScatter(_currentGroup);
  drawDistribution(_currentGroup);
}

export function updateScatterGroup(group) {
  _currentGroup = group;
  drawScatter(group);
  drawDistribution(group);
}

/** Re-draw scatter and distribution when score mode changes (baseline ↔ contextual). */
export function updateScatterMode() {
  drawScatter(_currentGroup);
  drawDistribution(_currentGroup);
}
