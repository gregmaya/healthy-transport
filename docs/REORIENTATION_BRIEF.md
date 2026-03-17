# Healthy Transport — Nørrebro: Project Reorientation Brief

> **Purpose:** This brief synthesises decisions made in a strategic design session to reorient the project. It documents the revised conceptual model, required changes to the data pipeline, and a phased delivery plan.

*Last updated: 15th March 2026*

---

## Table of Contents

1. [Strategic Context & Revised Vision](#1-strategic-context--revised-vision)
2. [The Health Benefit Model](#2-the-health-benefit-model)
3. [Segment Scoring: The Revised Output Layer](#3-segment-scoring-the-revised-output-layer)
4. [Revised Data Pipeline](#4-revised-data-pipeline)
5. [Web Application Architecture](#5-web-application-architecture)
6. [Current Status & Gap Analysis](#6-current-status--gap-analysis)
7. [Phased Delivery Plan](#7-phased-delivery-plan)
8. [Suggested Scrollytelling Narrative Arc](#8-suggested-scrollytelling-narrative-arc)

---

## 1. Strategic Context & Revised Vision

The original project framing centred on scoring address points for their proximity to transport stops. Through design review, two important corrections have been agreed:

> **Correction 1 — Output layer:**
> The primary display layer must be the **street network (20m segments)**, not address points or building footprints. The intervention space for transport planners and urban designers is the public realm. Scoring private addresses as the headline output misaligns the tool with its audience.

> **Correction 2 — Health model:**
> The health benefit model should produce **population-differentiated curves**, not a single optimum distance. Different demographic groups have genuinely different dose-response relationships with walking distance. This turns the output from a point into a range — a more honest and more useful planning input.

The revised vision: a web application that scores every street segment in Nørrebro for its **potential health benefit as a transit stop location**, differentiated by population group, and presents this as a coloured network layer within a scrollytelling narrative that lands on an interactive GIS tool.

### 1.1 Positioning

The tool should be positioned not just as a transport planning aid but as a **public health infrastructure tool**. Framing transit investment in terms of healthcare cost savings and active travel dose-response opens different funding channels and creates a more compelling policy narrative than traditional transport metrics alone.

### 1.2 Target Users

- Municipal transport planners
- Urban designers and architects
- Policy makers and government officers

The tool targets **all stages** of the planning process: greenfield network design, optimisation of existing networks, and evaluation of proposed changes. Delivered as a **web-based GIS interface**.

---

## 2. The Health Benefit Model

### 2.1 Population-Differentiated Curves

The health benefit is modelled as a smooth, tuneable function **B(d)** where `d` is the network walking distance from a point to its nearest transit stop. The model is run separately for each population segment, producing a **family of curves** rather than a single line. This generates a benefit *range* on the map — a band of optimal placement — rather than a single optimal point.

| Segment | Peak Benefit Zone | Zero Benefit Beyond | Key Driver |
|---|---|---|---|
| Working-age adults (18–64) | 400–700m | ~1,200m | Widest, furthest-peaking curve. Highest cardiovascular benefit per trip. |
| Elderly residents (65+) | 200–400m | ~700m | Curve shifts left. Relative benefit per metre walked is higher but deterrence rises sharply beyond 500m. |
| Children (under 15) | 150–350m | ~600m | Route safety quality dominates. Benefit is also habit-formation, not just immediate health outcome. |
| Reduced mobility | 0–200m | ~350m | Very narrow range. Most transit-dependent group; hardest to serve well. |

### 2.2 Curve Shape

Each curve is implemented as a **modified Gaussian or beta distribution** with three zones:

- **Ramp-up** (0 to ~150m): benefit rises from near-zero as the walk becomes metabolically meaningful
- **Peak plateau** (150m to segment-specific peak): aligns with WHO 10-minute walk targets
- **Decay** (peak to zero threshold): benefit falls as deterrence rises and self-selection dominates
- **Zero** beyond the threshold: the address is effectively outside the catchment

Three parameters should be exposed as **interactive sliders** in the tool:
- Peak distance
- Decay steepness
- Zero-benefit threshold

This lets planners test sensitivity and adapt the model to local context.

### 2.3 Data Requirements

The multi-curve approach requires **age-disaggregated population at address point level**. This is the single most critical data question for the pipeline.

Sources to investigate:
- **Statistics Denmark (Danmarks Statistik)** — population by age band, aggregated to address or grid cell
- **Copenhagen Municipality open data (data.kk.dk)** — may have finer-grained breakdowns
- **BBR/DAR data already in the pipeline** — check whether age attributes can be joined

**Fallback:** If address-level age data is unavailable, apply census-zone age distributions as weights uniformly to address points within each census zone. This assumption must be clearly flagged in the tool UI and documentation.

### 2.4 Literature Anchors

The benefit curves must be grounded in public health evidence:

- **Lars Bo Andersen et al.** — Danish studies on active travel dose-response and all-cause mortality. Directly applicable to this geography and highly credible for a Copenhagen case study.
- **WHO Global Action Plan on Physical Activity 2018–2030** — 150 min/week moderate activity target
- **MET-based walking studies** — for converting distance/time to metabolic equivalent units
- **Besser & Dannenberg (2005); Lachapelle & Frank (2009)** — active travel and transit walking literature; realistic walk-to-transit distance distributions

---

## 3. Segment Scoring: The Revised Output Layer

### 3.1 Why Segments, Not Address Points

The traditional approach scores address points or building footprints — answering *"who benefits?"*. The revised approach scores street network segments — answering *"where should the intervention go?"*. These are fundamentally different questions, and the tool's audience acts on the second one.

A coloured street network is **immediately legible and actionable** to a planner in a way that a scored building layer is not.

### 3.2 Computation Algorithm

For each 20m network segment:

1. Take the **midpoint** of the segment as the hypothetical stop location
2. Compute **network walking distance** from the midpoint to all address points within the maximum catchment radius (1,500m)
3. For each address point, look up its **population by demographic group** and compute `B(d)` for each population curve
4. Multiply `B(d) × population` for each group and sum across all address points within catchment
5. Store the resulting scores as **segment attributes** — one score per demographic group + one aggregate score

Output: a scored GeoPackage with 5–6 score attributes per segment feature.

### 3.3 Note on CTC vs NetworkX

The project uses **CTC** (Cython-based graph library) rather than NetworkX for network routing. This is the right call for performance at the scale of Nørrebro's 20m segment graph. The scoring loop above is the computationally intensive step; CTC's speed advantage is most valuable here.

**Critical:** Distance computation must use **network distance** (graph shortest path), not Euclidean distance. This is essential for credibility and for capturing real barriers in the urban fabric (dead ends, water, parks). The difference will be visually significant in Nørrebro's organic street pattern and is pedagogically useful in the narrative.

---

## 4. Revised Data Pipeline

The pipeline has five stages. Stages 1–3 are offline pre-processing; stages 4–5 serve the web application.

```
Stage 1: Data Assembly
  Address points (age-disaggregated population)
  + Stop locations (GTFS)
  + 20m street network segments
  → All clipped to Nørrebro boundary. CRS: EPSG:25832.

Stage 2: Network Graph Construction
  Build routable graph from 20m segments using CTC.
  Validate connectivity.
  Identify isolated subgraphs or dead ends.

Stage 3: Segment Scoring  ← core computation
  For each segment midpoint:
    → Network distances to all address points within 1,500m
    → Apply population-differentiated B(d) curves
    → Sum population-weighted scores per demographic group
    → Store 5–6 score attributes on segment feature
  Output: scored GeoPackage

Stage 4: Web Export
  Convert scored segments to GeoJSON / PMTiles.
  Optional: aggregate to H3 hex grid (resolution 9, ~100m hexagons).
  Set up MapLibre GL JS project.

Stage 5: Interactive Layer
  Pre-baked scored data served as static files.
  No live computation at runtime.
  Optional: pre-compute scores for candidate stop location grid
            to enable 'drop a stop' interaction without a backend.
```

### 4.1 Key Pipeline Decisions

**Network distance vs Euclidean distance**
Must use network distance throughout. The existing 20m segment decomposition makes this tractable.

**H3 aggregation vs raw segments**
Raw segments give maximum precision and map directly onto the street network planners work with. H3 hexagons render faster and provide a cleaner summary view. Recommended: expose both as a **toggle** in the tool, with segments as default.

**Age-disaggregated population fallback**
See Section 2.3. If census-zone resolution only, apply as weights and document clearly.

---

## 5. Web Application Architecture

### 5.1 Structure

The application has two sections that must feel like a single seamless experience:

1. **Scrollytelling narrative** — guides the reader through the problem, the model, and the Nørrebro findings. Map animations triggered by scroll position.
2. **Interactive GIS tool** — the map takes over the viewport. The reader becomes a planner, able to explore the scored network, toggle population layers, and test hypothetical stop placements.

The transition must feel *earned* — the reader arrives at the tool already understanding what they are looking at.

### 5.2 Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Map renderer | **MapLibre GL JS** | Open source, fast vector tile rendering, excellent layer animation support for the narrative section |
| Scrollytelling | **Scrollama** | Standard library for scroll-driven map narratives; used by major data journalism teams |
| Analysis layers | **Deck.gl** (optional) | For hexbin and arc layers if analytical views are needed beyond the segment layer |
| Hosting | **GitHub Pages or Netlify** | All data is pre-processed; the site can be fully static |
| Data format | **GeoJSON / PMTiles** | GeoJSON for development; PMTiles for production (tiled, efficient, no tile server required) |

### 5.3 Interactive Tool Features (MVP)

1. Scored segment network as primary display layer, coloured by aggregate health benefit score
2. **Population toggle** — switch between demographic group layers to see how the sweet-spot band shifts
3. **Existing stop overlay** — toggle on/off to compare current provision against optimal zones
4. **Benefit curve parameter sliders** — adjust peak distance and decay rate; map updates reactively
5. **Headline metric panel** — total daily walking-minutes generated by the current stop configuration

> **Deferred to post-MVP:** "Drop a hypothetical stop" feature (showing marginal benefit of a new stop location). Requires either a backend or a pre-computed lookup grid.

---

## 6. Current Status & Gap Analysis

### 6.1 What the Repository Already Has

- Well-structured project layout with clear `raw → processed → integrated → web` pipeline logic
- Data download scripts for key Copenhagen sources (Dataforsyningen, OpenData DK, Statistics Denmark, data.kk.dk)
- 20m pedestrian network segments (GraphML format) clipped to Nørrebro
- Address point population data (BBR/DAR sources)
- Building footprints (INSPIRE) and boundary file
- GTFS transport stop data (in progress)
- CTC-based routing chosen over NetworkX for performance
- QGIS-compatible GeoPackage outputs at each pipeline stage
- `CLAUDE.MD` and `PROGRESS.md` for AI-assisted development workflow

### 6.2 Gap Analysis

| Component | Current Status | Required Change | Priority |
|---|---|---|---|
| Age-disaggregated population | Not confirmed | Join age band data from Statistics Denmark to address points. Confirm availability at address level. Define fallback if only census-zone resolution available. | 🔴 Critical |
| Benefit curve implementation | Not started | Implement population-differentiated `B(d)` curves as a Python module. Parameterise peak, decay, and threshold for each demographic group. Plot and validate against literature. | 🔴 Critical |
| Segment scoring logic | Not started | Build the core scoring loop: for each segment midpoint, compute network distances to all address points within 1,500m, apply curves, sum population-weighted scores, store as segment attributes. | 🔴 Critical |
| Scoring unit: segments not points | Address points currently the output unit | Reframe pipeline output so that scored segments are the primary deliverable. Address point scores become an intermediate calculation, not the final layer. | 🔴 Critical |
| GTFS stop data | In progress | Complete stop location collection and processing. Ensure stops are snapped to nearest network segment. | 🟠 High |
| Web export layer | Not started | Convert scored segments to GeoJSON/PMTiles. Set up MapLibre GL JS project. Decide between raw segment display and H3 aggregation. | 🟠 High |
| Scrollytelling narrative | Not started | Define the narrative arc (5–7 scroll steps). Write section copy. Identify which map states correspond to each scroll step. | 🟠 High |
| Interactive tool UI | Not started | Build MapLibre GL JS interface with population toggle, existing stop overlay, parameter sliders, and headline metric panel. | 🟡 Medium |

---

## 7. Phased Delivery Plan

Phases are ordered by dependency. Do not begin a phase until its dependency is complete.

| Phase | Focus | Key Deliverables | Depends On |
|---|---|---|---|
| **1** | Health model | Benefit curve functions (Python module). Population segment parameters. Curve plots for validation. Literature citations documented. | Age data confirmed |
| **2** | Data completion | Age-disaggregated population joined to address points. GTFS stops processed and snapped to network. All `raw → processed` stages complete. | Phase 1 |
| **3** | Segment scoring pipeline | Core scoring loop implemented. All 20m segments scored with 5–6 demographic attributes. Output validated in QGIS. Scoring notebook committed. | Phase 2 |
| **4** | Web export | Scored segments exported to GeoJSON/PMTiles. MapLibre GL JS map with segment layer rendering. Basic population toggle working. | Phase 3 |
| **5** | Scrollytelling narrative | Narrative arc defined and written. 5–7 scroll steps implemented with Scrollama. Map transitions between narrative states. | Phase 4 |
| **6** | Interactive tool | Full interactive tool: population toggle, stop overlay, parameter sliders, headline metric. Seamless handoff from narrative. | Phase 5 |
| **7** | Hardening | Performance optimisation. Mobile responsiveness. Accessibility. Final copy editing. Deployment to GitHub Pages / Netlify. | Phase 6 |

### 7.1 Immediate Next Actions

Before any further code is written, complete these three actions **in order**:

> **Action 1 — Confirm age data availability**
> Query Statistics Denmark and data.kk.dk. If address-level data exists, plan the join. If not, define the census-zone fallback and document the assumption. This is the single biggest unknown in the project.

> **Action 2 — Implement and plot the benefit curves**
> Write a Python module with the `B(d)` function parameterised for each demographic group. Plot all four curves on the same axes. Pressure-test parameter choices against the Lars Bo Andersen literature. Commit as a notebook.

> **Action 3 — Reframe the pipeline output target**
> Update `PROGRESS.md` and `CLAUDE.MD` to reflect that **scored 20m segments are the primary deliverable**. Ensure any in-progress notebooks are aligned with this before more processing work is done.

---

## 8. Suggested Scrollytelling Narrative Arc

The narrative should build understanding progressively, arriving at the interactive tool with the reader fully equipped to use it.

| Step | Title | Content | Map State |
|---|---|---|---|
| 1 | The hidden cost of bad stop placement | Most transit stops are placed for operational convenience, not population health. A stop too close or too far generates almost no walking benefit. | Nørrebro overview, existing stops shown |
| 2 | Walking is medicine | 10–15 minutes of brisk walking twice a day meets WHO physical activity guidelines. Transit is one of the most scalable delivery mechanisms for active travel. | Zoom to a residential block; animate the catchment ring |
| 3 | The sweet spot is a range, not a point | Different people have different optimal walk distances. The right question is not "where is the best stop?" but "where is the zone where the most people benefit the most?" | Show the family of curves animating over the map |
| 4 | Scoring the streets | Every street segment in Nørrebro can be scored for its potential health benefit as a stop location. Darker colour = higher population-weighted benefit. | Segment scoring layer fades in across the district |
| 5 | Where the current network leaves gaps | Comparing the existing stops against the scored segments reveals both over-served corridors and underserved pockets. | Existing stops overlay; highlight gap areas |
| 6 | Explore it yourself | Hand off to the interactive tool. Adjust the population layer. Move the sliders. See how the sweet spot shifts for elderly residents vs. working-age adults. | Full interactive tool loads |

---

> **Note for CLAUDE.MD / PROGRESS.md:** The three binding project constraints introduced in this brief are:
> 1. **Scored 20m segments** are the primary output layer — not address points
> 2. **Population-differentiated benefit curves** produce a range of optimal stop locations — not a single point
> 3. The web app follows a **scrollytelling-to-interactive-tool** structure using MapLibre GL JS + Scrollama
