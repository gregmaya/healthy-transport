import { TABS, NEIGHBOURHOOD_POP, DISTRICT_POP } from "./config.js";
import { enableScrollLock, disableScrollLock, getActiveNeighbourhood, setActiveNeighbourhood, getSelectedStop, setSelectedStop } from "./state.js";
import { initScatter, updateScatterGroup, updateScatterMode, setScatterSelectCallback, highlightScatterStop, updateNeighbourhoodFilter } from "./scatter.js";
import {
  showOverview,
  showCatchmentRing,
  showBenefitCurves,
  showScoredNetwork,
  showGapAnalysis,
  enterInteractiveTool,
  enterInteractiveToolBasemap,
  backToNarrative,
  setActiveGroup,
  toggleStops,
  toggleDemographics,
  toggleParks,
  getStopFeatures,
  setScoreMode,
  setStopSelectCallback,
  highlightMapStop,
  resizeMap,
  setNeighbourhoodBoundary,
  getNeighbourhoodFeatures,
  neighbourhoodForPoint,
  showRailPlaceholder,
  showCyclingPlaceholder,
  showGreenPlaceholder,
  showStepOverlay,
  removeStepOverlay,
  showImageOverlay,
  removeImagePanel,
} from "./map.js";

// enterInteractiveTool is intentionally absent from TRANSITION_FNS —
// it is only triggered by the "Explore the map" button, never by scroll position.
const TRANSITION_FNS = {
  showOverview,
  showCatchmentRing,
  showBenefitCurves,
  showScoredNetwork,
  showGapAnalysis,
  showRailPlaceholder,
  showCyclingPlaceholder,
  showGreenPlaceholder,
};

let _scroller = null;
let _activeTabId = "bus";

// ── Build scroll sections from a steps array ─────────────────────────────────

export function buildSteps(steps) {
  const container = document.querySelector(".scroll-container");
  container.innerHTML = "";
  steps.forEach((step, i) => {
    const isLast = i === steps.length - 1;
    const div = document.createElement("div");
    div.className = "step";
    div.dataset.step = i;
    div.innerHTML = `
      <div class="step-inner">
        ${step.tag ? `<span class="step-tag">${step.tag}</span>` : ""}
        <h2>${step.title}</h2>
        <div class="step-body">${step.body}</div>
        ${isLast ? '<button class="cta-explore" id="btn-enter-tool">Explore the map →</button>' : ""}
      </div>`;
    container.appendChild(div);
  });
}


// ── Initialise (or re-initialise) Scrollama ──────────────────────────────────

export function initScroll(steps) {
  if (_scroller) {
    _scroller.destroy();
    _scroller = null;
  }

  _scroller = scrollama();
  const lastIndex = steps.length - 1;

  _scroller
    .setup({
      step: ".step",
      offset: 0.5,
      debug: false,
    })
    .onStepEnter(({ element, index }) => {
      document.querySelectorAll(".step").forEach((el) => el.classList.remove("active"));
      element.classList.add("active");

      if (index === lastIndex) {
        // Lock at the point where the card bottom reaches the viewport bottom,
        // so the user can read the full card and reach the CTA before being locked.
        const cardBottom = element.getBoundingClientRect().bottom + window.scrollY;
        const lockY = Math.max(window.scrollY, cardBottom - window.innerHeight);
        enableScrollLock(lockY);
      }

      const fnName = steps[index].mapFn;
      const fn = TRANSITION_FNS[fnName];
      if (fn) fn();

      const step = steps[index];
      if (step.images) {
        showImageOverlay(step.images);
        removeStepOverlay();
      } else if (step.svg) {
        showStepOverlay(step.svg, step.svgFullscreen || false);
        removeImagePanel();
      } else {
        removeStepOverlay();
        removeImagePanel();
      }
    })
    .onStepExit(({ index, direction }) => {
      if (index === lastIndex && direction === "up") {
        disableScrollLock();
      }
    });

  window.addEventListener("resize", _scroller.resize);
}

