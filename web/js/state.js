// Shared state — avoids circular imports between map.js and scroll.js

let _lockY = null;
let _scrollHandler = null;

export function enableScrollLock(lockY) {
  _lockY = lockY !== undefined ? lockY : window.scrollY;
  _scrollHandler = () => {
    if (_lockY !== null && window.scrollY > _lockY) {
      window.scrollTo(0, _lockY);
    }
  };
  window.addEventListener("scroll", _scrollHandler);
}

export function disableScrollLock() {
  _lockY = null;
  if (_scrollHandler) {
    window.removeEventListener("scroll", _scrollHandler);
    _scrollHandler = null;
  }
}

// Shared interactive-tool state — neighbourhood comparator and stop selection.
// Using getter/setter pattern so consumers always read the current value.

let _activeNeighbourhood = "";   // "" = All Nørrebro; otherwise neighbourhood_name string
let _selectedStop = null;         // stop_id string or null

export function getActiveNeighbourhood() { return _activeNeighbourhood; }
export function setActiveNeighbourhood(name) { _activeNeighbourhood = name || ""; }

export function getSelectedStop() { return _selectedStop; }
export function setSelectedStop(id) { _selectedStop = id ?? null; }
