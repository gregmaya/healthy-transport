import { TABS } from "./config.js";
import { enableScrollLock, disableScrollLock } from "./state.js";
import { initScatter, updateScatterGroup, updateScatterMode, setScatterSelectCallback, highlightScatterStop } from "./scatter.js";
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
      // _updatePeopleGreen wired in Task 8
    });
  });

  // Green Path Access block — populate from stop features
  function _updateGreenBlock(stopFeatures, selectedStopId) {
    const pctEl   = document.getElementById("kpi-green-pct");
    const noteEl  = document.getElementById("green-context-note");
    const waEl    = document.getElementById("green-time-working-age");
    const elEl    = document.getElementById("green-time-elderly");
    const chEl    = document.getElementById("green-time-children");
    if (!pctEl) return;

    if (selectedStopId && stopFeatures) {
      const f = stopFeatures.find(f => f.properties.stop_id === selectedStopId && !f.properties.context);
      if (f) {
        const p = f.properties;
        pctEl.textContent  = p.green_pct_catchment != null ? `${(+p.green_pct_catchment * 100).toFixed(0)}%` : "—";
        if (waEl) waEl.textContent = p.green_time_working_age != null ? `${(+p.green_time_working_age).toFixed(1)} min` : "—";
        if (elEl) elEl.textContent = p.green_time_elderly     != null ? `${(+p.green_time_elderly).toFixed(1)} min`     : "—";
        if (chEl) chEl.textContent = p.green_time_children    != null ? `${(+p.green_time_children).toFixed(1)} min`    : "—";
        if (noteEl) noteEl.textContent = `Selected stop · ${p.stop_name || p.stop_id}`;
        return;
      }
    }

    // District average across internal stops
    if (!stopFeatures) return;
    const internal = stopFeatures.filter(f => !f.properties.context);
    if (!internal.length) return;
    const avg = (col) => internal.reduce((s, f) => s + (+f.properties[col] || 0), 0) / internal.length;
    pctEl.textContent  = `${(avg("green_pct_catchment") * 100).toFixed(0)}%`;
    if (waEl) waEl.textContent = `${avg("green_time_working_age").toFixed(1)} min`;
    if (elEl) elEl.textContent = `${avg("green_time_elderly").toFixed(1)} min`;
    if (chEl) chEl.textContent = `${avg("green_time_children").toFixed(1)} min`;
    if (noteEl) noteEl.textContent = `District average · ${internal.length} scored stops`;
  }

  // Cross-highlight: map stop click ↔ scatter dot click; also update green block
  setStopSelectCallback(id => {
    highlightScatterStop(id);
    _updateGreenBlock(getStopFeatures(), id);
  });
  setScatterSelectCallback(id => {
    highlightMapStop(id);
    _updateGreenBlock(getStopFeatures(), id);
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
          _updateGreenBlock(features, null);
        }
        else { setTimeout(tryInit, 200); }
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

  // Neighbourhood selector — update population stats and demographic bars
  const NEIGHBOURHOOD_DATA = {
    "":           { pop: "356k", children: 18, working_age: 74, elderly: 8 },
    "indre":      { pop:  "88k", children: 16, working_age: 76, elderly: 8 },
    "ydre":       { pop:  "95k", children: 20, working_age: 72, elderly: 8 },
    "nordvest":   { pop:  "72k", children: 17, working_age: 74, elderly: 9 },
    "utterslev":  { pop:  "54k", children: 19, working_age: 72, elderly: 9 },
    "bispebjerg": { pop:  "47k", children: 18, working_age: 73, elderly: 9 },
  };

  function _updateDemoBars(key) {
    const d = NEIGHBOURHOOD_DATA[key] || NEIGHBOURHOOD_DATA[""];
    const kpi = document.getElementById("kpi-population");
    if (kpi) kpi.textContent = d.pop;
    for (const [suffix, field] of [
      ["children", "children"], ["working-age", "working_age"], ["elderly", "elderly"]
    ]) {
      const fill = document.getElementById(`bar-${suffix}`);
      const pct  = document.getElementById(`pct-${suffix}`);
      if (fill) fill.style.width = `${d[field]}%`;
      if (pct)  pct.textContent  = `${d[field]}%`;
    }
  }

  const nSel = document.getElementById("neighbourhood-select");
  if (nSel) nSel.addEventListener("change", () => _updateDemoBars(nSel.value));
}
