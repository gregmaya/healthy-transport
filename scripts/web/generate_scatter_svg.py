"""
Generate a static SVG scatter plot for the narrative step in config.js.

Source: data/web/norrebro_stops.geojson  (internal stops only, context=false)
X axis: score_catchment   (baseline — network geometry, no population weighting)
Y axis: score_health_combined (contextual — population-weighted mean of 3 groups)
Colour: score_health_combined mapped through the scatter.js STOPS ramp

Output: prints the <svg> block to stdout — paste into STEPS_BUS[4].svg in config.js.

Usage:
  python3 scripts/web/generate_scatter_svg.py
"""

import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
STOPS_GEOJSON = PROJECT_ROOT / "data" / "web" / "norrebro_stops.geojson"

X_FIELD = "score_catchment"
Y_FIELD = "score_health_combined"

# Colour ramp — matches scatter.js STOPS array exactly
RAMP = [
    (0.00, 0xff, 0x67, 0x00),
    (0.25, 0xeb, 0xeb, 0xeb),
    (0.50, 0xc0, 0xc0, 0xc0),
    (0.75, 0x3a, 0x6e, 0xa5),
    (1.00, 0x00, 0x4e, 0x98),
]

# SVG canvas — matches existing viewBox="-28 -42 258 268"
CHART_W = 200
CHART_H = 160
R = 2.2


def score_color(val: float) -> str:
    val = max(0.0, min(1.0, val or 0.0))
    for i in range(len(RAMP) - 1):
        t0, r0, g0, b0 = RAMP[i]
        t1, r1, g1, b1 = RAMP[i + 1]
        if val <= t1:
            t = (val - t0) / (t1 - t0)
            r = round(r0 + (r1 - r0) * t)
            g = round(g0 + (g1 - g0) * t)
            b = round(b0 + (b1 - b0) * t)
            return f"#{r:02x}{g:02x}{b:02x}"
    t0, r0, g0, b0 = RAMP[-1]
    return f"#{r0:02x}{g0:02x}{b0:02x}"


def main():
    with open(STOPS_GEOJSON) as f:
        geojson = json.load(f)

    features = [
        feat for feat in geojson["features"]
        if not feat["properties"].get("context", True)
    ]

    x_vals = [feat["properties"].get(X_FIELD) or 0.0 for feat in features]
    y_vals = [feat["properties"].get(Y_FIELD) or 0.0 for feat in features]

    # Shared normalisation range across both axes (matches scatter.js getRampDomain logic)
    lo = min(min(x_vals), min(y_vals))
    hi = max(max(x_vals), max(y_vals))

    def norm(v):
        return (v - lo) / (hi - lo) if hi > lo else 0.0

    def to_cx(v):
        return round(norm(v) * CHART_W, 1)

    def to_cy(v):
        # SVG y is inverted: high value = top = low cy
        return round((1.0 - norm(v)) * CHART_H, 1)

    # Sort by score_health_combined ascending so high-value dots render on top
    features_sorted = sorted(features, key=lambda f: f["properties"].get(Y_FIELD) or 0.0)

    circles = []
    for feat in features_sorted:
        xv = feat["properties"].get(X_FIELD) or 0.0
        yv = feat["properties"].get(Y_FIELD) or 0.0
        cx = to_cx(xv)
        cy = to_cy(yv)
        color = score_color(norm(yv))
        circles.append(f'  <circle cx="{cx}" cy="{cy}" r="{R}" fill="{color}" fill-opacity="0.8"/>')

    # Diagonal reference line: maps (lo,lo) → (hi,hi) in data space → chart corners
    diag_x1 = to_cx(lo)
    diag_y1 = to_cy(lo)
    diag_x2 = to_cx(hi)
    diag_y2 = to_cy(hi)

    n = len(features)
    circles_str = "\n".join(circles)

    svg = f"""`<svg class="step-svg" viewBox="-28 -42 258 268" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <!-- Title: two lines, centered over chart area -->
  <text font-size="8.5" font-weight="600" fill="#1a2a3a" font-family="sans-serif" text-anchor="middle">
    <tspan x="86" y="-25">Does network reach translate</tspan>
    <tspan x="86" dy="11">to health benefit?</tspan>
  </text>
  <!-- Diagonal reference line -->
  <line x1="{diag_x1}" y1="{diag_y1}" x2="{diag_x2}" y2="{diag_y2}" stroke="#c6dbef" stroke-width="1" stroke-dasharray="4,3"/>
  <!-- {n} internal stops: color = scoreColor(normalize({Y_FIELD})), matches scatter.js STOPS ramp -->
{circles_str}
  <!-- X axis -->
  <line x1="0" y1="160" x2="200" y2="160" stroke="#888" stroke-width="0.8"/>
  <text x="100" y="176" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle">Baseline (catchment reach)</text>
  <!-- Y axis -->
  <line x1="0" y1="0" x2="0" y2="160" stroke="#888" stroke-width="0.8"/>
  <text x="-8" y="80" font-size="7" fill="#555" font-family="sans-serif" text-anchor="middle" transform="rotate(-90,-8,80)">Health score (combined)</text>
</svg>`"""

    print(svg)
    print(f"\n<!-- Generated from {n} internal stops. X={X_FIELD}, Y={Y_FIELD}. lo={lo:.4f} hi={hi:.4f} -->",
          file=sys.stderr)


if __name__ == "__main__":
    main()
