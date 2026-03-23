/**
 * Baseline vs Contextual scatter plot for the bus analysis panel.
 * X axis: always score_baseline (network coverage, no demographics)
 * Y axis: contextual score for the currently selected demographic group
 * Colour: aggregate contextual score (score_aggregate_mid)
 */

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

// Design palette — matches map.js (orange=low, blue=high)
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

function drawScatter(group) {
  const container = document.getElementById("scatter-container");
  if (!container || !_features?.length) return;

  const yKey   = GROUP_Y_FIELD[group] || GROUP_Y_FIELD.aggregate;
  const yLabel = GROUP_LABEL[group]   || "All groups";
  const props  = _features.map(f => f.properties);
  const xVals  = props.map(p => +(p["score_baseline"]) || 0);
  const yVals  = props.map(p => +(p[yKey]) || 0);
  const aggVals = props.map(p => +(p["score_aggregate_mid"]) || 0);

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
    const circle = el("circle", {
      cx: px(xVals[i]), cy: py(yVals[i]),
      r: 2.2, fill: scoreColor(aggVals[i]), "fill-opacity": 0.65, stroke: "none",
    });
    const title = document.createElementNS(NS, "title");
    title.textContent = `Baseline: ${fmt(xVals[i])}  ${yLabel}: ${fmt(yVals[i])}  Agg: ${fmt(aggVals[i])}`;
    circle.appendChild(title);
    g.appendChild(circle);
  }
  svg.appendChild(g);
  container.appendChild(svg);
}

export function initScatter(features) {
  _features = features;
  drawScatter(_currentGroup);
}

export function updateScatterGroup(group) {
  _currentGroup = group;
  drawScatter(group);
}