// ── Tab switching ─────────────────────────────────────────────────────────────

export function switchTab(tabId) {
  const isInteractive = document.body.classList.contains("is-interactive");

  if (tabId === _activeTabId) {
    // Clicking the active tab while in interactive mode returns to chapter 1
    if (isInteractive) {
      backToNarrative();
      window.scrollTo({ top: 0, behavior: "instant" });
    }
    return;
  }

  // Exit interactive mode if currently active
  if (isInteractive) {
    backToNarrative();
  }

  disableScrollLock();
  _activeTabId = tabId;

  // Update tab button states
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabId);
  });

  // Find and load the tab's steps
  const tab = TABS.find((t) => t.id === tabId);
  if (!tab) return;

  buildSteps(tab.steps);
  initScroll(tab.steps);
  window.scrollTo({ top: 0, behavior: "instant" });

  // Re-wire the CTA button (injected fresh by buildSteps)
  const enterBtn = document.getElementById("btn-enter-tool");
  if (enterBtn) {
    const isBus = tab.id === "bus";
    const toolFn = isBus ? enterInteractiveTool : enterInteractiveToolBasemap;
    enterBtn.addEventListener("click", () => {
      toolFn();
      if (isBus) {
        // Init scatter once stop features are fetched (may already be ready)
        const tryInit = () => {
          const features = getStopFeatures();
          if (features) { initScatter(features); }
          else { setTimeout(tryInit, 200); }
        };
        tryInit();
      }
    });
  }
}

// ── Initialise tab nav ────────────────────────────────────────────────────────

export function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

// ── Interactive tool panel wiring ────────────────────────────────────────────

