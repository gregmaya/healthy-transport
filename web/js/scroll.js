import { TABS } from "./config.js";
import { enableScrollLock, disableScrollLock } from "./state.js";
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
  setScoreMode,
  showRailPlaceholder,
  showCyclingPlaceholder,
  showGreenPlaceholder,
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
        <span class="step-number">${String(i + 1).padStart(2, "0")}</span>
        <h2>${step.title}</h2>
        <p>${step.body}</p>
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
        enableScrollLock();
      }

      const fnName = steps[index].mapFn;
      const fn = TRANSITION_FNS[fnName];
      if (fn) fn();
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
  if (tabId === _activeTabId) return;

  // Exit interactive mode if currently active
  if (document.body.classList.contains("is-interactive")) {
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
    const toolFn = tab.id === "bus" ? enterInteractiveTool : enterInteractiveToolBasemap;
    enterBtn.addEventListener("click", toolFn);
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
        // Position popup to the right of the tool panel
        const panelRect = document.getElementById("tool-panel").getBoundingClientRect();
        const btnRect = btn.getBoundingClientRect();
        const top = Math.min(btnRect.top, window.innerHeight - 40); // keep on screen
        popup.style.left = `${panelRect.right + 8}px`;
        popup.style.top = `${top}px`;
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
    });
  });

  // Show stops toggle
  const stopsChk = document.getElementById("toggle-stops");
  if (stopsChk) {
    stopsChk.addEventListener("change", () => toggleStops(stopsChk.checked));
  }

  // Score mode toggle (Baseline / Contextual radio inputs)
  document.querySelectorAll("input[name='score-mode']").forEach((radio) => {
    radio.addEventListener("change", () => {
      const mode = radio.value;
      setScoreMode(mode);
      const rail = document.getElementById("scenario-rail");
      if (rail) rail.classList.toggle("hidden", mode !== "contextual");
    });
  });

  // Scenario rail (Low · Mid · High) — Contextual only
  document.querySelectorAll(".scenario-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".scenario-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      // Scenario switching wired once score columns exist in data
    });
  });

  // CTA button inside the last narrative step (wired initially; re-wired on tab switch)
  const enterBtn = document.getElementById("btn-enter-tool");
  if (enterBtn) enterBtn.addEventListener("click", enterInteractiveTool);

  // Back to narrative button (inside tool panel)
  const backBtn = document.getElementById("btn-back-narrative");
  if (backBtn) backBtn.addEventListener("click", backToNarrative);
}
