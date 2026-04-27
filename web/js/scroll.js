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
  setStopSizeMode,
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
      _updatePeopleGreen(getStopFeatures(), getSelectedStop(), getActiveNeighbourhood());
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

  // Stop size radio buttons
  document.querySelectorAll("input[name='stop-size']").forEach(radio => {
    radio.addEventListener("change", () => {
      if (radio.checked) setStopSizeMode(radio.value);
    });
  });

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
    const activeGroup = document.querySelector(".group-btn.active")?.dataset.group || "aggregate";
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

    const popSource = source === "nb" && NEIGHBOURHOOD_POP[nbName] ? NEIGHBOURHOOD_POP[nbName] : DISTRICT_POP;
    const GROUP_POP_KEY = { children: "children", working_age: "working_age", elderly: "elderly", aggregate: "total" };
    const hPopVal = popSource[GROUP_POP_KEY[activeGroup]] ?? popSource.total;

    const popEl    = document.getElementById("pg-headline-pop");
    const labelEl  = document.getElementById("pg-headline-label");
    const greenEl  = document.getElementById("pg-headline-green");
    const gLabelEl = document.getElementById("pg-headline-green-label");

    if (popEl)    popEl.textContent   = hPopVal.toLocaleString("en-DK");
    const GROUP_LABEL = { children: "children", working_age: "working-age adults", elderly: "elderly residents", aggregate: "residents" };
    if (labelEl)  labelEl.textContent = source === "nb"
      ? `${GROUP_LABEL[activeGroup] || "residents"} in ${nbName.replace("-kvarteret", "")}`
      : `${GROUP_LABEL[activeGroup] || "residents"} in Nørrebro`;
    if (greenEl) {
      if (isBaseline) {
        greenEl.textContent = fmtPct(hsAvg("green_pct_catchment"));
      } else {
        const waPop = hsAvg("pop_wa_reach_mid");
        const elPop = hsAvg("pop_el_reach_mid");
        const chPop = hsAvg("pop_ch_reach_mid");
        const totalReach = waPop + elPop + chPop || 1;
        const weightedGreen = (
          waPop * hsAvg("green_time_working_age") +
          elPop * hsAvg("green_time_elderly") +
          chPop * hsAvg("green_time_children")
        ) / totalReach;
        greenEl.textContent = fmtMin(weightedGreen);
      }
    }
    if (gLabelEl) gLabelEl.textContent = isBaseline ? "routes through parks" : "avg min in green";

    // ── Stop row ─────────────────────────────────────────────────────────────
    const stopRow = document.getElementById("pg-stop-row");
    if (stopRow) {
      if (selectedStopId) {
        const feat = internal.find(f => f.properties.stop_id === selectedStopId);
        if (feat) {
          const p = feat.properties;
          const sLow  = (+p.pop_wa_reach_low  || 0) + (+p.pop_el_reach_low  || 0) + (+p.pop_ch_reach_low  || 0);
          const sHigh = (+p.pop_wa_reach_high || 0) + (+p.pop_el_reach_high || 0) + (+p.pop_ch_reach_high || 0);
          const stopPopEl = document.getElementById("pg-stop-pop");
          if (stopPopEl) stopPopEl.textContent = `${fmtK(sLow)}–${fmtK(sHigh)}`;
          const stopNameEl = document.getElementById("pg-stop-name");
          if (stopNameEl) stopNameEl.textContent = p.stop_name || p.stop_id;
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
    const districtTot = DISTRICT_POP.total;
    const nbPop = source === "nb" && NEIGHBOURHOOD_POP[nbName] ? NEIGHBOURHOOD_POP[nbName] : null;

    for (const [suffix, field, waField, lowField, highField] of [
      ["children",    "children",    "green_time_children",    "pop_ch_reach_low",  "pop_ch_reach_high"],
      ["working-age", "working_age", "green_time_working_age", "pop_wa_reach_low",  "pop_wa_reach_high"],
      ["elderly",     "elderly",     "green_time_elderly",     "pop_el_reach_low",  "pop_el_reach_high"],
    ]) {
      const srcPop   = nbPop ?? DISTRICT_POP;
      const srcTotal = srcPop.total;
      const rawCount = srcPop[field] ?? 0;
      const share    = Math.round((rawCount / srcTotal) * 100);

      const districtShare = Math.round((DISTRICT_POP[field] / districtTot) * 100);

      const avgLow  = avg(lowField);
      const avgHigh = avg(highField);
      const uncPct  = avgLow > 0 ? Math.round(((avgHigh - avgLow) / (2 * ((avgLow + avgHigh) / 2))) * 100) : 0;

      const barEl = document.getElementById(`pgbar-${suffix}`);
      if (barEl) barEl.style.width = `${share}%`;
      const pctEl = document.getElementById(`pg-pct-${suffix}`);
      if (pctEl) pctEl.textContent = `${share}%`;
      const uncEl = document.getElementById(`pg-unc-${suffix}`);
      if (uncEl) uncEl.textContent = uncPct > 0 ? `± ${uncPct}%` : "";

      const rawEl = document.getElementById(`pg-raw-${suffix}`);
      if (rawEl) rawEl.textContent = rawCount.toLocaleString("en-DK");

      const markerEl = document.getElementById(`pg-dist-marker-${suffix}`);
      if (markerEl) {
        if (nbPop) {
          markerEl.style.left = `${districtShare}%`;
          markerEl.classList.remove("hidden");
        } else {
          markerEl.classList.add("hidden");
        }
      }

      const greenValEl = document.getElementById(`pg-green-${suffix}`);
      if (greenValEl) greenValEl.textContent = isBaseline
        ? fmtPct(avg("green_pct_catchment"))
        : fmtMin(avg(waField));
      const greenSubEl = document.getElementById(`pg-greenpath-${suffix}`);
      if (greenSubEl) greenSubEl.textContent = "";
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

  document.getElementById("pg-stop-close")?.addEventListener("click", () => {
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
        const newW = Math.max(320, Math.min(520, _startW + (_startX - ev.clientX)));
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
