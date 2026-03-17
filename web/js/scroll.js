import { STEPS } from "./config.js";
import {
  showOverview,
  showCatchmentRing,
  showBenefitCurves,
  showScoredNetwork,
  showGapAnalysis,
  enterInteractiveTool,
  setActiveGroup,
  toggleStops,
  toggleInteriorOnly,
} from "./map.js";

const TRANSITION_FNS = {
  showOverview,
  showCatchmentRing,
  showBenefitCurves,
  showScoredNetwork,
  showGapAnalysis,
  enterInteractiveTool,
};

// ── Build scroll sections from STEPS config ──────────────────────────────────

export function buildSteps() {
  const container = document.querySelector(".scroll-container");
  STEPS.forEach((step, i) => {
    const div = document.createElement("div");
    div.className = "step";
    div.dataset.step = i;
    div.innerHTML = `
      <div class="step-inner">
        <span class="step-number">${String(i + 1).padStart(2, "0")}</span>
        <h2>${step.title}</h2>
        <p>${step.body}</p>
      </div>`;
    container.appendChild(div);
  });
}

// ── Initialise Scrollama ─────────────────────────────────────────────────────

export function initScroll() {
  const scroller = scrollama();

  scroller
    .setup({
      step: ".step",
      offset: 0.5,
      debug: false,
    })
    .onStepEnter(({ element, index }) => {
      document.querySelectorAll(".step").forEach((el) => el.classList.remove("active"));
      element.classList.add("active");

      const fnName = STEPS[index].mapFn;
      const fn = TRANSITION_FNS[fnName];
      if (fn) fn();
    });

  window.addEventListener("resize", scroller.resize);
}

// ── Interactive tool panel wiring ────────────────────────────────────────────

export function initToolPanel() {
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

  // Interior-only filter
  const interiorChk = document.getElementById("toggle-interior");
  if (interiorChk) {
    interiorChk.addEventListener("change", () => toggleInteriorOnly(interiorChk.checked));
  }
}