export function initToolPanel() {
  // Per-category ⓘ info popup toggles (floating overlay + backdrop)
  const backdrop = document.getElementById("modal-backdrop");

  function closeAllPopups() {
    document.querySelectorAll(".info-popup").forEach((p) => p.classList.add("hidden"));
    if (backdrop) backdrop.classList.add("hidden");
  }

  document.querySelectorAll(".btn-icon[data-info]").forEach((btn) => {
    const popup = document.getElementById(`info-popup-${btn.dataset.info}`);
    if (!popup) return;
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isHidden = popup.classList.contains("hidden");
      closeAllPopups();
      if (isHidden) {
        const btnRect  = btn.getBoundingClientRect();
        const top      = Math.min(btnRect.top, window.innerHeight - 40);
        const inChartPanel  = !!btn.closest("#chart-panel");
        const inFloatToggle = !!btn.closest("#mode-toggle-float");
        if (inFloatToggle) {
          // Anchor below the toggle, horizontally centred
          const popupW = 288;
          const floatRect = document.getElementById("mode-toggle-float").getBoundingClientRect();
          popup.style.left = `${Math.max(4, floatRect.left + (floatRect.width - popupW) / 2)}px`;
          popup.style.top  = `${btnRect.bottom + 8}px`;
        } else if (inChartPanel) {
          // Position popup to the LEFT of the button (right panel buttons)
          const popupW = 288;
          popup.style.left = `${Math.max(4, btnRect.left - popupW - 8)}px`;
        } else {
          // Position popup to the RIGHT of the tool panel (left panel buttons)
          const panelRect = document.getElementById("tool-panel").getBoundingClientRect();
          popup.style.left = `${panelRect.right + 8}px`;
        }
        popup.style.top = inFloatToggle ? popup.style.top : `${top}px`;
        popup.classList.remove("hidden");
        if (backdrop) backdrop.classList.remove("hidden");
      }
    });
  });

  if (backdrop) backdrop.addEventListener("click", closeAllPopups);

  // Group toggle buttons
  document.querySelectorAll(".group-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".group-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      setActiveGroup(btn.dataset.group);
      updateScatterGroup(btn.dataset.group);
    });
  });

  // Show stops toggle
  const stopsChk = document.getElementById("toggle-stops");
  if (stopsChk) {
    stopsChk.addEventListener("change", () => toggleStops(stopsChk.checked));
  }

  // Demographics toggle
  const bldgChk = document.getElementById("toggle-demographics-bldg");
  if (bldgChk) {
    bldgChk.addEventListener("change", () => toggleDemographics(bldgChk.checked));
  }

  // Parks overlay toggle
  const parksChk = document.getElementById("toggle-parks");
  if (parksChk) {
    parksChk.addEventListener("change", () => toggleParks(parksChk.checked));
  }

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

  function _updatePeopleGreen(stopFeatures, selectedStopId, nbName) {
    if (!stopFeatures) return;
    const isBaseline = document.querySelector(".mode-btn.active")?.dataset.mode === "baseline";
    const internal = stopFeatures.filter(f => !f.properties.context);

    const sum = (col) => internal.reduce((s, f) => s + (+f.properties[col] || 0), 0);
    const avg = (col) => internal.length ? sum(col) / internal.length : 0;
    const fmtK = (n) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(Math.round(n));

    // District headline KPIs
    const popLow  = Math.round(sum("pop_wa_reach_low")  + sum("pop_el_reach_low")  + sum("pop_ch_reach_low"))  / (internal.length || 1);
    const popHigh = Math.round(sum("pop_wa_reach_high") + sum("pop_el_reach_high") + sum("pop_ch_reach_high")) / (internal.length || 1);
    const popRangeEl = document.getElementById("kpi-pop-range");
    if (popRangeEl) popRangeEl.textContent = `${fmtK(popLow)}–${fmtK(popHigh)}`;

    const greenDistEl  = document.getElementById("kpi-green-district");
    const greenLabelEl = document.getElementById("kpi-green-district-label");
    if (greenDistEl) {
      if (isBaseline) {
        greenDistEl.textContent = `${(avg("green_pct_catchment") * 100).toFixed(0)}%`;
        if (greenLabelEl) greenLabelEl.textContent = "routes through parks";
      } else {
        greenDistEl.textContent = `${avg("green_time_working_age").toFixed(1)} min`;
        if (greenLabelEl) greenLabelEl.textContent = "avg min in green (WA)";
      }
    }

    // Per-group bars
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
        greenEl.textContent = isBaseline
          ? `${(avg("green_pct_catchment") * 100).toFixed(0)}%`
          : `${avg(waField).toFixed(1)}m`;
      }
    }

    // Stop KPI row
    const stopRowEl = document.getElementById("kpi-stop-row");
    if (stopRowEl) {
      if (selectedStopId) {
        const feat = internal.find(f => f.properties.stop_id === selectedStopId);
        if (feat) {
          const p = feat.properties;
          const sPopLow  = (+p.pop_wa_reach_low  || 0) + (+p.pop_el_reach_low  || 0) + (+p.pop_ch_reach_low  || 0);
          const sPopHigh = (+p.pop_wa_reach_high || 0) + (+p.pop_el_reach_high || 0) + (+p.pop_ch_reach_high || 0);
          const stopNameEl  = document.getElementById("kpi-stop-name");
          const stopPopEl   = document.getElementById("kpi-stop-pop");
          const stopGreenEl = document.getElementById("kpi-stop-green");
          if (stopNameEl)  stopNameEl.textContent  = p.stop_name || p.stop_id;
          if (stopPopEl)   stopPopEl.textContent   = `${fmtK(sPopLow)}–${fmtK(sPopHigh)} people`;
          if (stopGreenEl) stopGreenEl.textContent = isBaseline
            ? `${(+p.green_pct_catchment * 100 || 0).toFixed(0)}% green`
            : `${(+p.green_time_working_age || 0).toFixed(1)} min green`;
          stopRowEl.classList.remove("hidden");
        }
      } else {
        stopRowEl.classList.add("hidden");
      }
    }

    // Neighbourhood comparison row
    const nbRowEl = document.getElementById("kpi-neighbourhood-row");
    if (nbRowEl) {
      if (nbName && NEIGHBOURHOOD_POP[nbName]) {
        const nb = NEIGHBOURHOOD_POP[nbName];
        const nbStops = internal.filter(f => {
          const [lng, lat] = f.geometry.coordinates;
          return neighbourhoodForPoint([lng, lat]) === nbName;
        });
        const nbAvg = (col) => nbStops.length
          ? nbStops.reduce((s, f) => s + (+f.properties[col] || 0), 0) / nbStops.length : 0;
        const nbPopLow  = nbStops.reduce((s, f) => s + (+f.properties.pop_wa_reach_low  || 0) + (+f.properties.pop_el_reach_low  || 0) + (+f.properties.pop_ch_reach_low  || 0), 0) / (nbStops.length || 1);
        const nbPopHigh = nbStops.reduce((s, f) => s + (+f.properties.pop_wa_reach_high || 0) + (+f.properties.pop_el_reach_high || 0) + (+f.properties.pop_ch_reach_high || 0), 0) / (nbStops.length || 1);

        const nbNameEl  = document.getElementById("kpi-nb-name");
        const nbPopEl   = document.getElementById("kpi-nb-pop");
        const nbGreenEl = document.getElementById("kpi-nb-green");
        if (nbNameEl)  nbNameEl.textContent  = nbName.replace("-kvarteret", "");
        if (nbPopEl)   nbPopEl.textContent   = `${fmtK(nbPopLow)}–${fmtK(nbPopHigh)} people`;
        if (nbGreenEl) nbGreenEl.textContent = isBaseline
          ? `${(nbAvg("green_pct_catchment") * 100).toFixed(0)}% green`
          : `${nbAvg("green_time_working_age").toFixed(1)} min green`;
        nbRowEl.classList.remove("hidden");

        for (const [suffix, field] of [
          ["children", "children"], ["working-age", "working_age"], ["elderly", "elderly"]
        ]) {
          const nbShare = Math.round((nb[field] / nb.total) * 100);
          const tickEl  = document.getElementById(`nb-tick-${suffix}`);
          if (tickEl) { tickEl.style.left = `${nbShare}%`; tickEl.classList.remove("hidden"); }
        }
      } else {
        nbRowEl.classList.add("hidden");
        ["children", "working-age", "elderly"].forEach(s =>
          document.getElementById(`nb-tick-${s}`)?.classList.add("hidden")
        );
      }
    }
  }

  // Cross-highlight: map stop click ↔ scatter dot click
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

  document.getElementById("kpi-stop-close")?.addEventListener("click", () => {
    setSelectedStop(null);
    highlightMapStop(null);
    highlightScatterStop(null);
    _updatePeopleGreen(getStopFeatures(), null, getActiveNeighbourhood());
  });

  // CTA button inside the last narrative step (wired initially; re-wired on tab switch)
  const enterBtn = document.getElementById("btn-enter-tool");
  if (enterBtn) {
    enterBtn.addEventListener("click", () => {
      enterInteractiveTool();
      const tryInit = () => {
        const features = getStopFeatures();
        if (features) {
          initScatter(features);
          _updatePeopleGreen(features, null, "");
        } else { setTimeout(tryInit, 200); }
      };
      tryInit();
    });
  }

  // Drag-to-resize chart panel handle
  const handle = document.getElementById("chart-resize-handle");
  if (handle) {
    let _startX, _startW;
    handle.addEventListener("mousedown", (e) => {
      _startX = e.clientX;
      _startW = parseFloat(
        getComputedStyle(document.documentElement).getPropertyValue("--chart-panel-w")
      ) || 280;
      handle.classList.add("dragging");
      const onMove = (ev) => {
        const newW = Math.max(260, Math.min(520, _startW + (_startX - ev.clientX)));
        document.documentElement.style.setProperty("--chart-panel-w", `${newW}px`);
        resizeMap();
      };
      const onUp = () => {
        handle.classList.remove("dragging");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      e.preventDefault();
    });
  }

  // Neighbourhood selector
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
}
