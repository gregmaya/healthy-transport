/**
 * Baseline vs Contextual scatter plot for the bus analysis panel.
 * X axis: always score_baseline (network coverage, no demographics)
 * Y axis: contextual score for the currently selected demographic group
 * Colour: selected group's contextual score (matches Y axis)
 */

import { getRampDomain } from "./map.js";

const BANDS = [
  { lo: 0,    hi: 0.15,     label: "Poorly placed" },
  { lo: 0.15, hi: 0.30,     label: "Limited reach"  },
  { lo: 0.30, hi: 0.45,     label: "Moderate"        },
  { lo: 0.45, hi: 0.60,     label: "Well placed"     },
  { lo: 0.60, hi: Infinity, label: "Optimal"          },
];

const GROUP_Y_FIELD = {
  aggregate:   "score_aggregate_mid",
  working_age: "score_working_age_mid_share",
  elderly:     "score_elderly_mid_share",
  children:    "score_children_mid_share",
};

const GROUP_LABEL = {
  aggregate:   "All groups",
  working_age: "Working-age",
  elderly:     "Elderly",
  children:    "Children",
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

/** Normalize a raw score value to [0,1] using the map's dynamic domain. */
function _normalize(val) {
  const { lo, hi } = getRampDomain();
  if (lo == null || hi === lo) return val;
  return Math.max(0, Math.min(1, (val - lo) / (hi - lo)));
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

function fmt(v) { return (v * 100).toFixed(0) + "%"; }

let _features = null;
let _currentGroup = "aggregate";
let _dotElements = new Map();   // stop_id → <circle> element
let _selectedId   = null;
let _scatterSelectCallback = null;

export function setScatterSelectCallback(fn) { _scatterSelectCallback = fn; }

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
}

function drawDistribution(group) {
  const container = document.getElementById("distribution-container");
  if (!container || !_features?.length) return;

  const yKey   = GROUP_Y_FIELD[group] || GROUP_Y_FIELD.aggregate;
  const yVals  = _features.map(f => +(f.properties[yKey]) || 0);
  const n      = yVals.length;
  const counts = BANDS.map(b => yVals.filter(v => v >= b.lo && v < b.hi).length);
  const maxCnt = Math.max(...counts, 1);

  container.innerHTML = BANDS.map((b, i) => {
    const pct   = Math.round((counts[i] / n) * 100);
    const mid   = b.hi === Infinity ? 0.75 : (b.lo + b.hi) / 2;
    const color = scoreColor(_normalize(mid));
    const barW  = Math.round((counts[i] / maxCnt) * 100);
    return `<div class="dist-row">
      <span class="dist-label" title="${b.lo === 0 ? "0" : b.lo.toFixed(2)}–${b.hi === Infinity ? "1.0+" : b.hi.toFixed(2)}">${b.label}</span>
      <div class="dist-track"><div class="dist-fill" style="width:${barW}%;background:${color}"></div></div>
      <span class="dist-pct">${pct}%</span>
    </div>`;
  }).join("");
}

function drawScatter(group) {
  const container = document.getElementById("scatter-container");
  if (!container || !_features?.length) return;

  _dotElements.clear();

  const yKey   = GROUP_Y_FIELD[group] || GROUP_Y_FIELD.aggregate;
  const yLabel = GROUP_LABEL[group]   || "All groups";
  const props  = _features.map(f => f.properties);
  const xVals   = props.map(p => +(p["score_baseline"]) || 0);
  const yVals   = props.map(p => +(p[yKey]) || 0);
  const aggVals = props.map(p => +(p["score_aggregate_mid"]) || 0); // z-order only

  const xDataMin = Math.min(...xVals), xDataMax = Math.max(...xVals);
  const yDataMin = Math.min(...yVals), yDataMax = Math.max(...yVals);
  const xPad = (xDataMax - xDataMin) * 0.06 || 0.02;
  const yPad = (yDataMax - yDataMin) * 0.06 || 0.02;
  const xDomMin = Math.max(0, xDataMin - xPad);
  const xDomMax = Math.min(1, xDataMax + xPad);
  const yDomMin = Math.max(0, yDataMin - yPad);
  const yDomMax = Math.min(1, yDataMax + yPad);

  const px = v => ML + ((v - xDomMin) / (xDomMax - xDomMin)) * PW;
  const py = v => MT + PH - ((v - yDomMin) / (yDomMax - yDomMin)) * PH;

  container.innerHTML = "";
  const svg = el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}` });
  svg.style.display = "block";
  svg.style.overflow = "visible";

  // Axis lines
  svg.appendChild(el("line", { x1: ML, y1: MT, x2: ML, y2: MT + PH, stroke: "#ddd", "stroke-width": 1 }));
  svg.appendChild(el("line", { x1: ML, y1: MT + PH, x2: ML + PW, y2: MT + PH, stroke: "#ddd", "stroke-width": 1 }));

  // Grid + ticks
  const NTICKS = 4;
  for (let i = 0; i <= NTICKS; i++) {
    const t = i / NTICKS;
    const xv = xDomMin + t * (xDomMax - xDomMin);
    const yv = yDomMin + t * (yDomMax - yDomMin);
    svg.appendChild(el("line", { x1: px(xv), y1: MT, x2: px(xv), y2: MT + PH, stroke: "#f0f0f0", "stroke-width": 1 }));
    svg.appendChild(el("line", { x1: ML, y1: py(yv), x2: ML + PW, y2: py(yv), stroke: "#f0f0f0", "stroke-width": 1 }));
    svg.appendChild(el("text", { x: px(xv), y: MT + PH + 11, "font-size": 7.5, fill: "#888", "text-anchor": "middle" }, fmt(xv)));
    svg.appendChild(el("text", { x: ML - 4, y: py(yv) + 3,   "font-size": 7.5, fill: "#888", "text-anchor": "end"    }, fmt(yv)));
  }

  // Axis labels
  svg.appendChild(el("text", {
    x: ML + PW / 2, y: H - 2,
    "font-size": 8, fill: "#555", "text-anchor": "middle",
  }, "← Baseline (network coverage)"));
  svg.appendChild(el("text", {
    x: 8, y: MT + PH / 2,
    "font-size": 8, fill: "#555", "text-anchor": "middle",
    transform: `rotate(-90, 8, ${MT + PH / 2})`,
  }, `${yLabel} ↑`));

  // Points — sorted ascending by aggregate so high scores render on top
  const order = props.map((_, i) => i).sort((a, b) => aggVals[a] - aggVals[b]);
  const g = el("g", {});
  for (const i of order) {
    const stopId = String(_features[i].properties.stop_id ?? "");
    const isSelected = stopId === _selectedId;
    const circle = el("circle", {
      cx: px(xVals[i]), cy: py(yVals[i]),
      r: isSelected ? 4.5 : 2.2,
      fill: scoreColor(_normalize(yVals[i])),
      "fill-opacity": 0.75,
      stroke: isSelected ? "#ffffff" : "none",
      "stroke-width": isSelected ? 1.5 : 0,
    });
    circle.style.cursor = "pointer";
    const title = document.createElementNS(NS, "title");
    title.textContent = `Baseline: ${fmt(xVals[i])}  ${yLabel}: ${fmt(yVals[i])}`;
    circle.appendChild(title);
    circle.addEventListener("click", (e) => {
      e.stopPropagation();
      const newId = _selectedId === stopId ? null : stopId;
      _selectedId = newId;
      highlightScatterStop(newId);
      if (_scatterSelectCallback) _scatterSelectCallback(newId);
    });
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
